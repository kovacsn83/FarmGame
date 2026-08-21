from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fields import (
    calculate_harvest_yield, complete_harvest, grow_crops, prepare_harvest,
)
from notification_system import NotificationManager
from progress_tooltips import get_field_progress_lines


def mature_field(crop, growth_weeks, harvest_count=0):
    return {
        "row": 1, "col": 1, "width": 4, "height": 4,
        "field_type": "field_4x4", "crop": crop,
        "growth": 100, "growth_weeks": growth_weeks,
        "harvestable": True, "fertilized": False, "watered": False,
        "harvest_count": harvest_count, "missed_harvest_count": 0,
        "planted_at_week": 0, "last_harvest_at_week": None,
        "next_maturity_at_week": None, "expires_at_week": None,
        "late_harvest_active": False,
        "late_harvest_started_at_week": None,
        "late_harvest_expires_at_week": None,
    }


def warehouse():
    return {
        "type": "warehouse", "capacity": 500,
        "inventory": {"tomato": 0, "wheat": 0, "alfalfa": 0},
    }


class LateHarvestTests(unittest.TestCase):
    def test_normal_yield_is_unchanged_and_late_yield_is_half(self):
        field = mature_field("wheat", 38)
        with patch("fields.random.uniform", return_value=1.0):
            self.assertEqual(calculate_harvest_yield(field), 10)
            self.assertEqual(
                calculate_harvest_yield(field, late_harvest=True), 5,
            )

    def test_annual_crop_disappears_after_two_late_weeks(self):
        field = mature_field("wheat", 38)
        grow_crops([field], 33)  # 1. év, 34. hét
        self.assertTrue(field["late_harvest_active"])
        grow_crops([field], 34)
        self.assertEqual(field["crop"], "wheat")
        grow_crops([field], 35)
        self.assertIsNone(field["crop"])

    def test_alfalfa_loses_only_current_cycle(self):
        field = mature_field("alfalfa", 10)
        grow_crops([field], 40)  # 1. év, 41. hét
        grow_crops([field], 41)
        grow_crops([field], 42)
        self.assertEqual(field["crop"], "alfalfa")
        self.assertEqual(field["harvest_count"], 1)
        self.assertEqual(field["missed_harvest_count"], 1)
        self.assertEqual(field["growth"], 0)

    def test_missed_first_tomato_harvest_ends_the_whole_cycle(self):
        field = mature_field("tomato", 9)
        storage = warehouse()
        grow_crops([field], 39)
        grow_crops([field], 40)
        grow_crops([field], 41)
        self.assertIsNone(field["crop"])
        self.assertEqual(storage["inventory"]["tomato"], 0)
        self.assertEqual(field["growth"], 0)
        self.assertFalse(field["late_harvest_active"])

    def test_successful_first_tomato_harvest_starts_three_week_regrowth(self):
        field = mature_field("tomato", 9)
        storage = warehouse()
        with patch("fields.random.uniform", return_value=1.0):
            harvest = prepare_harvest(field, [storage])
        self.assertEqual(harvest["amount"], 5)
        self.assertTrue(complete_harvest(
            field, [storage], "tomato", harvest["amount"],
            current_elapsed_week=30,
        ))
        self.assertEqual(storage["inventory"]["tomato"], 5)
        self.assertEqual(field["crop"], "tomato")
        self.assertEqual(field["harvest_count"], 1)
        self.assertEqual(field["growth"], 0)
        self.assertEqual(field["next_maturity_at_week"], 33)

    def test_late_first_tomato_harvest_does_not_start_impossible_regrowth(self):
        field = mature_field("tomato", 9)
        storage = warehouse()
        field["late_harvest_active"] = True
        field["late_harvest_started_at_week"] = 39
        field["late_harvest_expires_at_week"] = 41
        with patch("fields.random.uniform", return_value=1.0):
            harvest = prepare_harvest(
                field, [storage], late_harvest=True,
            )
        self.assertEqual(harvest["amount"], 3)
        self.assertTrue(complete_harvest(
            field, [storage], "tomato", harvest["amount"],
            current_elapsed_week=39,
        ))
        self.assertEqual(storage["inventory"]["tomato"], 3)
        self.assertIsNone(field["crop"])

    def test_second_tomato_harvest_can_expire_without_a_third_cycle(self):
        field = mature_field("tomato", 9)
        storage = warehouse()
        self.assertTrue(complete_harvest(
            field, [storage], "tomato", 4, current_elapsed_week=30,
        ))
        field["growth"] = 100
        field["growth_weeks"] = 3
        field["harvestable"] = True
        grow_crops([field], 39)
        grow_crops([field], 40)
        grow_crops([field], 41)
        self.assertIsNone(field["crop"])

    def test_latest_viable_normal_first_harvest_can_start_regrowth(self):
        field = mature_field("tomato", 9)
        storage = warehouse()
        self.assertTrue(complete_harvest(
            field, [storage], "tomato", 4,
            current_elapsed_week=37,
        ))
        self.assertEqual(field["crop"], "tomato")
        self.assertEqual(field["next_maturity_at_week"], 40)

    def test_tooltip_shows_late_yield_and_remaining_weeks(self):
        field = mature_field("corn", 21)
        field["late_harvest_active"] = True
        field["late_harvest_expires_at_week"] = 45
        lines = get_field_progress_lines(field, 44, 45)
        self.assertIn("Pótaratás", lines)
        self.assertIn("50% hozam", lines)
        self.assertIn("Még 1 hét", lines)

    def test_notification_is_emitted_once_for_the_transition(self):
        field = mature_field("wheat", 38)
        notifications = NotificationManager()
        grow_crops([field], 33, notifications)
        first_message = notifications.current_message
        grow_crops([field], 33, notifications)
        self.assertIn("pótaratási", first_message)
        self.assertEqual(notifications.current_message, first_message)
        self.assertEqual(len(notifications.queue), 0)


if __name__ == "__main__":
    unittest.main()
