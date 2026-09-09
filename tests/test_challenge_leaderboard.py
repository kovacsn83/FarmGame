import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from challenge_leaderboard import ChallengeLeaderboardController
from online_api import ApiResult


def entry(rank, name="Játékos"):
    return {
        "rank": rank, "player_name": name,
        "farm_value": 500000 - rank, "game_version": "0.1.0",
    }


class FakeApi:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def get_ten_year_leaderboard(self):
        self.calls += 1
        return self.results.pop(0)


class ChallengeLeaderboardTests(unittest.TestCase):
    def finish(self, controller):
        for _ in range(100):
            if controller.update():
                return
            time.sleep(0.01)
        self.fail("leaderboard worker did not finish")

    def test_open_request_starts_in_loading_and_preserves_backend_order(self):
        expected = [entry(2, "Második"), entry(1, "Első")]
        api = FakeApi([ApiResult(True, 200, {"results": expected})])
        controller = ChallengeLeaderboardController(api)
        self.assertTrue(controller.request())
        self.assertEqual(controller.state.status, "loading")
        self.finish(controller)
        self.assertEqual(controller.state.status, "success")
        self.assertEqual(list(controller.state.entries), expected)
        self.assertEqual(api.calls, 1)

    def test_ten_three_and_empty_result_counts_are_exact(self):
        for count in (10, 3, 0):
            with self.subTest(count=count):
                controller = ChallengeLeaderboardController(FakeApi([
                    ApiResult(True, 200, {
                        "results": [entry(rank) for rank in range(1, count + 1)],
                    }),
                ]))
                controller.request()
                self.finish(controller)
                self.assertEqual(len(controller.state.entries), count)
                self.assertEqual(
                    controller.state.status, "empty" if count == 0 else "success",
                )
                if count == 0:
                    self.assertIn("Még nincs", controller.state.message)

    def test_offline_timeout_server_and_invalid_response_are_retryable(self):
        for error_code, expected in (
            ("connection_error", "internetkapcsolatot"),
            ("timeout", "időkorlátot"),
            ("server_error", "ranglistaszerver"),
            ("invalid_response", "hibás választ"),
        ):
            with self.subTest(error_code=error_code):
                api = FakeApi([
                    ApiResult(False, error_code=error_code),
                    ApiResult(True, 200, {"results": [entry(1)]}),
                ])
                controller = ChallengeLeaderboardController(api)
                controller.request()
                self.finish(controller)
                self.assertEqual(controller.state.status, "error")
                self.assertIn(expected, controller.state.message)
                self.assertTrue(controller.request())
                self.finish(controller)
                self.assertEqual(controller.state.status, "success")
                self.assertEqual(api.calls, 2)

    def test_loading_prevents_duplicate_request(self):
        class SlowApi:
            calls = 0

            def get_ten_year_leaderboard(self):
                self.calls += 1
                time.sleep(0.05)
                return ApiResult(True, 200, {"results": []})

        api = SlowApi()
        controller = ChallengeLeaderboardController(api)
        self.assertTrue(controller.request())
        self.assertFalse(controller.request())
        self.finish(controller)
        self.assertEqual(api.calls, 1)


if __name__ == "__main__":
    unittest.main()
