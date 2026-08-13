import sys
import json
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from animal_troughs import FOOD_STOCK_KEY, WATER_STOCK_KEY
from animal_automation import (
    AUTOMATED_FEEDING_UPGRADE, AUTOMATED_WATERING_UPGRADE,
    run_weekly_animal_supply_automation,
)
from constants import BUILDING, FIELD, ROAD
from economy import Economy
from game_state import GameState
from game_logger import get_logger
from quest_system import (
    QUEST_EVENT_FOOD_TROUGH_FILLED, QUEST_EVENT_WATER_TROUGH_FILLED,
)
from time_system import GameTime, TIME_SLOW
from save_system import load_game, save_game
from tractor import (
    TRACTOR_IDLE, TRACTOR_LOADING_SUPPLY, TRACTOR_MOVING_TO_TROUGH,
)
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class SupplyTaskIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.world = [[ROAD for _ in range(40)] for _ in range(40)]
        self.garage = {
            "type": "garage", "row": 2, "col": 2,
            "width": 4, "height": 4,
        }
        self.warehouse = {
            "type": "warehouse", "row": 2, "col": 12,
            "width": 5, "height": 4, "capacity": 500, "inventory": {},
        }
        self.pond = {
            "type": "pond", "row": 2, "col": 24,
            "width": 6, "height": 6,
        }
        self.market = {
            "type": "market", "row": 10, "col": 2,
            "width": 4, "height": 3,
        }
        self.pen = {
            "type": "animal_pen", "row": 15, "col": 12,
            "width": 4, "height": 4,
        }
        self.buildings = [
            self.garage, self.warehouse, self.pond, self.market, self.pen,
        ]
        self.animals = [
            {"type": "cattle", "pen_row": 15, "pen_col": 12,
             "row": 15, "col": 12},
            {"type": "cattle", "pen_row": 15, "pen_col": 12,
             "row": 15, "col": 13},
        ]
        self.economy = Economy()
        self.game_time = GameTime(current_time_speed=TIME_SLOW, start_ticks=0)
        self.manager = VehicleManager()
        self.tractor = self.manager._create_managed_asset(
            VehicleType.TRACTOR, self.garage, 0,
        )
        self.trailer = self.manager._create_managed_asset(
            VehicleType.TRAILER, self.garage, 1,
        )
        self.tank = self.manager._create_managed_asset(
            VehicleType.WATER_TANK, self.garage, 2,
        )
        self.manager.ensure_idle_positions(self.world, self.buildings)
        get_logger().reset()

    def _run_to_idle(self):
        attached_types = set()
        for tick in range(100, 30000, 100):
            if self.tractor.attached_implement is not None:
                attached_types.add(self.tractor.attached_implement.vehicle_type)
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if self.tractor.state == TRACTOR_IDLE and tick > 100:
                return attached_types
        self.fail("Az ellátási feladat nem fejeződött be időben.")

    def _run_all_to_idle(self):
        for tick in range(100, 60000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if all(vehicle.state == TRACTOR_IDLE for vehicle in self.manager.vehicles):
                return
        self.fail("A párhuzamos ellátási feladatok nem fejeződtek be időben.")

    def _add_pen(self, row, col, animal_count=2):
        pen = {
            "type": "animal_pen", "row": row, "col": col,
            "width": 4, "height": 4,
        }
        self.buildings.append(pen)
        for index in range(animal_count):
            self.animals.append({
                "type": "cattle", "pen_row": row, "pen_col": col,
                "row": row, "col": col + index,
            })
        return pen

    def _prepare_valid_save_state(self):
        """A mentésvalidátor számára is valós világcsempéket állít be."""
        for building in self.buildings:
            for row in range(building["row"], building["row"] + building["height"]):
                for col in range(building["col"], building["col"] + building["width"]):
                    self.world[row][col] = BUILDING
        return GameState(
            self.world, [], self.buildings, self.economy, self.game_time,
            vehicles=self.manager, animals=self.animals,
        )

    def _advance_until(self, predicate, start_tick=100, end_tick=30000):
        for tick in range(start_tick, end_tick, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if predicate():
                return tick
        self.fail("A várt járműállapot nem állt elő időben.")

    @staticmethod
    def _log_count(fragment):
        return sum(
            fragment in entry.message for entry in get_logger().entries
        )

    def test_feed_supply_uses_trailer_and_fills_only_after_delivery(self):
        quest_events = []
        self.manager.quest_event_handler = quest_events.append
        trough = {"type": "food", "group": [self.pen]}
        self.assertTrue(self.manager.start_trough_supply(
            self.world, self.buildings, self.economy, self.animals, trough,
            current_ticks=0,
        ))
        self.assertEqual(self.pen.get(FOOD_STOCK_KEY, 0), 0)
        attached = self._run_to_idle()
        self.assertIn(VehicleType.TRAILER, attached)
        self.assertEqual(self.pen[FOOD_STOCK_KEY], 16)
        self.assertFalse(self.trailer.is_attached)
        self.assertIsNone(self.tractor.current_task)
        self.assertEqual(quest_events, [QUEST_EVENT_FOOD_TROUGH_FILLED])

    def test_automated_feed_uses_the_real_trailer_pipeline(self):
        quest_events = []
        self.manager.quest_event_handler = quest_events.append
        self.pen[FOOD_STOCK_KEY] = 4
        self.assertEqual(run_weekly_animal_supply_automation(
            self.world, self.buildings, self.economy, self.animals,
            self.manager, {AUTOMATED_FEEDING_UPGRADE}, current_ticks=0,
        ), 1)
        attached = self._run_to_idle()
        self.assertIn(VehicleType.TRAILER, attached)
        self.assertEqual(self.pen[FOOD_STOCK_KEY], 16)
        self.assertEqual(quest_events, [])

    def test_automated_water_uses_the_real_tank_and_pond_pipeline(self):
        quest_events = []
        self.manager.quest_event_handler = quest_events.append
        self.pen[WATER_STOCK_KEY] = 4
        self.assertEqual(run_weekly_animal_supply_automation(
            self.world, self.buildings, self.economy, self.animals,
            self.manager, {AUTOMATED_WATERING_UPGRADE}, current_ticks=0,
        ), 1)
        attached = self._run_to_idle()
        self.assertIn(VehicleType.WATER_TANK, attached)
        self.assertEqual(self.pen[WATER_STOCK_KEY], 16)
        self.assertEqual(quest_events, [])

    def test_feed_cargo_is_loaded_at_warehouse_and_cleared_after_delivery(self):
        self.warehouse["inventory"]["alfalfa"] = 16
        starting_money = self.economy.money
        self.assertTrue(self.manager.start_trough_supply(
            self.world, self.buildings, self.economy, self.animals,
            {"type": "food", "group": [self.pen]}, current_ticks=0,
        ))
        for tick in range(100, 10000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if self.trailer.cargo_amount:
                break
        self.assertEqual(self.trailer.cargo_type, "alfalfa")
        self.assertEqual(self.trailer.cargo_amount, 16)
        self.assertEqual(self.warehouse["inventory"]["alfalfa"], 0)
        self.assertEqual(self.pen.get(FOOD_STOCK_KEY, 0), 0)
        self.assertEqual(self.economy.money, starting_money)
        self._run_to_idle()
        self.assertEqual(self.pen[FOOD_STOCK_KEY], 16)
        self.assertEqual(self.trailer.cargo_type, "empty")
        self.assertEqual(self.trailer.cargo_amount, 0)

    def test_deleted_active_feed_target_returns_cargo_to_warehouse(self):
        self.warehouse["inventory"]["alfalfa"] = 16
        self.assertTrue(self.manager.start_trough_supply(
            self.world, self.buildings, self.economy, self.animals,
            {"type": "food", "group": [self.pen]}, current_ticks=0,
        ))
        last_tick = 0
        for tick in range(100, 10000, 100):
            last_tick = tick
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if self.trailer.cargo_amount:
                break
        self.buildings.remove(self.pen)
        for tick in range(last_tick + 100, last_tick + 30000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if self.tractor.state == TRACTOR_IDLE:
                break
        self.assertEqual(self.warehouse["inventory"]["alfalfa"], 16)
        self.assertEqual(self.trailer.cargo_type, "empty")
        self.assertEqual(self.trailer.cargo_amount, 0)

    def test_water_supply_uses_tank_and_fills_only_after_delivery(self):
        quest_events = []
        self.manager.quest_event_handler = quest_events.append
        trough = {"type": "water", "group": [self.pen]}
        self.assertTrue(self.manager.start_trough_supply(
            self.world, self.buildings, self.economy, self.animals, trough,
            current_ticks=0,
        ))
        self.assertEqual(self.pen.get(WATER_STOCK_KEY, 0), 0)
        attached = self._run_to_idle()
        self.assertIn(VehicleType.WATER_TANK, attached)
        self.assertEqual(self.pen[WATER_STOCK_KEY], 16)
        self.assertFalse(self.tank.is_attached)
        self.assertIsNone(self.tractor.current_task)
        self.assertEqual(quest_events, [QUEST_EVENT_WATER_TROUGH_FILLED])

    def test_existing_field_watering_still_uses_water_tank(self):
        field = {
            "row": 25, "col": 12, "width": 4, "height": 4,
            "crop": "wheat", "growth": 20, "watered": False,
            "fertilized": False,
        }
        for row in range(25, 29):
            for col in range(12, 16):
                self.world[row][col] = FIELD
        self.assertTrue(self.manager.start_watering(
            self.world, self.buildings, self.economy, field,
            current_ticks=0,
        ))
        attached = self._run_to_idle()
        self.assertIn(VehicleType.WATER_TANK, attached)
        self.assertNotIn(VehicleType.TRAILER, attached)
        self.assertTrue(field["watered"])

    def test_busy_feed_pair_queues_and_reloads_at_warehouse_for_each_target(self):
        second_pen = self._add_pen(15, 22)
        third_pen = self._add_pen(25, 22)
        troughs = [
            {"type": "food", "group": [pen]}
            for pen in (self.pen, second_pen, third_pen)
        ]
        for trough in troughs:
            self.assertTrue(self.manager.start_trough_supply(
                self.world, self.buildings, self.economy, self.animals, trough,
                current_ticks=0,
            ))
        self.assertEqual(len(self.manager.task_queue), 2)
        self.assertEqual(second_pen["vehicle_task_status"], "waiting")
        self.assertFalse(self.manager.start_trough_supply(
            self.world, self.buildings, self.economy, self.animals, troughs[1],
            current_ticks=0,
        ))

        self._run_to_idle()
        for pen in (self.pen, second_pen, third_pen):
            self.assertEqual(pen[FOOD_STOCK_KEY], 16)
        self.assertEqual(self._log_count("megérkezett a Raktárhoz"), 3)
        self.assertEqual(self._log_count("felcsatolta a Pótkocsit"), 1)
        self.assertEqual(self._log_count("lecsatolta a Pótkocsit"), 1)

    def test_busy_water_pair_queues_and_chains_without_second_pond_visit(self):
        second_pen = self._add_pen(15, 22)
        for pen in (self.pen, second_pen):
            self.assertTrue(self.manager.start_trough_supply(
                self.world, self.buildings, self.economy, self.animals,
                {"type": "water", "group": [pen]}, current_ticks=0,
            ))
        self.assertEqual(len(self.manager.task_queue), 1)
        self._run_to_idle()
        self.assertEqual(self.pen[WATER_STOCK_KEY], 16)
        self.assertEqual(second_pen[WATER_STOCK_KEY], 16)
        self.assertEqual(self._log_count("megérkezett a Tóhoz"), 1)
        self.assertEqual(self._log_count("felcsatolta a Locsolótartályt"), 1)

    def test_two_field_watering_tasks_share_one_tank_fill(self):
        fields = []
        for top, left in ((25, 12), (25, 22)):
            field = {
                "row": top, "col": left, "width": 4, "height": 4,
                "crop": "wheat", "growth": 20, "watered": False,
                "fertilized": False,
            }
            fields.append(field)
            for row in range(top, top + 4):
                for col in range(left, left + 4):
                    self.world[row][col] = FIELD
            self.assertTrue(self.manager.start_watering(
                self.world, self.buildings, self.economy, field,
                current_ticks=0,
            ))
        self.assertEqual(len(self.manager.task_queue), 1)
        self._run_to_idle()
        self.assertTrue(all(field["watered"] for field in fields))
        self.assertEqual(
            self._log_count("feltöltötte a Locsolótartályt"), 1,
        )

    def test_switching_water_task_type_revisits_pond(self):
        field = {
            "row": 25, "col": 12, "width": 4, "height": 4,
            "crop": "wheat", "growth": 20, "watered": False,
            "fertilized": False,
        }
        for row in range(25, 29):
            for col in range(12, 16):
                self.world[row][col] = FIELD
        self.assertTrue(self.manager.start_trough_supply(
            self.world, self.buildings, self.economy, self.animals,
            {"type": "water", "group": [self.pen]}, current_ticks=0,
        ))
        self.assertTrue(self.manager.start_watering(
            self.world, self.buildings, self.economy, field, current_ticks=0,
        ))
        self._run_to_idle()
        self.assertEqual(self.pen[WATER_STOCK_KEY], 16)
        self.assertTrue(field["watered"])
        self.assertEqual(self._log_count("Locsolótartály feltöltve"), 1)
        self.assertEqual(self._log_count("feltöltötte a Locsolótartályt"), 1)

    def test_multiple_feed_pairs_work_in_parallel_and_finish_queue(self):
        second_garage = {
            "type": "garage", "row": 32, "col": 2,
            "width": 4, "height": 4,
        }
        self.buildings.append(second_garage)
        second_tractor = self.manager._create_managed_asset(
            VehicleType.TRACTOR, second_garage, 0,
        )
        second_trailer = self.manager._create_managed_asset(
            VehicleType.TRAILER, self.garage, 3,
        )
        second_tractor.ensure_idle_position(self.world, self.buildings)
        second_trailer.ensure_idle_position(self.world, self.buildings)
        pens = [self.pen, *(
            self._add_pen(row, col)
            for row, col in ((15, 22), (25, 12), (25, 22))
        )]
        for pen in pens:
            self.assertTrue(self.manager.start_trough_supply(
                self.world, self.buildings, self.economy, self.animals,
                {"type": "food", "group": [pen]}, current_ticks=0,
            ))
        active = [
            vehicle for vehicle in self.manager.tractors
            if vehicle.current_task is not None
        ]
        self.assertEqual(len(active), 2)
        self.assertEqual(len(self.manager.task_queue), 2)
        self._run_all_to_idle()
        self.assertTrue(all(pen[FOOD_STOCK_KEY] == 16 for pen in pens))
        self.assertFalse(second_trailer.is_attached)

    def test_chained_feed_tasks_switch_between_alfalfa_and_corn(self):
        pig_pen = {
            "type": "animal_pen", "row": 25, "col": 22,
            "width": 4, "height": 4,
        }
        self.buildings.append(pig_pen)
        self.animals.extend([
            {"type": "pig", "pen_row": 25, "pen_col": 22,
             "row": 25, "col": 22},
            {"type": "pig", "pen_row": 25, "pen_col": 22,
             "row": 25, "col": 23},
        ])
        for trough in (
            {"type": "food", "group": [self.pen]},
            {"type": "food", "group": [pig_pen]},
        ):
            self.assertTrue(self.manager.start_trough_supply(
                self.world, self.buildings, self.economy, self.animals,
                trough, current_ticks=0,
            ))
        self._run_to_idle()
        self.assertEqual(self.pen[FOOD_STOCK_KEY], 16)
        self.assertEqual(pig_pen[FOOD_STOCK_KEY], 16)
        self.assertEqual(self._log_count("Pótkocsi megrakodva: 16 Lucerna"), 1)
        self.assertEqual(self._log_count("Pótkocsi megrakodva: 16 Kukorica"), 1)
        self.assertEqual(self.trailer.cargo_type, "empty")

    def test_queued_target_that_becomes_full_is_discarded(self):
        second_pen = self._add_pen(15, 22)
        for pen in (self.pen, second_pen):
            self.assertTrue(self.manager.start_trough_supply(
                self.world, self.buildings, self.economy, self.animals,
                {"type": "food", "group": [pen]}, current_ticks=0,
            ))
        self.assertEqual(len(self.manager.task_queue), 1)
        second_pen[FOOD_STOCK_KEY] = 16
        self._run_to_idle()
        self.assertEqual(len(self.manager.task_queue), 0)
        self.assertNotIn("vehicle_task_status", second_pen)
        self.assertEqual(self._log_count("Etetővályú feltöltve:"), 1)

    def test_load_reset_removes_transient_queue_markers(self):
        second_pen = self._add_pen(15, 22)
        for pen in (self.pen, second_pen):
            self.assertTrue(self.manager.start_trough_supply(
                self.world, self.buildings, self.economy, self.animals,
                {"type": "food", "group": [pen]}, current_ticks=0,
            ))
        self.assertFalse(self.manager.can_save(self.world, self.buildings))
        records = self.manager.save_records()
        self.manager.reset_for_loaded_game(
            self.world, [], self.buildings, records,
        )
        self.assertEqual(len(self.manager.task_queue), 0)
        self.assertNotIn("vehicle_task_status", self.pen)
        self.assertNotIn("vehicle_task_status", second_pen)

    def test_active_feed_task_round_trips_without_duplicate_transaction(self):
        state = self._prepare_valid_save_state()
        self.warehouse["inventory"]["alfalfa"] = 16
        starting_money = self.economy.money
        self.assertTrue(self.manager.start_trough_supply(
            self.world, self.buildings, self.economy, self.animals,
            {"type": "food", "group": [self.pen]}, current_ticks=0,
        ))
        last_tick = self._advance_until(
            lambda: self.tractor.state == TRACTOR_MOVING_TO_TROUGH,
        )
        saved_position = (
            self.tractor.row, self.tractor.col,
            self.tractor.world_x, self.tractor.world_y,
            self.tractor.next_path_index,
        )
        self.assertEqual(self.trailer.cargo_amount, 16)
        self.assertEqual(self.warehouse["inventory"]["alfalfa"], 0)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "active-feed.json"
            self.assertTrue(save_game(state, path))
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsNotNone(document["vehicle_runtime"])
            self.assertTrue(load_game(state, path))

        tractor = self.manager.tractors[0]
        trailer = next(
            item for item in self.manager.implements
            if item.vehicle_type == VehicleType.TRAILER
        )
        warehouse = next(
            building for building in self.buildings
            if building["type"] == "warehouse"
        )
        pen = next(
            building for building in self.buildings
            if building["type"] == "animal_pen"
        )
        self.assertEqual(tractor.state, TRACTOR_MOVING_TO_TROUGH)
        self.assertEqual((
            tractor.row, tractor.col, tractor.world_x, tractor.world_y,
            tractor.next_path_index,
        ), saved_position)
        self.assertIs(tractor.attached_implement, trailer)
        self.assertIs(trailer.attached_to, tractor)
        self.assertEqual(trailer.cargo_amount, 16)
        self.assertEqual(warehouse["inventory"]["alfalfa"], 0)
        self.assertEqual(self.economy.money, starting_money)

        for tick in range(last_tick + 100, last_tick + 30000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if tractor.state == TRACTOR_IDLE:
                break
        self.assertEqual(pen[FOOD_STOCK_KEY], 16)
        self.assertEqual(warehouse["inventory"]["alfalfa"], 0)
        self.assertEqual(self.economy.money, starting_money)

    def test_supply_timer_and_fifo_queue_round_trip(self):
        second_pen = self._add_pen(15, 22)
        state = self._prepare_valid_save_state()
        self.warehouse["inventory"]["alfalfa"] = 32
        for pen in (self.pen, second_pen):
            self.assertTrue(self.manager.start_trough_supply(
                self.world, self.buildings, self.economy, self.animals,
                {"type": "food", "group": [pen]}, current_ticks=0,
            ))
        self.assertEqual(len(self.manager.task_queue), 1)
        last_tick = self._advance_until(
            lambda: self.tractor.state == TRACTOR_LOADING_SUPPLY,
        )
        self.manager.update(
            self.world, self.buildings, self.economy, self.game_time,
            current_ticks=last_tick + 100,
        )
        remaining_wait = self.tractor.current_task.remaining_wait_ms
        queued_order = self.manager.task_queue[0].creation_order

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "active-queue.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))

        tractor = self.manager.tractors[0]
        self.assertEqual(tractor.state, TRACTOR_LOADING_SUPPLY)
        self.assertEqual(tractor.current_task.remaining_wait_ms, remaining_wait)
        self.assertEqual(len(self.manager.task_queue), 1)
        self.assertEqual(self.manager.task_queue[0].creation_order, queued_order)
        self.assertIsNot(tractor.current_task, self.manager.task_queue[0])

        for tick in range(last_tick + 200, last_tick + 60000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if (tractor.state == TRACTOR_IDLE
                    and not self.manager.task_queue):
                break
        loaded_pens = [
            building for building in self.buildings
            if building["type"] == "animal_pen"
        ]
        self.assertEqual(
            [pen[FOOD_STOCK_KEY] for pen in loaded_pens], [16, 16],
        )

    def test_version_one_save_without_runtime_loads_safely_idle(self):
        state = self._prepare_valid_save_state()
        self.assertTrue(self.manager.start_trough_supply(
            self.world, self.buildings, self.economy, self.animals,
            {"type": "water", "group": [self.pen]}, current_ticks=0,
        ))
        self._advance_until(lambda: self.tractor.state != TRACTOR_IDLE)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-v1.json"
            self.assertTrue(save_game(state, path))
            document = json.loads(path.read_text(encoding="utf-8"))
            document["save_version"] = 1
            document.pop("vehicle_runtime", None)
            path.write_text(
                json.dumps(document, ensure_ascii=False), encoding="utf-8",
            )
            self.assertTrue(load_game(state, path))

        self.assertTrue(all(
            vehicle.state == TRACTOR_IDLE
            for vehicle in self.manager.vehicles
        ))
        self.assertFalse(self.manager.task_queue)

    def test_loaded_orphan_trailer_cargo_returns_to_inventory(self):
        self.trailer.cargo_type = "alfalfa"
        self.trailer.cargo_amount = 6
        records = self.manager.save_records()
        self.manager.reset_for_loaded_game(
            self.world, [], self.buildings, records,
        )
        loaded_trailer = next(
            asset for asset in self.manager.implements
            if asset.vehicle_type == VehicleType.TRAILER
        )
        self.assertEqual(self.warehouse["inventory"]["alfalfa"], 6)
        self.assertEqual(loaded_trailer.cargo_type, "empty")
        self.assertEqual(loaded_trailer.cargo_amount, 0)

    def test_old_trailer_record_without_cargo_loads_empty(self):
        records = self.manager.save_records()
        trailer_record = next(
            record for record in records
            if record["vehicle_type"] == VehicleType.TRAILER.value
        )
        trailer_record.pop("cargo_type")
        trailer_record.pop("cargo_amount")
        self.manager.reset_for_loaded_game(
            self.world, [], self.buildings, records,
        )
        loaded_trailer = next(
            asset for asset in self.manager.implements
            if asset.vehicle_type == VehicleType.TRAILER
        )
        self.assertEqual(loaded_trailer.cargo_type, "empty")
        self.assertEqual(loaded_trailer.cargo_amount, 0)


if __name__ == "__main__":
    unittest.main()
