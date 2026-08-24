import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pygame

from buildings import get_marketable_item_amount, place_building
from constants import GRASS, ROAD
from economy import Economy
from financial_history import (
    EXPENSE_PROCESSING_INPUT, EXPENSE_SHIPPING,
    INCOME_PROCESSED_PRODUCT_SALES,
)
from game_state import GameState
from inventory import get_inventory_item_data, get_marketable_item_ids
from processing import (
    PROCESSING_RECIPES, complete_processing_batch,
    get_processing_in_transit, get_processing_tooltip_lines,
    initialize_processing_plant, run_weekly_processing_cycle,
    select_processing_recipe, start_processing_batch,
)
from save_system import load_game, save_game
from screen_layout import set_screen_size
from time_system import GameTime, TIME_SLOW
from ui import FinancialSummaryPanel, InfoPanel
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class AppleJuiceProcessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1000, 800))
        set_screen_size(1000, 800)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    @staticmethod
    def _plant(row=15, col=18):
        return initialize_processing_plant({
            "type": "processing_plant", "row": row, "col": col,
            "width": 6, "height": 5,
        })

    def test_catalog_recipe_and_ui_use_apple_juice_data(self):
        recipe = PROCESSING_RECIPES["apple_juice"]
        product = get_inventory_item_data("apple_juice")
        self.assertEqual(("apple", 5), (
            recipe["input_product"], recipe["input_amount"],
        ))
        self.assertEqual(("apple_juice", 5, 5), (
            recipe["output_product"], recipe["output_amount"],
            recipe["weekly_capacity"],
        ))
        self.assertEqual("Almalé", product["name"])
        self.assertEqual(20.00, product["price"])
        self.assertEqual("processing_plant", product["inventory_source"])
        self.assertIn("apple_juice", get_marketable_item_ids())

        plant = self._plant()
        self.assertTrue(select_processing_recipe(plant, "apple_juice"))
        panel = InfoPanel()
        panel.open_for_building(plant)
        state = GameState(
            [], [], [plant], Economy(), GameTime(start_ticks=0),
        )
        captured = []
        with patch.object(
            panel, "draw_text",
            side_effect=lambda screen, font, text, x, y: captured.append(text),
        ):
            panel.draw(
                pygame.display.get_surface(), pygame.font.Font(None, 20), state,
            )
        self.assertEqual(
            {"canned_tomato", "cheese", "apple_juice"},
            set(panel.processing_recipe_rects),
        )
        self.assertIn("  Alma: 0 db", captured)
        self.assertIn("  Almalé: 0 db", captured)
        self.assertNotIn("  Paradicsom: 0 db", captured)
        self.assertNotIn("  Tej: 0 db", captured)

    def test_full_and_partial_apple_batches_use_generic_pipeline(self):
        full = self._plant()
        self.assertTrue(select_processing_recipe(full, "apple_juice"))
        full["processing_inventory"]["apple"] = 5
        self.assertEqual(5, start_processing_batch(full, 1))
        self.assertEqual(5, complete_processing_batch(full, 2))
        self.assertEqual(5, full["processing_inventory"]["apple_juice"])

        partial = self._plant()
        self.assertTrue(select_processing_recipe(partial, "apple_juice"))
        partial["processing_inventory"]["apple"] = 3
        self.assertEqual(3, start_processing_batch(partial, 1))
        self.assertEqual(3, complete_processing_batch(partial, 2))
        self.assertEqual(3, partial["processing_inventory"]["apple_juice"])

    def test_market_procurement_uses_apple_price_and_central_shipping_cost(self):
        world = [[ROAD for _ in range(40)] for _ in range(40)]
        garage = {"type": "garage", "row": 2, "col": 2,
                  "width": 4, "height": 4}
        market = {"type": "market", "row": 2, "col": 10,
                  "width": 4, "height": 3}
        plant = self._plant()
        self.assertTrue(select_processing_recipe(plant, "apple_juice"))
        buildings = [garage, market, plant]
        manager = VehicleManager()
        tractor = manager._create_managed_asset(
            VehicleType.TRACTOR, garage, 0,
        )
        manager._create_managed_asset(VehicleType.TRAILER, garage, 1)
        manager.ensure_idle_positions(world, buildings)
        economy = Economy(starting_money=1000)

        run_weekly_processing_cycle(
            world, buildings, economy, manager, 1, current_ticks=0,
        )
        self.assertEqual(935, economy.money)
        self.assertEqual(
            [EXPENSE_PROCESSING_INPUT, EXPENSE_SHIPPING],
            [item["category"] for item in economy.financial_history],
        )
        self.assertEqual(5, get_processing_in_transit(plant, "apple"))
        self.assertEqual("apple", tractor.current_task.cargo_type)

        game_time = GameTime(current_time_speed=TIME_SLOW, start_ticks=0)
        for tick in range(100, 30000, 100):
            manager.update(
                world, buildings, economy, game_time, current_ticks=tick,
            )
            if tractor.is_idle and tick > 100:
                break
        else:
            self.fail("Az Alma piaci szállítása nem fejeződött be.")
        self.assertEqual(0, get_processing_in_transit(plant, "apple"))
        self.assertEqual(
            5, plant["processing_batch"]["outputs"]["apple_juice"],
        )

    def test_warehouse_apple_is_physically_delivered_without_money_cost(self):
        world = [[ROAD for _ in range(40)] for _ in range(40)]
        garage = {"type": "garage", "row": 2, "col": 2,
                  "width": 4, "height": 4}
        warehouse = {"type": "warehouse", "row": 2, "col": 12,
                     "width": 5, "height": 4, "capacity": 500,
                     "inventory": {"apple": 5}}
        plant = self._plant()
        self.assertTrue(select_processing_recipe(plant, "apple_juice"))
        buildings = [garage, warehouse, plant]
        manager = VehicleManager()
        tractor = manager._create_managed_asset(
            VehicleType.TRACTOR, garage, 0,
        )
        manager._create_managed_asset(VehicleType.TRAILER, garage, 1)
        manager.ensure_idle_positions(world, buildings)
        economy = Economy(starting_money=1000)

        run_weekly_processing_cycle(
            world, buildings, economy, manager, 1, current_ticks=0,
        )
        self.assertEqual(0, warehouse["inventory"]["apple"])
        self.assertEqual(1000, economy.money)
        self.assertEqual([], economy.financial_history)
        self.assertEqual("warehouse", tractor.current_task.source_type)

    def test_market_sale_aggregates_plants_and_books_processed_income(self):
        first, second = self._plant(), self._plant(24, 18)
        first["processing_inventory"]["apple_juice"] = 2
        second["processing_inventory"]["apple_juice"] = 3
        buildings = [first, second, {"type": "market"}]
        economy = Economy(starting_money=0)

        self.assertEqual(
            5, get_marketable_item_amount(buildings, "apple_juice"),
        )
        self.assertTrue(economy.sell_item(buildings, "apple_juice"))
        self.assertEqual(100, economy.money)
        record = economy.financial_history[-1]
        self.assertEqual(INCOME_PROCESSED_PRODUCT_SALES, record["category"])
        self.assertEqual("apple_juice", record["subcategory"])
        rows = FinancialSummaryPanel()._column_rows(
            economy.get_financial_summary(52), "income",
        )
        self.assertIn(("detail", "  Almalé", 100.0), rows)

    def test_tooltip_and_save_round_trip_preserve_apple_juice_state(self):
        world = [[GRASS for _ in range(40)] for _ in range(40)]
        buildings = []
        plant = place_building(
            world, buildings, 15, 18, "processing_plant",
        )
        self.assertTrue(select_processing_recipe(plant, "apple_juice"))
        plant["processing_inventory"]["apple"] = 8
        self.assertEqual(5, start_processing_batch(plant, 12))
        plant["processing_inventory"]["apple_juice"] = 4
        self.assertIn("Almalé", get_processing_tooltip_lines(plant))
        state = GameState(
            world, [], buildings, Economy(), GameTime(start_ticks=0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "apple-juice.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))
        loaded = state.buildings[0]
        self.assertEqual("apple_juice", loaded["active_recipe"])
        self.assertEqual(3, loaded["processing_inventory"]["apple"])
        self.assertEqual(4, loaded["processing_inventory"]["apple_juice"])
        self.assertEqual("apple_juice", loaded["processing_batch"]["recipe_id"])
        self.assertEqual({"apple": 5}, loaded["processing_batch"]["inputs"])
        self.assertEqual(
            {"apple_juice": 5}, loaded["processing_batch"]["outputs"],
        )


if __name__ == "__main__":
    unittest.main()
