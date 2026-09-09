import os
import sys
import unittest
from dataclasses import dataclass
from unittest.mock import patch

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from game_version import get_game_version
from online_api import (
    DEFAULT_API_BASE_URL,
    OnlineApiClient,
    get_api_base_url,
)


class FakeResponse:
    def __init__(self, status_code, data=None, invalid_json=False):
        self.status_code = status_code
        self.data = data
        self.invalid_json = invalid_json

    def json(self):
        if self.invalid_json:
            raise ValueError("bad json")
        return self.data


class RequestStub:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error:
            raise self.error
        return self.response


@dataclass(frozen=True)
class ResultRecord:
    player_id: str = "11111111-1111-4111-8111-111111111111"
    player_name: str = "Teszt Játékos"
    game_id: str = "22222222-2222-4222-8222-222222222222"
    game_version: str = "0.1.0"
    farm_value: float = 1234.5
    challenge_years: int = 10
    completed_at: str = "2026-09-09T12:00:00+00:00"
    local_only: str = "must not be sent"


class OnlineApiTests(unittest.TestCase):
    def client(self, response=None, error=None):
        request = RequestStub(response=response, error=error)
        return OnlineApiClient(request=request), request

    def test_default_and_environment_base_url(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_api_base_url(), DEFAULT_API_BASE_URL)
        with patch.dict(os.environ, {"FARMGAME_API_BASE_URL": "http://localhost:9/"}):
            self.assertEqual(get_api_base_url(), "http://localhost:9")

    def test_health_200_and_request_metadata(self):
        client, request = self.client(FakeResponse(200, {"status": "ok"}))
        result = client.check_health()
        self.assertTrue(result.success)
        args, kwargs = request.calls[0]
        self.assertEqual(args, ("GET", f"{DEFAULT_API_BASE_URL}/health"))
        self.assertEqual(kwargs["timeout"], (3.0, 5.0))
        self.assertEqual(kwargs["headers"]["User-Agent"], f"FarmGame/{get_game_version()}")

    def test_leaderboard_filters_malformed_entries(self):
        valid = {"rank": 1, "player_name": "Anna", "farm_value": 10, "game_version": "0.1.0"}
        client, _ = self.client(FakeResponse(200, {"results": [valid, {"rank": "bad"}]}))
        result = client.get_ten_year_leaderboard()
        self.assertTrue(result.success)
        self.assertEqual(result.data["results"], [valid])

    def test_submit_201_sends_only_backend_fields(self):
        client, request = self.client(FakeResponse(201, {"status": "created"}))
        result = client.submit_ten_year_result(ResultRecord())
        self.assertTrue(result.success)
        payload = request.calls[0][1]["json"]
        self.assertNotIn("local_only", payload)
        self.assertEqual(len(payload), 7)

    def test_duplicate_409_has_distinct_code(self):
        client, _ = self.client(FakeResponse(409, {
            "error": {"code": "duplicate", "message": "Already submitted."}
        }))
        result = client.submit_ten_year_result(ResultRecord())
        self.assertEqual(result.error_code, "already_submitted")
        self.assertEqual(result.error_message, "Already submitted.")

    def test_validation_and_server_errors(self):
        for status, code in ((400, "validation_error"), (422, "validation_error"), (500, "server_error")):
            with self.subTest(status=status):
                client, _ = self.client(FakeResponse(status, {"detail": "error"}))
                result = client.check_health()
                self.assertFalse(result.success)
                self.assertEqual(result.error_code, code)

    def test_timeout_connection_and_invalid_json(self):
        cases = (
            (requests.exceptions.Timeout("slow"), "timeout"),
            (requests.exceptions.ConnectionError("offline"), "connection_error"),
        )
        for error, code in cases:
            with self.subTest(code=code):
                client, _ = self.client(error=error)
                self.assertEqual(client.check_health().error_code, code)
        client, _ = self.client(FakeResponse(200, invalid_json=True))
        self.assertEqual(client.check_health().error_code, "invalid_response")

    def test_invalid_leaderboard_shape_and_submission_input(self):
        client, _ = self.client(FakeResponse(200, {"results": "bad"}))
        self.assertEqual(
            client.get_ten_year_leaderboard().error_code, "invalid_response"
        )
        self.assertEqual(
            client.submit_ten_year_result({}).error_code, "invalid_request"
        )


if __name__ == "__main__":
    unittest.main()
