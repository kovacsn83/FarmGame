import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pygame
from buildings import (BUILDING_TYPES, BUILD_OPTIONS, can_place_building,
                       place_building, remove_building, get_building_maintenance_base)
from building_renderers import draw_feed_mill, has_procedural_renderer
from constants import GRASS, ROAD, BUILDING
from economy import Economy
from game_state import GameState
from maintenance import calculate_annual_maintenance
from save_system import save_game, load_game, _migrate_save_schema, SAVE_VERSION
from time_system import GameTime
from screen_layout import set_screen_size, set_camera
from ui import BuildingSelectionPanel, InfoPanel


class FeedMillTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        set_screen_size(1500, 1000)
        set_camera(None)
        self.world = [[GRASS] * 60 for _ in range(35)]
        self.buildings = []

    def tearDown(self):
        pygame.quit()

    def test_catalog_menu_and_price(self):
        definition = BUILDING_TYPES["feed_mill"]
        self.assertIs(BUILD_OPTIONS["feed_mill"], definition)
        self.assertEqual(definition["build_cost"], 5000)
        self.assertEqual((definition["width"], definition["height"]), (12, 8))
        panel = BuildingSelectionPanel()
        panel.open()
        self.assertIn("feed_mill", panel.card_rects)
        economy = Economy()
        before = economy.money
        self.assertTrue(economy.can_build(definition["build_cost"]))
        economy.spend(definition["build_cost"])
        self.assertEqual(before - economy.money, 5000)

    def test_road_footprint_and_bounds(self):
        self.assertFalse(can_place_building(self.world, [], 8, 8, "feed_mill"))
        self.world[7][8] = ROAD
        self.assertTrue(can_place_building(self.world, [], 8, 8, "feed_mill"))
        self.assertFalse(can_place_building(self.world, [], 33, 38, "feed_mill"))
        mill = place_building(self.world, self.buildings, 8, 8, "feed_mill")
        self.assertTrue(all(self.world[r][c] == BUILDING
                            for r in range(8, 16) for c in range(8, 20)))
        self.assertFalse(can_place_building(self.world, self.buildings, 8, 8, "feed_mill"))
        self.assertEqual(mill["processing_capacity"], 200)
        self.assertTrue(InfoPanel().open_for_building(mill))

    def test_limit_and_demolition(self):
        for col in (2, 16):
            self.world[7][col] = ROAD
            place_building(self.world, self.buildings, 8, col, "feed_mill")
        self.world[7][32] = ROAD
        self.assertFalse(can_place_building(self.world, self.buildings, 8, 32, "feed_mill"))
        self.assertIsNone(place_building(self.world, self.buildings, 8, 32, "feed_mill"))
        remove_building(self.world, self.buildings, self.buildings[0])
        self.assertTrue(can_place_building(self.world, self.buildings, 8, 32, "feed_mill"))

    def test_maintenance(self):
        mill = place_building(self.world, self.buildings, 8, 8, "feed_mill")
        self.assertEqual(get_building_maintenance_base(mill), 5000)
        self.assertEqual(calculate_annual_maintenance(5000), 500)
        self.assertAlmostEqual(Economy().calculate_weekly_costs(
            self.world, self.buildings), 500 / 52)

    def test_save_load(self):
        mill = place_building(self.world, self.buildings, 8, 8, "feed_mill")
        expected = dict(mill)
        state = GameState(self.world, [], self.buildings, Economy(), GameTime(start_ticks=0))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "farm.json"
            self.assertTrue(save_game(state, path))
            remove_building(self.world, self.buildings, mill)
            self.assertTrue(load_game(state, path))
        self.assertEqual(state.buildings[0], expected)

    def test_procedural_renderer(self):
        mill = place_building(self.world, self.buildings, 8, 8, "feed_mill")
        self.assertTrue(has_procedural_renderer("feed_mill"))
        draw_feed_mill(pygame.Surface((1500, 1000)), mill)

    def test_legacy_footprint_is_preserved_without_overwriting_neighbors(self):
        mill = {"type": "feed_mill", "row": 8, "col": 8, "width": 6, "height": 5}
        for r in range(8, 13):
            for c in range(8, 14):
                self.world[r][c] = BUILDING
        data = {"save_version": SAVE_VERSION, "world": self.world, "buildings": [mill]}
        self.assertTrue(_migrate_save_schema(data))
        self.assertEqual((mill["row"], mill["col"], mill["width"], mill["height"]),
                         (8, 8, 6, 5))
        self.assertTrue(mill["legacy_footprint"])
        for r in range(8, 13):
            for c in range(8, 14):
                self.assertEqual(self.world[r][c], BUILDING)
        self.assertTrue(_migrate_save_schema(data))


if __name__ == "__main__":
    unittest.main()
