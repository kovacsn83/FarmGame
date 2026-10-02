import os
import sys
import tempfile
import unittest
from pathlib import Path
from copy import deepcopy

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pygame
from buildings import place_building, get_building_maintenance_base
from constants import ROAD, GRASS
from economy import Economy
from game_state import GameState
from game_rules import UPGRADES
from inventory import get_inventory_item_data
from processing import (apply_processing_upgrades, initialize_processing_plant,
    get_processing_recipe_ids, get_processing_lines, get_processing_weekly_capacity,
    select_processing_recipe, start_processing_batch, complete_processing_batch,
    run_weekly_processing_cycle)
from restaurant import RestaurantSystem, get_restaurant_sellable_item_ids, is_valid_restaurant_save_record
from save_system import save_game, load_game
from time_system import GameTime, TIME_SLOW
from ui import InfoPanel, RestaurantPanel
from screen_layout import set_screen_size
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType

LEVEL_TWO = {"processing_plant_level_2"}
LEVEL_THREE = LEVEL_TWO | {"processing_plant_level_3"}


class ProcessingLevelThreeTests(unittest.TestCase):
    def plant(self, upgrades=LEVEL_THREE):
        plant = initialize_processing_plant({"type": "processing_plant", "active_recipe": None})
        apply_processing_upgrades([plant], upgrades)
        return plant

    def test_recipe_unlocks_capacity_and_maintenance(self):
        for upgrades, recipes, capacity, maintenance in (
            (set(), ("cheese", "mayonnaise"), 5, 3000),
            (LEVEL_TWO, ("cheese", "mayonnaise", "canned_tomato", "apple_juice"), 10, 6000),
            (LEVEL_THREE, ("cheese", "mayonnaise", "canned_tomato", "apple_juice", "kefir", "plum_jam"), 18, 12000),
        ):
            plant = self.plant(upgrades)
            self.assertEqual(get_processing_recipe_ids(plant), recipes)
            self.assertEqual(get_processing_weekly_capacity(plant), capacity)
            self.assertEqual(get_building_maintenance_base(plant), maintenance)

    def test_new_products_are_one_to_one_and_marketable(self):
        for recipe, ingredient, price in (("kefir", "goat_milk", 22), ("plum_jam", "plum", 20)):
            plant = self.plant()
            self.assertTrue(select_processing_recipe(plant, recipe))
            plant["processing_inventory"][ingredient] = 8
            self.assertEqual(start_processing_batch(plant, 1), 6)
            self.assertEqual(plant["processing_inventory"][ingredient], 2)
            self.assertEqual(complete_processing_batch(plant, 2), 6)
            economy = Economy(0)
            self.assertTrue(economy.sell_item([plant], recipe))
            self.assertEqual(economy.money, 6 * price)
            self.assertEqual(get_inventory_item_data(recipe)["price"], price)

    def test_three_lines_produce_eighteen_and_upgrade_is_idempotent(self):
        plant = self.plant()
        for index in range(3):
            select_processing_recipe(plant, "cheese", index)
        plant["processing_inventory"]["milk"] = 18
        self.assertEqual(start_processing_batch(plant, 1), 18)
        before = deepcopy(plant)
        apply_processing_upgrades([plant], LEVEL_THREE)
        self.assertEqual(plant, before)
        self.assertEqual(complete_processing_batch(plant, 2), 18)

    def test_legacy_locked_recipe_finishes_batch_without_new_selection(self):
        plant = self.plant(LEVEL_TWO)
        select_processing_recipe(plant, "canned_tomato")
        plant["processing_inventory"]["tomato"] = 10
        start_processing_batch(plant, 1)
        batch = deepcopy(plant["processing_batch"])
        apply_processing_upgrades([plant], set())
        self.assertIsNone(plant["active_recipe"])
        self.assertEqual(plant["processing_batch"], batch)
        self.assertEqual(complete_processing_batch(plant, 2), 5)
        self.assertEqual(start_processing_batch(plant, 2), 0)
        self.assertEqual(plant["processing_inventory"]["tomato"], 5)

    def test_upgrade_requires_both_farmhouse_four_and_processing_two(self):
        house = {"type": "farmhouse", "farmhouse_level": 3}
        state = GameState([[GRASS]], [], [house], Economy(20000), GameTime(start_ticks=0))
        self.assertFalse(state.economy.purchase_upgrade(state, "processing_plant_level_3"))
        house["farmhouse_level"] = 4
        self.assertFalse(state.economy.purchase_upgrade(state, "processing_plant_level_3"))
        state.purchased_upgrades.add("processing_plant_level_2")
        self.assertTrue(state.economy.purchase_upgrade(state, "processing_plant_level_3"))
        self.assertEqual(state.economy.money, 8000)
        self.assertFalse(state.economy.purchase_upgrade(state, "processing_plant_level_3"))
        self.assertEqual(UPGRADES["processing_plant_level_3"]["tree_column"], 4)

    def test_restaurant_demand_uses_only_level_products(self):
        for level, count in ((1, 2), (3, 2), (4, 4), (6, 4), (7, 6), (8, 6)):
            system = RestaurantSystem()
            system.level = level
            self.assertEqual(len(get_restaurant_sellable_item_ids(level)), count)
            system.run_weekly([], Economy(0), 1)
            self.assertEqual(system.period_requested_units, count * level)
        system = RestaurantSystem()
        self.assertFalse(system.toggle("kefir"))
        self.assertFalse(system.toggle("canned_tomato"))

    def test_legacy_restaurant_nine_and_ten_load_as_eight(self):
        for level in (9, 10):
            system = RestaurantSystem()
            record = system.to_save_record()
            record["level"] = level
            record["auto_sell"]["cheese"] = True
            record["period_requested_units"] = 100
            record["period_fulfilled_units"] = 80
            self.assertTrue(is_valid_restaurant_save_record(record))
            system.load_save_record(record)
            self.assertEqual(system.level, 8)
            self.assertTrue(system.is_enabled("cheese"))
            self.assertEqual(system.period_requested_units, 100)

    def test_new_restaurant_products_sell_and_account_at_level_seven(self):
        plant = self.plant()
        plant["processing_inventory"].update(kefir=7, plum_jam=7)
        system = RestaurantSystem()
        system.level = 7
        system.toggle("kefir")
        system.toggle("plum_jam")
        economy = Economy(0)
        self.assertEqual(system.run_weekly([plant], economy, 1), ("kefir", "plum_jam"))
        self.assertAlmostEqual(economy.money, 7 * (22 + 20) * 1.32 - 14 * 3)
        self.assertEqual(system.period_requested_units, 42)
        self.assertEqual(system.period_fulfilled_units, 14)

    def test_real_six_unit_delivery_and_save_load_three_lines(self):
        world = [[ROAD] * 40 for _ in range(40)]
        buildings = []
        garage = place_building(world, buildings, 2, 2, "garage")
        place_building(world, buildings, 2, 10, "warehouse")
        plant = place_building(world, buildings, 15, 18, "processing_plant")
        manager = VehicleManager()
        tractor = manager._create_managed_asset(VehicleType.TRACTOR, garage, 0)
        manager._create_managed_asset(VehicleType.TRAILER, garage, 1)
        state = GameState(world, [], buildings, Economy(10000),
                          GameTime(current_time_speed=TIME_SLOW, start_ticks=0),
                          vehicles=manager, purchased_upgrades=LEVEL_THREE)
        select_processing_recipe(plant, "kefir")
        manager.ensure_idle_positions(world, buildings)
        run_weekly_processing_cycle(world, buildings, state.economy, manager, 1, current_ticks=0)
        self.assertEqual(plant["processing_in_transit"]["goat_milk"], 6)
        self.assertEqual(tractor.current_task.resource_amount, 6)
        for tick in range(100, 100001, 100):
            manager.update(world, buildings, state.economy, state.game_time, current_ticks=tick)
            if tractor.is_idle and not manager.task_queue:
                break
        self.assertEqual(plant["processing_batch"]["outputs"], {"kefir": 6})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "three.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))
        loaded = next(b for b in state.buildings if b["type"] == "processing_plant")
        self.assertEqual(get_processing_weekly_capacity(loaded), 18)
        self.assertEqual(loaded["processing_batch"]["outputs"], {"kefir": 6})

    def test_restaurant_scroll_reaches_sixth_product_without_clickthrough(self):
        pygame.init()
        set_screen_size(800, 700)
        screen = pygame.Surface((800, 700))
        font = pygame.font.Font(None, 24)
        system = RestaurantSystem()
        system.level = 8
        panel = RestaurantPanel()
        panel.open(system)
        panel.draw(screen, font, [])
        self.assertGreater(panel.max_scroll, 0)
        self.assertTrue(panel.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-100)))
        panel.draw(screen, font, [])
        self.assertIn("plum_jam", panel.checkbox_rects)
        self.assertFalse(system.is_enabled("plum_jam"))
        rect = panel.checkbox_rects["plum_jam"]
        self.assertTrue(panel.rect.contains(rect))
        panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        self.assertTrue(system.is_enabled("plum_jam"))
        pygame.quit()

    def test_eighteen_same_input_is_split_into_three_physical_deliveries(self):
        world = [[ROAD] * 40 for _ in range(40)]
        buildings = []
        garage = place_building(world, buildings, 2, 2, "garage")
        warehouse = place_building(world, buildings, 2, 10, "warehouse")
        warehouse["inventory"]["milk"] = 18
        plant = place_building(world, buildings, 15, 18, "processing_plant")
        plant["active_recipe"] = None
        manager = VehicleManager()
        tractor = manager._create_managed_asset(VehicleType.TRACTOR, garage, 0)
        manager._create_managed_asset(VehicleType.TRAILER, garage, 1)
        state = GameState(world, [], buildings, Economy(10000),
                          GameTime(current_time_speed=TIME_SLOW, start_ticks=0),
                          vehicles=manager, purchased_upgrades=LEVEL_THREE)
        for index in range(3):
            select_processing_recipe(plant, "cheese", index)
        manager.ensure_idle_positions(world, buildings)
        run_weekly_processing_cycle(world, buildings, state.economy, manager, 1, current_ticks=0)
        self.assertEqual(plant["processing_in_transit"]["milk"], 18)
        tasks = [tractor.current_task, *manager.task_queue]
        self.assertEqual([task.resource_amount for task in tasks], [6, 6, 6])
        self.assertEqual(warehouse["inventory"]["milk"], 0)
        for tick in range(100, 200001, 100):
            manager.update(world, buildings, state.economy, state.game_time, current_ticks=tick)
            if tractor.is_idle and not manager.task_queue:
                break
        self.assertEqual(complete_processing_batch(plant, 2), 18)
        self.assertEqual(state.economy.money, 10000)

    def test_two_plants_six_products_reach_seventy_five_percent_at_level_eight(self):
        plants = [self.plant(), self.plant()]
        ids = get_restaurant_sellable_item_ids(8)
        for index, product in enumerate(ids):
            plants[index // 3]["processing_inventory"][product] = 6
        system = RestaurantSystem()
        system.level = 8
        for product in ids:
            system.toggle(product)
        system.run_weekly(plants, Economy(0), 1)
        self.assertEqual(system.period_requested_units, 48)
        self.assertEqual(system.period_fulfilled_units, 36)
        self.assertEqual(system.period_ratio, 0.75)

    def test_three_selector_columns_show_all_six_recipes_without_scroll(self):
        pygame.init()
        set_screen_size(1000, 800)
        screen = pygame.Surface((1000, 800))
        font = pygame.font.Font(None, 24)
        plant = self.plant()
        state = GameState([[GRASS]], [], [plant], Economy(), GameTime(start_ticks=0),
                          purchased_upgrades=LEVEL_THREE)
        panel = InfoPanel()
        panel.open_for_building(plant)
        panel.draw(screen, font, state)
        self.assertLessEqual(panel.rect.height, 800)
        self.assertEqual(panel.processing_recipe_max_scroll, 0)
        self.assertEqual(len(panel.processing_recipe_rects), 18)
        for rect in panel.processing_recipe_rects.values():
            self.assertTrue(panel.rect.contains(rect))
        panel.processing_recipe_scroll = panel.processing_recipe_max_scroll
        panel.draw(screen, font, state)
        self.assertIn(("plum_jam", 2), panel.processing_recipe_rects)
        for index, recipe in enumerate(("apple_juice", "kefir", "plum_jam")):
            rect = panel.processing_recipe_rects[(recipe, index)]
            panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        self.assertEqual([line["active_recipe"] for line in get_processing_lines(plant)],
                         ["apple_juice", "kefir", "plum_jam"])
        pygame.quit()
