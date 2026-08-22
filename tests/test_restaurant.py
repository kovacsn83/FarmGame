import os
from pathlib import Path
import sys
import tempfile
import unittest


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pygame

from economy import Economy
from financial_history import EXPENSE_SHIPPING, INCOME_PROCESSED_PRODUCT_SALES
from processing import initialize_processing_plant
from restaurant import (
    RestaurantSystem, get_restaurant_sellable_item_ids,
    get_restaurant_unit_price,
)
from screen_layout import set_screen_size
from save_system import load_game, save_game
from simulation import SimulationBot
from ui import CityPanel, RestaurantPanel


def _plant(canned_tomato=0, cheese=0):
    plant = initialize_processing_plant({
        "type": "processing_plant", "row": 0, "col": 0,
        "width": 6, "height": 5,
    })
    plant["processing_inventory"]["canned_tomato"] = canned_tomato
    plant["processing_inventory"]["cheese"] = cheese
    return plant


class RestaurantSystemTests(unittest.TestCase):
    def test_catalog_and_dynamic_twenty_percent_premium(self):
        self.assertEqual(
            ("cheese", "canned_tomato"),
            get_restaurant_sellable_item_ids(),
        )
        self.assertEqual(19.2, get_restaurant_unit_price("cheese"))
        self.assertEqual(38.4, get_restaurant_unit_price("canned_tomato"))

    def test_selected_products_sell_one_each_and_book_shipping_separately(self):
        system = RestaurantSystem()
        system.toggle("cheese")
        system.toggle("canned_tomato")
        plant = _plant(canned_tomato=2, cheese=2)
        economy = Economy(starting_money=0)

        self.assertEqual(
            ("cheese", "canned_tomato"),
            system.run_weekly([plant], economy),
        )
        self.assertEqual(1, plant["processing_inventory"]["cheese"])
        self.assertEqual(1, plant["processing_inventory"]["canned_tomato"])
        self.assertAlmostEqual(51.6, economy.money)
        self.assertEqual(
            [INCOME_PROCESSED_PRODUCT_SALES, EXPENSE_SHIPPING,
             INCOME_PROCESSED_PRODUCT_SALES, EXPENSE_SHIPPING],
            [entry["category"] for entry in economy.financial_history],
        )

    def test_no_stock_keeps_checkbox_enabled_without_transaction(self):
        system = RestaurantSystem()
        system.toggle("cheese")
        economy = Economy(starting_money=100)
        self.assertEqual((), system.run_weekly([_plant()], economy))
        self.assertTrue(system.is_enabled("cheese"))
        self.assertEqual([], economy.financial_history)
        self.assertEqual(100, economy.money)

    def test_settings_round_trip_and_legacy_default_is_off(self):
        system = RestaurantSystem()
        system.toggle("canned_tomato")
        restored = RestaurantSystem()
        restored.load_save_record(system.to_save_record())
        self.assertTrue(restored.is_enabled("canned_tomato"))
        self.assertFalse(restored.is_enabled("cheese"))
        restored.load_save_record(None)
        self.assertFalse(any(restored.auto_sell.values()))

    def test_settings_round_trip_through_game_save(self):
        original = SimulationBot(41)
        original.state.restaurant_system = RestaurantSystem()
        original.state.restaurant_system.toggle("cheese")
        loaded = SimulationBot(42)
        loaded.state.restaurant_system = RestaurantSystem()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "restaurant.json"
            self.assertTrue(save_game(original.state, path))
            self.assertTrue(load_game(loaded.state, path))
        self.assertTrue(loaded.state.restaurant_system.is_enabled("cheese"))
        self.assertFalse(
            loaded.state.restaurant_system.is_enabled("canned_tomato")
        )


class RestaurantPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((900, 700))
        set_screen_size(900, 700)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_city_restaurant_is_enabled(self):
        service = next(
            item for item in CityPanel.SERVICES if item["id"] == "restaurant"
        )
        self.assertTrue(service["enabled"])

    def test_left_click_toggles_but_other_inputs_do_not(self):
        system = RestaurantSystem()
        panel = RestaurantPanel()
        panel.open(system)
        panel.draw(
            pygame.display.get_surface(), pygame.font.SysFont(None, 24),
            [_plant()],
        )
        rect = panel.checkbox_rects["cheese"]
        for button in (3, 4):
            panel.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, {"button": button, "pos": rect.center},
            ))
            self.assertFalse(system.is_enabled("cheese"))
        panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": rect.center},
        ))
        self.assertTrue(system.is_enabled("cheese"))

    def test_escape_and_outside_click_close_and_consume(self):
        panel = RestaurantPanel()
        panel.open(RestaurantSystem())
        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_ESCAPE},
        )))
        self.assertFalse(panel.visible)
        panel.open(RestaurantSystem())
        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (panel.rect.left - 1, panel.rect.top)},
        )))
        self.assertFalse(panel.visible)


if __name__ == "__main__":
    unittest.main()
