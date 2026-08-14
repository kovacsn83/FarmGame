import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame

from building_renderers import (
    draw_processing_plant, has_procedural_renderer,
)
from buildings import (
    BUILDING_TYPES, BUILD_OPTIONS, can_place_building, place_building,
    remove_building,
)
from constants import (
    BUILDING, GRASS, PROCESSING_PLANT_BUILD_COST, ROAD, TILE_SIZE,
)
from economy import Economy
from game_state import GameState
from maintenance import calculate_annual_maintenance
from save_system import load_game, save_game
from screen_layout import set_camera, set_screen_size, world_to_screen
from time_system import GameTime
from ui import BuildingSelectionPanel, InfoPanel


class ProcessingPlantTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        set_screen_size(1000, 800)
        set_camera(None)
        self.world = [[GRASS for _ in range(40)] for _ in range(35)]
        self.buildings = []

    def tearDown(self):
        pygame.quit()

    def _add_road_above(self, row, col):
        for offset in range(6):
            self.world[row - 1][col + offset] = ROAD

    def test_catalog_and_building_menu_use_the_central_definition(self):
        definition = BUILDING_TYPES["processing_plant"]
        self.assertIs(BUILD_OPTIONS["processing_plant"], definition)
        self.assertEqual("Feldolgozó üzem", definition["name"])
        self.assertEqual((6, 5), (definition["width"], definition["height"]))
        self.assertEqual(3000.0, definition["build_cost"])
        self.assertEqual(PROCESSING_PLANT_BUILD_COST, definition["build_cost"])
        self.assertEqual(300.0, calculate_annual_maintenance(3000.0))
        self.assertEqual((), definition["recipes"])

        panel = BuildingSelectionPanel()
        panel.open()
        self.assertIn("processing_plant", panel.card_rects)

    def test_road_rule_and_full_footprint_are_enforced(self):
        self.assertFalse(can_place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        ))
        self._add_road_above(8, 8)
        self.assertTrue(can_place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        ))
        plant = place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        )
        self.assertTrue(all(
            self.world[row][col] == BUILDING
            for row in range(8, 13) for col in range(8, 14)
        ))
        self.assertFalse(can_place_building(
            self.world, self.buildings, 9, 9, "warehouse",
        ))

        self.assertTrue(remove_building(self.world, self.buildings, plant))
        self.assertTrue(all(
            self.world[row][col] == GRASS
            for row in range(8, 13) for col in range(8, 14)
        ))

    def test_renderer_and_information_view_are_registered(self):
        plant = place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        )
        self.assertTrue(has_procedural_renderer("processing_plant"))
        surface = pygame.Surface((1000, 800))
        surface.fill((1, 2, 3))
        draw_processing_plant(surface, plant)
        x, y = map(round, world_to_screen(8 * TILE_SIZE, 8 * TILE_SIZE))
        self.assertNotEqual((1, 2, 3), surface.get_at((x + 10, y + 10))[:3])

        info = InfoPanel()
        self.assertTrue(info.open_for_building(plant))
        self.assertEqual("processing_plant", info.building_type)

    def test_save_load_preserves_position_and_footprint(self):
        plant = place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        )
        state = GameState(
            self.world, [], self.buildings, Economy(), GameTime(start_ticks=0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "processing-plant.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(remove_building(self.world, self.buildings, plant))
            self.assertTrue(load_game(state, path))

        loaded = state.buildings[0]
        self.assertEqual("processing_plant", loaded["type"])
        self.assertEqual((8, 8, 6, 5), (
            loaded["row"], loaded["col"], loaded["width"], loaded["height"],
        ))


if __name__ == "__main__":
    unittest.main()
