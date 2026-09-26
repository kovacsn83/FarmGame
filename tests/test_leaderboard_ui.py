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

from challenge_leaderboard import LeaderboardState
from leaderboard_ui import ChallengeLeaderboardPanel
from screen_layout import set_screen_size


class ControllerStub:
    def __init__(self, state=None):
        self.state = state or LeaderboardState()
        self.loading = False
        self.requests = 0

    def request(self):
        if self.loading:
            return False
        self.requests += 1
        self.loading = True
        self.state = LeaderboardState("loading", (), "Ranglista betöltése...")
        return True


class LeaderboardPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        set_screen_size(1000, 700)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_open_starts_exactly_one_request_and_shows_loading(self):
        controller = ControllerStub()
        panel = ChallengeLeaderboardPanel(controller)
        panel.open()
        self.assertTrue(panel.visible)
        self.assertEqual(controller.requests, 1)
        self.assertEqual(controller.state.status, "loading")

    def test_refresh_and_retry_use_the_same_request_action(self):
        for status in ("success", "empty", "error"):
            controller = ControllerStub(LeaderboardState(status))
            panel = ChallengeLeaderboardPanel(controller)
            panel.visible = True
            panel.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=panel.action_rect.center,
            ))
            self.assertEqual(controller.requests, 1)

    def test_escape_close_and_outside_click_are_modal(self):
        controller = ControllerStub()
        panel = ChallengeLeaderboardPanel(controller)
        panel.visible = True
        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE,
        )))
        self.assertFalse(panel.visible)
        panel.visible = True
        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=(panel.rect.left - 1, panel.rect.top),
        )))
        self.assertFalse(panel.visible)

    def test_draw_uses_shared_money_formatter_and_handles_long_name(self):
        entries = tuple({
            "rank": rank,
            "player_name": "HuszonnégyKarakteresNévXX",
            "farm_value": 482350 + rank,
            "game_version": "0.1.0",
        } for rank in range(1, 11))
        controller = ControllerStub(LeaderboardState("success", entries))
        panel = ChallengeLeaderboardPanel(controller)
        panel.visible = True
        surface = pygame.Surface((1000, 700))
        with patch("leaderboard_ui.format_money", side_effect=lambda value: f"${value}") as money:
            panel.draw(surface, pygame.font.SysFont(None, 24))
        self.assertEqual(money.call_count, 10)
        self.assertTrue(surface.get_bounding_rect().width)

    def test_small_window_keeps_panel_inside_screen(self):
        set_screen_size(430, 480)
        controller = ControllerStub(LeaderboardState("empty", (), "Még nincs"))
        panel = ChallengeLeaderboardPanel(controller)
        panel.visible = True
        panel.draw(pygame.Surface((430, 480)), pygame.font.SysFont(None, 20))
        self.assertGreaterEqual(panel.rect.left, 0)
        self.assertGreaterEqual(panel.rect.top, 0)
        self.assertLessEqual(panel.rect.right, 430)
        self.assertLessEqual(panel.rect.bottom, 480)
        set_screen_size(1000, 700)

    def tied_panel(self):
        entries = tuple({
            "rank": index + 1 if index < 9 else 10,
            "player_name": f"Gazda {index + 1}",
            "farm_value": 100 - index if index < 9 else -500,
            "game_version": "0.1.2",
        } for index in range(12))
        panel = ChallengeLeaderboardPanel(ControllerStub(LeaderboardState("success", entries)))
        panel.visible = True
        return panel

    def test_all_twelve_results_are_accessible_and_server_ranks_are_preserved(self):
        panel = self.tied_panel()
        surface = pygame.Surface((1000, 700))
        font = pygame.font.SysFont(None, 24)
        with patch.object(panel, "_text", wraps=panel._text) as text:
            panel.draw(surface, font)
            self.assertTrue(panel.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-2)))
            panel.draw(surface, font)
        labels = [call.args[2] for call in text.call_args_list]
        for index in range(1, 13):
            self.assertIn(f"Gazda {index}", labels)
        self.assertIn("-$500", labels)
        self.assertNotIn("11.", labels)
        self.assertNotIn("12.", labels)
        self.assertGreaterEqual(labels.count("10."), 3)
        self.assertIn("3–12 / 12", labels)

    def test_modern_and_legacy_wheels_are_modal_and_clamped(self):
        panel = self.tied_panel()
        self.assertTrue(panel.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-100)))
        self.assertEqual(panel.scroll_row, 2)
        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=4, pos=panel.rect.center)))
        self.assertEqual(panel.scroll_row, 1)
        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=5, pos=panel.rect.center)))
        self.assertEqual(panel.scroll_row, 2)
        panel.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=100))
        self.assertEqual(panel.scroll_row, 0)
        self.assertTrue(panel.visible)
        self.assertEqual(panel.controller.requests, 0)

    def test_tied_results_scroll_in_small_window_without_covering_buttons(self):
        set_screen_size(430, 480)
        self.addCleanup(set_screen_size, 1000, 700)
        panel = self.tied_panel()
        panel.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-100))
        panel.draw(pygame.Surface((430, 480)), pygame.font.SysFont(None, 20))
        table, height = panel._table_layout()
        self.assertLessEqual(table.bottom + 24, panel.action_rect.top)
        self.assertEqual(panel.scroll_row, 2)
        panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=panel.close_rect.center))
        self.assertFalse(panel.visible)

    def test_medal_backgrounds_follow_rank_not_row_index(self):
        panel = self.tied_panel()
        panel.controller.state.entries[0]["rank"] = 1
        panel.controller.state.entries[1]["rank"] = 1
        panel.controller.state.entries[2]["rank"] = 1
        with patch("leaderboard_ui.pygame.draw.rect", wraps=pygame.draw.rect) as draw_rect:
            panel.draw(pygame.Surface((1000, 700)), pygame.font.SysFont(None, 24))
        from leaderboard_ui import TOP_ROW_BACKGROUNDS
        colors = [call.args[1] for call in draw_rect.call_args_list]
        self.assertEqual(colors.count(TOP_ROW_BACKGROUNDS[0]), 3)


if __name__ == "__main__":
    unittest.main()
