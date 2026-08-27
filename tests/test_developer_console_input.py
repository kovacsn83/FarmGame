from pathlib import Path
import sys
import unittest

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from developer_console import DeveloperConsole
from game_logger import GameLogger
from screen_layout import set_camera, set_screen_size
from world import screen_to_grid


class DeveloperConsoleInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def setUp(self):
        set_camera(None)
        set_screen_size(800, 600)
        self.console = DeveloperConsole(GameLogger(), visible=True)

    def test_left_click_inside_console_is_click_through(self):
        position = self.console.rect.center
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=position,
        )

        self.assertFalse(self.console.handle_event(event, position))

    def test_console_area_still_maps_to_game_world(self):
        position = (
            self.console.rect.left + 100,
            self.console.rect.top + 20,
        )

        row, col = screen_to_grid(*position)

        self.assertGreaterEqual(row, 0)
        self.assertGreaterEqual(col, 0)

    def test_wheel_is_consumed_only_over_visible_console(self):
        self.console._last_total_lines = 20
        self.console._last_visible_lines = 4
        wheel = pygame.event.Event(pygame.MOUSEWHEEL, y=1)

        self.assertTrue(
            self.console.handle_event(wheel, self.console.rect.center),
        )
        self.assertFalse(self.console.handle_event(wheel, (10, 10)))

    def test_hidden_console_does_not_consume_wheel(self):
        self.console.set_visible(False)
        wheel = pygame.event.Event(pygame.MOUSEWHEEL, y=1)

        self.assertFalse(self.console.handle_event(wheel, (100, 500)))

    def test_f3_toggles_once_until_key_is_released(self):
        key_down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F3)
        key_up = pygame.event.Event(pygame.KEYUP, key=pygame.K_F3)

        self.assertTrue(self.console.handle_global_shortcut(key_down))
        self.assertFalse(self.console.visible)
        self.assertTrue(self.console.handle_global_shortcut(key_down))
        self.assertFalse(self.console.visible)
        self.assertTrue(self.console.handle_global_shortcut(key_up))
        self.assertTrue(self.console.handle_global_shortcut(key_down))
        self.assertTrue(self.console.visible)


if __name__ == "__main__":
    unittest.main()
