import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pygame
import animal_troughs
from building_renderers import draw_feed_mill
from screen_layout import set_camera, set_screen_size


class FeedMillTroughGraphicsTests(unittest.TestCase):
    def setUp(self):
        set_camera(None)
        set_screen_size(1500, 1000)
        self.mill = dict(type="feed_mill", row=3, col=3, width=12, height=8)

    def test_uses_shared_geometry_and_renderer_once_per_trough(self):
        with patch.object(animal_troughs, "_draw_trough") as draw:
            draw_feed_mill(pygame.Surface((1500, 1000)), self.mill)
        self.assertEqual(draw.call_count, 2)
        food, water = draw.call_args_list
        self.assertEqual(food.args[1].size, (animal_troughs.TROUGH_WIDTH, animal_troughs.TROUGH_HEIGHT))
        self.assertEqual(water.args[1].left - food.args[1].right, animal_troughs.TROUGH_GAP)
        self.assertEqual(food.args[3:5], (0, 1))
        self.assertEqual(water.args[3:5], (1, 1))
        self.assertFalse(food.kwargs["water"])
        self.assertTrue(water.kwargs["water"])

    def test_fed_state_uses_normal_full_feed_style_without_mutation(self):
        self.mill["fed_this_week"] = True
        before = dict(self.mill)
        with patch.object(animal_troughs, "_draw_trough") as draw:
            draw_feed_mill(pygame.Surface((1500, 1000)), self.mill)
        self.assertEqual(draw.call_args_list[0].args[3:5], (1, 1))
        self.assertEqual(self.mill, before)


if __name__ == "__main__":
    unittest.main()
