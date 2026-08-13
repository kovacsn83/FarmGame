from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buildings import BUILDING_TYPES
from constants import (
    ANIMAL_PEN_BUILD_COST, GRASS, ROAD, ROAD_BUILD_COST,
)
from economy import Economy
from maintenance import (
    ANNUAL_MAINTENANCE_RATE, calculate_weekly_maintenance,
)
from road_building import build_road_segment


class ConstructionPriceTests(unittest.TestCase):
    def test_central_prices_match_the_new_balance(self):
        self.assertEqual(ROAD_BUILD_COST, 20.00)
        self.assertEqual(ANIMAL_PEN_BUILD_COST, 400.00)
        self.assertEqual(
            BUILDING_TYPES["animal_pen"]["build_cost"],
            ANIMAL_PEN_BUILD_COST,
        )

    def test_road_construction_deducts_twenty_dollars_per_new_tile(self):
        world = [[GRASS for _ in range(4)] for _ in range(2)]
        economy = Economy(starting_money=100)
        success, count, cost = build_road_segment(
            world, [(0, 0), (0, 1), (0, 2)], economy,
        )
        self.assertTrue(success)
        self.assertEqual(count, 3)
        self.assertEqual(cost, 60.00)
        self.assertEqual(economy.money, 40.00)
        self.assertEqual(world[0][:3], [ROAD, ROAD, ROAD])

    def test_maintenance_remains_ten_percent_annualized_weekly(self):
        self.assertEqual(ANNUAL_MAINTENANCE_RATE, 0.10)
        self.assertAlmostEqual(
            calculate_weekly_maintenance(ROAD_BUILD_COST),
            ROAD_BUILD_COST * 0.10 / 52,
        )
        self.assertAlmostEqual(
            calculate_weekly_maintenance(ANIMAL_PEN_BUILD_COST),
            ANIMAL_PEN_BUILD_COST * 0.10 / 52,
        )


if __name__ == "__main__":
    unittest.main()
