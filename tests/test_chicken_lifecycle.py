from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from animal_renderer import ANIMAL_RENDERERS
from animal_troughs import FOOD_STOCK_KEY, WATER_STOCK_KEY
from animals import (
    ANIMAL_TYPES, CHICKEN_EGGS_PER_WEEK, CHICKEN_FATTENING_WEEKS,
    CHICKEN_MEAT_PER_CYCLE, get_animal_placement_error,
    purchase_and_place_animal, run_weekly_animal_cycle,
)
from economy import Economy
from feed_supply import get_feed_requirement, prepare_feed_supply
from game_logger import get_logger
from inventory import get_inventory_item_data, get_marketable_item_ids
from notification_system import NotificationManager
from progress_tooltips import find_timed_object_tooltip
from save_system import _migrate_legacy_crop_data


class ChickenLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.pen = {
            "type": "animal_pen", "row": 10, "col": 10,
            "width": 4, "height": 4,
        }
        self.warehouse = {
            "type": "warehouse", "row": 2, "col": 2,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {},
        }
        self.market = {
            "type": "market", "row": 2, "col": 10,
            "width": 4, "height": 3,
        }
        self.buildings = [self.pen, self.warehouse, self.market]
        self.chicken = {
            "type": "chicken", "row": 10, "col": 10,
            "pen_row": 10, "pen_col": 10,
            "age_weeks": 0, "visual_id": 1,
            "facing_direction": "down",
        }
        get_logger().reset()

    def _supply_one_week(self):
        self.pen[FOOD_STOCK_KEY] = 1
        self.pen[WATER_STOCK_KEY] = 1

    def test_purchase_cost_and_separate_species_pen_rule(self):
        economy = Economy(starting_money=100)
        self.assertTrue(purchase_and_place_animal(
            [], self.buildings, economy, 11, 10, "chicken",
        ))
        self.assertEqual(economy.money, 0)

        cattle = [{
            "type": "cattle", "row": 10, "col": 10,
            "pen_row": 10, "pen_col": 10,
        }]
        self.assertIsNotNone(get_animal_placement_error(
            cattle, self.buildings, 11, 10, "chicken",
        ))

    def test_weekly_feed_water_and_egg_production(self):
        animals = [self.chicken]
        self._supply_one_week()

        result = run_weekly_animal_cycle(
            animals, self.buildings, economy=None,
        )

        self.assertEqual(result["fed_animals"], 1)
        self.assertEqual(self.pen[FOOD_STOCK_KEY], 0)
        self.assertEqual(self.pen[WATER_STOCK_KEY], 0)
        self.assertEqual(
            self.warehouse["inventory"]["egg"], CHICKEN_EGGS_PER_WEEK,
        )
        self.assertEqual(self.chicken["age_weeks"], 1)

    def test_missing_food_or_water_pauses_production_and_age(self):
        for food, water in ((0, 1), (1, 0)):
            with self.subTest(food=food, water=water):
                chicken = {**self.chicken}
                self.pen[FOOD_STOCK_KEY] = food
                self.pen[WATER_STOCK_KEY] = water
                run_weekly_animal_cycle(
                    [chicken], self.buildings, economy=None,
                )
                self.assertEqual(chicken["age_weeks"], 0)
                self.assertEqual(self.warehouse["inventory"].get("egg", 0), 0)

    def test_week_26_produces_egg_then_slaughters_and_notifies(self):
        chicken = {
            **self.chicken,
            "age_weeks": CHICKEN_FATTENING_WEEKS - 1,
        }
        animals = [chicken]
        notifications = NotificationManager(start_ticks=0)
        self._supply_one_week()

        run_weekly_animal_cycle(
            animals, self.buildings, economy=None,
            notification_manager=notifications,
        )

        self.assertEqual(animals, [])
        self.assertEqual(self.warehouse["inventory"]["egg"], 1)
        self.assertEqual(
            self.warehouse["inventory"]["chicken_meat"],
            CHICKEN_MEAT_PER_CYCLE,
        )
        self.assertIn("5 db csirkehús", notifications.current_message)
        self.assertTrue(any(
            entry.category == "Animals"
            and "5 db csirkehús" in entry.message
            for entry in get_logger().entries
        ))

    def test_multiple_chickens_create_one_aggregated_notification(self):
        animals = [
            {
                **self.chicken,
                "row": 10 + index // 4,
                "col": 10 + index % 4,
                "visual_id": index + 1,
                "age_weeks": CHICKEN_FATTENING_WEEKS - 1,
            }
            for index in range(12)
        ]
        notifications = NotificationManager(start_ticks=0)
        self.pen[FOOD_STOCK_KEY] = 12
        self.pen[WATER_STOCK_KEY] = 12

        run_weekly_animal_cycle(
            animals, self.buildings, economy=None,
            notification_manager=notifications,
        )

        self.assertEqual(animals, [])
        self.assertEqual(self.warehouse["inventory"]["egg"], 12)
        self.assertEqual(self.warehouse["inventory"]["chicken_meat"], 60)
        self.assertEqual(
            notifications.current_message,
            "12 csirke levágásra került. 60 db csirkehús került a raktárba.",
        )

    def test_feed_supply_uses_wheat_and_can_buy_market_shortage(self):
        feed_type, amount = get_feed_requirement(
            [self.pen], [self.chicken],
        )
        self.assertEqual(feed_type, "wheat")
        self.assertEqual(amount, 8)

        economy = Economy(starting_money=200)
        transaction = prepare_feed_supply(
            self.buildings, economy, [self.pen], [self.chicken],
        )
        self.assertTrue(transaction.success)
        self.assertEqual(transaction.feed_type, "wheat")
        self.assertEqual(transaction.purchased_amount, 8)
        self.assertEqual(transaction.goods_cost, 80)
        self.assertEqual(transaction.delivery_cost, 24)
        self.assertEqual(transaction.purchase_cost, 104)
        self.assertEqual(economy.money, 96)

    def test_egg_and_chicken_meat_are_marketable_at_catalog_prices(self):
        self.assertEqual(get_inventory_item_data("egg")["price"], 6.00)
        self.assertEqual(
            get_inventory_item_data("chicken_meat")["price"], 50.00,
        )
        self.assertIn("egg", get_marketable_item_ids())
        self.assertIn("chicken_meat", get_marketable_item_ids())

        self.warehouse["inventory"].update({"egg": 2, "chicken_meat": 5})
        economy = Economy(starting_money=0)
        self.assertTrue(economy.sell_item(self.buildings, "egg"))
        self.assertTrue(economy.sell_item(self.buildings, "chicken_meat"))
        self.assertEqual(economy.money, 262)

    def test_tooltip_shows_age_egg_rate_and_missing_supply(self):
        chicken = {**self.chicken, "age_weeks": 12}
        lines = find_timed_object_tooltip(
            10, 10, [], [chicken], ANIMAL_TYPES, buildings=self.buildings,
        )
        self.assertIn("Kor:", lines)
        self.assertIn("12 / 26 hét", lines)
        self.assertIn("Heti tojástermelés:", lines)
        self.assertIn("1 db", lines)
        self.assertIn("Még 14 hét a levágásig", lines)
        self.assertIn("Nincs elegendő eledel", lines)
        self.assertIn("Nincs elegendő ivóvíz", lines)

    def test_save_migration_initializes_new_inventory_and_age(self):
        data = {
            "fields": [],
            "buildings": [self.warehouse, self.pen],
            "animals": [{
                "type": "chicken", "row": 10, "col": 10,
                "pen_row": 10, "pen_col": 10,
            }],
        }

        _migrate_legacy_crop_data(data)

        self.assertEqual(data["animals"][0]["age_weeks"], 0)
        self.assertEqual(self.warehouse["inventory"]["egg"], 0)
        self.assertEqual(self.warehouse["inventory"]["chicken_meat"], 0)

    def test_procedural_renderer_is_registered(self):
        self.assertIn("chicken", ANIMAL_RENDERERS)


if __name__ == "__main__":
    unittest.main()
