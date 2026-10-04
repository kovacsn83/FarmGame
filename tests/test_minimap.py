import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pygame
from camera import Camera
from minimap import draw_minimap, get_minimap_rect, get_viewport_rect
from screen_layout import set_screen_size, get_play_area_rect


class MinimapTests(unittest.TestCase):
    def setUp(self):
        set_screen_size(1500, 1000)
        self.world = [[0] * 100 for _ in range(80)]
        self.camera = Camera()
        self.camera.update_viewport(1000, 800)

    def test_bottom_right_and_aspect_ratio(self):
        rect = get_minimap_rect(self.world)
        self.assertEqual(rect.size, (220, 176))
        self.assertEqual(rect.bottomright, (1488, 938))
        self.assertTrue(get_play_area_rect().contains(rect))

    def test_viewport_tracks_camera_and_clips(self):
        rect = get_minimap_rect(self.world)
        first = get_viewport_rect(rect, self.camera)
        self.assertEqual(first.size, (110, 88))
        self.camera.camera_x = 1000
        self.camera.camera_y = 800
        last = get_viewport_rect(rect, self.camera)
        self.assertEqual(last.bottomright, rect.bottomright)
        self.camera.update_viewport(4000, 4000)
        self.assertEqual(get_viewport_rect(rect, self.camera), rect)

    def test_empty_and_small_screen(self):
        self.assertEqual(get_minimap_rect([]).size, (0, 0))
        set_screen_size(320, 240)
        self.assertTrue(get_play_area_rect().contains(get_minimap_rect(self.world)))

    def test_render_updates_without_changing_world(self):
        screen = pygame.Surface((1500, 1000))
        rect = get_minimap_rect(self.world)
        before = [row[:] for row in self.world]
        draw_minimap(screen, self.world, [], self.camera)
        self.assertEqual(self.world, before)
        self.world[60][20] = 1
        draw_minimap(screen, self.world, [], self.camera)
        self.assertEqual(screen.get_at((rect.x + 45, rect.y + 133))[:3],
                         (165, 145, 104))


if __name__ == "__main__":
    unittest.main()
