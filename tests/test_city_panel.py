import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from screen_layout import set_screen_size
from ui import CityPanel


class CityPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))
        set_screen_size(800, 600)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_panel_has_expandable_empty_service_catalog(self):
        panel = CityPanel()
        self.assertEqual([], panel.services)
        self.assertIn("hamarosan", panel.empty_message)

    def test_escape_closes_panel_and_consumes_event(self):
        panel = CityPanel()
        panel.open()
        event = pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_ESCAPE},
        )
        self.assertTrue(panel.handle_event(event))
        self.assertFalse(panel.visible)

    def test_outside_click_closes_panel_and_is_consumed(self):
        panel = CityPanel()
        panel.open()
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (panel.rect.left - 1, panel.rect.top)},
        )
        self.assertTrue(panel.handle_event(event))
        self.assertFalse(panel.visible)

    def test_inside_click_is_consumed_without_closing(self):
        panel = CityPanel()
        panel.open()
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": panel.rect.center},
        )
        self.assertTrue(panel.handle_event(event))
        self.assertTrue(panel.visible)


if __name__ == "__main__":
    unittest.main()
