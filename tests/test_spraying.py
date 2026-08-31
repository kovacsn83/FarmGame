from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constants import FIELD, ROAD
from economy import Economy
from fields import (
    _advance_crop_cycle, calculate_harvest_yield, can_spray_field, plant_crop,
    synchronize_annual_crop_cycle,
)
from financial_history import EXPENSE_SPRAYING
from game_rules import get_field_spraying_cost
from progress_tooltips import get_field_progress_lines
from quest_system import QUEST_EVENT_FIELD_SPRAYED
from save_system import _migrate_legacy_crop_data
from time_system import GameTime, TIME_SLOW
from tractor import TASK_FERTILIZING, TASK_SPRAYING, TASK_WATERING, TRACTOR_IDLE
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class SprayingTests(unittest.TestCase):
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
            "growth": 20, "growth_weeks": 8, "harvestable": False,
            "watered": False, "fertilized": False, "sprayed": False,
            "harvest_count": 0,
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

    def _run_to_idle(self):
        for tick in range(100, 60_000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if (
                all(vehicle.state == TRACTOR_IDLE for vehicle in self.manager.vehicles)
                and not self.manager.task_queue
                and tick > 100
            ):
                return
        self.fail("A permetezési feladat nem fejeződött be.")

    def test_central_costs_are_size_dependent(self):
        self.assertEqual(4, get_field_spraying_cost({"field_type": "field_4x4"}))
        self.assertEqual(6, get_field_spraying_cost({"field_type": "field_6x6"}))
        self.assertEqual(8, get_field_spraying_cost({"field_type": "field_8x8"}))

    def test_task_uses_only_tractor_and_records_cost(self):
        quest_events = []
        self.manager.quest_event_handler = lambda event_id, **data: (
            quest_events.append((event_id, data))
        )
        starting_money = self.economy.money
        self.assertTrue(self.manager.start_spraying(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertEqual(TASK_SPRAYING, self.tractor.current_task.task_type)
        self.assertIsNone(self.tractor.attached_implement)
        self.assertEqual(starting_money - 4, self.economy.money)
        summary = self.economy.get_financial_summary()
        self.assertEqual(4, summary["expense"][EXPENSE_SPRAYING]["total"])

        self._run_to_idle()
        self.assertTrue(self.field["sprayed"])
        self.assertIsNone(self.tractor.attached_implement)
        self.assertEqual(QUEST_EVENT_FIELD_SPRAYED, quest_events[0][0])
        self.assertEqual((20, 12), quest_events[0][1]["unique_key"])

    def test_busy_tractor_queues_spraying_and_rejects_duplicate(self):
        self.assertTrue(self.manager.start_fertilizing(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertTrue(self.manager.start_spraying(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertEqual(
            "waiting",
            self.manager.get_field_task_status(self.field, TASK_SPRAYING),
        )
        self.assertFalse(self.manager.start_spraying(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertEqual(1, sum(
            task.task_type == TASK_SPRAYING
            for task in self.manager._all_tasks()
        ))

    def test_all_three_treatments_can_share_the_same_fifo(self):
        self.assertTrue(self.manager.start_watering(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertTrue(self.manager.start_fertilizing(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertTrue(self.manager.start_spraying(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertEqual(
            {TASK_WATERING, TASK_FERTILIZING, TASK_SPRAYING},
            {task.task_type for task in self.manager._all_tasks()},
        )
        self._run_to_idle()
        self.assertTrue(self.field["watered"])
        self.assertTrue(self.field["fertilized"])
        self.assertTrue(self.field["sprayed"])

    def test_tomato_keeps_spraying_for_both_harvests_then_resets(self):
        empty_field = {"crop": None, "sprayed": True}
        self.assertTrue(plant_crop(empty_field, "tomato", 0))
        self.assertFalse(empty_field["sprayed"])

        tomato = dict(
            self.field, crop="tomato", field_type="field_8x8",
            sprayed=True, harvest_count=0,
        )
        self.assertTrue(_advance_crop_cycle(tomato, "tomato", 30))
        self.assertTrue(tomato["sprayed"])
        self.assertFalse(can_spray_field(tomato))
        with patch("fields.random.uniform", return_value=1.0):
            self.assertEqual(17, calculate_harvest_yield(tomato))

        self.assertFalse(_advance_crop_cycle(tomato, "tomato", 40))
        self.assertIsNone(tomato["crop"])
        self.assertFalse(tomato["sprayed"])
        self.assertTrue(plant_crop(tomato, "tomato", 50))
        self.assertTrue(can_spray_field(tomato))

    def test_other_crop_cycles_still_reset_spraying(self):
        wheat = dict(self.field, crop="wheat", sprayed=True)
        self.assertFalse(_advance_crop_cycle(wheat, "wheat", 30))
        self.assertFalse(wheat["sprayed"])

        perennial = dict(
            self.field, crop="hops", sprayed=True, planted_at_week=0,
            annual_cycle_year=1, annual_harvest_state="growing",
        )
        synchronize_annual_crop_cycle(perennial, 52)
        self.assertFalse(perennial["sprayed"])

    def test_tooltip_and_legacy_default(self):
        lines = get_field_progress_lines(self.field)
        spray_index = lines.index("Permetezés:")
        self.assertEqual("Nem", lines[spray_index + 1])
        self.field["sprayed"] = True
        lines = get_field_progress_lines(self.field)
        spray_index = lines.index("Permetezés:")
        self.assertEqual("Igen", lines[spray_index + 1])
        legacy = dict(self.field)
        legacy.pop("sprayed")
        _migrate_legacy_crop_data({"fields": [legacy]})
        self.assertFalse(legacy["sprayed"])
        self.assertTrue(can_spray_field(legacy))

    def test_runtime_round_trip_keeps_waiting_spraying_task(self):
        self.assertTrue(self.manager.start_fertilizing(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        self.assertTrue(self.manager.start_spraying(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        runtime = self.manager.runtime_save_record([self.field], self.buildings)
        records = self.manager.save_records()

        restored = VehicleManager()
        restored.reset_for_loaded_game(
            self.world, [self.field], self.buildings,
            tractor_records=records, runtime_record=runtime,
        )
        self.assertEqual(
            "waiting", restored.get_field_task_status(self.field, TASK_SPRAYING),
        )

    def test_active_spraying_continues_after_runtime_round_trip(self):
        self.assertTrue(self.manager.start_spraying(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0,
        ))
        for tick in range(100, 1_000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
        runtime = self.manager.runtime_save_record([self.field], self.buildings)
        records = self.manager.save_records()

        restored = VehicleManager()
        restored.reset_for_loaded_game(
            self.world, [self.field], self.buildings,
            tractor_records=records, runtime_record=runtime,
        )
        restored_tractor = restored.tractors[0]
        self.assertIsNotNone(restored_tractor.current_task)
        self.assertEqual(TASK_SPRAYING, restored_tractor.current_task.task_type)

        self.manager = restored
        self._run_to_idle()
        self.assertTrue(self.field["sprayed"])


if __name__ == "__main__":
    unittest.main()
