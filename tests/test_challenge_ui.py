import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pygame

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from challenge_results import ChallengeResultStore
from challenge_submission import ChallengeSubmissionController
from challenge_ui import ChallengeCompletionPanel
from online_api import ApiResult
from screen_layout import set_screen_size


GAME_ID = "6ba7b810-9dad-41d1-80b4-00c04fd430c8"


class NoopApi:
    def submit_ten_year_result(self, _record):
        return ApiResult(False, error_code="connection_error")


class ChallengeCompletionPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        set_screen_size(1000, 700)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        store = ChallengeResultStore(
            Path(self.temporary_directory.name) / "results.json",
        )
        self.assertTrue(store.save_snapshot(SimpleNamespace(
            player_id="550e8400-e29b-41d4-a716-446655440000",
            player_name="Snapshot Név", game_id=GAME_ID,
            game_version="0.1.0", farm_value=12345,
            completed_at="2026-09-09T12:00:00+00:00",
        )))
        self.controller = ChallengeSubmissionController(store, NoopApi())
        self.panel = ChallengeCompletionPanel(self.controller)
        self.panel.open(store.find(GAME_ID))

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_outside_click_is_consumed_without_closing(self):
        handled = self.panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=(self.panel.rect.left - 2, self.panel.rect.top),
        ))
        self.assertTrue(handled)
        self.assertTrue(self.panel.visible)

    def test_later_and_escape_close_without_deleting_result(self):
        self.panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=self.panel.close_rect.center,
        ))
        self.assertFalse(self.panel.visible)
        self.assertIsNotNone(self.controller.get_record(GAME_ID))
        self.panel.open(self.controller.get_record(GAME_ID))
        self.panel.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE,
        ))
        self.assertFalse(self.panel.visible)

    def test_submit_click_starts_only_one_background_request(self):
        self.panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=self.panel.submit_rect.center,
        ))
        self.assertTrue(self.controller.submitting)
        self.assertFalse(self.controller.request_for_game(GAME_ID))

    def test_leaderboard_button_closes_and_emits_one_request(self):
        handled = self.panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=self.panel.leaderboard_rect.center,
        ))
        self.assertTrue(handled)
        self.assertFalse(self.panel.visible)
        self.assertTrue(self.panel.take_leaderboard_request())
        self.assertFalse(self.panel.take_leaderboard_request())

    def test_submitted_button_label_contains_no_unsupported_checkmark(self):
        self.controller.result_store.update_submission(
            GAME_ID, 10, "submitted",
            submitted_at="2026-09-11T08:00:00+00:00",
            server_result_id=7,
        )
        surface = pygame.Surface((1000, 700))
        font = pygame.font.SysFont(None, 24)
        labels = []
        original_button = self.panel._button

        def capture_button(screen, used_font, rect, label, enabled=True):
            labels.append(label)
            return original_button(screen, used_font, rect, label, enabled)

        self.panel._button = capture_button
        self.panel.draw(surface, font)
        self.assertIn("Beküldve", labels)
        self.assertNotIn("✓", "".join(labels))

    def test_three_buttons_fit_inside_small_panel(self):
        set_screen_size(420, 440)
        self.panel._update_layout()
        for rect in (
            self.panel.submit_rect,
            self.panel.leaderboard_rect,
            self.panel.close_rect,
        ):
            self.assertTrue(self.panel.rect.contains(rect))
        self.assertLess(self.panel.submit_rect.right, self.panel.leaderboard_rect.left)
        self.assertLess(self.panel.leaderboard_rect.right, self.panel.close_rect.left)
        set_screen_size(1000, 700)

    def test_draw_works_at_supported_small_layout(self):
        set_screen_size(420, 440)
        surface = pygame.Surface((420, 440))
        self.panel.draw(surface, pygame.font.SysFont(None, 24))
        self.assertTrue(surface.get_bounding_rect().width)
        set_screen_size(1000, 700)


if __name__ == "__main__":
    unittest.main()
