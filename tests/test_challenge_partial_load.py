import json
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from challenge import ChallengeManager, ChallengeResult
from challenge_results import ChallengeResultStore, local_result_from_snapshot
from challenge_submission import ChallengeSubmissionController
from online_api import OnlineApiClient


class PartialChallengeLoadTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "results.json"
        self.store = ChallengeResultStore(self.path)
        self.snapshots = [ChallengeResult(
            "ten_year", f"22222222-2222-4222-8222-{index:012d}", 1000 + index,
            10, 52, "0.1.2", "11111111-1111-4111-8111-111111111111",
            f"Gazda {index}", "2026-09-26T12:00:00+00:00",
        ) for index in range(1, 5)]
        self.records = [asdict(local_result_from_snapshot(item)) for item in self.snapshots]

    def write(self, records, version=2):
        self.path.write_text(json.dumps({"format_version": version, "results": records}),
                             encoding="utf-8")

    def assert_load(self, records, expected):
        self.write(records)
        before = self.path.read_bytes()
        modified = self.path.stat().st_mtime_ns
        result = self.store.load()
        self.assertEqual([asdict(item) for item in result], expected)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, modified)
        return result

    def test_all_valid_records_preserve_every_field_and_order(self):
        self.assert_load(self.records[:3], self.records[:3])

    def test_invalid_middle_record_is_skipped(self):
        self.assert_load([self.records[0], {}, self.records[2]],
                         [self.records[0], self.records[2]])

    def test_invalid_first_record_is_skipped(self):
        self.assert_load([None, self.records[1], self.records[2]], self.records[1:3])

    def test_invalid_last_record_is_skipped(self):
        self.assert_load([self.records[0], self.records[1], "bad"], self.records[:2])

    def test_multiple_invalid_records_are_isolated(self):
        self.assert_load([{}, self.records[1], [], self.records[3]],
                         [self.records[1], self.records[3]])

    def test_all_invalid_records_return_empty_list(self):
        self.assert_load([{}, None, "bad", []], [])

    def test_validation_failures_keep_valid_neighbors(self):
        missing = dict(self.records[1])
        del missing["completed_at"]
        bad = [missing, {**self.records[1], "extra": 1}]
        bad += [{**self.records[1], "farm_value": value}
                for value in ("bad", None, True, False, float("nan"),
                              float("inf"), -float("inf"), 10**400)]
        bad += [{**self.records[1], "player_name": "Gaz" + control + "da"}
                for control in ("\0", "\n", "\r", "\t")]
        bad += [{**self.records[1], "game_id": "bad-uuid"},
                {**self.records[1], "completed_at": "bad-time"},
                {**self.records[1], "submission_status": "unknown"}]
        for record in bad:
            with self.subTest(record_type=type(record).__name__):
                self.assert_load([self.records[0], record, self.records[2]],
                                 [self.records[0], self.records[2]])

    def test_negative_farm_value_remains_valid(self):
        record = {**self.records[1], "farm_value": -50000.25}
        self.assert_load([self.records[0], record], [self.records[0], record])

    def test_invalid_json_remains_file_error(self):
        self.path.write_text("{invalid-json", encoding="utf-8")
        before = self.path.read_bytes()
        self.assertIsNone(self.store.load())
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_document_structure_remains_file_error(self):
        for document in ([], None, {"format_version": 99, "results": []},
                         {"format_version": 2}, {"format_version": 2, "results": {}},
                         {"format_version": 2, "results": None}):
            with self.subTest(document=document):
                self.path.write_text(json.dumps(document), encoding="utf-8")
                before = self.path.read_bytes()
                self.assertIsNone(self.store.load())
                self.assertEqual(self.path.read_bytes(), before)

    def test_read_error_remains_file_error(self):
        self.write(self.records[:1])
        with patch("pathlib.Path.open", side_effect=PermissionError("denied")):
            self.assertIsNone(self.store.load())

    def test_skipped_record_log_has_index_and_no_identity(self):
        self.write([self.records[0], {**self.records[1], "farm_value": True}, self.records[2]])
        with patch("challenge_results.log") as log:
            self.assertEqual(len(self.store.load()), 2)
        message = log.call_args.args[0]
        self.assertIn("index 1 skipped", message)
        self.assertIn("invalid fields or values", message)
        self.assertNotIn(self.records[1]["game_id"], message)
        self.assertNotIn(self.records[1]["player_id"], message)
        self.assertNotIn(self.records[1]["player_name"], message)

    def test_duplicate_key_rejection_remains_unchanged(self):
        for duplicate in (self.records[0], {**self.records[0], "farm_value": 999999}):
            self.write([self.records[0], {}, duplicate, self.records[2]])
            before = self.path.read_bytes()
            self.assertIsNone(self.store.load())
            self.assertFalse(self.store.save_snapshot(self.snapshots[3]))
            self.assertEqual(self.path.read_bytes(), before)

    def test_partial_read_does_not_allow_destructive_followup_writes(self):
        self.write([self.records[0], {**self.records[1], "extra": 1}, self.records[2]])
        before = self.path.read_bytes()
        self.assertEqual(len(self.store.load()), 2)
        self.assertFalse(self.store.save_snapshot(self.snapshots[3]))
        self.assertFalse(self.store.update_submission(
            self.snapshots[0].game_id, 10, "submitted", server_result_id=1))
        self.assertFalse(self.store.save_snapshot(replace(self.snapshots[0], farm_value=999)))
        self.assertEqual(self.path.read_bytes(), before)

    def test_good_record_is_submittable_but_skipped_record_is_not(self):
        self.write([self.records[0], {**self.records[1], "extra": 1}, self.records[2]])
        before = self.path.read_bytes()
        response = Mock(status_code=201)
        response.json.return_value = {"rank": 1, "result_id": 1}
        request = Mock(return_value=response)
        controller = ChallengeSubmissionController(self.store, OnlineApiClient(request=request))
        self.assertFalse(controller.request_for_game(self.snapshots[1].game_id))
        request.assert_not_called()
        def immediate_thread(target, args, **kwargs):
            return SimpleNamespace(start=lambda: target(*args))
        with patch("challenge_submission.Thread", side_effect=immediate_thread):
            self.assertTrue(controller.request_for_game(self.snapshots[0].game_id))
        self.assertTrue(controller.update())
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.kwargs["json"]["game_id"], self.snapshots[0].game_id)
        # Metadata writes keep the original protection of a damaged file.
        self.assertEqual(controller.feedback.state, "failed")
        self.assertEqual(self.path.read_bytes(), before)

    def test_pending_retry_retains_snapshot_until_source_is_repaired(self):
        self.write([self.records[0], {}])
        before = self.path.read_bytes()
        manager = ChallengeManager(None, result_store=self.store)
        manager.result = self.snapshots[3]
        self.assertFalse(manager.retry_persistence())
        self.assertIs(manager.result, self.snapshots[3])
        self.assertFalse(manager.persisted)
        self.assertEqual(self.path.read_bytes(), before)
        self.write(self.records[:1])  # Explicit repair by the test, not by loading.
        self.assertTrue(manager.retry_persistence())
        self.assertIs(manager.result, self.snapshots[3])
        self.assertEqual(self.store.find(self.snapshots[3].game_id).farm_value,
                         self.snapshots[3].farm_value)

    def test_legacy_defaults_remain_read_only(self):
        record = dict(self.records[0])
        for field in ("submission_status", "submitted_at", "server_result_id"):
            del record[field]
        self.write([record, {}], version=1)
        before = self.path.read_bytes()
        self.assertEqual(asdict(self.store.load()[0]), self.records[0])
        self.assertEqual(self.path.read_bytes(), before)

    def test_unexpected_programming_errors_are_not_swallowed(self):
        self.write(self.records[:1])
        with patch("challenge_results._is_valid_result", side_effect=RuntimeError("bug")):
            with self.assertRaisesRegex(RuntimeError, "bug"):
                self.store.load()
