import tempfile
import unittest
from pathlib import Path
from copy import deepcopy

from test_garage_fleet import GarageFleetTests
from buildings import place_building, remove_building, get_garage_capacity, get_garage_parking_position
from game_rules import UPGRADES, get_upgrade_status
from game_state import GameState
from garage_view import parking_slot_rects, parking_view_height
from save_system import save_game, load_game, _create_save_data, _validate_vehicles
from time_system import GameTime
from vehicle_types import VehicleType
import pygame


class GarageUpgradeTests(GarageFleetTests):
    def state(self, level=2):
        farmhouse = place_building(self.world, self.buildings, 15, 2, "farmhouse")
        farmhouse["farmhouse_level"] = level
        return GameState(self.world, [], self.buildings, self.economy,
                         GameTime(start_ticks=0), vehicles=self.manager)

    def test_purchase_prerequisite_cost_and_global_effect(self):
        state = self.state(1)
        self.assertTrue(get_upgrade_status("garage_level_2", set(), 1).startswith("Zárolt"))
        self.assertFalse(self.economy.purchase_upgrade(state, "garage_level_2"))
        state.buildings[-1]["farmhouse_level"] = 2
        self.assertEqual(UPGRADES["garage_level_2"]["price"], 3000)
        self.assertEqual(get_upgrade_status("garage_level_2", set(), 2), "Fejleszthető")
        positions = [get_garage_parking_position(self.garages[0], i) for i in range(4)]
        self.buy()
        vehicle_state = self.manager.vehicles[0].__dict__.copy()
        before_money = self.economy.money
        before_value = self.economy.calculate_net_farm_value(state)
        self.assertTrue(self.economy.purchase_upgrade(state, "garage_level_2"))
        self.assertEqual(self.economy.money, before_money - 3000)
        self.assertEqual(self.economy.calculate_net_farm_value(state), before_value)
        self.assertEqual(self.manager.vehicles[0].__dict__, vehicle_state)
        self.assertEqual([get_garage_parking_position(self.garages[0], i) for i in range(4)], positions)
        self.assertTrue(all(get_garage_capacity(g) == 8 for g in self.garages))
        self.assertFalse(self.economy.purchase_upgrade(state, "garage_level_2"))
        new = place_building(self.world, self.buildings, 15, 25, "garage")
        state.synchronize_processing_upgrades()
        self.assertEqual(get_garage_capacity(new), 8)
        self.assertEqual(self.manager.fleet_capacity(self.buildings)["capacity"], 32)

    def test_sixteen_units_save_and_demolition(self):
        remove_building(self.world, self.buildings, self.garages.pop())
        state = self.state()
        self.economy.purchase_upgrade(state, "garage_level_2")
        for i in range(16):
            self.assertTrue(self.buy(VehicleType.TRAILER if i % 2 else VehicleType.TRACTOR))
        self.assertEqual(self.manager.fleet_capacity(self.buildings)["capacity"], 16)
        self.assertEqual({a.parking_slot_id for a in self.manager.managed_assets}, set(range(8)))
        self.assertFalse(self.buy())
        self.assertFalse(self.manager.prepare_garage_demolition(self.world, self.buildings, self.garages[0]))
        data = _create_save_data(state)
        self.assertTrue(all("_garage_level" not in b for b in data["buildings"]))
        self.assertTrue(_validate_vehicles(data))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "upgraded.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))
        self.assertEqual(self.manager.fleet_capacity(self.buildings)["capacity"], 16)
        self.assertEqual(len(self.manager.managed_assets), 16)
        self.manager.vehicles[0].state = "moving"
        self.assertFalse(self.buy())

    def test_eight_slot_layout(self):
        slots = parking_slot_rects(pygame.Rect(0, 0, 400, parking_view_height(8)), 8)
        self.assertEqual(len({s.x for s in slots}), 4)
        self.assertEqual(len({s.y for s in slots}), 2)
        self.assertTrue(all(s.size == (36, 36) for s in slots))

    def test_seven_assets_can_move_to_one_upgraded_garage(self):
        remove_building(self.world, self.buildings, self.garages.pop())
        state = self.state()
        self.economy.purchase_upgrade(state, "garage_level_2")
        for i in range(7):
            self.buy(VehicleType.TRAILER if i % 2 else VehicleType.TRACTOR)
        old_home = self.garages[0]
        self.assertTrue(self.manager.prepare_garage_demolition(self.world, self.buildings, old_home))
        self.assertTrue(remove_building(self.world, self.buildings, old_home))
        self.assertEqual(self.manager.fleet_capacity(self.buildings), {"capacity": 8, "owned": 7, "free": 1})
        self.assertTrue(all(a.assigned_parking_building is self.garages[1] for a in self.manager.managed_assets))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "relocated.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))


if __name__ == "__main__":
    unittest.main()
