from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from crops import (
    CROPS, can_harvest_crop_in_week, can_plant_crop_in_week,
    get_crop_productive_year_range,
)
from constants import TILE_SIZE
from field_renderer import CROP_RENDERERS, _create_field_surface
from fields import (
    calculate_harvest_yield, can_fertilize_field, can_water_field,
    complete_harvest, grow_crops, plant_crop, water_crop,
)
from inventory import (
    get_inventory_item_data, get_inventory_item_ids, get_marketable_item_ids,
)
from progress_tooltips import get_field_progress_lines
from save_system import _migrate_legacy_crop_data


def empty_field():
    return {
        "row": 1, "col": 1, "width": 4, "height": 4,
        "field_type": "field_4x4", "crop": None, "growth": 0,
        "growth_weeks": 0, "harvestable": False, "fertilized": False,
        "watered": False, "harvest_count": 0, "planted_at_week": None,
        "last_harvest_at_week": None, "next_maturity_at_week": None,
        "expires_at_week": None, "late_harvest_active": False,
        "late_harvest_started_at_week": None,
        "late_harvest_expires_at_week": None, "missed_harvest_count": 0,
        "annual_cycle_year": None, "annual_harvest_state": None,
    }


class HopsCropTests(unittest.TestCase):
    def setUp(self):
        self.field = empty_field()
        self.assertTrue(plant_crop(self.field, "hops", 13))  # 1. év, 14. hét
        self.warehouse = {
            "type": "warehouse", "capacity": 500,
            "inventory": {item_id: 0 for item_id in get_inventory_item_ids()},
        }

    def test_catalog_calendar_market_and_graphic(self):
        hops = CROPS["hops"]
        self.assertEqual("Komló", hops["name"])
        self.assertEqual(10, hops["yield"])
        self.assertEqual(11.0, hops["price"])
        self.assertEqual((2, 20), get_crop_productive_year_range("hops"))
        self.assertTrue(can_plant_crop_in_week("hops", 14))
        self.assertTrue(can_plant_crop_in_week("hops", 18))
        self.assertFalse(can_plant_crop_in_week("hops", 19))
        self.assertTrue(can_harvest_crop_in_week("hops", 34))
        self.assertTrue(can_harvest_crop_in_week("hops", 38))
        self.assertIn("hops", get_marketable_item_ids())
        self.assertEqual(11.0, get_inventory_item_data("hops")["price"])
        self.assertIn("hops", CROP_RENDERERS)
        surface = _create_field_surface({**self.field, "growth": 100})
        self.assertEqual((4 * TILE_SIZE, 4 * TILE_SIZE), surface.get_size())

    def test_first_year_never_harvests_then_years_two_to_twenty_do(self):
        grow_crops([self.field], 33)  # 1. év, 34. hét
        self.assertEqual("ineligible", self.field["annual_harvest_state"])
        self.assertFalse(self.field["harvestable"])

        grow_crops([self.field], 52 + 33)  # 2. év, 34. hét
        self.assertEqual("ripe", self.field["annual_harvest_state"])
        self.assertTrue(self.field["harvestable"])
        with patch("fields.random.uniform", return_value=1.0):
            amount = calculate_harvest_yield(self.field)
        self.assertEqual(10, amount)
        self.assertTrue(complete_harvest(
            self.field, [self.warehouse], "hops", amount, 52 + 33,
        ))
        self.assertEqual(10, self.warehouse["inventory"]["hops"])
        self.assertEqual("harvested", self.field["annual_harvest_state"])
        self.assertEqual("hops", self.field["crop"])

        grow_crops([self.field], 2 * 52 + 33)
        self.assertEqual("ripe", self.field["annual_harvest_state"])
        with patch("fields.random.uniform", return_value=1.0):
            self.assertEqual(10, calculate_harvest_yield(self.field))
        grow_crops([self.field], 19 * 52 + 33)  # 20. életév
        self.assertEqual("ripe", self.field["annual_harvest_state"])
        grow_crops([self.field], 20 * 52)  # 21. életév
        self.assertIsNone(self.field["crop"])

    def test_first_year_care_is_allowed_and_preserved_for_first_harvest(self):
        self.assertTrue(can_water_field(self.field))
        self.assertTrue(water_crop(self.field))
        self.assertTrue(can_fertilize_field(self.field))
        self.field["fertilized"] = True

        grow_crops([self.field], 52)  # 2. év, 1. hét
        self.assertEqual("growing", self.field["annual_harvest_state"])
        self.assertTrue(self.field["watered"])
        self.assertTrue(self.field["fertilized"])

        grow_crops([self.field], 52 + 33)
        with patch("fields.random.uniform", return_value=1.0):
            amount = calculate_harvest_yield(self.field)
        self.assertEqual(13, amount)
        self.assertTrue(complete_harvest(
            self.field, [self.warehouse], "hops", amount, 52 + 33,
        ))
        self.assertFalse(self.field["watered"])
        self.assertFalse(self.field["fertilized"])
        self.assertFalse(can_water_field(self.field))

    def test_late_harvest_and_missed_year_preserve_the_perennial(self):
        grow_crops([self.field], 52 + 38)  # 2. év, 39. hét
        self.assertTrue(self.field["late_harvest_active"])
        with patch("fields.random.uniform", return_value=1.0):
            self.assertEqual(5, calculate_harvest_yield(self.field))
        grow_crops([self.field], 52 + 39)
        grow_crops([self.field], 52 + 40)
        self.assertEqual("lost", self.field["annual_harvest_state"])
        self.assertEqual("hops", self.field["crop"])
        grow_crops([self.field], 2 * 52 + 33)
        self.assertEqual("ripe", self.field["annual_harvest_state"])

    def test_tooltip_reports_age_and_productive_state(self):
        grow_crops([self.field], 52 + 33)
        lines = get_field_progress_lines(
            self.field, 52 + 33, 34,
        )
        self.assertIn("Életkor: 2 / 20 év", lines)
        self.assertIn("Termőkor: 2–20. év", lines)
        self.assertIn("Állapot: aratható", lines)

    def test_old_save_migration_and_hops_inventory_are_compatible(self):
        legacy_field = empty_field()
        legacy_field.pop("annual_cycle_year")
        legacy_field.pop("annual_harvest_state")
        legacy_warehouse = {
            "type": "warehouse", "inventory": {"wheat": 2},
        }
        data = {"fields": [legacy_field], "buildings": [legacy_warehouse]}
        _migrate_legacy_crop_data(data)
        self.assertIsNone(legacy_field["annual_cycle_year"])
        self.assertIsNone(legacy_field["annual_harvest_state"])
        self.assertEqual(0, legacy_warehouse["inventory"]["hops"])


if __name__ == "__main__":
    unittest.main()
