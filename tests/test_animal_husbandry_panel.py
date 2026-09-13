import os
from pathlib import Path
import sys
import unittest


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from screen_layout import set_screen_size
from ui import AnimalHusbandryPanel


class AnimalHusbandryPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 700))
        set_screen_size(800, 700)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_cards_use_requested_display_order(self):
        panel = AnimalHusbandryPanel()
        panel.open()

        displayed = tuple(
            animal_type for animal_type, _rect in sorted(
                panel.card_rects.items(), key=lambda item: item[1].top,
            )
        )

        self.assertEqual(displayed, ("cattle", "goat", "pig", "chicken"))

    def test_reordered_goat_card_keeps_correct_selection(self):
        panel = AnimalHusbandryPanel()
        panel.open()

        panel._handle_content_click(panel.card_rects["goat"].center)

        self.assertEqual(panel.take_selection(), "goat")
        self.assertFalse(panel.visible)


if __name__ == "__main__":
    unittest.main()
