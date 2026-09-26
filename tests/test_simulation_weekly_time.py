import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from constants import BUILDING, ROAD
from field_automation import AUTOMATED_FIELD_HARVESTING_UPGRADE
from field_automation import run_field_automation
from fields import clear_crop, plant_crop
from simulation import SimulationBot
from time_system import BASE_WEEK_DURATION_MS
import test_field_storage_blocking as storage_fixture


class SimulationWeeklyTimeTests(unittest.TestCase):
    def bot(self, elapsed=487):
        bot = SimulationBot(123)
        bot.game_time.elapsed_weeks = elapsed
        bot.world[0][0] = ROAD
        return bot

    def test_week_transition(self):
        bot = self.bot()
        bot.run_week()
        self.assertEqual((bot.year, bot.week), (10, 21))

    def test_starting_week_decisions_remain_on_starting_week(self):
        bot = self.bot()
        seen = []
        with patch.object(bot, "_sell_market_surplus", side_effect=lambda: seen.append(
                (bot.year, bot.week))):
            bot.run_week()
        self.assertEqual(seen, [(10, 20)])

    def test_maintenance_date_and_amount_match_normal_weekly_path(self):
        bot = self.bot()
        normal = self.bot()
        for _ in normal.game_time.iter_weekly_updates(BASE_WEEK_DURATION_MS):
            normal.economy.apply_weekly_costs(normal.world, [], [])
        bot.run_week()
        self.assertEqual(bot.economy.financial_history, normal.economy.financial_history)
        self.assertEqual(bot.economy.money, normal.economy.money)
        self.assertEqual(bot.economy.financial_history[0]["week"], 488)

    def test_repayment_date_amount_and_balance(self):
        bot = self.bot()
        self.assertTrue(bot.bank_system.take_loan())
        payment = bot.bank_system.loan.weekly_payment_cents / 100
        before = bot.bank_system.loan.remaining_balance_cents
        bot.economy.financial_history.clear()
        bot.run_week()
        records = bot.economy.financial_history
        self.assertEqual([r["week"] for r in records], [488, 488])
        self.assertEqual(records[-1]["amount"], payment)
        self.assertEqual(bot.bank_system.loan.remaining_balance_cents,
                         before - round(payment * 100))

    def test_year_boundary_transactions_and_annual_statistics(self):
        bot = self.bot(519)
        self.assertTrue(bot.bank_system.take_loan())
        bot.economy.financial_history.clear()
        bot.run_week()
        self.assertEqual((bot.year, bot.week), (11, 1))
        self.assertTrue(all(r["week"] == 520 for r in bot.economy.financial_history))
        self.assertGreater(bot.expenses[11], 0)
        self.assertEqual(bot.expenses[10], 0)
        self.assertGreater(bot.bank_repayments_by_year[11], 0)

    def test_year_boundary_new_loan_statistics(self):
        bot = self.bot(519)
        bot.economy.money = 0.01
        bot.run_week()
        self.assertEqual(bot.loan_count_by_year[11], 1)
        self.assertEqual(bot.loan_count_by_year[10], 0)
        self.assertEqual(bot.economy.financial_history[-1]["week"], 520)

    def test_consecutive_weeks_book_in_order(self):
        bot = self.bot(517)
        seen = []
        for _ in range(4):
            bot.run_week()
            seen.append((bot.year, bot.week))
        self.assertEqual(seen, [(10, 51), (10, 52), (11, 1), (11, 2)])
        self.assertEqual([r["week"] for r in bot.economy.financial_history],
                         [518, 519, 520, 521])

    def test_automation_argument_and_global_time_agree_in_both_phases(self):
        bot = self.bot(519)
        seen = []
        def observe(*args, **kwargs):
            seen.append((kwargs["current_elapsed_week"],
                         bot.game_time.elapsed_weeks, bot.year, bot.week))
            return run_field_automation(*args, **kwargs)
        with patch("simulation.run_field_automation", side_effect=observe):
            bot.run_week()
        self.assertEqual(seen, [(519, 519, 10, 52), (520, 520, 11, 1)])

    def crop_bot(self, crop, planted, elapsed, growth_weeks):
        fixture = storage_fixture.FieldStorageBlockingTests()
        fixture.setUp()
        for building in fixture.buildings:
            for row in range(building["row"], building["row"] + building["height"]):
                for col in range(building["col"], building["col"] + building["width"]):
                    fixture.world[row][col] = BUILDING
        fixture.warehouse["inventory"].clear()
        clear_crop(fixture.field)
        self.assertTrue(plant_crop(fixture.field, crop, planted))
        fixture.field.update(growth_weeks=growth_weeks, growth=90,
                             sprayed=True, watered=False)
        bot = SimulationBot(124)
        bot.world = bot.state.world = fixture.world
        bot.buildings = bot.state.buildings = fixture.buildings
        bot.fields = bot.state.fields = [fixture.field]
        bot.vehicles = bot.state.vehicles = bot.state.tractor = fixture.manager
        bot.game_time.elapsed_weeks = elapsed
        bot.state.purchased_upgrades.add(AUTOMATED_FIELD_HARVESTING_UPGRADE)
        # Isolate the weekly transition from optional bot management decisions.
        for method in ("_purchase_animal_automation", "_purchase_field_automation",
                       "_supply_animals", "_harvest", "_plant_and_tend",
                       "_sell_market_surplus"):
            patcher = patch.object(bot, method)
            patcher.start()
            self.addCleanup(patcher.stop)
        return bot, fixture

    def test_tomato_first_automatic_harvest_retains_second_stage(self):
        bot, fixture = self.crop_bot("tomato", 18, 26, 8)
        bot.run_week()
        field = fixture.field
        self.assertEqual(fixture.warehouse["inventory"]["tomato"], 6)
        self.assertEqual(field["crop"], "tomato")
        self.assertEqual(field["harvest_count"], 1)
        self.assertTrue(field["sprayed"])
        self.assertEqual(field["last_harvest_at_week"], 27)
        self.assertEqual(field["next_maturity_at_week"], 30)

    def test_tomato_second_automatic_harvest_completes_cycle(self):
        bot, fixture = self.crop_bot("tomato", 18, 26, 8)
        for _ in range(4):
            bot.run_week()
        # Existing integer rounding: 5 * 1.1 -> 6, 3 * 1.1 -> 3.
        self.assertEqual(fixture.warehouse["inventory"]["tomato"], 9)
        self.assertIsNone(fixture.field["crop"])
        self.assertFalse(fixture.field["sprayed"])

    def test_alfalfa_recurring_harvest_uses_current_completion_week(self):
        bot, fixture = self.crop_bot("alfalfa", 10, 19, 9)
        bot.run_week()
        self.assertEqual(fixture.field["crop"], "alfalfa")
        self.assertEqual(fixture.field["last_harvest_at_week"], 20)
        self.assertEqual(fixture.field["next_maturity_at_week"], 25)


if __name__ == "__main__":
    unittest.main()
