import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from challenge import ChallengeManager, ChallengeResult
from challenge_results import ChallengeResultStore, SubmissionStatus
from challenge_ui import ChallengeCompletionPanel


class SubmittedSnapshotConflictTests(unittest.TestCase):
    def test_conflict_is_archived_and_not_presented_after_repeated_loads(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ChallengeResultStore(Path(folder) / "results.json")
            original = ChallengeResult("ten_year", "4ff579a7-ff79-41e7-a3a0-fec62328c8fc",
                118032.14, 10, 52, "0.1.1", "player", "Norbi", "2026-09-11T07:42:33+02:00")
            self.assertTrue(store.save_snapshot(original))
            self.assertTrue(store.update_submission(original.game_id, 10, SubmissionStatus.SUBMITTED,
                submitted_at="2026-09-11T07:42:40+02:00", server_result_id=5))
            canonical = store._path().read_bytes()
            snapshot = replace(original, farm_value=119973.03, completed_at="2026-09-11T08:12:16+02:00")
            manager = ChallengeManager(None, result_store=store)
            manager.result = snapshot
            manager.status = __import__('challenge').ChallengeStatus.COMPLETED
            record = manager.to_save_record()
            panel = SimpleNamespace(_presented_snapshot=None, open_snapshot=Mock())
            for _ in range(2):
                manager.load_save_record(record, 685, original.game_id)
                self.assertTrue(manager.submitted_snapshot_conflict_preserved)
                self.assertFalse(manager.persisted)
                self.assertEqual(manager.result, snapshot)
                self.assertTrue(manager.ensure_result_safe_to_discard())
                ChallengeCompletionPanel.show_pending_after_load(panel, manager)
            panel.open_snapshot.assert_not_called()
            self.assertEqual(store._path().read_bytes(), canonical)
            archives = list(Path(folder).glob('snapshot-conflict-*.json'))
            self.assertEqual(len(archives), 1)
            self.assertEqual(ChallengeResultStore(archives[0]).load()[0].farm_value, snapshot.farm_value)

    def test_archive_failure_keeps_retry_pending(self):
        store = Mock()
        store.save_snapshot.return_value = False
        store.preserve_submitted_conflict.return_value = False
        manager = ChallengeManager(None, result_store=store)
        manager.result = object()
        self.assertFalse(manager.retry_persistence())
        self.assertFalse(manager.submitted_snapshot_conflict_preserved)
