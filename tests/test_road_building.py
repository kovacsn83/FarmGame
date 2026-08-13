from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from camera import Camera
from constants import BUILDING, GRASS, ROAD, ROAD_BUILD_COST, TILE_SIZE, TOP_BAR_HEIGHT
from road_building import (
    ROAD_DRAG_AXIS_HORIZONTAL, ROAD_DRAG_AXIS_VERTICAL,
    RoadDragState, build_road_segment, calculate_road_tiles,
    validate_road_segment,
)
from screen_layout import set_camera, set_screen_size
from world import screen_to_grid


class FakeEconomy:
    def __init__(self, money):
        self.money = float(money)

    def can_build(self, cost):
        return self.money >= cost

    def spend(self, cost):
        if not self.can_build(cost):
            return False
        self.money -= cost
        return True


class RoadBuildingTests(unittest.TestCase):
    def setUp(self):
        self.world = [[GRASS for _ in range(12)] for _ in range(12)]

    def test_single_click_builds_one_tile(self):
        economy = FakeEconomy(100)
        events = []
        result = build_road_segment(
            self.world, [(3, 4)], economy, events.append,
        )
        self.assertEqual(result, (True, 1, ROAD_BUILD_COST))
        self.assertEqual(self.world[3][4], ROAD)
        self.assertEqual(events, [1])

    def test_all_four_drag_directions_create_straight_segments(self):
        cases = (
            ((5, 5), (5, 8), [(5, col) for col in range(5, 9)]),
            ((5, 5), (5, 2), [(5, col) for col in range(2, 6)]),
            ((5, 5), (2, 5), [(row, 5) for row in range(2, 6)]),
            ((5, 5), (8, 5), [(row, 5) for row in range(5, 9)]),
        )
        for start, end, expected in cases:
            with self.subTest(start=start, end=end):
                self.assertEqual(calculate_road_tiles(start, end), expected)

    def test_axis_locks_and_ignores_later_sideways_drift(self):
        drag = RoadDragState()
        drag.begin((5, 5))
        drag.update((6, 8))
        self.assertEqual(drag.axis, ROAD_DRAG_AXIS_HORIZONTAL)
        drag.update((10, 9))
        self.assertEqual(drag.axis, ROAD_DRAG_AXIS_HORIZONTAL)
        self.assertTrue(all(row == 5 for row, _ in drag.tiles))

        drag.cancel()
        drag.begin((5, 5))
        drag.update((8, 6))
        self.assertEqual(drag.axis, ROAD_DRAG_AXIS_VERTICAL)
        drag.update((9, 10))
        self.assertEqual(drag.axis, ROAD_DRAG_AXIS_VERTICAL)
        self.assertTrue(all(col == 5 for _, col in drag.tiles))

    def test_existing_roads_are_valid_and_free(self):
        self.world[4][3] = ROAD
        self.world[4][4] = ROAD
        tiles = calculate_road_tiles((4, 2), (4, 5))
        new_tiles, invalid_tiles = validate_road_segment(self.world, tiles)
        self.assertEqual(invalid_tiles, [])
        self.assertEqual(new_tiles, [(4, 2), (4, 5)])
        economy = FakeEconomy(2 * ROAD_BUILD_COST)
        self.assertEqual(
            build_road_segment(self.world, tiles, economy),
            (True, 2, 2 * ROAD_BUILD_COST),
        )
        self.assertEqual(economy.money, 0)

    def test_forbidden_tile_rejects_entire_segment(self):
        self.world[4][4] = BUILDING
        tiles = calculate_road_tiles((4, 2), (4, 6))
        economy = FakeEconomy(1000)
        self.assertEqual(
            build_road_segment(self.world, tiles, economy),
            (False, 0, 0.0),
        )
        self.assertTrue(all(self.world[4][col] != ROAD for col in range(2, 7)))
        self.assertEqual(economy.money, 1000)

    def test_insufficient_money_rejects_entire_segment(self):
        tiles = calculate_road_tiles((4, 2), (4, 6))
        economy = FakeEconomy(4 * ROAD_BUILD_COST)
        success, count, cost = build_road_segment(self.world, tiles, economy)
        self.assertFalse(success)
        self.assertEqual(count, 0)
        self.assertEqual(cost, 5 * ROAD_BUILD_COST)
        self.assertTrue(all(self.world[4][col] == GRASS for col in range(2, 7)))

    def test_cancel_clears_preview_without_building(self):
        drag = RoadDragState()
        drag.begin((2, 2))
        drag.update((2, 7))
        self.assertTrue(drag.tiles)
        drag.cancel()
        self.assertFalse(drag.active)
        self.assertEqual(drag.tiles, [])

    def test_screen_to_grid_uses_camera_offset(self):
        camera = Camera()
        camera.update_world_size(100, 80)
        set_screen_size(400, 300)
        set_camera(camera)
        camera.camera_x = 6 * TILE_SIZE
        camera.camera_y = 4 * TILE_SIZE
        row, col = screen_to_grid(
            2 * TILE_SIZE + 1,
            TOP_BAR_HEIGHT + 3 * TILE_SIZE + 1,
            self.world,
        )
        self.assertEqual((row, col), (7, 8))
        set_camera(None)


if __name__ == "__main__":
    unittest.main()
