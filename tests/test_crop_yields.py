from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from crops import CROPS, get_current_base_yield
from fields import calculate_harvest_yield


def field_for(crop, harvest_count=0, **states):
    field = {
        "crop": crop,
        "field_type": "field_4x4",
        "harvest_count": harvest_count,
        "watered": False,
        "fertilized": False,
        "sprayed": False,
        "pests": False,
        "weeds": False,
        "late_harvest_active": False,
    }
    field.update(states)
    return field


class CropYieldTests(unittest.TestCase):
    def test_central_catalog_contains_the_new_base_yields(self):
        self.assertEqual(10, get_current_base_yield(CROPS["wheat"], 0))
        self.assertEqual(12, get_current_base_yield(CROPS["corn"], 0))
        self.assertEqual(5, get_current_base_yield(CROPS["tomato"], 0))
        self.assertEqual(3, get_current_base_yield(CROPS["tomato"], 1))
        self.assertEqual(4, get_current_base_yield(CROPS["alfalfa"], 0))
        self.assertEqual(4, get_current_base_yield(CROPS["alfalfa"], 5))

    def test_harvest_uses_the_catalog_values_without_random_variation(self):
        expected = {
            ("wheat", 0): 10,
            ("corn", 0): 12,
            ("tomato", 0): 5,
            ("tomato", 1): 3,
            ("alfalfa", 0): 4,
        }
        with patch("fields.random.uniform", return_value=1.0):
            for (crop, harvest_count), amount in expected.items():
                with self.subTest(crop=crop, harvest_count=harvest_count):
                    self.assertEqual(
                        amount,
                        calculate_harvest_yield(field_for(crop, harvest_count)),
                    )

    def test_existing_watering_and_fertilizer_bonuses_apply_to_new_yield(self):
        with patch("fields.random.uniform", return_value=1.0):
            self.assertEqual(
                14, calculate_harvest_yield(field_for("corn", watered=True)),
            )
            self.assertEqual(
                13, calculate_harvest_yield(field_for("corn", fertilized=True)),
            )
            self.assertEqual(
                15,
                calculate_harvest_yield(
                    field_for("corn", watered=True, fertilized=True),
                ),
            )

    def test_late_harvest_is_applied_after_the_existing_bonuses(self):
        with patch("fields.random.uniform", return_value=1.0):
            self.assertEqual(
                8,
                calculate_harvest_yield(
                    field_for("corn", watered=True, fertilized=True),
                    late_harvest=True,
                ),
            )

    def test_spraying_bonus_combines_with_watering_and_fertilizing(self):
        with patch("fields.random.uniform", return_value=1.0):
            self.assertEqual(
                13, calculate_harvest_yield(field_for("corn", sprayed=True)),
            )
            self.assertEqual(
                16,
                calculate_harvest_yield(field_for(
                    "corn", watered=True, fertilized=True, sprayed=True,
                )),
            )


if __name__ == "__main__":
    unittest.main()
