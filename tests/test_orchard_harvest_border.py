from pathlib import Path
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buildings import place_building
from economy import Economy
from field_renderer import (
    FIELD_HARVEST_READY_BORDER_COLOR, FIELD_BORDER_WIDTH,
)
from orchards import (
    complete_tree_harvest, draw_orchard_trees, find_tree_at, plant_tree,
    synchronize_tree_season,
)
from screen_layout import set_camera, set_screen_size
from world import create_world


class OrchardHarvestBorderTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        set_screen_size(1000, 800)
        set_camera(None)
        self.world = create_world()
        self.buildings = []
        self.orchard = place_building(
            self.world, self.buildings, 10, 10, "orchard",
        )
        self.warehouse = {
            "type": "warehouse", "row": 2, "col": 2,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {},
        }
        self.buildings.append(self.warehouse)
        self.economy = Economy()
        self.economy.money = 10_000
        self.surface = pygame.Surface((1000, 800))

    def _render(self):
        self.surface.fill((0, 0, 0))
        draw_orchard_trees(self.surface, self.buildings)

    def _assert_slot_border(self, left, top, expected=True):
        sample_points = (
            (left, top),
            (left + 20, top + FIELD_BORDER_WIDTH - 1),
            (left + 39, top + 20),
            (left + 20, top + 39),
        )
        for point in sample_points:
            color = self.surface.get_at(point)[:3]
            if expected:
                self.assertEqual(FIELD_HARVEST_READY_BORDER_COLOR, color)
            else:
                self.assertNotEqual(FIELD_HARVEST_READY_BORDER_COLOR, color)

    def test_ripe_apple_has_border_without_changing_click_target(self):
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "apple",
        )
        tree["age_weeks"] = 3 * 52
        synchronize_tree_season(tree, 4, 30)

        self._render()

        self._assert_slot_border(200, 250)
        self.assertIs(tree, find_tree_at(self.buildings, 10, 10)[1])
        self.assertNotEqual(
            FIELD_HARVEST_READY_BORDER_COLOR,
            self.surface.get_at((220, 270))[:3],
        )

    def test_unripe_harvested_and_expired_tree_have_no_border(self):
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "apple",
        )
        tree["age_weeks"] = 3 * 52
        synchronize_tree_season(tree, 4, 29)
        self._render()
        self._assert_slot_border(200, 250, expected=False)

        synchronize_tree_season(tree, 4, 30)
        self.assertTrue(complete_tree_harvest(
            self.buildings, self.orchard, tree["slot"],
        ))
        self._render()
        self._assert_slot_border(200, 250, expected=False)

        expired_tree = plant_tree(
            self.buildings, self.economy, 10, 12, "apple",
        )
        expired_tree["age_weeks"] = 3 * 52 + 6
        synchronize_tree_season(expired_tree, 4, 36)
        self.assertEqual("lost", expired_tree["annual_harvest_state"])
        self._render()
        self._assert_slot_border(240, 250, expected=False)

    def test_apple_and_cherry_receive_separate_slot_borders(self):
        apple = plant_tree(
            self.buildings, self.economy, 10, 10, "apple",
        )
        cherry = plant_tree(
            self.buildings, self.economy, 10, 12, "cherry",
        )
        apple["age_weeks"] = 3 * 52
        cherry["age_weeks"] = 5 * 52
        synchronize_tree_season(apple, 6, 30)
        synchronize_tree_season(cherry, 6, 24)

        self._render()

        self._assert_slot_border(200, 250)
        self._assert_slot_border(240, 250)
        self.assertEqual(
            FIELD_HARVEST_READY_BORDER_COLOR,
            self.surface.get_at((240, 270))[:3],
        )


if __name__ == "__main__":
    unittest.main()
