import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pygame
from feed_mill import initialize_feed_mill, run_weekly_feed_mills, get_feed_mill_tooltip_lines
from processing import get_processing_delivery_capacity, get_processing_line_capacity
from vehicle_manager import VehicleManager
from economy import Economy
from screen_layout import set_screen_size
from ui import draw_storage_meter, draw_tooltip


class FeedMillBufferTests(unittest.TestCase):
    def mill(self):
        return initialize_feed_mill(dict(type="feed_mill", row=0, col=0, width=12, height=8))

    def request(self, mill):
        with patch("processing._request_processing_input") as request:
            run_weekly_feed_mills([[0]], [mill], [], Economy(), VehicleManager(), 1)
        return request.call_args_list

    def test_requests_four_week_target_when_below_two_weeks(self):
        calls = self.request(self.mill())
        self.assertEqual([(c.args[5], c.args[6]) for c in calls], [("wheat", 20), ("corn", 20)])

    def test_no_refill_at_two_week_threshold(self):
        mill = self.mill()
        mill["processing_inventory"].update(wheat=15, corn=15)
        # One batch is produced first, leaving exactly ten of each.
        self.assertEqual(self.request(mill), [])

    def test_reserved_cargo_counts_toward_threshold(self):
        mill = self.mill()
        mill["processing_in_transit"] = {"wheat": 20, "corn": 20}
        with patch.object(VehicleManager, "reconcile_processing_deliveries"):
            self.assertEqual(self.request(mill), [])

    def test_only_missing_ingredient_is_refilled(self):
        mill = self.mill()
        mill["processing_inventory"].update(wheat=15, corn=0)
        calls = self.request(mill)
        self.assertEqual([(c.args[5], c.args[6]) for c in calls], [("corn", 20)])

    def test_freight_increase_does_not_change_processing_capacity(self):
        self.assertEqual(get_processing_delivery_capacity(self.mill()), 20)
        for level, expected in ((1, 5), (2, 5), (3, 6)):
            plant = {"type": "processing_plant", "_processing_plant_level": level}
            self.assertEqual(get_processing_delivery_capacity(plant), expected)
            self.assertEqual(get_processing_line_capacity(plant), expected)

    def test_storage_meter_separates_stored_and_incoming(self):
        screen = pygame.Surface((202, 20))
        draw_storage_meter(screen, screen.get_rect(), 50, 50, 200)
        self.assertEqual(screen.get_at((25, 10))[:3], (65, 158, 88))
        self.assertEqual(screen.get_at((75, 10))[:3], (218, 171, 66))
        self.assertEqual(screen.get_at((150, 10))[:3], (66, 69, 64))

    def test_tooltip_reserves_space_for_meter(self):
        pygame.font.init()
        set_screen_size(1000, 900)
        screen = pygame.Surface((1000, 900))
        font = pygame.font.Font(None, 22)
        lines = get_feed_mill_tooltip_lines(self.mill(), [])
        anchor = pygame.Rect(500, 800, 20, 20)
        plain = draw_tooltip(screen, font, list(lines), anchor)
        metered = draw_tooltip(screen, font, lines, anchor)
        self.assertEqual(metered.height, plain.height + 24)
        self.assertEqual(lines.storage_meter, (0, 0, 200))


if __name__ == "__main__":
    unittest.main()
