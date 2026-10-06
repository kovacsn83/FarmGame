import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pygame
from buildings import place_building, get_total_inventory
from animals import purchase_and_place_animal, can_place_animal, run_weekly_animal_cycle, animal_pen_demolition_block_reason
from constants import ROAD, GRASS
from economy import Economy
from feed_mill import run_weekly_feed_mills, yard_tiles
from game_state import GameState
from save_system import save_game, load_game
from time_system import GameTime, TIME_SLOW
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType
from ui import InfoPanel


class FeedMillOperationTests(unittest.TestCase):
    def setUp(self):
        self.world = [[ROAD] * 50 for _ in range(40)]
        self.buildings = []
        self.warehouse = place_building(self.world, self.buildings, 2, 10, "warehouse")
        self.mill = place_building(self.world, self.buildings, 15, 18, "feed_mill")
        self.animals = []
        self.economy = Economy(100000)
        self.inventory = self.mill["processing_inventory"]

    def flock(self, count):
        for row, col in sorted(yard_tiles(self.mill)):
            if len(self.animals) == count:
                break
            purchase_and_place_animal(self.animals, self.buildings, self.economy,
                                      row, col, "chicken")
        self.assertEqual(len(self.animals), count)

    def week(self, week):
        run_weekly_feed_mills(self.world, self.buildings, self.animals,
                             self.economy, None, week)
        return run_weekly_animal_cycle(self.animals, self.buildings, self.economy)

    def test_recipe_leftovers_and_same_week_production(self):
        self.flock(4)
        self.inventory.update(wheat=5, corn=5)
        result = self.week(1)
        self.assertEqual(self.inventory, {"wheat": 0, "corn": 0, "chicken_feed": 8})
        self.assertEqual(result["fed_animals"], 4)
        self.assertEqual(get_total_inventory(self.buildings)["egg"], 4)
        self.assertEqual(self.mill["bonus_tenths"]["egg"], 4)

    def test_partial_feed_pauses_entire_flock_then_resumes(self):
        self.flock(12)
        self.inventory["chicken_feed"] = 8
        self.assertEqual(self.week(1)["fed_animals"], 0)
        self.assertEqual(self.inventory["chicken_feed"], 8)
        self.assertTrue(all(a["age_weeks"] == 0 for a in self.animals))
        self.inventory.update(wheat=5, corn=5)
        self.assertEqual(self.week(2)["fed_animals"], 12)
        self.assertTrue(all(a["age_weeks"] == 1 for a in self.animals))

    def test_ten_weeks_keep_exact_bonus(self):
        self.flock(1)
        self.inventory["chicken_feed"] = 10
        for week in range(1, 11):
            self.week(week)
        self.assertEqual(get_total_inventory(self.buildings)["egg"], 11)
        self.assertEqual(self.mill["bonus_tenths"]["egg"], 0)

    def test_meat_bonus_survives_starvation_and_death(self):
        self.flock(2)
        self.inventory["chicken_feed"] = 52
        self.week(1)
        saved = self.inventory["chicken_feed"]
        self.inventory["chicken_feed"] = 0
        self.week(2)
        self.inventory["chicken_feed"] = saved
        for week in range(3, 28):
            self.week(week)
        self.assertEqual(self.animals, [])
        self.assertEqual(get_total_inventory(self.buildings)["chicken_meat"], 13)
        self.assertEqual(self.mill["bonus_tenths"]["chicken_meat"], 2)

    def test_yard_limit_species_and_demolition(self):
        self.flock(12)
        row, col = sorted(yard_tiles(self.mill))[-1]
        self.assertFalse(can_place_animal(self.animals, self.buildings, row, col, "chicken"))
        self.assertFalse(can_place_animal([], self.buildings, row, col, "pig"))
        self.assertFalse(can_place_animal([], self.buildings, 21, 19, "chicken"))
        self.assertIsNotNone(animal_pen_demolition_block_reason(self.mill, self.buildings, self.animals))

    def test_storage_reserves_output_and_week_is_idempotent(self):
        self.inventory.update(wheat=5, corn=5, chicken_feed=190)
        self.week(1)
        self.assertEqual(self.inventory["chicken_feed"], 190)
        self.inventory["chicken_feed"] = 0
        self.week(2)
        run_weekly_feed_mills(self.world, self.buildings, [], self.economy, None, 2)
        self.assertEqual(self.inventory["chicken_feed"], 12)

    def test_save_load_animals_inventory_bonus_and_week(self):
        self.flock(1)
        self.inventory["chicken_feed"] = 12
        self.week(1)
        state = GameState(self.world, [], self.buildings, self.economy,
                          GameTime(start_ticks=0), animals=self.animals)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mill.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))
        loaded = next(b for b in state.buildings if b["type"] == "feed_mill")
        self.assertEqual(loaded["bonus_tenths"]["egg"], 1)
        self.assertEqual(loaded["processing_inventory"]["chicken_feed"], 11)
        self.assertEqual(state.animals[0]["age_weeks"], 1)

    def test_freight_is_real_and_pending_tasks_survive_save(self):
        garage = place_building(self.world, self.buildings, 2, 2, "garage")
        self.warehouse["inventory"].update(wheat=5, corn=5)
        manager = VehicleManager()
        tractor = manager._create_managed_asset(VehicleType.TRACTOR, garage, 0)
        manager._create_managed_asset(VehicleType.TRAILER, garage, 1)
        time = GameTime(current_time_speed=TIME_SLOW, start_ticks=0)
        state = GameState(self.world, [], self.buildings, self.economy, time, vehicles=manager)
        manager.ensure_idle_positions(self.world, self.buildings)
        run_weekly_feed_mills(self.world, self.buildings, [], self.economy, manager, 1, current_ticks=0)
        self.assertEqual(sum(self.mill["processing_in_transit"].values()), 10)
        self.assertEqual(self.inventory["wheat"], 0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "freight.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))
        for tick in range(100, 200001, 100):
            state.vehicles.update(state.world, state.buildings, state.economy,
                                  state.game_time, current_ticks=tick)
            if all(a.is_idle for a in state.vehicles.tractors) and not state.vehicles.task_queue:
                break
        mill = next(b for b in state.buildings if b["type"] == "feed_mill")
        self.assertEqual(mill["processing_inventory"]["wheat"], 5)
        self.assertEqual(mill["processing_inventory"]["corn"], 5)

    def test_no_vehicle_means_no_purchase_or_virtual_delivery(self):
        before = self.economy.money
        run_weekly_feed_mills(self.world, self.buildings, [], self.economy, VehicleManager(), 1)
        self.assertEqual(self.economy.money, before)
        self.assertEqual(sum(self.inventory.values()), 0)

    def test_market_purchase_charges_inputs_and_delivery_once(self):
        from inventory import get_inventory_item_data
        garage = place_building(self.world, self.buildings, 2, 2, "garage")
        manager = VehicleManager()
        manager._create_managed_asset(VehicleType.TRACTOR, garage, 0)
        manager._create_managed_asset(VehicleType.TRAILER, garage, 1)
        manager.ensure_idle_positions(self.world, self.buildings)
        before = self.economy.money
        run_weekly_feed_mills(self.world, self.buildings, [], self.economy, manager, 1, current_ticks=0)
        expected = sum((get_inventory_item_data(item)["price"] + 3) * 5
                       for item in ("wheat", "corn"))
        self.assertEqual(before - self.economy.money, expected)
        self.assertEqual(sum(self.mill["processing_in_transit"].values()), 10)
        self.assertEqual(sum(self.inventory.values()), 0)
        run_weekly_feed_mills(self.world, self.buildings, [], self.economy, manager, 2, current_ticks=0)
        self.assertEqual(before - self.economy.money, expected)

    def test_missing_ingredient_does_not_consume_other(self):
        self.inventory.update(wheat=5, corn=4)
        self.week(1)
        self.assertEqual(self.inventory, {"wheat": 5, "corn": 4, "chicken_feed": 0})

    def test_storage_block_keeps_fraction_until_meat_can_be_stored(self):
        from animals import retry_waiting_animal_slaughters
        self.flock(1)
        self.animals[0]["age_weeks"] = 25
        self.mill["bonus_tenths"]["chicken_meat"] = 6
        self.inventory["chicken_feed"] = 1
        self.warehouse["inventory"]["wheat"] = 494
        self.week(1)
        self.assertEqual(len(self.animals), 1)
        self.assertEqual(self.mill["bonus_tenths"]["chicken_meat"], 6)
        self.warehouse["inventory"]["wheat"] = 0
        retry_waiting_animal_slaughters(self.animals, self.buildings)
        self.assertEqual(self.animals, [])
        self.assertEqual(self.warehouse["inventory"]["chicken_meat"], 7)
        self.assertEqual(self.mill["bonus_tenths"]["chicken_meat"], 2)

    def test_information_panel(self):
        pygame.init()
        state = GameState(self.world, [], self.buildings, self.economy, GameTime(start_ticks=0))
        panel = InfoPanel()
        panel.open_for_building(self.mill)
        panel.draw(pygame.Surface((1500, 1000)), pygame.font.Font(None, 24), state)
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
