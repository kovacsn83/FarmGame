import json
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from challenge import ChallengeManager, ChallengeResult, is_valid_challenge_save_record
from challenge_results import ChallengeResultStore, local_result_from_snapshot
from online_api import OnlineApiClient, _valid_leaderboard_entry
from player_profile import validate_player_name
from money_format import format_money


class ChallengeHardeningTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = ChallengeResult(
            "ten_year", "22222222-2222-4222-8222-222222222222", 1234.5,
            10, 52, "0.1.2", "11111111-1111-4111-8111-111111111111",
            "Árvíztűrő Gazda", "2026-09-26T12:00:00+00:00",
        )
        self.record = {"status": "completed", "result": asdict(self.snapshot)}
        self.local = asdict(local_result_from_snapshot(self.snapshot))
        self.entry = {"rank": 1, "player_name": self.snapshot.player_name,
                      "farm_value": 1234.5, "game_version": "0.1.2"}

    def load_local(self, record):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.json"
            document = json.dumps({"format_version": 2, "results": [record]})
            path.write_text(document, encoding="utf-8")
            result = ChallengeResultStore(path).load()
            self.assertEqual(path.read_text(encoding="utf-8"), document)
            return result

    def test_valid_snapshot_and_local_record_load(self):
        manager = ChallengeManager(None)
        manager.load_save_record(self.record, 520, self.snapshot.game_id)
        self.assertEqual(manager.result, self.snapshot)
        self.assertEqual(self.load_local(self.local)[0].farm_value, 1234.5)

    def test_extra_snapshot_field_is_controlled(self):
        self.record["result"]["unexpected"] = 1
        self.assertFalse(is_valid_challenge_save_record(self.record))
        manager = ChallengeManager(None)
        with self.assertRaises(ValueError):
            manager.load_save_record(self.record, 520, self.snapshot.game_id)
        self.assertIsNone(manager.result)

    def test_all_required_snapshot_fields_are_checked(self):
        for field in asdict(self.snapshot):
            if field == "game_id":
                continue  # Existing migration compatibility is intentional.
            with self.subTest(field=field):
                record = {"status": "completed", "result": asdict(self.snapshot)}
                del record["result"][field]
                self.assertFalse(is_valid_challenge_save_record(record))
                with self.assertRaises(ValueError):
                    ChallengeManager(None).load_save_record(record, 520)

    def test_legacy_snapshot_without_game_id_remains_loadable(self):
        del self.record["result"]["game_id"]
        manager = ChallengeManager(None)
        manager.load_save_record(self.record, 520, self.snapshot.game_id)
        self.assertEqual(manager.result, self.snapshot)

    def test_local_extra_and_missing_fields_are_controlled(self):
        self.assertIsNone(self.load_local({**self.local, "unexpected": 1}))
        for field in ("player_id", "player_name", "game_id", "game_version",
                      "farm_value", "challenge_years", "completed_at"):
            with self.subTest(field=field):
                record = dict(self.local)
                del record[field]
                self.assertIsNone(self.load_local(record))

    def test_invalid_numeric_values_are_rejected_at_all_boundaries(self):
        for value in (float("nan"), float("inf"), -float("inf"), 10**400,
                      True, False, "123", None):
            with self.subTest(value=str(value)):
                self.record["result"]["farm_value"] = value
                self.assertFalse(is_valid_challenge_save_record(self.record))
                self.assertIsNone(self.load_local({**self.local, "farm_value": value}))
                self.assertFalse(_valid_leaderboard_entry({**self.entry, "farm_value": value}))

    def test_finite_numbers_without_business_maximum(self):
        for value in (0, 1, 12.5, -1, 1e30):
            with self.subTest(value=value):
                self.record["result"]["farm_value"] = value
                self.assertTrue(is_valid_challenge_save_record(self.record))
                self.assertIsNotNone(self.load_local({**self.local, "farm_value": value}))
        self.assertFalse(_valid_leaderboard_entry({**self.entry, "farm_value": 1e30}))
        self.assertTrue(_valid_leaderboard_entry(self.entry))
        self.assertEqual(format_money(self.entry["farm_value"]), "$1 235")

    def test_control_names_rejected_at_all_boundaries(self):
        for control in ("\0", "\n", "\r", "\t"):
            for name in (control + "Gazda", "Gaz" + control + "da", "Gazda" + control):
                with self.subTest(name=repr(name)):
                    with self.assertRaises(ValueError):
                        validate_player_name(name)
                    self.record["result"]["player_name"] = name
                    self.assertFalse(is_valid_challenge_save_record(self.record))
                    self.assertIsNone(self.load_local({**self.local, "player_name": name}))
                    self.assertFalse(_valid_leaderboard_entry({**self.entry, "player_name": name}))

    def test_unicode_spaces_and_plain_text_remain_supported(self):
        for name in ("Árvíztűrő Gazda", "Gazda 🌾", "<b>Gazda</b>", "O'Gazda"):
            with self.subTest(name=name):
                self.assertEqual(validate_player_name("  " + name + "  "), name)
                self.assertIsNotNone(self.load_local({**self.local, "player_name": name}))
                self.assertTrue(_valid_leaderboard_entry({**self.entry, "player_name": name}))
        with self.assertRaises(ValueError):
            validate_player_name("x" * 25)

    def test_bad_leaderboard_rows_do_not_remove_valid_rows(self):
        invalid = [{**self.entry, "farm_value": value}
                   for value in (float("nan"), float("inf"), -float("inf"),
                                 10**400, True, "123", None, 1e30)]
        invalid += [{**self.entry, "player_name": "A" + control + "B"}
                    for control in ("\0", "\n", "\r", "\t")]
        response = Mock(status_code=200)
        response.json.return_value = {"results": [*invalid, self.entry]}
        result = OnlineApiClient(request=Mock(return_value=response)).get_ten_year_leaderboard()
        self.assertTrue(result.success)
        self.assertEqual(result.data["results"], [self.entry])
