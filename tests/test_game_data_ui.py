import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pygame

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from challenge import ChallengeResult, ChallengeStatus
from clipboard_utils import copy_text_to_clipboard
from game_data_ui import GameDataPanel
from game_version import get_game_version
from screen_layout import set_screen_size


PLAYER_ID = "550e8400-e29b-41d4-a716-446655440000"
GAME_ID = "6ba7b810-9dad-41d1-80b4-00c04fd430c8"
PROFILE = SimpleNamespace(player_id=PLAYER_ID, player_name="Árvíztűrő Norbi")


class SubmissionControllerStub:
    def __init__(self, record=None):
        self.record = record
        self.submitting = False
        self.requests = []

    def get_record(self, _game_id, _challenge_years=10):
        return self.record

    def request_for_game(self, game_id, challenge_years=10):
        self.requests.append((game_id, challenge_years))
        return True


def game_state(status=ChallengeStatus.NOT_COMPLETED, farm_value=None):
    result = None
    if status is ChallengeStatus.COMPLETED:
        result = ChallengeResult(
            challenge_type="ten_year", game_id=GAME_ID,
            farm_value=farm_value, completed_year=10, completed_week=52,
            game_version=get_game_version(), player_id=PLAYER_ID,
            player_name=PROFILE.player_name,
            completed_at="2026-09-09T12:00:00+02:00",
        )
    return SimpleNamespace(
        game_id=GAME_ID,
        challenge_manager=SimpleNamespace(status=status, result=result),
    )


class GameDataPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        set_screen_size(1000, 700)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.panel = GameDataPanel()

    def test_without_active_game_uses_profile_and_version_without_creating_id(self):
        self.panel.open(PROFILE, None)
        data = self.panel.get_display_data()
        self.assertEqual(data["player_name"], PROFILE.player_name)
        self.assertEqual(data["player_id"], PLAYER_ID)
        self.assertEqual(data["game_version"], get_game_version())
        self.assertIsNone(data["game_id"])
        self.assertEqual(data["challenge_status"], "Nincs aktív játék")

    def test_active_game_data_is_read_live_and_open_does_not_modify_id(self):
        state = game_state()
        original_id = state.game_id
        self.panel.open(PROFILE, state)
        self.assertEqual(self.panel.get_display_data()["game_id"], original_id)
        self.assertEqual(state.game_id, original_id)
        state.game_id = "67e55044-10b1-426f-9247-bb680e5fe0c8"
        self.assertEqual(self.panel.get_display_data()["game_id"], state.game_id)

    def test_completed_and_legacy_challenge_states_are_displayed(self):
        controller = SubmissionControllerStub(SimpleNamespace(
            submission_status="not_submitted",
        ))
        self.panel.open(
            PROFILE, game_state(ChallengeStatus.COMPLETED, 482350.0), controller,
        )
        data = self.panel.get_display_data()
        self.assertEqual(data["challenge_status"], "Teljesítve")
        self.assertEqual(data["farm_value"], 482350.0)
        self.assertEqual(data["submission_status"], "not_submitted")
        self.panel.open(PROFILE, game_state(ChallengeStatus.LEGACY_INELIGIBLE))
        data = self.panel.get_display_data()
        self.assertIn("korábbi mentés", data["challenge_status"])
        self.assertIsNone(data["farm_value"])

    def test_completed_result_can_be_submitted_from_game_data(self):
        controller = SubmissionControllerStub(SimpleNamespace(
            submission_status="failed",
        ))
        self.panel.open(
            PROFILE, game_state(ChallengeStatus.COMPLETED, 482350.0), controller,
        )
        self.panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=self.panel.submit_rect.center,
        ))
        self.assertEqual(controller.requests, [(GAME_ID, 10)])

    def test_submitted_result_has_no_submission_action(self):
        controller = SubmissionControllerStub(SimpleNamespace(
            submission_status="submitted",
        ))
        self.panel.open(
            PROFILE, game_state(ChallengeStatus.COMPLETED, 482350.0), controller,
        )
        self.panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=self.panel.submit_rect.center,
        ))
        self.assertEqual(controller.requests, [])

    def test_top_ten_request_is_available_without_completed_challenge(self):
        self.panel.open(PROFILE, game_state())
        self.panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=self.panel.leaderboard_rect.center,
        ))
        self.assertTrue(self.panel.take_leaderboard_request())
        self.assertFalse(self.panel.take_leaderboard_request())

    def test_copy_buttons_copy_full_identifiers_and_show_feedback(self):
        self.panel.open(PROFILE, game_state())
        with patch("game_data_ui.copy_text_to_clipboard", return_value=True) as copy:
            self.panel.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1,
                pos=self.panel.player_copy_rect.center,
            ), current_ticks=100)
            copy.assert_called_once_with(PLAYER_ID)
            self.assertGreater(self.panel.copy_feedback["player_id"], 100)
            copy.reset_mock()
            self.panel.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1,
                pos=self.panel.game_copy_rect.center,
            ), current_ticks=200)
            copy.assert_called_once_with(GAME_ID)

    def test_game_copy_is_disabled_without_active_game(self):
        self.panel.open(PROFILE, None)
        with patch("game_data_ui.copy_text_to_clipboard") as copy:
            self.panel.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1,
                pos=self.panel.game_copy_rect.center,
            ))
            copy.assert_not_called()

    def test_close_button_escape_and_outside_click_are_modal(self):
        for event_factory in (
            lambda panel: pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=panel.close_rect.center),
            lambda panel: pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
            lambda panel: pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1,
                pos=(panel.rect.left - 1, panel.rect.top)),
        ):
            with self.subTest(event=event_factory):
                self.panel.open(PROFILE, game_state())
                self.assertTrue(self.panel.handle_event(event_factory(self.panel)))
                self.assertFalse(self.panel.visible)

    def test_panel_draws_full_uuid_without_mutating_sources(self):
        state = game_state(ChallengeStatus.COMPLETED, 482350.0)
        self.panel.open(PROFILE, state)
        screen = pygame.Surface((1000, 700))
        font = pygame.font.SysFont(None, 24)
        self.panel.draw(screen, font, current_ticks=0)
        self.assertEqual(state.game_id, GAME_ID)
        self.assertEqual(PROFILE.player_id, PLAYER_ID)

    def test_clipboard_adapter_writes_full_utf8_text(self):
        with (
            patch("clipboard_utils.pygame.scrap.get_init", return_value=False),
            patch("clipboard_utils.pygame.scrap.init") as initialize,
            patch("clipboard_utils.pygame.scrap.put") as put,
        ):
            self.assertTrue(copy_text_to_clipboard(PLAYER_ID))
        initialize.assert_called_once_with()
        put.assert_called_once_with(
            pygame.SCRAP_TEXT, PLAYER_ID.encode("utf-8") + b"\0",
        )

    def test_clipboard_adapter_fails_safely(self):
        with patch(
                "clipboard_utils.pygame.scrap.get_init",
                side_effect=pygame.error("clipboard unavailable")):
            self.assertFalse(copy_text_to_clipboard(PLAYER_ID))
        self.assertFalse(copy_text_to_clipboard(""))


if __name__ == "__main__":
    unittest.main()
