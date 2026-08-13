import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame

from buildings import (
    BUILDING_TYPES, BUILD_OPTIONS, can_place_building, get_orchard_groups,
    get_orchard_tiles, place_building, remove_building,
)
from constants import (
    BUILDING, GRASS, ORCHARD_BUILD_COST, ROAD, TILE_SIZE, TOP_BAR_HEIGHT,
)
from maintenance import calculate_weekly_maintenance
from economy import Economy
from game_state import GameState
from save_system import load_game, save_game
from screen_layout import set_camera
from time_system import GameTime
from world import draw_orchard_fences


class OrchardTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        set_camera(None)
        self.world = [[GRASS for _ in range(30)] for _ in range(30)]
        self.buildings = []

    def tearDown(self):
        pygame.quit()

    def _add_road_above(self, row, col, width=4):
        for offset in range(width):
            self.world[row - 1][col + offset] = ROAD

    def test_catalog_contains_configured_orchard(self):
        definition = BUILDING_TYPES["orchard"]
        self.assertIs(BUILD_OPTIONS["orchard"], definition)
        self.assertEqual("Gyümölcsös", definition["name"])
        self.assertEqual((4, 4), (definition["width"], definition["height"]))
        self.assertEqual(200.0, definition["build_cost"])
        self.assertEqual(ORCHARD_BUILD_COST, definition["build_cost"])
        self.assertEqual(
            20.0 / 52,
            calculate_weekly_maintenance(definition["build_cost"]),
        )

    def test_first_orchard_requires_road_and_diagonal_touch_does_not_count(self):
        self.assertFalse(can_place_building(
            self.world, self.buildings, 5, 5, "orchard",
        ))
        self._add_road_above(5, 5)
        self.assertTrue(can_place_building(
            self.world, self.buildings, 5, 5, "orchard",
        ))
        place_building(self.world, self.buildings, 5, 5, "orchard")
        self.assertFalse(can_place_building(
            self.world, self.buildings, 9, 9, "orchard",
        ))

    def test_connected_orchard_needs_no_second_road(self):
        self._add_road_above(5, 5)
        first = place_building(self.world, self.buildings, 5, 5, "orchard")
        self.assertTrue(can_place_building(
            self.world, self.buildings, 5, 9, "orchard",
        ))
        second = place_building(self.world, self.buildings, 5, 9, "orchard")
        self.assertEqual(32, len(get_orchard_tiles(self.buildings)))
        self.assertEqual([[first, second]], get_orchard_groups(self.buildings))
        self.assertTrue(all(
            self.world[row][col] == BUILDING
            for row, col in get_orchard_tiles(self.buildings)
        ))
        self.assertIn(first, self.buildings)
        self.assertIn(second, self.buildings)

    def test_orchard_round_trips_through_save_system(self):
        orchard = place_building(
            self.world, self.buildings, 5, 5, "orchard",
        )
        state = GameState(
            self.world, [], self.buildings, Economy(), GameTime(start_ticks=0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orchard.json"
            self.assertTrue(save_game(state, path))
            remove_building(self.world, self.buildings, orchard)
            self.assertTrue(load_game(state, path))

        self.assertEqual("orchard", state.buildings[0]["type"])
        self.assertEqual((5, 5, 4, 4), (
            state.buildings[0]["row"], state.buildings[0]["col"],
            state.buildings[0]["width"], state.buildings[0]["height"],
        ))
        self.assertEqual(16, len(get_orchard_tiles(state.buildings)))

    def test_fence_omits_shared_edge_and_returns_after_demolition(self):
        first = place_building(self.world, self.buildings, 5, 5, "orchard")
        second = place_building(self.world, self.buildings, 5, 9, "orchard")
        surface = pygame.Surface((30 * TILE_SIZE, 30 * TILE_SIZE))
        fence_color = (112, 72, 38)

        draw_orchard_fences(surface, self.buildings)
        shared_x = 9 * TILE_SIZE
        shared_y = TOP_BAR_HEIGHT + 7 * TILE_SIZE
        self.assertNotEqual(fence_color, surface.get_at((shared_x, shared_y))[:3])

        self.assertTrue(remove_building(self.world, self.buildings, second))
        surface.fill((0, 0, 0))
        draw_orchard_fences(surface, self.buildings)
        self.assertEqual(fence_color, surface.get_at((shared_x, shared_y))[:3])
        self.assertTrue(all(
            self.world[row][col] == GRASS
            for row in range(5, 9) for col in range(9, 13)
        ))
        self.assertIn(first, self.buildings)


if __name__ == "__main__":
    unittest.main()
