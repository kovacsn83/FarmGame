"""Environment polish contracts: connectivity, transparency and render-only state."""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pygame

from building_renderers import _create_pond_surface
from camera import Camera
from environment_renderer import draw_area_fence
from orchards import TREE_TYPES, _tree_surface, draw_orchard_trees
from road_renderer import _create_road_surface, get_road_neighbor_mask
from screen_layout import set_camera, set_screen_size


class EnvironmentRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def setUp(self):
        set_screen_size(800, 600)
        set_camera(None)

    def tearDown(self):
        set_camera(None)

    def test_all_road_masks_and_variants_join_with_identical_lane_pixels(self):
        for mask in range(16):
            world = [[0] * 3 for _ in range(3)]
            world[1][1] = 1
            for bit, (row, col) in enumerate(((0, 1), (1, 2), (2, 1), (1, 0))):
                if mask & (1 << bit):
                    world[row][col] = 1
            self.assertEqual(mask, get_road_neighbor_mask(world, 1, 1))
            for variant in range(4):
                tile = _create_road_surface(mask, variant)
                self.assertEqual((20, 20), tile.get_size())
                for bit in range(4):
                    if not mask & (1 << bit):
                        continue
                    opposite = 1 << ((bit + 2) % 4)
                    for other_mask in range(16):
                        if not other_mask & opposite:
                            continue
                        for other_variant in range(4):
                            other = _create_road_surface(other_mask, other_variant)
                            for p in range(3, 17):
                                edge = ((p, 0), (19, p), (p, 19), (0, p))[bit]
                                paired = ((p, 19), (0, p), (p, 0), (19, p))[bit]
                                self.assertEqual(tile.get_at(edge), other.get_at(paired),
                                                 (mask, variant, bit, other_mask, other_variant, p))

    def test_pond_variants_are_native_resolution_opaque_inside_clear_outside(self):
        images = set()
        with patch('pygame.transform.smoothscale', side_effect=AssertionError('pixel art must not be filtered')):
            for variant in range(4):
                pond = _create_pond_surface(120, 120, variant)
                self.assertEqual((120, 120), pond.get_size())
                self.assertEqual(0, pond.get_at((0, 0)).a)
                self.assertEqual(255, pond.get_at((60, 60)).a)
                self.assertEqual({0, 255}, {pond.get_at((x, y)).a for x in range(120) for y in range(120)})
                images.add(pygame.image.tobytes(pond, 'RGBA'))
        self.assertEqual(4, len(images))

    def test_fence_cache_tracks_merge_and_demolition_without_internal_seam(self):
        left = {(r, c) for r in range(4, 8) for c in range(4, 8)}
        right = {(r, c) for r in range(4, 8) for c in range(8, 12)}
        screen = pygame.Surface((400, 300))
        background = (91, 139, 73)
        for tiles, shared_edge_present in ((left, True), (left | right, False), (left, True)):
            screen.fill(background)
            before = tiles.copy()
            draw_area_fence(screen, tiles)
            self.assertEqual(before, tiles)
            self.assertEqual(shared_edge_present, screen.get_at((160, 170))[:3] != background)

    def test_tree_shadows_blend_on_grass_soil_and_snow(self):
        for kind in TREE_TYPES:
            sprite = _tree_surface(kind, False)
            # Isolated exposed upper-right shadow, beyond the canopy.
            self.assertEqual(64, sprite.get_at((42, 18)).a)
            for ground in ((91, 139, 73), (137, 105, 67), (227, 231, 222)):
                screen = pygame.Surface((48, 48))
                screen.fill(ground)
                screen.blit(sprite, (0, 0))
                color = screen.get_at((42, 18))[:3]
                self.assertTrue(all(0 < dark < light for dark, light in zip(color, ground)))

    def test_tree_rendering_is_state_preserving_and_camera_relative(self):
        buildings = [dict(type='orchard', row=10, col=10, width=4, height=4, trees=[
            dict(type=kind, row=10, col=10 + i*2, annual_harvest_state='ripe')
            for i, kind in enumerate(TREE_TYPES)])]
        before = copy.deepcopy(buildings)
        first, shifted = pygame.Surface((800, 600)), pygame.Surface((800, 600))
        first.fill((91, 139, 73))
        shifted.fill((91, 139, 73))
        draw_orchard_trees(first, buildings)
        camera = Camera()
        set_camera(camera)
        camera.camera_x, camera.camera_y = 37, 19
        draw_orchard_trees(shifted, buildings)
        for x in range(190, 330):
            for y in range(240, 300):
                self.assertEqual(first.get_at((x, y)), shifted.get_at((x-37, y-19)))
        self.assertEqual(before, buildings)

    def test_warm_tree_and_fence_rendering_reuses_small_surfaces(self):
        for kind in TREE_TYPES:
            for ripe in (False, True):
                first = _tree_surface(kind, ripe)
                self.assertIs(first, _tree_surface(kind, ripe))
                self.assertEqual((48, 48), first.get_size())
        self.assertLessEqual(_tree_surface.cache_info().currsize, 6)
        screen = pygame.Surface((400, 300))
        tiles = {(4, 4), (4, 5)}
        draw_area_fence(screen, tiles)
        with patch('pygame.draw.line', side_effect=AssertionError('warm fences should only blit')):
            draw_area_fence(screen, tiles)


if __name__ == '__main__':
    unittest.main()
