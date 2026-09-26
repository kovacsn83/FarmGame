import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from online_api import OnlineApiClient, _parse_response_farm_value
from challenge_results import LocalChallengeResult
from money_format import format_money


class OnlineDecimalValueTests(unittest.TestCase):
    def client(self, status, data):
        response = Mock(status_code=status)
        response.json.return_value = data
        request = Mock(return_value=response)
        return OnlineApiClient(request=request), request

    def record(self):
        return LocalChallengeResult(
            "11111111-1111-4111-8111-111111111111", "Gazda",
            "22222222-2222-4222-8222-222222222222", "0.1.2", -1234.56,
            10, "2026-09-26T12:00:00+00:00")

    def test_decimal_text_preserves_cents_and_negative_storage_bounds(self):
        for text in ("1234.56", "0.00", "-50000.25",
                     "9999999999999999999999.99", "-9999999999999999999999.99"):
            with self.subTest(value=text):
                result = _parse_response_farm_value(text)
                self.assertIsInstance(result, Decimal)
                self.assertEqual(result, Decimal(text))
                self.assertIsInstance(format_money(result), str)

    def test_legacy_numeric_responses_remain_supported(self):
        for value in (0, 100, 1234.56, -1234.56):
            with self.subTest(value=value):
                self.assertEqual(_parse_response_farm_value(value), Decimal(str(value)))

    def test_invalid_decimal_values_are_rejected(self):
        for value in (True, False, None, {}, [], float("nan"), float("inf"),
                      -float("inf"), 10**400, "NaN", "Infinity", "-Infinity",
                      "bad", "123", "1e2", "1.234", "1.00\n", "1_000.00",
                      "9" * 400 + ".00"):
            with self.subTest(value=str(value)):
                self.assertIsNone(_parse_response_farm_value(value))

    def test_leaderboard_normalizes_old_and_new_values_without_changing_ranks(self):
        entries = [{"rank": 10, "player_name": "Gazda", "farm_value": value,
                    "game_version": "0.1.2"}
                   for value in ("-1234.56", "9999999999999999999999.99", 0, -12.5, "NaN")]
        client, request = self.client(200, {"results": entries})
        result = client.get_ten_year_leaderboard()
        self.assertTrue(result.success)
        self.assertEqual(len(result.data["results"]), 4)
        self.assertEqual([row["rank"] for row in result.data["results"]], [10] * 4)
        self.assertEqual([row["farm_value"] for row in result.data["results"]],
                         [Decimal("-1234.56"), Decimal("9999999999999999999999.99"),
                          Decimal(0), Decimal("-12.5")])
        self.assertEqual(entries[0]["farm_value"], "-1234.56")

    def test_submission_response_is_exact_but_request_and_snapshot_are_unchanged(self):
        for value in ("-1234.56", "9999999999999999999999.99", -1234.56):
            with self.subTest(value=value):
                client, request = self.client(201, {"rank": 10, "result_id": 1, "farm_value": value})
                record = self.record()
                result = client.submit_ten_year_result(record)
                self.assertTrue(result.success)
                self.assertEqual(result.data["farm_value"], Decimal(str(value)))
                self.assertEqual(result.data["rank"], 10)
                self.assertIsInstance(request.call_args.kwargs["json"]["farm_value"], float)
                self.assertEqual(record.farm_value, -1234.56)

    def test_invalid_submission_score_returns_controlled_error(self):
        client, request = self.client(201, {"result_id": 1, "rank": 1, "farm_value": "NaN"})
        result = client.submit_ten_year_result(self.record())
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "invalid_response")
