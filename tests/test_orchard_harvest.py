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
from constants import GRASS, ROAD
from economy import Economy
from game_state import GameState
from orchards import (
    get_tree_in_slot, is_tree_harvestable, plant_tree,
    synchronize_tree_season,
)
from save_system import load_game, save_game
from time_system import GameTime, TIME_SLOW
from tractor import TRACTOR_IDLE, TRACTOR_WORKING_ORCHARD
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class OrchardHarvestWorkflowTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        self.world = [[GRASS for _ in range(40)] for _ in range(30)]
        self.buildings = []
        self.garage = place_building(
            self.world, self.buildings, 2, 2, "garage",
        )
        self.warehouse = place_building(
            self.world, self.buildings, 2, 20, "warehouse",
        )
        self.first_orchard = place_building(
            self.world, self.buildings, 10, 10, "orchard",
        )
        self.inner_orchard = place_building(
            self.world, self.buildings, 10, 14, "orchard",
        )
        for col in range(2, 21):
            self.world[1][col] = ROAD
        for row in range(1, 10):
            self.world[row][10] = ROAD

        self.economy = Economy(5000)
        self.manager = VehicleManager()
        self.harvester = self.manager._create_managed_asset(
            VehicleType.FRUIT_HARVESTER, self.garage, 0,
        )
        self.harvester.ensure_idle_position(self.world, self.buildings)
        self.game_time = GameTime(TIME_SLOW, start_ticks=0)
        # 4. év, 30. hét: az Almafa szezonális szüreti időszaka.
        self.game_time.elapsed_weeks = 3 * 52 + 29
        self.tree = plant_tree(
            self.buildings, self.economy, 10, 14, "apple",
        )
        self.tree["age_weeks"] = 3 * 52
        synchronize_tree_season(self.tree, 4, 30)

    def _run_until_idle(self, start_tick=0, limit=30000):
        for tick in range(start_tick + 100, start_tick + limit, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if self.harvester.state == TRACTOR_IDLE:
                return tick
        self.fail("A Gyümölcs szüretelőgép nem tért vissza a Garázsba.")

    def test_mature_inner_tree_is_harvested_by_fruit_harvester(self):
        self.assertTrue(is_tree_harvestable(self.tree))
        self.assertTrue(self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree, current_ticks=0,
        ))
        self.assertIs(self.harvester.current_task.field, self.inner_orchard)
        self.assertEqual("orchard_harvest", self.harvester.current_task.task_type)
        self.assertEqual(self.tree["slot"], self.harvester.current_task.tree_slot)

        self._run_until_idle()
        self.assertEqual(20, get_total_inventory(self.buildings)["apple"])
        self.assertEqual(3, self.tree["last_produced_year"])
        self.assertFalse(is_tree_harvestable(self.tree))
        self.assertIs(self.harvester.assigned_parking_building, self.garage)

    def test_immature_harvested_and_duplicate_tree_are_rejected(self):
        self.tree["age_weeks"] = 2 * 52
        self.assertFalse(self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree,
        ))
        self.tree["age_weeks"] = 3 * 52
        synchronize_tree_season(self.tree, 4, 30)
        self.assertTrue(self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree,
        ))
        self.assertFalse(self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree,
        ))
        self._run_until_idle()
        self.assertFalse(self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree,
        ))

    def test_busy_harvester_leaves_second_tree_in_fifo_queue(self):
        second_tree = plant_tree(
            self.buildings, self.economy, 12, 14, "apple",
        )
        second_tree["age_weeks"] = 3 * 52
        synchronize_tree_season(second_tree, 4, 30)
        self.assertTrue(self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree,
        ))
        self.assertTrue(self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, second_tree,
        ))
        self.assertEqual(1, len(self.manager.task_queue))
        self.assertEqual(second_tree["slot"], self.manager.task_queue[0].tree_slot)
        self._run_until_idle(limit=50000)
        self.assertEqual(40, get_total_inventory(self.buildings)["apple"])

    def test_tree_becomes_harvestable_again_next_year(self):
        self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree,
        )
        self._run_until_idle()
        self.tree["age_weeks"] = 4 * 52
        synchronize_tree_season(self.tree, 5, 30)
        self.assertTrue(is_tree_harvestable(self.tree))

    def test_vehicle_and_warehouse_capacity_are_required(self):
        empty_manager = VehicleManager()
        self.assertFalse(empty_manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree,
        ))
        self.warehouse["inventory"]["wheat"] = self.warehouse["capacity"]
        self.assertFalse(self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree,
        ))
        self.assertEqual(0, len(self.manager.task_queue))

    def test_active_orchard_harvest_continues_after_save_and_load(self):
        queued_tree = plant_tree(
            self.buildings, self.economy, 12, 14, "apple",
        )
        queued_tree["age_weeks"] = 3 * 52
        synchronize_tree_season(queued_tree, 4, 30)
        self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, self.tree, current_ticks=0,
        )
        self.manager.start_orchard_harvest(
            self.world, self.buildings, self.economy,
            self.inner_orchard, queued_tree, current_ticks=0,
        )
        last_tick = 0
        for tick in range(100, 10000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            last_tick = tick
            if self.harvester.state == TRACTOR_WORKING_ORCHARD:
                break
        self.assertEqual(TRACTOR_WORKING_ORCHARD, self.harvester.state)
        saved_wait = self.harvester.current_task.remaining_wait_ms
        state = GameState(
            self.world, [], self.buildings, self.economy, self.game_time,
            vehicles=self.manager,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orchard-harvest.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))

        self.harvester = next(
            vehicle for vehicle in self.manager.vehicles
            if vehicle.vehicle_type == VehicleType.FRUIT_HARVESTER
        )
        self.inner_orchard = next(
            building for building in state.buildings
            if building.get("type") == "orchard" and building["col"] == 14
        )
        self.tree = get_tree_in_slot(self.inner_orchard, 0)
        self.assertEqual(TRACTOR_WORKING_ORCHARD, self.harvester.state)
        self.assertEqual(saved_wait, self.harvester.current_task.remaining_wait_ms)
        self.assertEqual(1, len(self.manager.task_queue))
        self.assertEqual(queued_tree["slot"], self.manager.task_queue[0].tree_slot)
        self._run_until_idle(start_tick=last_tick)
        self.assertEqual(40, get_total_inventory(state.buildings)["apple"])
        self.assertEqual(3, self.tree["last_produced_year"])


if __name__ == "__main__":
    unittest.main()
