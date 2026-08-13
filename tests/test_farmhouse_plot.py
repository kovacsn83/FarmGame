from pathlib import Path
import sys
import tempfile
import unittest

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from building_renderers import FARMHOUSE_FENCE_COLOR, draw_farmhouse
from buildings import (
    BUILDING_TYPES, FARMHOUSE_LEVELS, can_place_building,
    find_building_data, get_building_maintenance_base,
    place_building, remove_building,
)
from constants import BUILDING, GRASS, ROAD, TILE_SIZE
from economy import Economy
from game_state import GameState
from maintenance import calculate_annual_maintenance, calculate_weekly_maintenance
from save_system import _migrate_farmhouse_footprints, _migrate_farmhouse_levels
from save_system import load_game, save_game
from screen_layout import set_camera, set_screen_size, world_to_screen
from time_system import GameTime


class FarmhousePlotTests(unittest.TestCase):
    def setUp(self):
        self.world = [[GRASS for _ in range(24)] for _ in range(24)]
        self.buildings = []
        for col in range(2, 10):
            self.world[10][col] = ROAD

    def test_definition_preview_and_placement_use_eight_by_eight_plot(self):
        definition = BUILDING_TYPES["farmhouse"]
        self.assertEqual((definition["width"], definition["height"]), (8, 8))
        self.assertTrue(can_place_building(
            self.world, self.buildings, 2, 2, "farmhouse",
        ))
        farmhouse = place_building(
            self.world, self.buildings, 2, 2, "farmhouse",
        )
        self.assertEqual((farmhouse["width"], farmhouse["height"]), (8, 8))
        self.assertEqual(farmhouse["farmhouse_level"], 1)
        self.assertTrue(all(
            self.world[row][col] == BUILDING
            for row in range(2, 10) for col in range(2, 10)
        ))
        self.assertIs(find_building_data(self.buildings, 2, 2), farmhouse)
        self.assertIs(find_building_data(self.buildings, 9, 9), farmhouse)

    def test_occupied_tile_and_world_edge_reject_whole_plot(self):
        self.world[5][5] = ROAD
        self.assertFalse(can_place_building(
            self.world, self.buildings, 2, 2, "farmhouse",
        ))
        self.assertFalse(can_place_building(
            self.world, self.buildings, 18, 18, "farmhouse",
        ))

    def test_demolition_releases_complete_plot(self):
        farmhouse = place_building(
            self.world, self.buildings, 2, 2, "farmhouse",
        )
        self.assertTrue(remove_building(self.world, self.buildings, farmhouse))
        self.assertFalse(self.buildings)
        self.assertTrue(all(
            self.world[row][col] == GRASS
            for row in range(2, 10) for col in range(2, 10)
        ))

    def test_legacy_house_expands_without_moving_visible_house(self):
        world = [[GRASS for _ in range(20)] for _ in range(20)]
        farmhouse = {
            "type": "farmhouse", "row": 8, "col": 8,
            "width": 4, "height": 4,
        }
        for row in range(8, 12):
            for col in range(8, 12):
                world[row][col] = BUILDING
        data = {
            "world": world, "buildings": [farmhouse],
            "tractors": [{
                "parking_type": "farmhouse", "parking_row": 8,
                "parking_col": 8,
            }],
        }
        _migrate_farmhouse_footprints(data)
        _migrate_farmhouse_levels(data)
        self.assertEqual(
            (farmhouse["row"], farmhouse["col"],
             farmhouse["width"], farmhouse["height"]),
            (4, 4, 8, 8),
        )
        self.assertEqual(
            (data["tractors"][0]["parking_row"],
             data["tractors"][0]["parking_col"]),
            (4, 4),
        )
        self.assertEqual(farmhouse["farmhouse_level"], 2)

    def test_blocked_legacy_house_is_preserved_without_relocation(self):
        world = [[GRASS for _ in range(20)] for _ in range(20)]
        farmhouse = {
            "type": "farmhouse", "row": 8, "col": 8,
            "width": 4, "height": 4,
        }
        for row in range(8, 12):
            for col in range(8, 12):
                world[row][col] = BUILDING
        world[4][4] = ROAD
        data = {"world": world, "buildings": [farmhouse], "tractors": []}
        _migrate_farmhouse_footprints(data)
        self.assertEqual(
            (farmhouse["row"], farmhouse["col"],
             farmhouse["width"], farmhouse["height"]),
            (8, 8, 4, 4),
        )
        self.assertTrue(farmhouse["legacy_footprint"])

    def test_level_two_upgrade_is_atomic_and_replaces_maintenance_base(self):
        farmhouse = place_building(
            self.world, self.buildings, 2, 2, "farmhouse",
        )
        poor_state = GameState(
            self.world, [], self.buildings, Economy(4999), GameTime(start_ticks=0),
        )
        self.assertFalse(poor_state.economy.purchase_upgrade(
            poor_state, "farmhouse_level_2",
        ))
        self.assertEqual(farmhouse["farmhouse_level"], 1)
        self.assertEqual(poor_state.economy.money, 4999)

        state = GameState(
            self.world, [], self.buildings, Economy(7000), GameTime(start_ticks=0),
        )
        self.assertTrue(state.economy.purchase_upgrade(
            state, "farmhouse_level_2",
        ))
        self.assertEqual(state.economy.money, 2000)
        self.assertEqual(farmhouse["farmhouse_level"], 2)
        base = get_building_maintenance_base(farmhouse)
        self.assertEqual(base, 5000)
        self.assertEqual(calculate_annual_maintenance(base), 500)
        self.assertAlmostEqual(calculate_weekly_maintenance(base), 500 / 52)

    def test_level_round_trips_and_legacy_defaults_to_level_two(self):
        farmhouse = place_building(
            self.world, self.buildings, 2, 2, "farmhouse",
        )
        farmhouse["farmhouse_level"] = 2
        state = GameState(
            self.world, [], self.buildings, Economy(), GameTime(start_ticks=0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "farmhouse-level.json"
            self.assertTrue(save_game(state, path))
            farmhouse["farmhouse_level"] = 1
            self.assertTrue(load_game(state, path))
        self.assertEqual(state.buildings[0]["farmhouse_level"], 2)

    def test_renderer_places_uniform_fence_and_house_in_lower_right(self):
        pygame.init()
        set_screen_size(300, 300)
        set_camera(None)
        plot_x, plot_y = map(round, world_to_screen(TILE_SIZE, TILE_SIZE))
        plot_size = 8 * TILE_SIZE
        background = (1, 2, 3)

        for level in (1, 2):
            with self.subTest(level=level):
                screen = pygame.Surface((300, 300))
                screen.fill(background)
                draw_farmhouse(screen, {
                    "type": "farmhouse", "row": 1, "col": 1,
                    "width": 8, "height": 8, "farmhouse_level": level,
                })
                fence_points = (
                    (plot_x + plot_size // 2, plot_y),
                    (plot_x + plot_size // 2, plot_y + plot_size - 1),
                    (plot_x, plot_y + plot_size // 2),
                    (plot_x + plot_size - 1, plot_y + plot_size // 2),
                    (plot_x, plot_y),
                    (plot_x + plot_size - 1, plot_y + plot_size - 1),
                )
                for point in fence_points:
                    self.assertEqual(
                        screen.get_at(point)[:3], FARMHOUSE_FENCE_COLOR,
                    )

                # A folytonos kerítésen kívül nincs kinyúló sarokoszlop.
                self.assertEqual(
                    screen.get_at((plot_x - 1, plot_y - 1))[:3], background,
                )
                self.assertEqual(
                    screen.get_at((plot_x + 20, plot_y + 20))[:3], background,
                )
                self.assertNotEqual(
                    screen.get_at((plot_x + 5 * TILE_SIZE + 8,
                                   plot_y + 5 * TILE_SIZE + 8))[:3],
                    background,
                )
        self.assertEqual(FARMHOUSE_LEVELS[1]["size"], (3, 3))
        self.assertEqual(FARMHOUSE_LEVELS[2]["size"], (4, 4))


if __name__ == "__main__":
    unittest.main()
