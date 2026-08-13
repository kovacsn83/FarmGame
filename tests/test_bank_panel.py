import os
from pathlib import Path
import sys
import unittest


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pygame

from bank import BankSystem
from economy import Economy
from screen_layout import set_screen_size
from ui import BankPanel


class BankPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((900, 600))
        set_screen_size(900, 600)
        cls.font = pygame.font.Font(None, 24)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_market_button_keeps_bank_panel_open(self):
        panel = BankPanel()
        panel.open(previous_time_speed=1)
        surface = pygame.Surface((900, 600))
        panel.draw(surface, self.font, BankSystem(Economy()))

        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": panel.button_rects["market"].center},
        )
        self.assertTrue(panel.handle_event(event))
        self.assertEqual(panel.take_decision(), "market")
        self.assertTrue(panel.visible)

        panel.begin_market()
        self.assertTrue(panel.market_active)
        panel.finish_market()
        self.assertFalse(panel.market_active)

    def test_buttons_follow_requested_order(self):
        panel = BankPanel()
        panel.open(previous_time_speed=1)
        panel.draw(
            pygame.Surface((900, 600)), self.font, BankSystem(Economy()),
        )
        self.assertLess(
            panel.button_rects["market"].left,
            panel.button_rects["accept"].left,
        )
        self.assertLess(
            panel.button_rects["accept"].left,
            panel.button_rects["decline"].left,
        )


if __name__ == "__main__":
    unittest.main()
