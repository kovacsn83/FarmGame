from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from animals import (
    PIG_FATTENING_WEEKS, PIG_PORK_PER_CYCLE, can_place_animal,
    produce_weekly_animal_products,
)
from game_logger import get_logger
from notification_system import NotificationManager


class PigLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.pen = {
            "type": "animal_pen", "row": 10, "col": 10,
            "width": 4, "height": 4,
        }
        self.warehouse = {
            "type": "warehouse", "row": 5, "col": 5,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {"pork": 0},
        }
        self.buildings = [self.pen, self.warehouse]
        self.pig = {
            "type": "pig", "row": 10, "col": 10,
            "pen_row": 10, "pen_col": 10,
            "fattening_weeks": PIG_FATTENING_WEEKS - 1,
            "visual_id": 1, "facing_direction": "down",
        }
        get_logger().reset()

    def test_finished_pig_is_stored_removed_and_announced(self):
        animals = [self.pig]
        notifications = NotificationManager(start_ticks=0)

        produced = produce_weekly_animal_products(
            animals, self.buildings, notification_manager=notifications,
        )

        self.assertEqual(produced, 1)
        self.assertEqual(
            self.warehouse["inventory"]["pork"], PIG_PORK_PER_CYCLE,
        )
        self.assertEqual(animals, [])
        self.assertIn("10 db sertéshús", notifications.current_message)
        self.assertTrue(any(
            entry.category == "Animals"
            and "10 db sertéshús" in entry.message
            for entry in get_logger().entries
        ))

    def test_slaughter_notification_expires_after_ten_running_seconds(self):
        animals = [self.pig]
        notifications = NotificationManager(start_ticks=0)

        produce_weekly_animal_products(
            animals, self.buildings, notification_manager=notifications,
        )
        notifications.update(9_999, time_running=True)
        self.assertIsNotNone(notifications.current_message)
        notifications.update(10_000, time_running=True)
        self.assertIsNone(notifications.current_message)

    def test_multiple_pigs_create_one_aggregated_notification_and_log(self):
        pig_count = 15
        self.warehouse["capacity"] = 500
        animals = [
            {
                **self.pig,
                "row": 10 + index // 4,
                "col": 10 + index % 4,
                "visual_id": index + 1,
            }
            for index in range(pig_count)
        ]
        notifications = NotificationManager(start_ticks=0)

        produce_weekly_animal_products(
            animals, self.buildings, notification_manager=notifications,
        )

        self.assertEqual(animals, [])
        self.assertEqual(self.warehouse["inventory"]["pork"], 150)
        self.assertEqual(
            notifications.current_message,
            "15 sertés levágásra került. 150 db sertéshús került a raktárba.",
        )
        self.assertEqual(len(notifications.queue), 0)
        slaughter_logs = [
            entry for entry in get_logger().entries
            if entry.category == "Animals" and "levágásra került" in entry.message
        ]
        self.assertEqual(len(slaughter_logs), 1)
        self.assertIn("15 sertés", slaughter_logs[0].message)
        self.assertIn("150 db sertéshús", slaughter_logs[0].message)

    def test_slaughter_notification_appears_beside_existing_message(self):
        animals = [self.pig]
        notifications = NotificationManager(start_ticks=0)
        notifications.enqueue("Korábbi szezonális értesítés")

        produce_weekly_animal_products(
            animals, self.buildings, notification_manager=notifications,
        )

        self.assertEqual(
            notifications.current_message, "Korábbi szezonális értesítés",
        )
        self.assertEqual(len(notifications.queue), 1)
        self.assertIn("Egy sertés", notifications.active_messages[1])
        notifications.update(10_000, time_running=True)
        self.assertIsNone(notifications.current_message)

    def test_removal_releases_pen_capacity_for_a_new_pig(self):
        animals = [
            self.pig,
            {**self.pig, "row": 10, "col": 11, "visual_id": 2,
             "fattening_weeks": 0},
            {**self.pig, "row": 10, "col": 12, "visual_id": 3,
             "fattening_weeks": 0},
            {**self.pig, "row": 10, "col": 13, "visual_id": 4,
             "fattening_weeks": 0},
        ]
        self.assertFalse(can_place_animal(
            animals, self.buildings, 11, 10, "pig",
        ))

        produce_weekly_animal_products(animals, self.buildings)

        self.assertEqual(len(animals), 3)
        self.assertTrue(can_place_animal(
            animals, self.buildings, 11, 10, "pig",
        ))

    def test_full_warehouse_keeps_pig_and_does_not_announce_slaughter(self):
        self.warehouse["capacity"] = 0
        animals = [self.pig]
        notifications = NotificationManager(start_ticks=0)

        produce_weekly_animal_products(
            animals, self.buildings, notification_manager=notifications,
        )

        self.assertEqual(animals, [self.pig])
        self.assertEqual(self.warehouse["inventory"]["pork"], 0)
        self.assertIsNone(notifications.current_message)


if __name__ == "__main__":
    unittest.main()
