import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import save_system
from challenge import ChallengeManager, ChallengeStatus
from challenge_results import ChallengeResultStore, SubmissionStatus
from game_identity import generate_game_id
from game_version import GAME_VERSION
from simulation import SimulationBot


PROFILE = SimpleNamespace(
    player_id="player-local-result-id", player_name="Helyi Játékos",
)
WEEK_10_52 = 9 * 52 + 51
WEEK_11_1 = 10 * 52


class ChallengeResultStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "challenge" / "results.json"
        self.store = ChallengeResultStore(self.path)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def make_state(self, seed=800):
        state = SimulationBot(seed).state
        state.game_id = generate_game_id()
        state.challenge_manager = ChallengeManager(
            PROFILE, result_store=self.store,
        )
        return state

    def complete(self, state):
        return state.challenge_manager.handle_week_transition(
            WEEK_10_52, WEEK_11_1, state,
        )

    def test_boundary_persists_standard_record_from_snapshot(self):
        state = self.make_state()
        snapshot_value = state.economy.calculate_net_farm_value(state)
        snapshot = self.complete(state)
        record = self.store.find(state.game_id)

        self.assertEqual(record.player_id, PROFILE.player_id)
        self.assertEqual(record.player_name, PROFILE.player_name)
        self.assertEqual(record.game_id, state.game_id)
        self.assertEqual(record.game_version, GAME_VERSION)
        self.assertEqual(record.farm_value, snapshot_value)
        self.assertEqual(record.farm_value, snapshot.farm_value)
        self.assertEqual(record.challenge_years, 10)
        self.assertIn("T", record.completed_at)
        self.assertEqual(
            record.submission_status, SubmissionStatus.NOT_SUBMITTED.value,
        )
        self.assertEqual(self.path.parent, Path(self.temporary_directory.name) / "challenge")

    def test_later_value_changes_do_not_modify_the_result(self):
        state = self.make_state(801)
        snapshot = self.complete(state)
        state.economy.money += 5_000_000
        state.challenge_manager.handle_week_transition(
            WEEK_11_1 + 51, WEEK_11_1 + 52, state,
        )
        self.assertEqual(self.store.find(state.game_id).farm_value, snapshot.farm_value)

    def test_multiple_games_remain_and_same_key_is_idempotent(self):
        first = self.make_state(802)
        second = self.make_state(803)
        first_snapshot = self.complete(first)
        self.assertTrue(self.store.save_snapshot(first_snapshot))
        self.complete(second)
        records = self.store.load()
        self.assertEqual(len(records), 2)
        self.assertEqual({item.game_id for item in records}, {
            first.game_id, second.game_id,
        })

    def test_save_load_backfills_once_from_trusted_snapshot(self):
        state = self.make_state(804)
        snapshot = self.complete(state)
        self.path.unlink()
        save_path = Path(self.temporary_directory.name) / "save.json"
        self.assertTrue(save_system.save_game(state, save_path))

        restored = self.make_state(805)
        self.assertTrue(save_system.load_game(restored, save_path))
        self.assertEqual(restored.challenge_manager.status, ChallengeStatus.COMPLETED)
        self.assertEqual(self.store.find(state.game_id).farm_value, snapshot.farm_value)
        self.assertTrue(save_system.load_game(restored, save_path))
        self.assertEqual(len(self.store.load()), 1)

    def test_ineligible_or_missing_snapshot_never_creates_result(self):
        state = self.make_state(806)
        state.challenge_manager.load_save_record(None, WEEK_11_1, state.game_id)
        self.assertEqual(
            state.challenge_manager.status, ChallengeStatus.LEGACY_INELIGIBLE,
        )
        self.assertFalse(self.path.exists())
        self.assertIsNone(state.challenge_manager.handle_week_transition(
            WEEK_10_52, WEEK_11_1, state,
        ))
        self.assertFalse(self.path.exists())

    def test_corrupt_file_and_write_failure_do_not_escape(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not-json", encoding="utf-8")
        state = self.make_state(807)
        self.assertIsNotNone(self.complete(state))
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{not-json")

        self.path.unlink()
        snapshot = state.challenge_manager.result
        with patch("challenge_results.os.replace", side_effect=OSError("disk")):
            self.assertFalse(self.store.save_snapshot(snapshot))
        self.assertFalse(self.path.exists())

    def test_document_is_upload_ready_json_in_user_data_shape(self):
        state = self.make_state(808)
        self.complete(state)
        document = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(document["format_version"], 2)
        self.assertEqual(set(document["results"][0]), {
            "player_id", "player_name", "game_id", "game_version",
            "farm_value", "challenge_years", "completed_at",
            "submission_status", "submitted_at", "server_result_id",
        })

    def test_submission_status_is_persistent_and_shared_by_game_id(self):
        state = self.make_state(809)
        self.complete(state)
        self.assertTrue(self.store.update_submission(
            state.game_id, 10, SubmissionStatus.SUBMITTED,
            submitted_at="2026-09-09T12:30:00+00:00",
            server_result_id=42,
        ))
        record = self.store.find(state.game_id)
        self.assertEqual(record.submission_status, "submitted")
        self.assertEqual(record.server_result_id, 42)

        second_store = ChallengeResultStore(self.path)
        self.assertEqual(
            second_store.find(state.game_id).submission_status, "submitted",
        )

    def test_legacy_v1_document_migrates_submission_defaults(self):
        state = self.make_state(810)
        self.complete(state)
        document = json.loads(self.path.read_text(encoding="utf-8"))
        document["format_version"] = 1
        for key in ("submission_status", "submitted_at", "server_result_id"):
            document["results"][0].pop(key)
        self.path.write_text(json.dumps(document), encoding="utf-8")
        record = self.store.find(state.game_id)
        self.assertEqual(record.submission_status, "not_submitted")
        self.assertIsNone(record.submitted_at)


if __name__ == "__main__":
    unittest.main()
