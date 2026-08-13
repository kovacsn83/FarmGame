from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from animal_troughs import (
    FOOD_STOCK_KEY, TROUGH_WEEKS, WATER_STOCK_KEY, fill_group_trough,
    get_group_supply, get_trough_tooltip, iter_troughs,
    supply_animals_from_troughs,
)
from feed_supply import get_feed_requirement


class TroughCapacityTests(unittest.TestCase):
    def setUp(self):
        self.pen = {
            "type": "animal_pen", "row": 10, "col": 10,
            "width": 4, "height": 4,
        }

    def _animals(self, animal_type, count):
        return [
            {
                "type": animal_type,
                "row": 10 + index // 4,
                "col": 10 + index % 4,
                "pen_row": 10,
                "pen_col": 10,
            }
            for index in range(count)
        ]

    def test_four_cattle_require_thirty_two_feed_units(self):
        feed_type, required = get_feed_requirement(
            [self.pen], self._animals("cattle", 4),
        )
        self.assertEqual(TROUGH_WEEKS, 8)
        self.assertEqual(feed_type, "alfalfa")
        self.assertEqual(required, 32)

    def test_twenty_four_pigs_require_one_hundred_ninety_two_feed_units(self):
        feed_type, required = get_feed_requirement(
            [self.pen], self._animals("pig", 24),
        )
        self.assertEqual(feed_type, "corn")
        self.assertEqual(required, 192)

    def test_water_trough_fills_to_eight_weeks(self):
        animals = self._animals("cattle", 4)
        self.assertTrue(fill_group_trough([self.pen], animals, "water"))
        self.assertEqual(self.pen[WATER_STOCK_KEY], 32)

    def test_weekly_consumption_is_unchanged(self):
        animals = self._animals("cattle", 4)
        self.pen[FOOD_STOCK_KEY] = 32
        self.pen[WATER_STOCK_KEY] = 32

        supplied = supply_animals_from_troughs(animals, [self.pen])

        self.assertEqual(len(supplied), 4)
        self.assertEqual(get_group_supply([self.pen]), (28, 28))

    def test_legacy_partial_stock_is_preserved_and_refilled_to_new_target(self):
        animals = self._animals("cattle", 4)
        self.pen[FOOD_STOCK_KEY] = 8  # A régi rendszer szerinti 2 heti készlet.

        feed_type, required = get_feed_requirement([self.pen], animals)

        self.assertEqual(feed_type, "alfalfa")
        self.assertEqual(self.pen[FOOD_STOCK_KEY], 8)
        self.assertEqual(required, 24)

    def test_tooltip_counts_down_from_eight_weeks(self):
        animals = self._animals("cattle", 4)
        self.pen[FOOD_STOCK_KEY] = 32
        food_trough = next(
            trough for trough in iter_troughs([self.pen], animals)
            if trough["type"] == "food"
        )

        tooltip, _rect = get_trough_tooltip(
            food_trough["rect"].center, [self.pen], animals,
        )
        self.assertIn("8 / 8 hét", tooltip)

        self.pen[FOOD_STOCK_KEY] = 28
        tooltip, _rect = get_trough_tooltip(
            food_trough["rect"].center, [self.pen], animals,
        )
        self.assertIn("7 / 8 hét", tooltip)


if __name__ == "__main__":
    unittest.main()
