import sys
import unittest
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from game_version import (
    GAME_VERSION, RELEASE_STAGE, get_full_version_display,
    get_game_version, get_game_version_tuple, get_version_display,
)
from screen_layout import set_screen_size
from startup_ui import MainMenu


class GameVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_central_version_api(self):
        self.assertEqual(GAME_VERSION, "0.1.1")
        self.assertEqual(RELEASE_STAGE, "Alpha")
        self.assertEqual(get_game_version(), "0.1.1")
        self.assertEqual(get_game_version_tuple(), (0, 1, 1))
        self.assertEqual(get_version_display(), "Alpha v0.1.1")
        self.assertEqual(get_full_version_display(), "FarmGame Alpha v0.1.1")

    def test_main_menu_uses_the_central_display_value(self):
        set_screen_size(800, 600)
        menu = MainMenu()
        self.assertEqual(menu.version_display, get_version_display())
        screen = pygame.Surface((800, 600))
        menu.draw(screen, pygame.font.SysFont(None, 24))


if __name__ == "__main__":
    unittest.main()
