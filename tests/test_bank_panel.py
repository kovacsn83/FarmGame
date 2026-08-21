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

    def test_escape_closes_panel_and_consumes_event(self):
        panel = BankPanel()
        panel.open(previous_time_speed=1)
        event = pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_ESCAPE},
        )
        self.assertTrue(panel.handle_event(event))
        self.assertFalse(panel.visible)
        self.assertEqual(panel.take_decision(), "decline")

    def test_outside_click_closes_panel_and_consumes_event(self):
        panel = BankPanel()
        panel.open(previous_time_speed=1)
        outside = (panel.rect.left - 1, panel.rect.top)
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": outside},
        )
        self.assertTrue(panel.handle_event(event))
        self.assertFalse(panel.visible)
        self.assertEqual(panel.take_decision(), "decline")

    def test_manual_mode_hides_market_and_uses_close_button(self):
        panel = BankPanel()
        panel.open(previous_time_speed=1, emergency_mode=False)
        panel.draw(
            pygame.Surface((900, 600)), self.font, BankSystem(Economy(8500)),
        )
        self.assertNotIn("market", panel.button_rects)
        self.assertIn("accept", panel.button_rects)
        self.assertIn("decline", panel.button_rects)
        self.assertTrue(panel.accept_enabled)

    def test_active_loan_disables_accept_button(self):
        economy = Economy(8500)
        bank = BankSystem(economy)
        bank.take_loan()
        panel = BankPanel()
        panel.open(previous_time_speed=1, emergency_mode=False)
        panel.draw(pygame.Surface((900, 600)), self.font, bank)
        self.assertFalse(panel.accept_enabled)

        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": panel.button_rects["accept"].center},
        )
        self.assertTrue(panel.handle_event(event))
        self.assertIsNone(panel.take_decision())
        self.assertTrue(panel.visible)


if __name__ == "__main__":
    unittest.main()
