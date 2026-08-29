import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buildings import get_total_inventory, place_building
from constants import GRASS
from economy import Economy
from financial_history import EXPENSE_FRUIT_TREE, INCOME_ORCHARD_SALES
from game_state import GameState
from inventory import get_inventory_item_data, get_marketable_item_ids
from orchards import (
    TREE_TYPES, complete_tree_harvest, draw_orchard_trees,
    get_tree_tooltip_lines, is_tree_harvestable, plant_tree,
    synchronize_tree_season,
)
from save_system import load_game, save_game
from screen_layout import set_camera, set_screen_size
from time_system import GameTime
from ui import FinancialSummaryPanel, OrchardSelectionPanel


class CherryTreeTests(unittest.TestCase):
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
            self.world, self.buildings, 30, 30, "market",
        )
        self.economy = Economy(2000)

    def test_catalog_selector_and_exact_planting_cost(self):
        cherry = TREE_TYPES["cherry"]
        self.assertEqual("Cseresznye", cherry["name"])
        self.assertEqual(250, cherry["planting_cost"])
        self.assertEqual(5, cherry["first_yield_age_years"])
        self.assertEqual(50, cherry["last_yield_age_years"])
        self.assertEqual((24, 28), (
            cherry["ripening_week"], cherry["harvest_end_week"],
        ))
        self.assertEqual(20, cherry["annual_yield"])

        panel = OrchardSelectionPanel()
        panel.open()
        self.assertEqual({"apple", "cherry", "plum"}, set(panel.card_rects))
        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": panel.card_rects["cherry"].center},
        )))
        self.assertEqual("cherry", panel.take_selection())

        before = self.economy.money
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "cherry",
        )
        self.assertIsNotNone(tree)
        self.assertEqual(250, before - self.economy.money)
        purchase = self.economy.financial_history[-1]
        self.assertEqual(EXPENSE_FRUIT_TREE, purchase["category"])
        self.assertEqual("cherry", purchase["subcategory"])
        self.assertEqual(250, purchase["amount"])
        self.assertEqual(1, len(self.economy.financial_history))

    def test_apple_and_cherry_can_share_the_same_orchard(self):
        apple = plant_tree(
            self.buildings, self.economy, 10, 10, "apple",
        )
        cherry = plant_tree(
            self.buildings, self.economy, 10, 12, "cherry",
        )
        self.assertEqual({"apple", "cherry"}, {
            apple["type"], cherry["type"],
        })
        self.assertEqual({0, 1}, {apple["slot"], cherry["slot"]})

    def test_five_year_maturity_and_24_to_28_week_window(self):
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "cherry",
        )
        tree["age_weeks"] = 5 * 52
        synchronize_tree_season(tree, 6, 23)
        self.assertFalse(is_tree_harvestable(tree))
        synchronize_tree_season(tree, 6, 24)
        self.assertTrue(is_tree_harvestable(tree))
        tree["age_weeks"] += 4
        synchronize_tree_season(tree, 6, 28)
        self.assertTrue(is_tree_harvestable(tree))
        tree["age_weeks"] += 1
        synchronize_tree_season(tree, 6, 29)
        self.assertFalse(is_tree_harvestable(tree))
        self.assertEqual("lost", tree["annual_harvest_state"])
        synchronize_tree_season(tree, 7, 24)
        self.assertTrue(is_tree_harvestable(tree))

    def test_tree_maturing_after_week_24_waits_until_next_year(self):
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "cherry",
        )
        tree["age_weeks"] = 5 * 52
        synchronize_tree_season(tree, 6, 25)
        self.assertEqual("ineligible", tree["annual_harvest_state"])
        tree["age_weeks"] += 51
        synchronize_tree_season(tree, 7, 24)
        self.assertTrue(is_tree_harvestable(tree))

    def test_last_productive_age_is_50_inclusive(self):
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "cherry",
        )
        tree["age_weeks"] = 50 * 52
        synchronize_tree_season(tree, 51, 24)
        self.assertTrue(is_tree_harvestable(tree))
        tree["age_weeks"] = 51 * 52
        synchronize_tree_season(tree, 52, 24)
        self.assertFalse(is_tree_harvestable(tree))

    def test_harvest_market_and_financial_summary(self):
        product = get_inventory_item_data("cherry")
        self.assertIn("cherry", get_marketable_item_ids())
        self.assertEqual(20, product["price"])
        self.assertEqual(INCOME_ORCHARD_SALES, product["income_category"])
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "cherry",
        )
        tree["age_weeks"] = 5 * 52
        synchronize_tree_season(tree, 6, 24)
        self.assertTrue(complete_tree_harvest(
            self.buildings, self.orchard, tree["slot"],
        ))
        self.assertEqual(20, get_total_inventory(self.buildings)["cherry"])

        money_before_sale = self.economy.money
        self.assertTrue(self.economy.sell_item(
            self.buildings, "cherry", amount=20,
        ))
        self.assertEqual(400, self.economy.money - money_before_sale)
        self.assertEqual(0, get_total_inventory(self.buildings)["cherry"])
        sale = self.economy.financial_history[-1]
        self.assertEqual(INCOME_ORCHARD_SALES, sale["category"])
        self.assertEqual("cherry", sale["subcategory"])
        rows = FinancialSummaryPanel()._column_rows(
            self.economy.get_financial_summary(52), "income",
        )
        self.assertIn(("detail", "  Cseresznye", 400), rows)

    def test_graphic_tooltip_and_ripe_fruit_pixels(self):
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "cherry",
        )
        tree["age_weeks"] = 12 * 52
        synchronize_tree_season(tree, 13, 24)
        tooltip = get_tree_tooltip_lines(tree)
        self.assertIn("Cseresznyefa", tooltip)
        self.assertIn("Kor:", tooltip)
        self.assertIn("12 év", tooltip)
        self.assertIn("Szüretelhető", tooltip)
        self.assertIn("Szüreti időszak:", tooltip)
        self.assertIn("24–28. hét", tooltip)
        self.assertIn("Éves termés:", tooltip)
        self.assertIn("20 db Cseresznye", tooltip)

        surface = pygame.Surface((1000, 800))
        surface.fill((0, 0, 0))
        draw_orchard_trees(surface, self.buildings)
        fruit_pixel = (214, 273)
        self.assertEqual(
            TREE_TYPES["cherry"]["fruit_color"],
            surface.get_at(fruit_pixel)[:3],
        )
        self.assertTrue(complete_tree_harvest(
            self.buildings, self.orchard, tree["slot"],
        ))
        surface.fill((0, 0, 0))
        draw_orchard_trees(surface, self.buildings)
        self.assertNotEqual(
            TREE_TYPES["cherry"]["fruit_color"],
            surface.get_at(fruit_pixel)[:3],
        )

    def test_mixed_orchard_save_load_round_trip(self):
        plant_tree(self.buildings, self.economy, 10, 10, "apple")
        cherry = plant_tree(
            self.buildings, self.economy, 10, 12, "cherry",
        )
        cherry["age_weeks"] = 8 * 52 + 7
        synchronize_tree_season(cherry, 9, 24)
        state = GameState(
            self.world, [], self.buildings, self.economy,
            GameTime(start_ticks=0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mixed-orchard.json"
            self.assertTrue(save_game(state, path))
            self.orchard["trees"].clear()
            self.assertTrue(load_game(state, path))
        loaded_orchard = next(
            item for item in state.buildings if item["type"] == "orchard"
        )
        self.assertEqual(["apple", "cherry"], [
            tree["type"] for tree in loaded_orchard["trees"]
        ])
        loaded_cherry = loaded_orchard["trees"][1]
        self.assertEqual(8 * 52 + 7, loaded_cherry["age_weeks"])
        synchronize_tree_season(loaded_cherry, 9, 24)
        self.assertEqual("ripe", loaded_cherry["annual_harvest_state"])


if __name__ == "__main__":
    unittest.main()
