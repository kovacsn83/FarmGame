from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constants import FIELD, ROAD
from economy import Economy
from notification_system import NotificationManager
from storage_blocking import (
    FIELD_HARVEST_STORAGE_MESSAGE, StorageBlockManager,
)
from time_system import GameTime, TIME_NORMAL, TIME_PAUSED
from tractor import TRACTOR_IDLE
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class FieldStorageBlockingTests(unittest.TestCase):
    def setUp(self):
        self.world = [[ROAD for _ in range(40)] for _ in range(40)]
        self.garage = {
            "type": "garage", "row": 2, "col": 2,
            "width": 4, "height": 4,
        }
        self.warehouse = {
            "type": "warehouse", "row": 2, "col": 12,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {"corn": 500},
        }
        self.buildings = [self.garage, self.warehouse]
        self.field = {
            "row": 20, "col": 12, "width": 4, "height": 4,
            "field_type": "field_4x4", "crop": "wheat",
            "growth": 100, "growth_weeks": 38,
            "harvestable": True, "watered": False,
            "fertilized": False,
        }
        for row in range(20, 24):
            for col in range(12, 16):
                self.world[row][col] = FIELD
        self.economy = Economy()
        self.notifications = NotificationManager(start_ticks=0)
        self.game_time = GameTime(TIME_NORMAL, start_ticks=0)
        self.guard = StorageBlockManager(
            self.notifications, self.game_time,
        )
        self.manager = VehicleManager(self.guard)
        combine = self.manager._create_managed_asset(
            VehicleType.COMBINE, self.garage, 0,
        )
        combine.ensure_idle_position(self.world, self.buildings)

    def _start_harvest(self):
        return self.manager.start_harvesting(
            self.world, self.buildings, self.economy, self.field,
            current_ticks=0, current_week=30, current_elapsed_week=29,
        )

    def test_enough_capacity_starts_harvest_normally(self):
        self.warehouse["inventory"]["corn"] = 0

        self.assertTrue(self._start_harvest())
        self.assertEqual(self.game_time.current_time_speed, TIME_NORMAL)
        self.assertIsNone(self.notifications.current_message)

    def test_capacity_block_notifies_pauses_and_preserves_crop(self):
        self.assertFalse(self._start_harvest())

        self.assertEqual(self.game_time.current_time_speed, TIME_PAUSED)
        self.assertEqual(
            self.notifications.current_message,
            FIELD_HARVEST_STORAGE_MESSAGE,
        )
        self.assertEqual(self.field["crop"], "wheat")
        self.assertEqual(self.field["growth"], 100)
        self.assertTrue(self.field["harvestable"])

    def test_repeated_attempt_does_not_duplicate_notification(self):
        self.assertFalse(self._start_harvest())
        active_count = len(self.notifications.active_notifications)
        pending_count = len(self.notifications.pending_notifications)

        self.assertFalse(self._start_harvest())

        self.assertEqual(
            len(self.notifications.active_notifications), active_count,
        )
        self.assertEqual(
            len(self.notifications.pending_notifications), pending_count,
        )
        self.assertEqual(len(self.guard.active_events), 1)

    def test_freeing_space_allows_immediate_harvest_and_resolves_block(self):
        self.assertFalse(self._start_harvest())
        self.warehouse["inventory"]["corn"] = 0

        self.assertTrue(self._start_harvest())
        self.assertEqual(len(self.guard.active_events), 0)
        self.assertEqual(self.game_time.current_time_speed, TIME_PAUSED)
        self.game_time.set_time_speed(TIME_NORMAL, current_ticks=0)
        for tick in range(100, 30_000, 100):
            self.manager.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=tick,
            )
            if self.field["crop"] is None and all(
                vehicle.state == TRACTOR_IDLE
                for vehicle in self.manager.vehicles
            ):
                break
        self.assertIsNone(self.field["crop"])
        self.assertGreater(self.warehouse["inventory"].get("wheat", 0), 0)


if __name__ == "__main__":
    unittest.main()
