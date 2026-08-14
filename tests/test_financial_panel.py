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

from economy import Economy
from financial_history import INCOME_CROP_SALES, EXPENSE_CONSTRUCTION
from screen_layout import set_screen_size
from ui import FinancialSummaryPanel


class FinancialSummaryPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.font = pygame.font.SysFont(None, 24)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.economy = Economy()
        self.economy.record_income(INCOME_CROP_SALES, 300, "wheat")
        self.economy.record_expense(EXPENSE_CONSTRUCTION, 125, "road")
        self.panel = FinancialSummaryPanel()

    def _draw_at(self, width, height):
        screen = pygame.display.set_mode((width, height))
        set_screen_size(width, height)
        self.panel.open()
        self.panel.draw(screen, self.font, self.economy)
        return self.panel._layout_rects()

    def test_income_and_expense_columns_are_side_by_side(self):
        income, expense, _ = self._draw_at(1500, 1000)
        self.assertLess(income.right, expense.left)
        self.assertEqual(income.top, expense.top)
        self.assertEqual(income.width, expense.width)

    def test_totals_are_kept_in_their_own_columns(self):
        summary = self.economy.get_financial_summary(52)
        income_rows = self.panel._column_rows(summary, "income")
        expense_rows = self.panel._column_rows(summary, "expense")
        self.assertEqual(income_rows[-1], ("total_income", "Összes bevétel", 300))
        self.assertEqual(expense_rows[-1], ("total_expense", "Összes kiadás", 125))

    def test_normal_resolution_needs_no_scrolling(self):
        self._draw_at(1500, 1000)
        self.assertEqual(self.panel.max_scroll, 0)

    def test_small_resolution_keeps_fixed_net_row_inside_panel(self):
        income, expense, net = self._draw_at(640, 420)
        self.assertGreaterEqual(net.top, income.bottom)
        self.assertLessEqual(net.bottom, self.panel.rect.bottom)
        self.assertGreater(income.width, 0)
        self.assertGreater(expense.width, 0)


if __name__ == "__main__":
    unittest.main()
