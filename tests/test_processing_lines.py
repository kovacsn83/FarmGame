import os
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pygame

from buildings import place_building
from constants import GRASS, ROAD
from economy import Economy
from game_state import GameState
from processing import (
    PROCESSING_UPGRADE_ID, apply_processing_upgrades,
    complete_processing_batch, get_processing_lines,
    get_processing_inventory_used, get_processing_available_capacity,
    get_processing_weekly_capacity, initialize_processing_plant,
    receive_processing_delivery, run_weekly_processing_cycle,
    select_processing_recipe, start_processing_batch,
)
from save_system import load_game, save_game, _validate_inventory
from screen_layout import set_screen_size
from time_system import GameTime, TIME_SLOW
from ui import InfoPanel
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class ProcessingLineTests(unittest.TestCase):
    def plant(self, upgraded=True):
        plant = initialize_processing_plant({"type": "processing_plant"})
        apply_processing_upgrades([plant], {PROCESSING_UPGRADE_ID} if upgraded else set())
        return plant

    def test_level_one_unchanged_and_second_line_locked(self):
        plant = self.plant(False)
        self.assertEqual(len(get_processing_lines(plant)), 1)
        self.assertEqual(get_processing_weekly_capacity(plant), 5)
        self.assertEqual(plant["processing_capacity"], 200)
        self.assertFalse(select_processing_recipe(plant, "cheese", 1))

    def test_global_upgrade_preserves_inventory_batch_and_selection(self):
        plants = [self.plant(False), self.plant(False)]
        plants[0]["processing_inventory"]["tomato"] = 150
        start_processing_batch(plants[0], 2)
        batch = deepcopy(plants[0]["processing_batch"])
        inventory = deepcopy(plants[0]["processing_inventory"])
        apply_processing_upgrades(plants, {PROCESSING_UPGRADE_ID})
        apply_processing_upgrades(plants, {PROCESSING_UPGRADE_ID})
        for plant in plants:
            self.assertEqual(len(get_processing_lines(plant)), 2)
            self.assertEqual(plant["processing_capacity"], 400)
            self.assertEqual(get_processing_weekly_capacity(plant), 10)
            self.assertIsNone(get_processing_lines(plant)[1]["active_recipe"])
        self.assertEqual(plants[0]["processing_batch"], batch)
        self.assertEqual(plants[0]["processing_inventory"], inventory)

    def test_two_same_products_share_input_deterministically(self):
        for stock, expected in ((20, 10), (7, 7), (3, 3), (0, 0)):
            with self.subTest(stock=stock):
                plant = self.plant()
                select_processing_recipe(plant, "cheese", 0)
                select_processing_recipe(plant, "cheese", 1)
                plant["processing_inventory"]["milk"] = stock
                self.assertEqual(start_processing_batch(plant, 1), expected)
                self.assertEqual(start_processing_batch(plant, 1), 0)
                self.assertEqual(complete_processing_batch(plant, 1), 0)
                self.assertEqual(complete_processing_batch(plant, 2), expected)
                self.assertEqual(complete_processing_batch(plant, 2), 0)
                self.assertEqual(plant["processing_inventory"]["cheese"], expected)
                self.assertEqual(plant["processing_inventory"]["milk"], stock - expected)

    def test_different_products_and_one_or_no_selected_line(self):
        plant = self.plant()
        select_processing_recipe(plant, "mayonnaise", 1)
        plant["processing_inventory"].update(tomato=20, egg=20)
        self.assertEqual(start_processing_batch(plant, 1), 10)
        self.assertEqual(complete_processing_batch(plant, 2), 10)
        self.assertEqual(plant["processing_inventory"]["canned_tomato"], 5)
        self.assertEqual(plant["processing_inventory"]["mayonnaise"], 5)
        select_processing_recipe(plant, "canned_tomato", 0)
        self.assertEqual(start_processing_batch(plant, 2), 5)
        select_processing_recipe(plant, "mayonnaise", 1)
        self.assertEqual(complete_processing_batch(plant, 3), 5)
        self.assertEqual(start_processing_batch(plant, 3), 0)

    def test_shared_storage_reserves_pending_outputs(self):
        plant = self.plant()
        select_processing_recipe(plant, "canned_tomato", 1)
        plant["processing_inventory"].update(cheese=397, tomato=3)
        self.assertEqual(start_processing_batch(plant, 1), 3)
        self.assertEqual(get_processing_available_capacity(plant), 0)
        self.assertEqual(receive_processing_delivery(plant, "egg", 5), 0)
        self.assertEqual(complete_processing_batch(plant, 2), 3)
        self.assertEqual(get_processing_inventory_used(plant), 400)

    def test_blocked_completed_product_is_not_lost(self):
        plant = self.plant()
        plant["processing_inventory"]["tomato"] = 5
        start_processing_batch(plant, 1)
        plant["processing_inventory"]["cheese"] = 398
        self.assertEqual(complete_processing_batch(plant, 2), 0)
        self.assertIsNotNone(plant["processing_batch"])
        plant["processing_inventory"]["cheese"] = 395
        self.assertEqual(complete_processing_batch(plant, 2), 5)

    def test_legacy_selected_product_is_first_line(self):
        plant = {"type": "processing_plant", "selected_product": "cheese"}
        apply_processing_upgrades([plant], {PROCESSING_UPGRADE_ID})
        self.assertEqual(get_processing_lines(plant)[0]["active_recipe"], "cheese")
        self.assertIsNone(get_processing_lines(plant)[1]["active_recipe"])

    def test_both_line_batches_and_selection_survive_save_load(self):
        world = [[GRASS] * 40 for _ in range(35)]
        buildings = []
        plant = place_building(world, buildings, 8, 8, "processing_plant")
        state = GameState(world, [], buildings, Economy(), GameTime(start_ticks=0),
                          purchased_upgrades={PROCESSING_UPGRADE_ID})
        select_processing_recipe(plant, "cheese", 1)
        plant["processing_inventory"].update(tomato=5, milk=3, apple_juice=220)
        start_processing_batch(plant, 1)
        expected = deepcopy(plant)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lines.json"
            self.assertTrue(save_game(state, path))
            plant["additional_processing_lines"].clear()
            self.assertTrue(load_game(state, path))
        plant = buildings[0]
        self.assertEqual(plant["processing_inventory"], expected["processing_inventory"])
        self.assertEqual(plant["additional_processing_lines"], expected["additional_processing_lines"])
        self.assertEqual(complete_processing_batch(plant, 2), 8)

    def test_invalid_second_line_is_rejected(self):
        plant = self.plant()
        self.assertTrue(_validate_inventory(plant))
        get_processing_lines(plant)[1]["active_recipe"] = "unknown"
        self.assertFalse(_validate_inventory(plant))

    def test_real_two_product_market_deliveries_and_continuous_weeks(self):
        world = [[ROAD] * 40 for _ in range(40)]
        buildings = []
        garage = place_building(world, buildings, 2, 2, "garage")
        place_building(world, buildings, 2, 10, "market")
        plant = place_building(world, buildings, 15, 18, "processing_plant")
        apply_processing_upgrades(buildings, {PROCESSING_UPGRADE_ID})
        select_processing_recipe(plant, "cheese", 1)
        manager = VehicleManager()
        tractor = manager._create_managed_asset(VehicleType.TRACTOR, garage, 0)
        manager._create_managed_asset(VehicleType.TRAILER, garage, 1)
        manager.ensure_idle_positions(world, buildings)
        economy = Economy(10000)
        game_time = GameTime(current_time_speed=TIME_SLOW, start_ticks=0)
        state = GameState(world, [], buildings, economy, game_time,
                          vehicles=manager, purchased_upgrades={PROCESSING_UPGRADE_ID})
        tick = 0
        for week in (1, 2, 3):
            run_weekly_processing_cycle(world, buildings, economy, manager, week, current_ticks=tick)
            self.assertEqual(plant["processing_in_transit"], {"tomato": 5, "milk": 5})
            self.assertTrue(all(line["processing_batch"] is None for line in get_processing_lines(plant)))
            if week == 1:
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "two-deliveries.json"
                    self.assertTrue(save_game(state, path))
                    self.assertTrue(load_game(state, path))
                plant = next(item for item in buildings if item["type"] == "processing_plant")
                tractor = manager.tractors[0]
            for _ in range(1000):
                tick += 100
                manager.update(world, buildings, economy, game_time, current_ticks=tick)
                if tractor.is_idle and not manager.task_queue:
                    break
            else:
                self.fail("A két alapanyagfuvar nem ért vissza.")
            self.assertTrue(all(line["processing_batch"] is not None for line in get_processing_lines(plant)))
        self.assertEqual(plant["processing_inventory"]["cheese"], 10)
        self.assertEqual(plant["processing_inventory"]["canned_tomato"], 10)
        self.assertEqual(economy.money, 10000 - 3 * (5 * (16 + 3) + 5 * (8 + 3)))

    def test_same_input_requirements_are_combined_and_not_reordered(self):
        plant = self.plant()
        select_processing_recipe(plant, "cheese", 0)
        select_processing_recipe(plant, "cheese", 1)
        requests = []

        class DeliveryRecorder:
            def start_processing_market_supply(self, world, buildings, target,
                                               item_id, amount, economy, **kwargs):
                requests.append((item_id, amount))
                target["processing_in_transit"][item_id] = amount
                return amount

        manager = DeliveryRecorder()
        for _ in range(2):
            run_weekly_processing_cycle([], [plant], Economy(), manager, 1)
        self.assertEqual(requests, [("milk", 10)])
        receive_processing_delivery(plant, "milk", 10)
        self.assertEqual(complete_processing_batch(plant, 2), 10)

    def test_newly_built_plant_gets_existing_global_upgrade(self):
        state = GameState([[0]], [], [], Economy(), GameTime(start_ticks=0),
                          purchased_upgrades={PROCESSING_UPGRADE_ID})
        state.buildings.append(self.plant(False))
        state.synchronize_processing_upgrades()
        self.assertEqual(get_processing_weekly_capacity(state.buildings[0]), 10)


