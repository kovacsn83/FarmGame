import sys
import unittest
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from exit_ui import ExitConfirmationPanel
from screen_layout import set_screen_size


class ExitConfirmationPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        set_screen_size(1000, 700)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.panel = ExitConfirmationPanel()
        self.assertTrue(self.panel.open(previous_time_speed=2))

    def _click(self, rect, button=1):
        return self.panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=button, pos=rect.center,
        ))

    def test_three_buttons_emit_the_expected_actions(self):
        for rect_name, action in (
            ("save_exit_rect", "save_and_exit"),
            ("discard_rect", "discard"),
            ("cancel_rect", "cancel"),
        ):
            with self.subTest(action=action):
                self.panel.pending_action = None
                self.assertTrue(self._click(getattr(self.panel, rect_name)))
                self.assertEqual(self.panel.take_action(), action)
                self.assertIsNone(self.panel.take_action())

    def test_escape_means_cancel_and_quit_does_not_bypass_popup(self):
        self.assertTrue(self.panel.handle_event(pygame.event.Event(pygame.QUIT)))
        self.assertIsNone(self.panel.take_action())
        self.assertTrue(self.panel.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE,
        )))
        self.assertEqual(self.panel.take_action(), "cancel")

    def test_non_left_and_outside_clicks_are_consumed_without_action(self):
        self.assertTrue(self._click(self.panel.discard_rect, button=3))
        self.assertIsNone(self.panel.take_action())
        self.assertTrue(self.panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=(self.panel.rect.left - 1, self.panel.rect.top),
        )))
        self.assertIsNone(self.panel.take_action())

    def test_second_open_cannot_create_another_flow(self):
        self.assertFalse(self.panel.open(previous_time_speed=1))
        self.assertEqual(self.panel.previous_time_speed, 2)

    def test_small_layout_keeps_all_buttons_inside(self):
        set_screen_size(420, 320)
        self.panel._update_layout()
        for rect in (
            self.panel.save_exit_rect,
            self.panel.discard_rect,
            self.panel.cancel_rect,
        ):
            self.assertTrue(self.panel.rect.contains(rect))
        set_screen_size(1000, 700)

    def test_panel_draws_with_shared_popup_style(self):
        surface = pygame.Surface((1000, 700))
        self.panel.draw(surface, pygame.font.SysFont(None, 24))
        self.assertTrue(surface.get_bounding_rect().width)


if __name__ == "__main__":
    unittest.main()
