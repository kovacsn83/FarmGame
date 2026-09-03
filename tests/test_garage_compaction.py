import unittest
from copy import deepcopy
import test_garage_fleet as fleet_tests
from buildings import place_building, remove_building, apply_garage_upgrades
from constants import GRASS, ROAD
from garage_view import is_parked_in_garage
from tractor import find_building_parking
from vehicle_types import VehicleType


class GarageCompactionTests(fleet_tests.GarageFleetTests):
    def fragmented(self):
        self.world = [[GRASS] * 90 for _ in range(30)]
        self.world[4] = [ROAD] * 90
        self.buildings = []
        self.garages = [place_building(self.world, self.buildings, 5, 2+10*i, "garage") for i in range(7)]
        for i in range(27):
            asset = self.manager._create_managed_asset(
                VehicleType.TRAILER if i % 3 == 0 else VehicleType.TRACTOR,
                self.garages[i // 4], i % 4)
            asset.ensure_idle_position(self.world, self.buildings)
        apply_garage_upgrades(self.buildings, {"garage_level_2"})

    def test_twenty_seven_compact_atomic_idempotent_and_demolition(self):
        self.fragmented()
        self.assertTrue(self.manager.compact_garage_assignments(self.world, self.buildings))
        self.assertEqual([len(self.manager.assets_in_garage(g)) for g in self.garages], [8,8,8,3,0,0,0])
        slots = {(id(a.assigned_parking_building), a.parking_slot_id) for a in self.manager.managed_assets}
        self.assertEqual(len(slots), 27)
        self.assertTrue(all(is_parked_in_garage(a) for a in self.manager.managed_assets))
        records = deepcopy(self.manager.save_records())
        self.assertTrue(self.manager.compact_garage_assignments(self.world, self.buildings))
        self.assertEqual(records, self.manager.save_records())
        for garage in self.garages[:3]:
            self.assertTrue(self.manager.prepare_garage_demolition(self.world, self.buildings, garage))
            remove_building(self.world, self.buildings, garage)
        before = deepcopy(self.manager.save_records())
        self.assertFalse(self.manager.prepare_garage_demolition(self.world, self.buildings, self.garages[3]))
        self.assertEqual(before, self.manager.save_records())
        self.assertEqual(self.manager.fleet_capacity(self.buildings)["capacity"], 32)

    def test_active_task_route_untouched_then_returns_to_new_home(self):
        self.fragmented()
        vehicle = self.manager.vehicles[-1]
        old_home = vehicle.assigned_parking_building
        vehicle.state = "working_field"
        task = object()
        vehicle.current_task = task
        vehicle.path = [(4, 60), (4, 61)]
        vehicle.next_path_index = 1
        vehicle.row, vehicle.col = 4, 60
        before = (vehicle.world_x, vehicle.world_y, vehicle.path.copy(), vehicle.state)
        self.manager.compact_garage_assignments(self.world, self.buildings)
        self.assertIs(vehicle.current_task, task)
        self.assertEqual(before, (vehicle.world_x, vehicle.world_y, vehicle.path, vehicle.state))
        self.assertIsNot(vehicle.assigned_parking_building, old_home)
        vehicle.current_task = None
        vehicle.begin_return_home(self.world, self.buildings, current_ticks=0)
        self.assertEqual(vehicle.path[-1], find_building_parking(self.world, vehicle.assigned_parking_building))

    def test_already_returning_keeps_route_until_old_destination(self):
        self.fragmented()
        vehicle = self.manager.vehicles[-1]
        old_tile = vehicle.parking_tile
        vehicle.state = "returning_home"
        vehicle.path = [(4, 50), old_tile]
        before = vehicle.path.copy()
        self.manager.compact_garage_assignments(self.world, self.buildings)
        self.assertEqual(vehicle.path, before)
        vehicle._set_tile_position(*old_tile)
        vehicle._arrive_home(self.world, None, 0)
        self.assertEqual(vehicle.path[-1], find_building_parking(self.world, vehicle.assigned_parking_building))
