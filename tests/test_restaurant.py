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
    RESTAURANT_MAX_LEVEL, RestaurantSystem, get_restaurant_period,
    get_restaurant_sellable_item_ids, get_restaurant_unit_price,
)
from notification_system import NotificationManager
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
            system.run_weekly([plant], economy, 1),
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
        self.assertEqual((), system.run_weekly([_plant()], economy, 1))
        self.assertTrue(system.is_enabled("cheese"))
        self.assertEqual([], economy.financial_history)
        self.assertEqual(100, economy.money)

    def test_level_controls_demand_and_partial_stock_is_partial_fulfillment(self):
        system = RestaurantSystem()
        system.level = 5
        system.toggle("cheese")
        plant = _plant(cheese=3)
        economy = Economy(starting_money=0)
        self.assertEqual(("cheese",), system.run_weekly([plant], economy, 1))
        self.assertEqual(10, system.period_requested_units)
        self.assertEqual(3, system.period_fulfilled_units)
        self.assertEqual(0, plant["processing_inventory"]["cheese"])
        self.assertAlmostEqual(48.6, economy.money)

    def test_weekly_quantity_matches_levels_one_five_and_ten(self):
        system = RestaurantSystem()
        for level in (1, 5, 10):
            with self.subTest(level=level):
                system.level = level
                self.assertEqual(level, system.weekly_quantity_per_product)

    def test_unchecked_product_counts_as_requested_but_not_fulfilled(self):
        system = RestaurantSystem()
        system.level = 2
        system.toggle("canned_tomato")
        system.run_weekly([_plant(canned_tomato=10, cheese=10)], Economy(0), 1)
        self.assertEqual(4, system.period_requested_units)
        self.assertEqual(2, system.period_fulfilled_units)

    def test_calendar_periods_are_four_fixed_thirteen_week_ranges(self):
        self.assertEqual((0, 1, 13), get_restaurant_period(0))
        self.assertEqual((0, 1, 13), get_restaurant_period(12))
        self.assertEqual((1, 14, 26), get_restaurant_period(13))
        self.assertEqual((2, 27, 39), get_restaurant_period(26))
        self.assertEqual((3, 40, 52), get_restaurant_period(39))
        self.assertEqual((4, 1, 13), get_restaurant_period(52))

    def test_thirteen_week_evaluation_levels_up_and_notifies_once(self):
        system = RestaurantSystem()
        system.toggle("cheese")
        system.toggle("canned_tomato")
        plant = _plant(canned_tomato=100, cheese=100)
        notifications = NotificationManager(start_ticks=0)
        economy = Economy(0)
        for elapsed_week in range(1, 14):
            system.run_weekly(
                [plant], economy, elapsed_week, notifications,
            )
        self.assertEqual(2, system.level)
        self.assertEqual(0, system.period_requested_units)
        self.assertIn("2. szintre fejlődött", notifications.current_message)
        history_size = len(economy.financial_history)
        system.run_weekly([plant], economy, 13, notifications)
        self.assertEqual(2, system.level)
        self.assertEqual(history_size, len(economy.financial_history))

    def test_thresholds_and_level_bounds(self):
        scenarios = (
            (75, 100, 5, 6),
            (7499, 10000, 5, 5),
            (40, 100, 5, 5),
            (3999, 10000, 5, 4),
            (0, 100, 1, 1),
            (100, 100, RESTAURANT_MAX_LEVEL, RESTAURANT_MAX_LEVEL),
        )
        for fulfilled, requested, level, expected in scenarios:
            with self.subTest(fulfilled=fulfilled, requested=requested):
                system = RestaurantSystem()
                system.level = level
                system.period_requested_units = requested
                system.period_fulfilled_units = fulfilled
                system._evaluate_period(0)
                self.assertEqual(expected, system.level)

    def test_year_end_evaluates_once_and_next_year_starts_new_period(self):
        system = RestaurantSystem()
        economy = Economy(0)
        for elapsed_week in range(1, 53):
            system.run_weekly([_plant()], economy, elapsed_week)
        self.assertEqual(3, system.last_evaluated_period)
        self.assertEqual(1, system.level)
        system.run_weekly([_plant()], economy, 53)
        self.assertEqual(4, system.current_period_id)
        self.assertEqual(2, system.period_requested_units)

    def test_level_down_notification_is_emitted(self):
        system = RestaurantSystem()
        system.level = 5
        system.period_requested_units = 100
        system.period_fulfilled_units = 39
        notifications = NotificationManager(start_ticks=0)
        system._evaluate_period(7, notifications)
        self.assertEqual(4, system.level)
        self.assertIn("4. szintre csökkent", notifications.current_message)

    def test_settings_round_trip_and_legacy_default_is_off(self):
        system = RestaurantSystem()
        system.toggle("canned_tomato")
        restored = RestaurantSystem()
        restored.load_save_record(system.to_save_record())
        self.assertTrue(restored.is_enabled("canned_tomato"))
        self.assertFalse(restored.is_enabled("cheese"))
        restored.load_save_record(None)
        self.assertFalse(any(restored.auto_sell.values()))

    def test_previous_flat_checkbox_save_remains_compatible(self):
        restored = RestaurantSystem()
        restored.load_save_record({
            "cheese": True, "canned_tomato": False,
        })
        self.assertTrue(restored.is_enabled("cheese"))
        self.assertFalse(restored.is_enabled("canned_tomato"))
        self.assertEqual(1, restored.level)
        self.assertEqual(0, restored.period_requested_units)

    def test_settings_round_trip_through_game_save(self):
        original = SimulationBot(41)
        original.state.restaurant_system = RestaurantSystem()
        original.state.restaurant_system.toggle("cheese")
        original.state.restaurant_system.level = 4
        original.state.restaurant_system.period_requested_units = 20
        original.state.restaurant_system.period_fulfilled_units = 13
        original.state.restaurant_system.current_period_id = 2
        original.state.restaurant_system.last_processed_week = 30
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
        self.assertEqual(4, loaded.state.restaurant_system.level)
        self.assertEqual(20, loaded.state.restaurant_system.period_requested_units)
        self.assertEqual(13, loaded.state.restaurant_system.period_fulfilled_units)
        self.assertEqual(2, loaded.state.restaurant_system.current_period_id)
        self.assertEqual(30, loaded.state.restaurant_system.last_processed_week)


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
