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
        self.assertEqual(
            ["bank", "market", "restaurant"],
            [service["id"] for service in panel.services],
        )

    def _draw_panel(self, panel):
        surface = pygame.display.get_surface()
        font = pygame.font.SysFont(None, 24)
        panel.draw(surface, font)

    def test_three_equal_buttons_are_stacked_evenly(self):
        panel = CityPanel()
        panel.open()
        self._draw_panel(panel)
        rects = [panel.button_rects[key] for key in (
            "bank", "market", "restaurant",
        )]
        self.assertEqual(3, len(rects))
        self.assertEqual(1, len({rect.size for rect in rects}))
        self.assertEqual(
            CityPanel.BUTTON_GAP, rects[1].top - rects[0].bottom,
        )
        self.assertEqual(
            CityPanel.BUTTON_GAP, rects[2].top - rects[1].bottom,
        )

    def test_bank_and_market_emit_actions(self):
        for service_id in ("bank", "market"):
            with self.subTest(service=service_id):
                panel = CityPanel()
                panel.open()
                self._draw_panel(panel)
                event = pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": panel.button_rects[service_id].center},
                )
                self.assertTrue(panel.handle_event(event))
                self.assertEqual(service_id, panel.take_action())
                self.assertTrue(panel.visible)

    def test_restaurant_only_shows_coming_soon_message(self):
        panel = CityPanel()
        panel.open()
        self._draw_panel(panel)
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": panel.button_rects["restaurant"].center},
        )
        self.assertTrue(panel.handle_event(event))
        self.assertIsNone(panel.take_action())
        self.assertEqual("Hamarosan elérhető.", panel.status_message)
        self.assertTrue(panel.visible)

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
