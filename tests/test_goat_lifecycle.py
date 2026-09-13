import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from animal_automation import (
    AUTOMATED_FEEDING_UPGRADE, AUTOMATED_WATERING_UPGRADE,
    run_weekly_animal_supply_automation,
)
from animal_renderer import (
    ANIMAL_RENDERERS, CATTLE_DIRECTIONS, CATTLE_SPRITE_SIZE,
    GOAT_BODY_COLOR, GOAT_HORN_COLOR, _get_goat_sprite,
    clear_animal_render_cache,
)
from animal_troughs import FOOD_STOCK_KEY, WATER_STOCK_KEY
from animals import (
    ANIMAL_TYPES, GOAT_MEAT_PER_CYCLE, GOAT_MILK_PER_WEEK,
    GOAT_SLAUGHTER_AGE_WEEKS,
    purchase_and_place_animal, run_weekly_animal_cycle,
)
from economy import Economy
from constants import BUILDING, GRASS
from financial_history import EXPENSE_ANIMAL_PURCHASE
from game_state import GameState
from inventory import get_inventory_item_data, get_marketable_item_ids
from restaurant import get_restaurant_sellable_item_ids
from save_system import _migrate_legacy_crop_data, load_game, save_game
from time_system import GameTime


class RecordingVehicleManager:
    def __init__(self):
        self.calls = []

    def start_trough_supply(
            self, world, buildings, economy, animals, trough,
            current_ticks=None):
        self.calls.append(trough["type"])
        return True


class GoatLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.pen = {
            "type": "animal_pen", "row": 10, "col": 10,
            "width": 4, "height": 4,
            FOOD_STOCK_KEY: 0, WATER_STOCK_KEY: 0,
        }
        self.warehouse = {
            "type": "warehouse", "row": 2, "col": 2,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {},
        }
        self.buildings = [self.pen, self.warehouse]

    def _goat(self, index=0, age_weeks=0):
        return {
            "type": "goat", "row": 10 + index // 4,
            "col": 10 + index % 4, "pen_row": 10, "pen_col": 10,
            "age_weeks": age_weeks, "visual_id": index + 1,
            "facing_direction": "down",
        }

    def test_purchase_cost_capacity_species_and_financial_category(self):
        economy = Economy(starting_money=200)
        animals = []
        self.assertTrue(purchase_and_place_animal(
            animals, self.buildings, economy, 11, 10, "goat",
        ))
        self.assertEqual(economy.money, 25)
        self.assertEqual(animals[0]["type"], "goat")
        summary = economy.get_financial_summary(52)
        self.assertEqual(
            summary["expense"][EXPENSE_ANIMAL_PURCHASE]["total"], 175,
        )
        self.assertFalse(purchase_and_place_animal(
            animals, self.buildings, economy, 11, 11, "pig",
        ))

    def test_one_and_ten_goats_consume_one_alfalfa_each_and_water(self):
        for count in (1, 10):
            with self.subTest(count=count):
                self.warehouse["inventory"].clear()
                animals = [self._goat(index) for index in range(count)]
                self.pen[FOOD_STOCK_KEY] = count
                self.pen[WATER_STOCK_KEY] = count
                run_weekly_animal_cycle(animals, self.buildings, economy=None)
                self.assertEqual(self.pen[FOOD_STOCK_KEY], 0)
                self.assertEqual(self.pen[WATER_STOCK_KEY], 0)
                self.assertTrue(all(goat["age_weeks"] == 1 for goat in animals))
                self.assertEqual(
                    self.warehouse["inventory"]["goat_milk"],
                    count * GOAT_MILK_PER_WEEK,
                )

    def test_goat_produces_no_milk_without_both_food_and_water(self):
        for food, water in ((0, 1), (1, 0), (0, 0)):
            with self.subTest(food=food, water=water):
                self.warehouse["inventory"].clear()
                self.pen[FOOD_STOCK_KEY] = food
                self.pen[WATER_STOCK_KEY] = water
                goat = self._goat()
                run_weekly_animal_cycle([goat], self.buildings, economy=None)
                self.assertEqual(
                    self.warehouse["inventory"].get("goat_milk", 0), 0,
                )
                self.assertEqual(goat["age_weeks"], 0)

    def test_automation_dispatches_feed_and_water_for_goats(self):
        vehicles = RecordingVehicleManager()
        created = run_weekly_animal_supply_automation(
            [[0] * 20 for _ in range(20)], self.buildings, Economy(1000),
            [self._goat()], vehicles,
            {AUTOMATED_FEEDING_UPGRADE, AUTOMATED_WATERING_UPGRADE},
        )
        self.assertEqual(created, 2)
        self.assertEqual(vehicles.calls, ["food", "water"])

    def test_slaughter_occurs_at_week_78_and_stores_exact_yield(self):
        goat = self._goat(age_weeks=GOAT_SLAUGHTER_AGE_WEEKS - 2)
        animals = [goat]
        self.pen[FOOD_STOCK_KEY] = 1
        self.pen[WATER_STOCK_KEY] = 1
        run_weekly_animal_cycle(animals, self.buildings, economy=None)
        self.assertEqual(animals, [goat])
        self.assertEqual(goat["age_weeks"], GOAT_SLAUGHTER_AGE_WEEKS - 1)

        self.pen[FOOD_STOCK_KEY] = 1
        self.pen[WATER_STOCK_KEY] = 1
        run_weekly_animal_cycle(animals, self.buildings, economy=None)
        self.assertEqual(animals, [])
        self.assertEqual(
            self.warehouse["inventory"]["goat_meat"], GOAT_MEAT_PER_CYCLE,
        )

    def test_goat_meat_is_urban_market_item_but_not_restaurant_item(self):
        self.assertEqual(get_inventory_item_data("goat_meat")["price"], 150)
        self.assertIn("goat_meat", get_marketable_item_ids())
        self.assertNotIn("goat_meat", get_restaurant_sellable_item_ids())
        self.warehouse["inventory"]["goat_meat"] = 10
        economy = Economy(0)
        self.assertTrue(economy.sell_item(self.buildings, "goat_meat"))
        self.assertEqual(economy.money, 1500)

    def test_goat_milk_is_marketable_for_eleven_dollars(self):
        self.assertEqual(get_inventory_item_data("goat_milk")["price"], 11)
        self.assertIn("goat_milk", get_marketable_item_ids())
        self.warehouse["inventory"]["goat_milk"] = 4
        economy = Economy(0)
        self.assertTrue(economy.sell_item(self.buildings, "goat_milk"))
        self.assertEqual(economy.money, 44)
        summary = economy.get_financial_summary(52)
        self.assertEqual(
            summary["income"]["livestock_sales"]["items"]["goat_milk"], 44,
        )

    def test_goat_and_meat_are_included_once_in_farm_value(self):
        self.warehouse["inventory"].update({"goat_meat": 10, "goat_milk": 3})
        economy = Economy(0)
        state = GameState(
            [[0]], [], self.buildings, economy, GameTime(start_ticks=0),
            animals=[self._goat()],
        )
        breakdown = economy.get_farm_value_breakdown(state)
        self.assertEqual(breakdown["animals"], 175)
        self.assertEqual(breakdown["warehouse_inventory"], 1533)

    def test_save_load_preserves_goat_and_meat(self):
        self.warehouse["inventory"].update({"goat_meat": 7, "goat_milk": 5})
        world = [[GRASS] * 20 for _ in range(20)]
        for building in self.buildings:
            for row in range(building["row"], building["row"] + building["height"]):
                for col in range(building["col"], building["col"] + building["width"]):
                    world[row][col] = BUILDING
        state = GameState(
            world, [], self.buildings, Economy(1000),
            GameTime(start_ticks=0), animals=[self._goat(age_weeks=20)],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "goat.json"
            self.assertTrue(save_game(state, path))
            state.animals.clear()
            self.warehouse["inventory"]["goat_meat"] = 0
            self.assertTrue(load_game(state, path))
        self.assertEqual(state.animals[0]["type"], "goat")
        self.assertEqual(state.animals[0]["age_weeks"], 20)
        self.assertEqual(
            state.buildings[1]["inventory"]["goat_meat"], 7,
        )
        self.assertEqual(
            state.buildings[1]["inventory"]["goat_milk"], 5,
        )

    def test_old_save_migration_initializes_goat_meat_without_adding_goats(self):
        old_data = {
            "fields": [], "animals": [],
            "buildings": [{
                "type": "warehouse", "inventory": {}, "capacity": 500,
            }],
        }
        _migrate_legacy_crop_data(old_data)
        self.assertEqual(old_data["animals"], [])
        self.assertEqual(
            old_data["buildings"][0]["inventory"]["goat_meat"], 0,
        )
        self.assertEqual(
            old_data["buildings"][0]["inventory"]["goat_milk"], 0,
        )

    def test_catalog_uses_exact_requested_balance(self):
        goat = ANIMAL_TYPES["goat"]
        self.assertEqual(goat["purchase_price"], 175)
        self.assertEqual(goat["weekly_feed"], {"item": "alfalfa", "amount": 1})
        self.assertEqual(goat["weekly_products"], {"goat_milk": 1})
        production = goat["periodic_products"]["goat_meat"]
        self.assertEqual(production["interval_weeks"], 78)
        self.assertEqual(production["amount"], 10)

    def test_procedural_goat_renderer_has_gray_body_horns_and_directions(self):
        clear_animal_render_cache()
        goat = self._goat()
        self.assertIn("goat", ANIMAL_RENDERERS)
        sprites = {
            direction: _get_goat_sprite(
                {**goat, "facing_direction": direction}, direction,
            )
            for direction in CATTLE_DIRECTIONS
        }
        self.assertTrue(all(
            sprite.get_size() == (CATTLE_SPRITE_SIZE, CATTLE_SPRITE_SIZE)
            for sprite in sprites.values()
        ))
        canonical = sprites["up"]
        opaque_colors = {
            pixel[:3]
            for y in range(CATTLE_SPRITE_SIZE)
            for x in range(CATTLE_SPRITE_SIZE)
            if (pixel := canonical.get_at((x, y))).a
        }
        self.assertTrue(any(
            all(abs(channel - reference) <= 3 for channel, reference in zip(color, GOAT_BODY_COLOR))
            for color in opaque_colors
        ))
        self.assertIn(GOAT_HORN_COLOR, opaque_colors)
        self.assertNotEqual(sprites["up"].get_view("1").raw, sprites["right"].get_view("1").raw)


if __name__ == "__main__":
    unittest.main()
