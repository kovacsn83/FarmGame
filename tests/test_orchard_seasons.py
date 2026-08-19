import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buildings import place_building
from constants import GRASS
from economy import Economy
from orchards import (
    complete_tree_harvest, get_tree_tooltip_lines, is_tree_harvestable,
    plant_tree, synchronize_tree_season,
)


class OrchardSeasonTests(unittest.TestCase):
    def setUp(self):
        self.world = [[GRASS for _ in range(30)] for _ in range(30)]
        self.buildings = []
        self.orchard = place_building(
            self.world, self.buildings, 5, 5, "orchard",
        )
        place_building(self.world, self.buildings, 15, 15, "warehouse")
        self.tree = plant_tree(
            self.buildings, Economy(1000), 5, 5, "apple",
        )

    def test_window_is_closed_on_29_open_through_35_and_closed_on_36(self):
        self.tree["age_weeks"] = 8 * 52
        synchronize_tree_season(self.tree, 9, 29)
        self.assertFalse(is_tree_harvestable(self.tree))
        synchronize_tree_season(self.tree, 9, 30)
        self.assertTrue(is_tree_harvestable(self.tree))
        synchronize_tree_season(self.tree, 9, 35)
        self.assertTrue(is_tree_harvestable(self.tree))
        synchronize_tree_season(self.tree, 9, 36)
        self.assertFalse(is_tree_harvestable(self.tree))
        self.assertEqual("lost", self.tree["annual_harvest_state"])
        self.assertIn("Az idei termés elveszett", get_tree_tooltip_lines(self.tree))
        synchronize_tree_season(self.tree, 10, 30)
        self.assertTrue(is_tree_harvestable(self.tree))

    def test_tree_maturing_before_week_30_can_crop_that_year(self):
        self.tree["age_weeks"] = 3 * 52 + 10
        synchronize_tree_season(self.tree, 4, 30)
        self.assertTrue(is_tree_harvestable(self.tree))

    def test_tree_maturing_after_week_30_waits_until_next_year(self):
        self.tree["age_weeks"] = 3 * 52
        synchronize_tree_season(self.tree, 4, 40)
        self.assertFalse(is_tree_harvestable(self.tree))
        self.assertEqual("ineligible", self.tree["annual_harvest_state"])
        self.tree["age_weeks"] += 42
        synchronize_tree_season(self.tree, 5, 30)
        self.assertTrue(is_tree_harvestable(self.tree))

    def test_successful_harvest_is_once_per_year_and_yields_20(self):
        self.tree["age_weeks"] = 8 * 52
        synchronize_tree_season(self.tree, 9, 32)
        self.assertTrue(complete_tree_harvest(
            self.buildings, self.orchard, self.tree["slot"],
        ))
        self.assertFalse(complete_tree_harvest(
            self.buildings, self.orchard, self.tree["slot"],
        ))
        warehouse = next(
            item for item in self.buildings if item["type"] == "warehouse"
        )
        self.assertEqual(20, warehouse["inventory"]["apple"])

    def test_visual_and_tooltip_state_follow_season(self):
        self.tree["age_weeks"] = 8 * 52
        synchronize_tree_season(self.tree, 9, 20)
        self.assertIn("Érés alatt", get_tree_tooltip_lines(self.tree))
        synchronize_tree_season(self.tree, 9, 32)
        lines = get_tree_tooltip_lines(self.tree)
        self.assertIn("Szüretelhető", lines)
        self.assertIn("30–35. hét", lines)


if __name__ == "__main__":
    unittest.main()
