import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simulation import SimulationBot, run_simulation
from simulation_report import build_economic_summary


class FiveYearSimulationTests(unittest.TestCase):
    def test_apple_sales_use_fruit_report_category(self):
        self.assertEqual(
            SimulationBot._sale_income_category("apple"), "fruit_sales",
        )
        self.assertEqual(
            SimulationBot._sale_income_category("cherry"), "fruit_sales",
        )
        self.assertEqual(
            SimulationBot._sale_income_category("plum"), "fruit_sales",
        )

    def test_processed_products_use_their_own_report_category(self):
        self.assertEqual(
            SimulationBot._sale_income_category("canned_tomato"),
            "processed_product_sales",
        )

    def test_bot_builds_and_demolishes_through_game_rules(self):
        bot = SimulationBot(3)
        bot.bootstrap()
        temporary = bot.build_field(21, 64)
        self.assertIsNotNone(temporary)
        self.assertTrue(bot.demolish_field(temporary))
        bot.assert_invariants()

    def test_bot_integrates_chicken_feed_and_market_products(self):
        with tempfile.TemporaryDirectory() as report_dir:
            result = run_simulation(1, 17, report_dir)
        snapshot = result["snapshots"][0]
        self.assertEqual(snapshot["investments"].get("animal:chicken"), 1)
        self.assertGreater(snapshot["sold_products"].get("egg", 0), 0)
        self.assertGreater(
            snapshot["sold_products"].get("chicken_meat", 0), 0,
        )

    def test_five_year_run_is_complete_and_reproducible(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = run_simulation(5, 12345, first_dir)
            second = run_simulation(5, 12345, second_dir)
        self.assertEqual(first["weeks_processed"], 260)
        self.assertEqual(len(first["snapshots"]), 5)
        self.assertEqual(first["final_money"], second["final_money"])
        self.assertEqual(first["snapshots"], second["snapshots"])
        self.assertFalse(first["invariant_errors"])

    def test_reports_are_written_and_machine_readable(self):
        with tempfile.TemporaryDirectory() as report_dir:
            result = run_simulation(1, 7, report_dir)
            markdown = Path(result["report_paths"]["markdown"])
            json_path = Path(result["report_paths"]["json"])
            self.assertTrue(markdown.exists())
            self.assertTrue(json_path.exists())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["weeks_processed"], 52)
            report = markdown.read_text(encoding="utf-8")
            self.assertIn("| Év vége |", report)
            self.assertIn("## Ötéves összesítő", report)
            self.assertIn("#### Bevételi bontás", report)
            self.assertIn("#### Kiadási bontás", report)
            self.assertIn("economic_summary", data)

    def test_annual_ledgers_reconcile_with_their_totals(self):
        bot = SimulationBot(23)
        starting_cash = bot.economy.money
        bot.bootstrap()
        for elapsed_week in range(1, 105):
            bot.run_week()
            if elapsed_week % 52:
                continue
            year = elapsed_week // 52
            raw_income = bot.income[year]
            raw_expenses = bot.expenses[year]
            self.assertAlmostEqual(sum(bot.income_breakdown[year].values()),
                                   raw_income, delta=1e-7)
            self.assertAlmostEqual(sum(bot.expense_breakdown[year].values()),
                                   raw_expenses, delta=1e-7)
            # Check the year assignment against actual, unrounded transactions.
            for kind, total in (("income", raw_income), ("expense", raw_expenses)):
                self.assertAlmostEqual(sum(
                    record["amount"] for record in bot.economy.financial_history
                    if record["type"] == kind and record["week"] // 52 + 1 == year
                ), total, delta=1e-7)
            snapshot = vars(bot.take_snapshot(year))
            self.assertEqual(snapshot["income"], round(raw_income, 2))
            self.assertEqual(snapshot["expenses"], round(raw_expenses, 2))
            self.assertEqual(snapshot["net_profit"], round(raw_income - raw_expenses, 2))
            # Precise totals need not equal the sum of rounded report rows.
            if year == 1:
                self.assertEqual(snapshot["expenses"], 9560.12)
                self.assertAlmostEqual(sum(snapshot["expense_breakdown"].values()),
                                       9560.11, delta=1e-7)
                self.assertAlmostEqual(bot.expenses[2], 13.884615384615245,
                                       delta=1e-7)
            self.assertIn("building_maintenance", snapshot["expense_breakdown"])
            self.assertIn("road_maintenance", snapshot["expense_breakdown"])
            self.assertIn("vehicle_maintenance", snapshot["expense_breakdown"])
            self.assertIn("crop_sales", snapshot["income_breakdown"])
            self.assertIn("milk_sales", snapshot["income_breakdown"])
            self.assertIn("pork_sales", snapshot["income_breakdown"])
        self.assertAlmostEqual(starting_cash + sum(bot.income.values())
                               - sum(bot.expenses.values()), bot.economy.money,
                               delta=1e-7)
        self.assertAlmostEqual(starting_cash + sum(
            record["amount"] * (1 if record["type"] == "income" else -1)
            for record in bot.economy.financial_history
        ), bot.economy.money, delta=1e-7)

    def test_report_summary_calculates_ratios_and_largest_categories(self):
        snapshots = [{
            "income": 120.0,
            "expenses": 80.0,
            "income_breakdown": {"crop_sales": 100.0, "milk_sales": 20.0},
            "expense_breakdown": {
                "building_maintenance": 20.0,
                "feed_purchase": 10.0,
                "building_construction": 50.0,
            },
        }]
        summary = build_economic_summary(snapshots)
        self.assertEqual(summary["net_profit"], 40.0)
        self.assertEqual(summary["maintenance_expense_ratio"], 0.25)
        self.assertEqual(summary["feed_expense_ratio"], 0.125)
        self.assertEqual(summary["investment_expense_ratio"], 0.625)
        self.assertEqual(
            summary["largest_income_source"]["category"], "crop_sales",
        )
        self.assertEqual(
            summary["largest_expense_category"]["category"],
            "building_construction",
        )


if __name__ == "__main__":
    unittest.main()
