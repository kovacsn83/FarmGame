from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from economy import Economy
from financial_history import (
    EXPENSE_ANIMAL_FEED, EXPENSE_SHIPPING, INCOME_CROP_SALES,
)
from game_state import GameState
from market_procurement import purchase_automatically
from save_system import load_game, save_game
from simulation import SimulationBot
from time_system import GameTime


class FinancialHistoryTests(unittest.TestCase):
    def setUp(self):
        self.time = GameTime()
        self.economy = Economy(1000)
        GameState([], [], [], self.economy, self.time)

    def test_summary_uses_only_last_fifty_two_weeks(self):
        self.economy.record_transaction(
            "income", INCOME_CROP_SALES, 20, "wheat", week=0,
        )
        self.time.elapsed_weeks = 52
        self.economy.record_income(INCOME_CROP_SALES, 30, "corn")
        summary = self.economy.get_financial_summary()
        self.assertEqual(summary["income_total"], 30)
        self.assertEqual(summary["net"], 30)

    def test_purchase_splits_goods_and_shipping(self):
        purchase_automatically(
            self.economy, "Lucerna", 7, 2,
            EXPENSE_ANIMAL_FEED, "alfalfa",
        )
        summary = self.economy.get_financial_summary()
        self.assertEqual(summary["expense"][EXPENSE_ANIMAL_FEED]["total"], 14)
        self.assertEqual(summary["expense"][EXPENSE_SHIPPING]["total"], 6)

    def test_history_round_trip_and_old_save_default(self):
        self.economy.record_income(INCOME_CROP_SALES, 50, "wheat")
        saved = self.economy.financial_history_save_record()
        loaded = Economy()
        loaded.load_financial_history(saved)
        self.assertEqual(loaded.financial_history, saved)
        loaded.load_financial_history(None)
        self.assertEqual(loaded.financial_history, [])

    def test_financial_history_round_trips_through_game_save(self):
        original = SimulationBot(31)
        original.economy.record_income(INCOME_CROP_SALES, 75, "wheat")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "finance_save.json"
            self.assertTrue(save_game(original.state, path))
            loaded = SimulationBot(32)
            self.assertTrue(load_game(loaded.state, path))
        self.assertEqual(
            loaded.economy.get_financial_summary()["income_total"], 75,
        )

    def test_refunded_seed_removes_purchase_costs(self):
        payment = self.economy.reserve_seed([], "wheat")
        self.assertIsNotNone(payment)
        self.economy.refund_seed(payment, "wheat")
        self.assertEqual(self.economy.get_financial_summary()["expense_total"], 0)


if __name__ == "__main__":
    unittest.main()
