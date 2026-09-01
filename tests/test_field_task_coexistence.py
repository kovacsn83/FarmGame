from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constants import BUILDING, FIELD, ROAD
from economy import Economy
from game_state import GameState
from game_logger import get_logger
from save_system import load_game, save_game
from time_system import GameTime, TIME_SLOW
from tractor import TASK_FERTILIZING, TASK_WATERING, TRACTOR_IDLE
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class FieldTaskCoexistenceTests(unittest.TestCase):
    def setUp(self):
        self.world = [[ROAD for _ in range(40)] for _ in range(40)]
        self.garage = {
            "type": "garage", "row": 2, "col": 2,
            "width": 4, "height": 4,
        }
        self.warehouse = {
            "type": "warehouse", "row": 2, "col": 12,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {"manure": 20},
        }
        self.pond = {
            "type": "pond", "row": 2, "col": 24,
            "width": 6, "height": 6,
        }
        self.buildings = [self.garage, self.warehouse, self.pond]
        self.field = {
            "row": 20, "col": 12, "width": 4, "height": 4,
            "field_type": "field_4x4", "crop": "wheat",
            "growth": 20, "growth_weeks": 8,
            "harvestable": False, "watered": False,
            "fertilized": False,
        }
        for row in range(20, 24):
            for col in range(12, 16):
                self.world[row][col] = FIELD
        self.economy = Economy()
        self.game_time = GameTime(current_time_speed=TIME_SLOW, start_ticks=0)
        self.manager = VehicleManager()
        self.tractor = self.manager._create_managed_asset(
            VehicleType.TRACTOR, self.garage, 0,
        )
        self.manager._create_managed_asset(
            VehicleType.WATER_TANK, self.garage, 1,
        )
        self.manager.ensure_idle_positions(self.world, self.buildings)
        get_logger().reset()

    def _run_to_idle(self):
        for tick in range(100, 60_000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if (
                all(
                    vehicle.state == TRACTOR_IDLE
                    and vehicle.current_task is None
                    for vehicle in self.manager.vehicles
                )
                and not self.manager.task_queue
                and tick > 100
            ):
                return
        self.fail("A vegyes Veteményes-feladatok nem fejeződtek be.")

    def test_watering_then_fertilizing_are_both_accepted_in_order(self):
        self.assertTrue(self.manager.start_watering(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertTrue(self.manager.start_fertilizing(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertEqual(
            self.manager.get_field_task_status(self.field, TASK_WATERING),
            "active",
        )
        self.assertEqual(
            self.manager.get_field_task_status(self.field, TASK_FERTILIZING),
            "waiting",
        )

        self._run_to_idle()

        self.assertTrue(self.field["watered"])
        self.assertTrue(self.field["fertilized"])

    def test_fertilizing_then_watering_are_both_accepted_in_order(self):
        self.assertTrue(self.manager.start_fertilizing(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertTrue(self.manager.start_watering(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertEqual(
            self.manager.get_field_task_status(self.field, TASK_FERTILIZING),
            "active",
        )
        self.assertEqual(
            self.manager.get_field_task_status(self.field, TASK_WATERING),
            "waiting",
        )

        self._run_to_idle()

        self.assertTrue(self.field["fertilized"])
        self.assertTrue(self.field["watered"])

    def test_duplicate_watering_is_rejected(self):
        self.assertTrue(self.manager.start_watering(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertFalse(self.manager.start_watering(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        tasks = [
            task for task in self.manager._all_tasks()
            if task.field is self.field and task.task_type == TASK_WATERING
        ]
        self.assertEqual(len(tasks), 1)

    def test_duplicate_fertilizing_is_rejected_without_double_reservation(self):
        self.assertTrue(self.manager.start_fertilizing(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        reserved = self.manager.reserved_fertilizer
        self.assertFalse(self.manager.start_fertilizing(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertEqual(self.manager.reserved_fertilizer, reserved)

    def test_automatic_treatments_share_pipeline_but_do_not_emit_quest_events(self):
        quest_events = []
        self.manager.quest_event_handler = quest_events.append
        self.assertTrue(self.manager.start_watering(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0, source="automatic",
        ))
        self.assertTrue(self.manager.start_fertilizing(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0, source="automatic",
        ))
        tasks = [
            task for task in self.manager._all_tasks()
            if task.field is self.field
        ]
        self.assertEqual(len(tasks), 2)
        self.assertTrue(all(not task.manually_initiated for task in tasks))

        self._run_to_idle()

        self.assertTrue(self.field["watered"])
        self.assertTrue(self.field["fertilized"])
        self.assertEqual(quest_events, [])

    def test_treatments_finish_before_later_harvest(self):
        self.manager._create_managed_asset(
            VehicleType.COMBINE, self.garage, 2,
        ).ensure_idle_position(self.world, self.buildings)
        self.assertTrue(self.manager.start_watering(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertTrue(self.manager.start_fertilizing(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.field["growth"] = 100
        self.field["growth_weeks"] = 38
        self.field["harvestable"] = True
        self.assertTrue(self.manager.start_harvesting(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0, current_week=30, current_elapsed_week=29,
        ))
        self.assertEqual(
            self.manager.get_field_task_status(self.field, TASK_WATERING),
            "active",
        )
        self.assertEqual(
            self.manager.get_field_task_status(self.field, TASK_FERTILIZING),
            "waiting",
        )

        self._run_to_idle()

        messages = [entry.message for entry in get_logger().entries]
        watering_index = next(
            index for index, message in enumerate(messages)
            if "sikeresen meglocsolva" in message
        )
        fertilizing_index = next(
            index for index, message in enumerate(messages)
            if "trágyázás befejeződött" in message
        )
        harvest_index = next(
            index for index, message in enumerate(messages)
            if "aratás befejeződött" in message
        )
        self.assertLess(watering_index, fertilizing_index)
        self.assertLess(fertilizing_index, harvest_index)

    def test_automatic_harvest_keeps_fifo_order_and_skips_quest(self):
        self.manager._create_managed_asset(
            VehicleType.COMBINE, self.garage, 2,
        ).ensure_idle_position(self.world, self.buildings)
        quest_events = []
        self.manager.quest_event_handler = (
            lambda event, **kwargs: quest_events.append(event)
        )
        self.assertTrue(self.manager.start_watering(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0, source="automatic",
        ))
        self.field["growth"] = 100
        self.field["growth_weeks"] = 38
        self.field["harvestable"] = True
        self.assertTrue(self.manager.start_harvesting(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0, current_week=30, current_elapsed_week=29,
            source="automatic",
        ))
        self.assertFalse(self.manager.start_harvesting(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0, current_week=30, current_elapsed_week=29,
        ))

        self._run_to_idle()

        messages = [entry.message for entry in get_logger().entries]
        watering_index = next(
            index for index, message in enumerate(messages)
            if "sikeresen meglocsolva" in message
        )
        harvest_index = next(
            index for index, message in enumerate(messages)
            if "aratás befejeződött" in message
        )
        self.assertLess(watering_index, harvest_index)
        self.assertEqual(quest_events, [])

    def test_moving_combine_continues_harvest_after_save_and_load(self):
        combine = self.manager._create_managed_asset(
            VehicleType.COMBINE, self.garage, 2,
        )
        combine.ensure_idle_position(self.world, self.buildings)
        for building in self.buildings:
            for row in range(building["row"], building["row"] + building["height"]):
                for col in range(building["col"], building["col"] + building["width"]):
                    self.world[row][col] = BUILDING
        self.field["growth"] = 100
        self.field["growth_weeks"] = 38
        self.field["harvestable"] = True
        self.assertTrue(self.manager.start_harvesting(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0, current_week=30, current_elapsed_week=29,
            source="automatic",
        ))
        last_tick = None
        for tick in range(100, 10000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if combine.state != TRACTOR_IDLE and combine.next_path_index > 1:
                last_tick = tick
                break
        self.assertIsNotNone(last_tick)
        saved_runtime = (
            combine.state, combine.row, combine.col,
            combine.world_x, combine.world_y, combine.next_path_index,
        )
        state = GameState(
            self.world, [self.field], self.buildings,
            self.economy, self.game_time, vehicles=self.manager,
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "moving-combine.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))

        loaded_combine = next(
            vehicle for vehicle in self.manager.vehicles
            if vehicle.vehicle_type == VehicleType.COMBINE
        )
        self.assertEqual((
            loaded_combine.state, loaded_combine.row, loaded_combine.col,
            loaded_combine.world_x, loaded_combine.world_y,
            loaded_combine.next_path_index,
        ), saved_runtime)
        self.assertFalse(loaded_combine.current_task.manually_initiated)
        for tick in range(last_tick + 100, last_tick + 30000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if loaded_combine.state == TRACTOR_IDLE:
                break
        self.assertIsNone(state.fields[0]["crop"])
        warehouse = next(
            building for building in self.buildings
            if building["type"] == "warehouse"
        )
        self.assertGreater(warehouse["inventory"].get("wheat", 0), 0)


if __name__ == "__main__":
    unittest.main()
