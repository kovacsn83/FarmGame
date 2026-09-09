import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pygame

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import save_system
from challenge import (
    TEN_YEAR_CHALLENGE, ChallengeManager, ChallengeStatus,
    is_valid_challenge_save_record,
)
from game_version import GAME_VERSION
from notification_system import NotificationManager
from simulation import SimulationBot
from time_system import BASE_WEEK_DURATION_MS, TIME_NORMAL, TIME_PAUSED, GameTime


PROFILE = SimpleNamespace(player_id="player-test-id", player_name="Teszt Játékos")
WEEK_10_51 = 9 * 52 + 50
WEEK_10_52 = 9 * 52 + 51
WEEK_11_1 = 10 * 52


def challenge_state(seed=700):
    bot = SimulationBot(seed)
    notifications = NotificationManager(start_ticks=0)
    manager = ChallengeManager(PROFILE, notifications)
    bot.state.challenge_manager = manager
    return bot.state, manager, notifications


class TenYearChallengeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_only_exact_boundary_creates_snapshot(self):
        state, manager, _ = challenge_state()
        self.assertIsNone(manager.handle_week_transition(
            WEEK_10_51, WEEK_10_52, state))
        self.assertEqual(manager.status, ChallengeStatus.NOT_COMPLETED)
        expected = state.economy.calculate_net_farm_value(state)
        result = manager.handle_week_transition(WEEK_10_52, WEEK_11_1, state)
        self.assertEqual(result.farm_value, expected)
        self.assertEqual(manager.status, ChallengeStatus.COMPLETED)

    def test_result_contains_profile_version_and_completion_metadata(self):
        state, manager, _ = challenge_state(701)
        result = manager.handle_week_transition(WEEK_10_52, WEEK_11_1, state)
        self.assertEqual(result.challenge_type, TEN_YEAR_CHALLENGE)
        self.assertEqual(result.completed_year, 10)
        self.assertEqual(result.completed_week, 52)
        self.assertEqual(result.game_version, GAME_VERSION)
        self.assertEqual(result.player_id, PROFILE.player_id)
        self.assertEqual(result.player_name, PROFILE.player_name)
        self.assertIn("T", result.completed_at)

    def test_snapshot_is_immutable_and_later_years_do_not_retrigger(self):
        state, manager, notifications = challenge_state(702)
        original_speed = state.game_time.current_time_speed
        result = manager.handle_week_transition(WEEK_10_52, WEEK_11_1, state)
        state.economy.money += 1_000_000
        self.assertIsNone(manager.handle_week_transition(
            WEEK_11_1 + 51, WEEK_11_1 + 52, state))
        self.assertIs(manager.result, result)
        self.assertEqual(len(notifications.active_notifications), 1)
        self.assertEqual(state.game_time.current_time_speed, original_speed)

    def test_notification_uses_existing_money_formatting(self):
        state, manager, notifications = challenge_state(703)
        state.economy.money = 482_350
        manager.handle_week_transition(WEEK_10_52, WEEK_11_1, state)
        self.assertIn("10 éves Challenge teljesítve!", notifications.current_message)
        self.assertIn("$482 350", notifications.current_message)

    def test_time_update_reports_boundary_at_both_speeds_and_large_delta(self):
        for speed, real_delta in (
                (1, BASE_WEEK_DURATION_MS * 2),
                (2, BASE_WEEK_DURATION_MS)):
            with self.subTest(speed=speed):
                game_time = GameTime(current_time_speed=speed, start_ticks=0)
                game_time.elapsed_weeks = WEEK_10_51
                self.assertEqual(
                    game_time.update(real_delta), [WEEK_10_52, WEEK_11_1])

    def test_pause_resume_does_not_duplicate_transition(self):
        state, manager, _ = challenge_state(704)
        state.game_time.set_time_speed(TIME_PAUSED, current_ticks=0)
        self.assertIsNone(manager.handle_week_transition(
            WEEK_10_51, WEEK_10_52, state))
        state.game_time.set_time_speed(TIME_NORMAL, current_ticks=1000)
        first = manager.handle_week_transition(WEEK_10_52, WEEK_11_1, state)
        second = manager.handle_week_transition(WEEK_10_52, WEEK_11_1, state)
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_save_load_preserves_completed_result(self):
        state, manager, _ = challenge_state(705)
        original = manager.handle_week_transition(WEEK_10_52, WEEK_11_1, state)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "challenge.json"
            self.assertTrue(save_system.save_game(state, path))
            restored, restored_manager, restored_notifications = challenge_state(706)
            self.assertTrue(save_system.load_game(restored, path))
            self.assertEqual(restored_manager.status, ChallengeStatus.COMPLETED)
            self.assertEqual(restored_manager.result, original)
            self.assertIsNone(restored_manager.handle_week_transition(
                WEEK_10_52, WEEK_11_1, restored))
            self.assertEqual(len(restored_notifications.active_notifications), 0)

    def test_legacy_before_or_at_boundary_remains_eligible(self):
        for elapsed_week in (6 * 52, WEEK_10_52):
            with self.subTest(elapsed_week=elapsed_week):
                state, manager, _ = challenge_state(707 + elapsed_week)
                manager.load_save_record(None, elapsed_week)
                self.assertEqual(manager.status, ChallengeStatus.NOT_COMPLETED)

    def test_legacy_after_boundary_is_ineligible_and_persistent(self):
        state, manager, _ = challenge_state(709)
        manager.load_save_record(None, WEEK_11_1)
        self.assertEqual(manager.status, ChallengeStatus.LEGACY_INELIGIBLE)
        record = manager.to_save_record()
        restored = ChallengeManager(PROFILE)
        restored.load_save_record(record, WEEK_11_1 + 100)
        self.assertEqual(restored.status, ChallengeStatus.LEGACY_INELIGIBLE)
        self.assertIsNone(restored.handle_week_transition(
            WEEK_10_52, WEEK_11_1, state))

    def test_challenge_save_validation_keeps_legacy_optional(self):
        self.assertTrue(is_valid_challenge_save_record(None))
        self.assertFalse(is_valid_challenge_save_record({"status": "broken"}))

    def test_slot_copy_carries_the_same_challenge_result(self):
        state, manager, _ = challenge_state(710)
        manager.handle_week_transition(WEEK_10_52, WEEK_11_1, state)
        with tempfile.TemporaryDirectory() as directory, patch.object(
                save_system, "get_saves_dir", return_value=Path(directory)):
            self.assertTrue(save_system.save_game_to_slot(state, 1, "Első"))
            self.assertTrue(save_system.save_game_to_slot(state, 2, "Másolat"))
            first = json.loads((Path(directory) / "save_slot_1.json").read_text())
            second = json.loads((Path(directory) / "save_slot_2.json").read_text())
            self.assertEqual(
                first["game_state"]["ten_year_challenge"],
                second["game_state"]["ten_year_challenge"],
            )


if __name__ == "__main__":
    unittest.main()
