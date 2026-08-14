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
        with tempfile.TemporaryDirectory() as report_dir:
            result = run_simulation(2, 23, report_dir)
        for snapshot in result["snapshots"]:
            self.assertAlmostEqual(
                sum(snapshot["income_breakdown"].values()),
                snapshot["income"], places=2,
            )
            self.assertAlmostEqual(
                sum(snapshot["expense_breakdown"].values()),
                snapshot["expenses"], places=2,
            )
            self.assertAlmostEqual(
                snapshot["income"] - snapshot["expenses"],
                snapshot["net_profit"], places=2,
            )
            self.assertIn("building_maintenance", snapshot["expense_breakdown"])
            self.assertIn("road_maintenance", snapshot["expense_breakdown"])
            self.assertIn("vehicle_maintenance", snapshot["expense_breakdown"])
            self.assertIn("crop_sales", snapshot["income_breakdown"])
            self.assertIn("milk_sales", snapshot["income_breakdown"])
            self.assertIn("pork_sales", snapshot["income_breakdown"])

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