class ProcessingLineUiTests(unittest.TestCase):
    def test_independent_checkbox_columns_and_capacity(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        set_screen_size(1000, 800)
        plant = initialize_processing_plant({"type": "processing_plant"})
        state = GameState([[0]], [], [plant], Economy(), GameTime(start_ticks=0),
                          purchased_upgrades={PROCESSING_UPGRADE_ID})
        panel = InfoPanel()
        panel.open_for_building(plant)
        surface = pygame.Surface((1000, 800))
        font = pygame.font.Font(None, 24)
        with patch.object(panel, "draw_text", wraps=panel.draw_text) as draw:
            panel.draw(surface, font, state)
        texts = [call.args[2] for call in draw.call_args_list]
        self.assertIn("Heti kapacitás: 10 db", texts)
        self.assertIn("Üzemi raktár: 0 / 400", texts)
        self.assertEqual(len(panel.processing_recipe_rects), 8)
        for line_index in (0, 1):
            rect = panel.processing_recipe_rects[("cheese", line_index)]
            panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                               {"button": 1, "pos": rect.center}))
        self.assertEqual([line["active_recipe"] for line in get_processing_lines(plant)], ["cheese", "cheese"])
        panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                           {"button": 1, "pos": rect.center}))
        self.assertEqual([line["active_recipe"] for line in get_processing_lines(plant)], ["cheese", None])


if __name__ == "__main__":
    unittest.main()
