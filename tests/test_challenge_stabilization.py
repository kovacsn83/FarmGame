import json
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pygame
import save_system
from challenge import ChallengeManager, ChallengeStatus
from challenge_results import ChallengeResultStore, local_result_from_snapshot
from challenge_submission import ChallengeSubmissionController
from challenge_ui import ChallengeCompletionPanel
from game_identity import generate_game_id
from online_api import ApiResult
from simulation import SimulationBot
from time_system import TIME_PAUSED


PROFILE = SimpleNamespace(player_id=generate_game_id(), player_name="Audit")


class ChallengeStabilizationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.store = ChallengeResultStore(self.root / "results.json")
        self.state = SimulationBot(1200).state
        self.state.game_id = generate_game_id()
        self.manager = ChallengeManager(PROFILE, result_store=self.store)
        self.state.challenge_manager = self.manager

    def complete(self):
        return self.manager.handle_week_transition(519, 520, self.state)

    def pending(self):
        with patch.object(self.store, "_write", return_value=False):
            result = self.complete()
        self.assertFalse(self.manager.persisted)
        return result

    def legacy(self, name="legacy.json", slot=False):
        path = self.root / name
        if slot:
            with patch.object(save_system, "get_saves_dir", return_value=self.root):
                self.assertTrue(save_system.save_game_to_slot(self.state, 1, "Legacy"))
            path = self.root / "save_slot_1.json"
        else:
            self.assertTrue(save_system.save_game(self.state, path))
        document = json.loads(path.read_text(encoding="utf-8"))
        data = document["game_state"] if slot else document
        data.pop("game_id")
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def test_normal_completion_is_persisted_and_paused(self):
        result = self.complete()
        self.assertTrue(self.manager.persisted)
        self.assertEqual(self.store.find(result.game_id).farm_value, result.farm_value)
        self.assertEqual(self.state.time_speed, TIME_PAUSED)

    def test_write_failure_retains_snapshot_and_pauses(self):
        result = self.pending()
        self.assertIs(self.manager.result, result)
        self.assertEqual(self.manager.status, ChallengeStatus.COMPLETED)
        self.assertFalse(self.manager.to_save_record()["persisted"])
        self.assertIsNone(self.store.find(result.game_id))
        self.assertEqual(self.state.time_speed, TIME_PAUSED)

    def test_io_exception_is_controlled(self):
        with patch.object(self.store, "save_snapshot", side_effect=PermissionError("denied")):
            result = self.complete()
        self.assertIs(self.manager.result, result)
        self.assertFalse(self.manager.persisted)
        self.assertTrue(self.manager.retry_persistence())

    def test_retry_does_not_recalculate_value_or_identity(self):
        result = self.pending()
        self.state.economy.money += 100000
        with patch.object(self.state.economy, "calculate_net_farm_value",
                          side_effect=AssertionError("must not recalculate")):
            self.assertTrue(self.manager.retry_persistence())
        self.assertIs(self.manager.result, result)
        self.assertEqual(self.store.find(result.game_id).farm_value, result.farm_value)

    def test_repeated_retry_is_idempotent(self):
        result = self.pending()
        self.assertTrue(self.manager.retry_persistence())
        self.assertTrue(self.manager.retry_persistence())
        self.assertEqual(len(self.store.load()), 1)
        self.assertEqual(self.store.load()[0].game_id, result.game_id)

    def test_conflicting_snapshot_is_not_reported_as_persisted(self):
        result = self.complete()
        altered = replace(result, farm_value=result.farm_value + 100)
        self.assertFalse(self.store.save_snapshot(altered))
        self.assertEqual(self.store.find(result.game_id).farm_value, result.farm_value)

    def test_pending_exit_without_saving_is_blocked_until_persisted(self):
        self.pending()
        with patch.object(self.store, "_write", return_value=False):
            self.assertFalse(self.manager.ensure_result_safe_to_discard())
        self.assertTrue(self.manager.ensure_result_safe_to_discard())

    def test_exit_without_challenge_is_unaffected(self):
        self.assertTrue(self.manager.ensure_result_safe_to_discard())

    def test_retry_after_uncertain_success_is_idempotent(self):
        actual_write = self.store._write
        def uncertain(results):
            self.assertTrue(actual_write(results))
            return False
        with patch.object(self.store, "_write", side_effect=uncertain):
            result = self.complete()
        self.assertFalse(self.manager.persisted)
        self.assertTrue(self.manager.retry_persistence())
        self.assertEqual(len(self.store.load()), 1)
        self.assertEqual(self.store.load()[0].game_id, result.game_id)

    def test_submit_rejects_unpersisted_runtime_result(self):
        result = self.pending()
        api = Mock()
        controller = ChallengeSubmissionController(self.store, api)
        self.assertFalse(controller.request(local_result_from_snapshot(result)))
        self.assertFalse(controller.submitting)
        api.submit_ten_year_result.assert_not_called()

    def test_submit_uses_durable_record_after_retry(self):
        result = self.pending()
        self.assertTrue(self.manager.retry_persistence())
        api = Mock()
        api.submit_ten_year_result.return_value = ApiResult(True, 201, {"result_id": 1})
        controller = ChallengeSubmissionController(self.store, api)
        with patch("challenge_submission.Thread") as thread:
            self.assertTrue(controller.request(local_result_from_snapshot(result)))
            thread.return_value.start.assert_called_once()
            worker_record = thread.call_args.kwargs["args"][1]
            self.assertEqual(worker_record, self.store.find(result.game_id))

    def test_atomic_replace_failure_preserves_final_file(self):
        self.complete()
        previous = self.store._path().read_bytes()
        self.state.game_id = generate_game_id()
        manager = ChallengeManager(PROFILE, result_store=self.store)
        with patch("challenge_results.os.replace", side_effect=OSError("disk full")):
            manager.handle_week_transition(519, 520, self.state)
        self.assertFalse(manager.persisted)
        self.assertEqual(previous, self.store._path().read_bytes())
        self.assertEqual(len(self.store.load()), 1)

    def test_pending_snapshot_survives_save_load_and_retry(self):
        result = self.pending()
        path = self.root / "pending.json"
        self.assertTrue(save_system.save_game(self.state, path))
        restored = SimulationBot(1201).state
        manager = ChallengeManager(PROFILE, result_store=self.store)
        restored.challenge_manager = manager
        with patch.object(self.store, "_write", return_value=False):
            self.assertTrue(save_system.load_game(restored, path))
        self.assertFalse(manager.persisted)
        self.assertEqual(manager.result, result)
        restored.economy.money += 123456
        self.assertTrue(manager.retry_persistence())
        self.assertEqual(self.store.find(result.game_id).farm_value, result.farm_value)

    def test_reload_rechecks_missing_local_record(self):
        self.complete()
        record = self.manager.to_save_record()
        self.store._path().unlink()
        manager = ChallengeManager(PROFILE, result_store=self.store)
        with patch.object(self.store, "_write", return_value=False):
            manager.load_save_record(record, 520, self.state.game_id)
        self.assertFalse(manager.persisted)
        self.assertTrue(manager.retry_persistence())

    def test_successful_retry_on_load_shows_normal_completion_once(self):
        self.pending()
        record = self.manager.to_save_record()
        manager = ChallengeManager(PROFILE, result_store=self.store)
        manager.load_save_record(record, 520, self.state.game_id)
        self.assertTrue(manager.persisted)
        panel = ChallengeCompletionPanel(ChallengeSubmissionController(self.store, Mock()))
        panel.show_pending_after_load(manager)
        self.assertTrue(panel.visible)
        self.assertTrue(panel.can_submit)
        panel.close()
        panel.show_pending_after_load(manager)
        self.assertFalse(panel.visible)

    def test_pending_popup_retry_never_submits(self):
        self.pending()
        api = Mock()
        controller = ChallengeSubmissionController(self.store, api)
        panel = ChallengeCompletionPanel(controller)
        panel.open_snapshot(self.manager)
        self.assertFalse(panel.can_submit)
        panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=panel.submit_rect.center))
        self.assertTrue(self.manager.persisted)
        self.assertTrue(panel.can_submit)
        api.submit_ten_year_result.assert_not_called()

    def test_same_legacy_file_keeps_id_across_sessions_without_resaving(self):
        path = self.legacy()
        self.assertTrue(save_system.load_game(self.state, path))
        identity = self.state.game_id
        restored = SimulationBot(1202).state
        self.assertTrue(save_system.load_game(restored, path))
        self.assertEqual(restored.game_id, identity)
        self.assertEqual(json.loads(path.read_text())["game_id"], identity)

    def test_two_identical_legacy_files_get_different_ids_in_same_session(self):
        first = self.legacy()
        second = self.root / "other.json"
        second.write_bytes(first.read_bytes())
        self.assertTrue(save_system.load_game(self.state, first))
        first_id = self.state.game_id
        self.assertTrue(save_system.load_game(self.state, second))
        self.assertNotEqual(self.state.game_id, first_id)
        self.assertTrue(save_system.load_game(self.state, first))
        self.assertEqual(self.state.game_id, first_id)

    def test_legacy_slot_identity_is_persisted_without_changing_metadata(self):
        path = self.legacy(slot=True)
        metadata = json.loads(path.read_text())["metadata"]
        with patch.object(save_system, "get_saves_dir", return_value=self.root):
            self.assertTrue(save_system.load_game_from_slot(self.state, 1))
            identity = self.state.game_id
            self.assertTrue(save_system.load_game_from_slot(self.state, 1))
        self.assertEqual(self.state.game_id, identity)
        self.assertEqual(json.loads(path.read_text())["metadata"], metadata)

    def test_identity_write_failure_leaves_live_game_and_file_unchanged(self):
        path = self.legacy()
        before = path.read_bytes()
        identity = self.state.game_id
        with patch.object(save_system, "_atomic_write_json", return_value=False):
            self.assertFalse(save_system.load_game(self.state, path))
        self.assertEqual(self.state.game_id, identity)
        self.assertEqual(path.read_bytes(), before)

    def test_legacy_challenge_integration_keeps_player_and_game_identity(self):
        path = self.legacy()
        self.assertTrue(save_system.load_game(self.state, path))
        identity = self.state.game_id
        result = self.complete()
        self.assertEqual(result.game_id, identity)
        self.assertEqual(result.player_id, PROFILE.player_id)
        self.assertTrue(save_system.save_game(self.state, path))
        restored = SimulationBot(1203).state
        restored.challenge_manager = ChallengeManager(PROFILE, result_store=self.store)
        self.assertTrue(save_system.load_game(restored, path))
        self.assertEqual(restored.game_id, identity)
        self.assertEqual(restored.challenge_manager.result, result)
        self.assertTrue(restored.challenge_manager.persisted)
        self.assertEqual(len(self.store.load()), 1)

    def test_current_save_is_not_rewritten_on_load(self):
        path = self.root / "current.json"
        self.assertTrue(save_system.save_game(self.state, path))
        before = path.read_bytes()
        identity = self.state.game_id
        self.assertTrue(save_system.load_game(self.state, path))
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(self.state.game_id, identity)
