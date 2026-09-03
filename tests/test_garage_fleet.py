import os
import sys
import tempfile
import unittest
from pathlib import Path
from copy import deepcopy

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from buildings import place_building, remove_building
from constants import GRASS, ROAD
from economy import Economy
from game_state import GameState
from garage_view import is_parked_in_garage
from save_system import save_game, load_game, _validate_vehicles
from time_system import GameTime
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType
from tractor import TASK_PLANTING


class GarageFleetTests(unittest.TestCase):
    def setUp(self):
        self.world = [[GRASS] * 45 for _ in range(30)]
        self.world[4] = [ROAD] * 45
        self.buildings = []
        self.manager = VehicleManager()
        self.economy = Economy()
        self.economy.money = 50000
        self.garages = [place_building(self.world, self.buildings, 5, 2 + 10*i, "garage") for i in range(3)]

    def buy(self, kind=VehicleType.TRACTOR):
        return self.manager.purchase_vehicle(self.world, self.buildings, self.economy, self.garages[0], kind)

    def test_shared_capacity_and_deterministic_assignment(self):
        for count in (1, 2, 3):
            self.assertEqual(self.manager.fleet_capacity(self.garages[:count])["capacity"], 4*count)
        for index in range(12):
            self.assertTrue(self.buy(VehicleType.TRAILER if index % 2 else VehicleType.TRACTOR))
            asset = max(self.manager.managed_assets, key=lambda a: a.vehicle_id)
            self.assertIs(asset.assigned_parking_building, self.garages[index // 4])
            self.assertEqual(asset.parking_slot_id, index % 4)
        self.manager.vehicles[0].state = "moving"
        before = self.economy.money
        self.assertFalse(self.buy())
        self.assertEqual(self.economy.money, before)
        self.assertEqual(self.manager.fleet_capacity(self.buildings)["free"], 0)
        candidates = self.manager.vehicles_for_task(TASK_PLANTING)
        self.assertEqual(len(candidates), 6)
        self.assertEqual(len({id(v) for v in candidates}), 6)

    def test_demolition_reassigns_idle_assets_atomically(self):
        for _ in range(6):
            self.assertTrue(self.buy())
        garage = self.garages[0]
        self.assertIsNone(self.manager.demolition_block_reason(5, 2, garage, buildings=self.buildings))
        self.assertTrue(self.manager.prepare_garage_demolition(self.world, self.buildings, garage))
        self.assertTrue(remove_building(self.world, self.buildings, garage))
        slots = set()
        for asset in self.manager.managed_assets:
            self.assertIsNot(asset.assigned_parking_building, garage)
            self.assertTrue(is_parked_in_garage(asset))
            slots.add((id(asset.assigned_parking_building), asset.parking_slot_id))
        self.assertEqual(len(slots), 6)
        self.assertEqual(self.manager.fleet_capacity(self.buildings), {"capacity": 8, "owned": 6, "free": 2})
        self.assertIsNotNone(self.manager.demolition_block_reason(5, 12, self.garages[1], buildings=self.buildings))

    def test_active_home_garage_cannot_be_demolished(self):
        self.buy()
        self.manager.vehicles[0].state = "moving"
        self.assertFalse(self.manager.prepare_garage_demolition(self.world, self.buildings, self.garages[0]))
        self.assertIs(self.manager.vehicles[0].assigned_parking_building, self.garages[0])

    def test_save_load_preserves_home_slots_and_validation(self):
        for _ in range(5):
            self.buy()
        state = GameState(self.world, [], self.buildings, self.economy, GameTime(start_ticks=0), vehicles=self.manager)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fleet.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))
        self.assertEqual(self.manager.fleet_capacity(self.buildings)["owned"], 5)
        self.assertTrue(all(is_parked_in_garage(a) for a in self.manager.managed_assets))
        records = self.manager.save_records()
        data = {"buildings": self.buildings, "tractors": records}
        self.assertTrue(_validate_vehicles(data))
        bad = deepcopy(data)
        bad["tractors"][1]["slot_id"] = bad["tractors"][0]["slot_id"]
        self.assertFalse(_validate_vehicles(bad))
        bad = deepcopy(data)
        bad["tractors"][0]["parking_row"] = 99
        self.assertFalse(_validate_vehicles(bad))
