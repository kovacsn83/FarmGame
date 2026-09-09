import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from challenge_results import ChallengeResultStore, LocalChallengeResult
from challenge_submission import ChallengeSubmissionController
from online_api import ApiResult


GAME_ID = "6ba7b810-9dad-41d1-80b4-00c04fd430c8"


class FakeApi:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def submit_ten_year_result(self, _record):
        self.calls += 1
        return self.result


class BlockingApi(FakeApi):
    def submit_ten_year_result(self, record):
        time.sleep(0.05)
        return super().submit_ten_year_result(record)


class ChallengeSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.store = ChallengeResultStore(
            Path(self.temporary_directory.name) / "results.json",
        )
        snapshot = SimpleNamespace(
            player_id="550e8400-e29b-41d4-a716-446655440000",
            player_name="Snapshot Név", game_id=GAME_ID,
            game_version="0.1.0", farm_value=12345,
            completed_at="2026-09-09T12:00:00+00:00",
        )
        self.assertTrue(self.store.save_snapshot(snapshot))

    def tearDown(self):
        self.temporary_directory.cleanup()

    def finish(self, controller):
        for _ in range(100):
            if controller.update():
                return
            time.sleep(0.005)
        self.fail("submission worker did not finish")

    def test_201_persists_submitted_rank_and_server_id(self):
        api = FakeApi(ApiResult(True, 201, {
            "result_id": 8, "rank": 3,
        }))
        controller = ChallengeSubmissionController(self.store, api)
        self.assertTrue(controller.request_for_game(GAME_ID))
        self.finish(controller)
        record = self.store.find(GAME_ID)
        self.assertEqual(record.submission_status, "submitted")
        self.assertEqual(record.game_version, "0.1.0")
        self.assertEqual(record.server_result_id, 8)
        self.assertEqual(controller.feedback.rank, 3)

    def test_409_is_treated_as_submitted(self):
        api = FakeApi(ApiResult(
            False, 409, error_code="already_submitted",
        ))
        controller = ChallengeSubmissionController(self.store, api)
        controller.request_for_game(GAME_ID)
        self.finish(controller)
        self.assertEqual(self.store.find(GAME_ID).submission_status, "submitted")
        self.assertIn("már szerepel", controller.feedback.message)

    def test_network_and_server_failures_are_retryable(self):
        for code in ("timeout", "connection_error", "server_error"):
            with self.subTest(code=code):
                api = FakeApi(ApiResult(False, 500, error_code=code))
                controller = ChallengeSubmissionController(self.store, api)
                controller.request_for_game(GAME_ID)
                self.finish(controller)
                self.assertEqual(
                    self.store.find(GAME_ID).submission_status, "failed",
                )
                self.assertTrue(controller.request_for_game(GAME_ID))
                self.finish(controller)

    def test_double_click_and_submitted_record_do_not_send_twice(self):
        api = BlockingApi(ApiResult(True, 201, {"result_id": 9}))
        controller = ChallengeSubmissionController(self.store, api)
        self.assertTrue(controller.request_for_game(GAME_ID))
        self.assertFalse(controller.request_for_game(GAME_ID))
        self.finish(controller)
        self.assertEqual(api.calls, 1)
        self.assertFalse(controller.request_for_game(GAME_ID))
        self.assertEqual(api.calls, 1)

    def test_missing_local_result_never_starts_request(self):
        api = FakeApi(ApiResult(True, 201, {}))
        controller = ChallengeSubmissionController(self.store, api)
        self.assertFalse(controller.request_for_game(
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        ))
        self.assertEqual(api.calls, 0)


if __name__ == "__main__":
    unittest.main()
