from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from animals import (
    CATTLE_BEEF_PER_CYCLE, CATTLE_LIFESPAN_WEEKS, can_place_animal,
    produce_weekly_animal_products,
)
from game_logger import get_logger
from notification_system import NotificationManager
from save_system import _migrate_legacy_crop_data


class CattleLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.pen = {
            "type": "animal_pen", "row": 10, "col": 10,
            "width": 4, "height": 4,
        }
        self.warehouse = {
            "type": "warehouse", "row": 2, "col": 2,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {},
        }
        self.buildings = [self.pen, self.warehouse]
        get_logger().reset()

    def _cattle(self, index=0, age_weeks=0):
        return {
            "type": "cattle", "row": 10 + index // 4,
            "col": 10 + index % 4,
            "pen_row": 10, "pen_col": 10,
            "age_weeks": age_weeks,
            "visual_id": index + 1, "facing_direction": "down",
        }

    def test_age_increases_and_cattle_produces_before_lifespan_end(self):
        cattle = self._cattle(age_weeks=CATTLE_LIFESPAN_WEEKS - 2)
        animals = [cattle]

        produce_weekly_animal_products(animals, self.buildings)

        self.assertEqual(cattle["age_weeks"], CATTLE_LIFESPAN_WEEKS - 1)
        self.assertEqual(animals, [cattle])
        self.assertEqual(self.warehouse["inventory"]["milk"], 1)
        self.assertEqual(self.warehouse["inventory"]["manure"], 1)
        self.assertEqual(self.warehouse["inventory"].get("beef", 0), 0)

    def test_week_104_produces_then_slaughters_and_releases_capacity(self):
        animals = [
            self._cattle(index, CATTLE_LIFESPAN_WEEKS - 1)
            for index in range(4)
        ]
        self.assertFalse(can_place_animal(
            animals, self.buildings, 11, 10, "cattle",
        ))

        produce_weekly_animal_products(animals, self.buildings)

        self.assertEqual(animals, [])
        self.assertEqual(self.warehouse["inventory"]["milk"], 4)
        self.assertEqual(self.warehouse["inventory"]["manure"], 4)
        self.assertEqual(
            self.warehouse["inventory"]["beef"],
            4 * CATTLE_BEEF_PER_CYCLE,
        )
        self.assertTrue(can_place_animal(
            animals, self.buildings, 11, 10, "cattle",
        ))

    def test_multiple_slaughters_are_aggregated_and_expire(self):
        animals = [
            self._cattle(index, CATTLE_LIFESPAN_WEEKS - 1)
            for index in range(4)
        ]
        notifications = NotificationManager(start_ticks=0)

        produce_weekly_animal_products(
            animals, self.buildings, notification_manager=notifications,
        )

        self.assertEqual(
            notifications.current_message,
            "4 szarvasmarha levágásra került. 40 db marhahús került a raktárba.",
        )
        slaughter_logs = [
            entry for entry in get_logger().entries
            if entry.category == "Animals" and "szarvasmarha levágásra" in entry.message
        ]
        self.assertEqual(len(slaughter_logs), 1)
        self.assertIn("40 db marhahús", slaughter_logs[0].message)
        notifications.update(10_000, time_running=True)
        self.assertIsNone(notifications.current_message)

    def test_old_save_gets_safe_zero_age_and_beef_inventory(self):
        data = {
            "fields": [],
            "buildings": [self.warehouse, self.pen],
            "animals": [{
                "type": "cattle", "row": 11, "col": 10,
                "pen_row": 10, "pen_col": 10,
            }],
        }

        _migrate_legacy_crop_data(data)

        self.assertEqual(data["animals"][0]["age_weeks"], 0)
        self.assertEqual(self.warehouse["inventory"]["beef"], 0)


if __name__ == "__main__":
    unittest.main()
