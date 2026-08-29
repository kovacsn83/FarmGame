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
from financial_history import (
    EXPENSE_CONSTRUCTION, EXPENSE_UPGRADE, INCOME_CROP_SALES,
    INCOME_QUEST_REWARD,
)
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
        layout = self._draw_at(1500, 1000)
        income = layout["income_content"]
        expense = layout["expense_content"]
        self.assertLess(income.right, expense.left)
        self.assertEqual(income.top, expense.top)
        self.assertEqual(income.width, expense.width)

    def test_quest_rewards_have_their_own_income_row(self):
        self.economy.credit_income(INCOME_QUEST_REWARD, 700)
        summary = self.economy.get_financial_summary(52)
        rows = self.panel._column_rows(summary, "income")
        reward_row = next(row for row in rows if row[1] == "Quest jutalmak")
        self.assertEqual(reward_row[2], 700)

    def test_upgrade_detail_uses_the_central_hungarian_name(self):
        self.economy.record_expense(
            EXPENSE_UPGRADE, 2000, "unlock_field_6x6",
        )
        summary = self.economy.get_financial_summary(52)
        rows = self.panel._column_rows(summary, "expense")
        self.assertIn(
            ("detail", "  6x6-os veteményes", 2000),
            rows,
        )

    def test_totals_are_kept_in_their_own_columns(self):
        summary = self.economy.get_financial_summary(52)
        income_rows = self.panel._column_rows(summary, "income")
        expense_rows = self.panel._column_rows(summary, "expense")
        self.assertNotIn("total_income", {row[0] for row in income_rows})
        self.assertNotIn("total_expense", {row[0] for row in expense_rows})
        layout = self._draw_at(1500, 1000)
        self.assertLess(layout["income_total"].right, layout["expense_total"].left)

    def test_normal_resolution_needs_no_scrolling(self):
        self._draw_at(1500, 1000)
        self.assertEqual(self.panel.max_scroll, 0)

    def test_small_resolution_keeps_fixed_net_row_inside_panel(self):
        layout = self._draw_at(640, 420)
        income = layout["income_content"]
        expense = layout["expense_content"]
        net = layout["net"]
        self.assertGreaterEqual(layout["totals"].top, income.bottom)
        self.assertGreaterEqual(net.top, layout["totals"].bottom)
        self.assertLessEqual(net.bottom, self.panel.rect.bottom)
        self.assertGreater(income.width, 0)
        self.assertGreater(expense.width, 0)

    def test_headers_totals_and_net_do_not_move_when_scrolling(self):
        screen = pygame.display.set_mode((640, 420))
        set_screen_size(640, 420)
        self.panel.open()
        self.panel.draw(screen, self.font, self.economy)
        layout = self.panel._layout_rects()
        self.assertGreater(self.panel.max_scroll, 0)
        fixed_rects = (
            layout["income_heading"], layout["expense_heading"],
            layout["totals"], layout["net"],
        )
        before = [
            pygame.image.tobytes(screen.subsurface(rect), "RGB")
            for rect in fixed_rects
        ]
        self.panel.scroll_offset = self.panel.max_scroll
        self.panel.draw(screen, self.font, self.economy)
        after = [
            pygame.image.tobytes(screen.subsurface(rect), "RGB")
            for rect in fixed_rects
        ]
        self.assertEqual(before, after)

    def test_scroll_range_uses_only_category_row_height(self):
        layout = self._draw_at(640, 420)
        summary = self.economy.get_financial_summary(52)
        row_count = max(
            len(self.panel._column_rows(summary, "income")),
            len(self.panel._column_rows(summary, "expense")),
        )
        expected = max(
            0, row_count * 24 - layout["income_content"].height,
        )
        self.assertEqual(expected, self.panel.max_scroll)

    def test_bank_button_is_top_right_and_emits_request(self):
        self._draw_at(1500, 1000)
        button = self.panel.bank_button_rect
        self.assertGreater(button.left, self.panel.rect.centerx)
        self.assertLess(button.right, self.panel.rect.right)
        self.assertLess(button.top, self.panel._layout_rects()["income_heading"].top)

        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": button.center},
        )
        self.assertTrue(self.panel.handle_event(event))
        self.assertTrue(self.panel.take_bank_request())
        self.assertFalse(self.panel.take_bank_request())


if __name__ == "__main__":
    unittest.main()
