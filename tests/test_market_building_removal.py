import unittest
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from buildings import BUILDING_TYPES, BUILD_OPTIONS
from constants import BUILDING, GRASS
from save_system import SAVE_VERSION, _migrate_save_schema


class MarketBuildingRemovalTests(unittest.TestCase):
    def test_market_is_not_an_available_building_or_build_option(self):
        self.assertNotIn("market", BUILDING_TYPES)
        self.assertNotIn("market", BUILD_OPTIONS)

    def test_current_save_market_is_removed_and_footprint_becomes_grass(self):
        world = [[GRASS for _ in range(10)] for _ in range(10)]
        market = {
            "type": "market", "row": 2, "col": 3,
            "width": 4, "height": 3,
        }
        for row in range(2, 5):
            for col in range(3, 7):
                world[row][col] = BUILDING
        warehouse = {
            "type": "warehouse", "row": 7, "col": 1,
            "width": 5, "height": 2,
        }
        data = {
            "save_version": SAVE_VERSION,
            "world": world,
            "buildings": [market, warehouse],
        }

        self.assertTrue(_migrate_save_schema(data))

        self.assertEqual([warehouse], data["buildings"])
        self.assertTrue(all(
            world[row][col] == GRASS
            for row in range(2, 5)
            for col in range(3, 7)
        ))


if __name__ == "__main__":
    unittest.main()
