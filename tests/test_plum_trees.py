import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buildings import get_total_inventory, place_building
from constants import GRASS, ROAD
from economy import Economy
from field_renderer import FIELD_HARVEST_READY_BORDER_COLOR
from financial_history import INCOME_ORCHARD_SALES
from game_state import GameState
from inventory import get_inventory_item_data, get_marketable_item_ids
from orchards import (
    TREE_TYPES, complete_tree_harvest, draw_orchard_trees,
    get_tree_tooltip_lines, is_tree_harvestable, plant_tree,
    synchronize_tree_season,
)
from save_system import load_game, save_game
from screen_layout import set_camera, set_screen_size
from simulation import SimulationBot
from time_system import GameTime
from ui import FinancialSummaryPanel, OrchardSelectionPanel
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class PlumTreeTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        set_screen_size(1000, 800)
        set_camera(None)
        self.world = [[GRASS for _ in range(100)] for _ in range(80)]
        self.buildings = []
        self.orchard = place_building(
            self.world, self.buildings, 10, 10, "orchard",
        )
        self.warehouse = place_building(
            self.world, self.buildings, 20, 20, "warehouse",
        )
        self.market = place_building(
            self.world, self.buildings, 20, 30, "market",
        )
        self.economy = Economy(5000)

    def _plant_plum(self, row=10, col=10):
        return plant_tree(
            self.buildings, self.economy, row, col, "plum",
        )

    def test_catalog_and_selector_card_use_plum_definition(self):
        plum = TREE_TYPES["plum"]
        self.assertEqual("Szilva", plum["name"])
        self.assertEqual("Szilvafa", plum["tree_name"])
        self.assertEqual(100, plum["planting_cost"])
        self.assertEqual((2, 25), (
            plum["first_yield_age_years"],
            plum["last_yield_age_years"],
        ))
        self.assertEqual((34, 38), (
            plum["ripening_week"], plum["harvest_end_week"],
        ))
        self.assertEqual(20, plum["annual_yield"])

        panel = OrchardSelectionPanel()
        panel.open()
        surface = pygame.Surface((1000, 800))
        font = pygame.font.Font(None, 20)
        panel.draw(surface, font)
        self.assertEqual({"apple", "cherry", "plum"}, set(panel.card_rects))
        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": panel.card_rects["plum"].center},
        )))
        self.assertEqual("plum", panel.take_selection())

    def test_maturity_window_loss_and_productive_lifetime(self):
        tree = self._plant_plum()
        tree["age_weeks"] = 2 * 52 - 1
        synchronize_tree_season(tree, 3, 34)
        self.assertFalse(is_tree_harvestable(tree))

        tree["age_weeks"] = 2 * 52
        synchronize_tree_season(tree, 3, 34)
        self.assertTrue(is_tree_harvestable(tree))
        tree["age_weeks"] += 4
        synchronize_tree_season(tree, 3, 38)
        self.assertTrue(is_tree_harvestable(tree))
        tree["age_weeks"] += 1
        synchronize_tree_season(tree, 3, 39)
        self.assertFalse(is_tree_harvestable(tree))
        self.assertEqual("lost", tree["annual_harvest_state"])
        self.assertIn(tree, self.orchard["trees"])

        tree["age_weeks"] = 25 * 52
        synchronize_tree_season(tree, 26, 34)
        self.assertTrue(is_tree_harvestable(tree))
        tree["age_weeks"] = 26 * 52
        synchronize_tree_season(tree, 27, 34)
        self.assertFalse(is_tree_harvestable(tree))

    def test_maturing_after_ripening_waits_until_next_year(self):
        tree = self._plant_plum()
        tree["age_weeks"] = 2 * 52
        synchronize_tree_season(tree, 3, 35)
        self.assertEqual("ineligible", tree["annual_harvest_state"])
        tree["age_weeks"] += 51
        synchronize_tree_season(tree, 4, 34)
        self.assertTrue(is_tree_harvestable(tree))

    def test_harvest_market_finances_graphic_and_highlight(self):
        tree = self._plant_plum()
        tree["age_weeks"] = 5 * 52
        synchronize_tree_season(tree, 6, 34)
        product = get_inventory_item_data("plum")
        self.assertEqual(10, product["price"])
        self.assertEqual(INCOME_ORCHARD_SALES, product["income_category"])
        self.assertIn("plum", get_marketable_item_ids())
        self.assertIn("Szüretelhető", get_tree_tooltip_lines(tree))

        surface = pygame.Surface((1000, 800))
        surface.fill((0, 0, 0))
        draw_orchard_trees(surface, self.buildings)
        self.assertEqual(
            FIELD_HARVEST_READY_BORDER_COLOR,
            surface.get_at((200, 250))[:3],
        )
        self.assertEqual(
            TREE_TYPES["plum"]["fruit_color"],
            surface.get_at((214, 273))[:3],
        )

        self.assertTrue(complete_tree_harvest(
            self.buildings, self.orchard, tree["slot"],
        ))
        self.assertEqual(20, get_total_inventory(self.buildings)["plum"])
        money_before = self.economy.money
        self.assertTrue(self.economy.sell_item(
            self.buildings, "plum", amount=20,
        ))
        self.assertEqual(200, self.economy.money - money_before)
        summary_rows = FinancialSummaryPanel()._column_rows(
            self.economy.get_financial_summary(52), "income",
        )
        self.assertIn(("detail", "  Szilva", 200), summary_rows)

    def test_mixed_orchard_and_save_load_round_trip(self):
        plant_tree(self.buildings, self.economy, 10, 10, "apple")
        plant_tree(self.buildings, self.economy, 10, 12, "cherry")
        plum = self._plant_plum(12, 10)
        plum["age_weeks"] = 7 * 52 + 4
        synchronize_tree_season(plum, 8, 34)
        state = GameState(
            self.world, [], self.buildings, self.economy, GameTime(),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mixed-plum.json"
            self.assertTrue(save_game(state, path))
            self.orchard["trees"].clear()
            self.assertTrue(load_game(state, path))
        loaded_orchard = next(
            item for item in state.buildings if item["type"] == "orchard"
        )
        self.assertEqual(["apple", "cherry", "plum"], [
            tree["type"] for tree in loaded_orchard["trees"]
        ])
        loaded_plum = loaded_orchard["trees"][2]
        self.assertEqual(7 * 52 + 4, loaded_plum["age_weeks"])

    def test_fruit_harvester_and_simulation_bot_support_plum(self):
        garage = {
            "type": "garage", "row": 2, "col": 2,
            "width": 4, "height": 4,
        }
        for col in range(2, 11):
            self.world[6][col] = ROAD
        for row in range(6, 10):
            self.world[row][10] = ROAD
        for col in range(10, 14):
            self.world[9][col] = ROAD
        self.buildings.append(garage)
        manager = VehicleManager()
        harvester = manager._create_managed_asset(
            VehicleType.FRUIT_HARVESTER, garage, 0,
        )
        harvester.ensure_idle_position(self.world, self.buildings)
        tree = self._plant_plum()
        tree["age_weeks"] = 2 * 52
        synchronize_tree_season(tree, 3, 34)
        self.assertTrue(manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.orchard, tree, current_ticks=0,
        ))

        bot = SimulationBot(91)
        bot.buildings.append(self.orchard)
        bot.state.buildings = bot.buildings
        bot.economy.money = 1000
        bot_tree = bot.plant_fruit_tree(12, 12, "plum")
        self.assertIsNotNone(bot_tree)
        self.assertEqual("plum", bot_tree["type"])
        self.assertEqual(
            "fruit_sales", SimulationBot._sale_income_category("plum"),
        )
        snapshot = bot.take_snapshot(bot.year)
        self.assertEqual(
            100, snapshot.expense_breakdown["fruit_tree_purchase"],
        )

    def test_simulation_bot_routes_ripe_plum_to_harvest_and_sale(self):
        bot = SimulationBot(92)
        tree = {
            "type": "plum", "slot": 0, "row": 10, "col": 10,
            "age_weeks": 2 * 52, "annual_harvest_state": "ripe",
        }
        orchard = {
            "type": "orchard", "row": 10, "col": 10,
            "width": 4, "height": 4, "trees": [tree],
        }
        bot.fields = []
        bot.buildings = [orchard]
        bot.vehicles = MagicMock()
        bot.vehicles.start_orchard_harvest.return_value = True
        bot.drain_vehicle_tasks = MagicMock()

        bot._harvest()

        bot.vehicles.start_orchard_harvest.assert_called_once_with(
            bot.world, bot.buildings, bot.economy,
            orchard, tree, current_ticks=bot.virtual_ticks,
        )
        bot.drain_vehicle_tasks.assert_called_once()

        warehouse = {
            "type": "warehouse", "row": 2, "col": 2,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {"plum": 20},
        }
        market = {
            "type": "market", "row": 2, "col": 10,
            "width": 4, "height": 3,
        }
        bot.buildings = [warehouse, market]
        bot.game_time.elapsed_weeks = 12
        money_before = bot.economy.money

        bot._sell_market_surplus()

        self.assertEqual(0, warehouse["inventory"]["plum"])
        self.assertEqual(200, bot.economy.money - money_before)
        self.assertEqual(20, bot.sold[bot.year]["plum"])
        snapshot = bot.take_snapshot(bot.year)
        self.assertEqual(200, snapshot.income_breakdown["fruit_sales"])


if __name__ == "__main__":
    unittest.main()
