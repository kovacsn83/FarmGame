"""Building shadows darken their receiving material without replacing its color."""
import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pygame

from building_renderers import (
    BUILDING_RENDERERS, PROCEDURAL_SHADOW_COLOR, _building_shadow_surface,
    _draw_building_shadow,
)
from buildings import BUILDING_TYPES
from screen_layout import set_camera, set_screen_size


class BuildingShadowTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        set_camera(None)
        set_screen_size(500, 400)

    def assert_darkened(self, actual, original):
        # Neutral 25% opacity preserves material channel ratios, within rounding.
        for channel, ground in zip(actual[:3], original):
            self.assertAlmostEqual(ground * 191 / 255, channel, delta=1)

    def test_same_shadow_blends_independently_with_road_field_and_grass(self):
        surface = pygame.Surface((160, 160))
        grass, road, field = (91, 139, 73), (148, 126, 97), (137, 105, 67)
        surface.fill(grass)
        pygame.draw.rect(surface, road, (0, 0, 160, 40))
        pygame.draw.rect(surface, field, (100, 40, 60, 120))
        _draw_building_shadow(surface, pygame.Rect(40, 40, 60, 60), PROCEDURAL_SHADOW_COLOR)
        self.assert_darkened(surface.get_at((60, 38)), road)
        self.assert_darkened(surface.get_at((102, 60)), field)
        self.assert_darkened(surface.get_at((60, 60)), grass)
        self.assertEqual(grass, surface.get_at((30, 60))[:3])

    def test_every_building_uses_material_preserving_upper_and_right_shadows(self):
        for kind, render in BUILDING_RENDERERS.items():
            if kind == 'pond' or kind not in BUILDING_TYPES:
                continue
            for ground in ((91, 139, 73), (148, 126, 97), (137, 105, 67)):
                with self.subTest(kind=kind, ground=ground):
                    surface = pygame.Surface((500, 400))
                    surface.fill(ground)
                    building = dict(BUILDING_TYPES[kind], type=kind, row=3, col=3)
                    if kind == 'farmhouse':
                        building.update(width=4, height=4, legacy_footprint=True)
                    render(surface, building)
                    width, height = building['width'] * 20, building['height'] * 20
                    self.assert_darkened(surface.get_at((60 + width // 2, 108)), ground)
                    self.assert_darkened(surface.get_at((60 + width + 1, 110 + height // 2)), ground)

    def test_cached_shadow_does_not_capture_the_background(self):
        first = _building_shadow_surface((100, 80), PROCEDURAL_SHADOW_COLOR)
        self.assertIs(first, _building_shadow_surface((100, 80), PROCEDURAL_SHADOW_COLOR))
        self.assertEqual(64, first.get_at((50, 40)).a)
        self.assertEqual(0, first.get_at((0, 0)).a)


if __name__ == '__main__':
    unittest.main()
