import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from buildings import place_building, remove_item
from constants import GRASS, ROAD
from economy import Economy
from financial_history import EXPENSE_PROCESSING_INPUT, EXPENSE_SHIPPING
from inventory import get_marketable_item_ids
from processing import (
    PROCESSING_STATUS_NO_MONEY, PROCESSING_STATUS_STOPPED,
    PROCESSING_STORAGE_CAPACITY,
    complete_processing_batch, get_processing_in_transit,
    initialize_processing_plant, select_processing_recipe,
    start_processing_batch,
    run_weekly_processing_cycle,
)
from time_system import GameTime, TIME_SLOW
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class _ReservationManager:
    def start_processing_supply(
            self, world, buildings, plant, item_id, amount, current_ticks=None):
        if not remove_item(buildings, item_id, amount):
            return 0
        plant["processing_in_transit"][item_id] = (
            plant["processing_in_transit"].get(item_id, 0) + amount
        )
        return amount


class _CountingReservationManager(_ReservationManager):
    def __init__(self):
        self.requests = 0

    def start_processing_supply(self, *args, **kwargs):
        self.requests += 1
        return super().start_processing_supply(*args, **kwargs)


class ProcessingProductionTests(unittest.TestCase):
    def _plant(self):
        return initialize_processing_plant({
            "type": "processing_plant", "row": 15, "col": 18,
            "width": 6, "height": 5,
        })

    def test_weekly_capacity_and_partial_production(self):
        plant = self._plant()
        plant["processing_inventory"]["tomato"] = 8
        self.assertEqual(5, start_processing_batch(plant, 1))
        self.assertEqual(3, plant["processing_inventory"]["tomato"])
        self.assertEqual(0, plant["processing_inventory"]["canned_tomato"])
        self.assertEqual(0, start_processing_batch(plant, 1))
        self.assertEqual(0, complete_processing_batch(plant, 1))
        self.assertEqual(5, complete_processing_batch(plant, 2))
        self.assertEqual(3, start_processing_batch(plant, 2))
        self.assertEqual(3, complete_processing_batch(plant, 3))
        self.assertEqual(8, plant["processing_inventory"]["canned_tomato"])

    def test_partial_warehouse_supply_buys_only_market_shortage(self):
        plant = self._plant()
        warehouse = {
            "type": "warehouse", "row": 2, "col": 10,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {"tomato": 3},
        }
        economy = Economy(starting_money=1000)
        run_weekly_processing_cycle(
            [], [warehouse, plant], economy, _ReservationManager(), 1,
        )
        self.assertEqual(0, warehouse["inventory"]["tomato"])
        self.assertEqual(3, get_processing_in_transit(plant, "tomato"))
        self.assertEqual(2, plant["processing_inventory"]["tomato"])
        self.assertEqual(0, plant["processing_inventory"]["canned_tomato"])
        self.assertEqual(962, economy.money)
        categories = [item["category"] for item in economy.financial_history]
        self.assertEqual([EXPENSE_PROCESSING_INPUT, EXPENSE_SHIPPING], categories)

    def test_internal_storage_has_one_shared_200_item_limit(self):
        plant = self._plant()
        plant["processing_inventory"].update({
            "tomato": 60, "canned_tomato": 140,
        })
        self.assertEqual(PROCESSING_STORAGE_CAPACITY, sum(
            plant["processing_inventory"].values()
        ))
        self.assertEqual(5, start_processing_batch(plant, 1))
        self.assertEqual(195, sum(plant["processing_inventory"].values()))
        self.assertEqual(5, complete_processing_batch(plant, 2))

    def test_multiple_plants_keep_independent_inventory_and_no_money_waits(self):
        first, second = self._plant(), self._plant()
        second.update({"row": 24, "col": 18})
        first["processing_inventory"]["tomato"] = 5
        second["processing_inventory"]["tomato"] = 3
        self.assertEqual(5, start_processing_batch(first, 4))
        self.assertEqual(3, start_processing_batch(second, 4))
        self.assertEqual(5, complete_processing_batch(first, 5))
        self.assertEqual(3, complete_processing_batch(second, 5))
        self.assertEqual(5, first["processing_inventory"]["canned_tomato"])
        self.assertEqual(3, second["processing_inventory"]["canned_tomato"])

        empty = self._plant()
        run_weekly_processing_cycle(
            [], [empty], Economy(starting_money=0), _ReservationManager(), 1,
        )
        self.assertEqual(PROCESSING_STATUS_NO_MONEY, empty["processing_status"])
        self.assertEqual(0, empty["processing_inventory"]["canned_tomato"])
        self.assertNotIn("canned_tomato", get_marketable_item_ids())

    def test_after_startup_a_new_batch_starts_on_every_weekly_cycle(self):
        plant = self._plant()
        economy = Economy(starting_money=1000)
        manager = _ReservationManager()
        run_weekly_processing_cycle([], [plant], economy, manager, 1)
        self.assertEqual(0, plant["processing_inventory"]["canned_tomato"])
        self.assertIsNotNone(plant["processing_batch"])
        run_weekly_processing_cycle([], [plant], economy, manager, 2)
        self.assertEqual(5, plant["processing_inventory"]["canned_tomato"])
        self.assertIsNotNone(plant["processing_batch"])
        run_weekly_processing_cycle([], [plant], economy, manager, 3)
        self.assertEqual(10, plant["processing_inventory"]["canned_tomato"])
        self.assertIsNotNone(plant["processing_batch"])

    def test_stopped_plant_finishes_current_batch_without_new_procurement(self):
        plant = self._plant()
        plant["processing_inventory"]["tomato"] = 5
        self.assertEqual(5, start_processing_batch(plant, 1))
        self.assertTrue(select_processing_recipe(plant, "canned_tomato"))
        self.assertIsNone(plant["active_recipe"])

        warehouse = {
            "type": "warehouse", "row": 2, "col": 10,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {"tomato": 20},
        }
        economy = Economy(starting_money=1000)
        manager = _CountingReservationManager()
        run_weekly_processing_cycle(
            [], [warehouse, plant], economy, manager, 2,
        )

        self.assertEqual(5, plant["processing_inventory"]["canned_tomato"])
        self.assertIsNone(plant["processing_batch"])
        self.assertEqual(PROCESSING_STATUS_STOPPED, plant["processing_status"])
        self.assertEqual(0, manager.requests)
        self.assertEqual(20, warehouse["inventory"]["tomato"])
        self.assertEqual(1000, economy.money)

        run_weekly_processing_cycle(
            [], [warehouse, plant], economy, manager, 3,
        )
        self.assertEqual(5, plant["processing_inventory"]["canned_tomato"])
        self.assertIsNone(plant["processing_batch"])
        self.assertEqual(0, manager.requests)

    def test_real_tractor_and_trailer_deliver_only_on_arrival(self):
        world = [[ROAD for _ in range(40)] for _ in range(40)]
        garage = {"type": "garage", "row": 2, "col": 2, "width": 4, "height": 4}
        warehouse = {
            "type": "warehouse", "row": 2, "col": 12,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {"tomato": 3},
        }
        plant = self._plant()
        buildings = [garage, warehouse, plant]
        manager = VehicleManager()
        tractor = manager._create_managed_asset(VehicleType.TRACTOR, garage, 0)
        manager._create_managed_asset(VehicleType.TRAILER, garage, 1)
        manager.ensure_idle_positions(world, buildings)
        economy = Economy()
        game_time = GameTime(current_time_speed=TIME_SLOW, start_ticks=0)

        self.assertEqual(3, manager.start_processing_supply(
            world, buildings, plant, "tomato", 3, current_ticks=0,
        ))
        self.assertEqual(0, manager.start_processing_supply(
            world, buildings, plant, "tomato", 1, current_ticks=0,
        ))
        self.assertEqual(0, warehouse["inventory"]["tomato"])
        self.assertEqual(0, plant["processing_inventory"]["tomato"])
        self.assertEqual(3, get_processing_in_transit(plant, "tomato"))
        for tick in range(100, 30000, 100):
            manager.update(world, buildings, economy, game_time, current_ticks=tick)
            if tractor.is_idle and tick > 100:
                break
        else:
            self.fail("A Feldolgozó üzem szállítása nem fejeződött be.")
        self.assertEqual(0, plant["processing_inventory"]["tomato"])
        self.assertEqual(0, get_processing_in_transit(plant, "tomato"))
        self.assertEqual(3, plant["processing_batch"]["outputs"]["canned_tomato"])
        self.assertEqual(10000, economy.money)


if __name__ == "__main__":
    unittest.main()
