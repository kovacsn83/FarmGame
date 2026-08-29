from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from field_renderer import (
    FIELD_BORDER_COLOR, FIELD_HARVEST_READY_BORDER_COLOR,
    FIELD_LATE_HARVEST_BORDER_COLOR,
    FIELD_STATUS_MARKER_POSITION, FIELD_STATUS_MARKER_SPACING,
    SPRAYED_MARKER_COLOR,
    GROWTH_DEVELOPED, _create_field_surface, _draw_corn,
    get_field_border_color,
)


class CornRendererTests(unittest.TestCase):
    def test_every_corn_tile_draws_a_plant_for_all_affected_fields(self):
        surface = pygame.Surface((4 * 20, 4 * 20))
        for field_col in (7, 12, 17, 22, 27, 32):
            field = {
                "row": 13, "col": field_col,
                "width": 4, "height": 4,
            }
            with patch("field_renderer.pygame.draw.line") as draw_line:
                _draw_corn(surface, field, GROWTH_DEVELOPED)

            # Fejlett fázisban növényenként egy szár és két levél készül.
            self.assertEqual(draw_line.call_count, 4 * 4 * 3)


class FieldBorderRendererTests(unittest.TestCase):
    def setUp(self):
        self.field = {
            "row": 2, "col": 3, "width": 4, "height": 4,
            "crop": "alfalfa", "growth": 100, "growth_weeks": 20,
            "harvestable": True, "harvest_count": 1,
            "fertilized": False, "watered": False,
        }

    def test_normal_field_uses_dark_brown_border(self):
        self.assertEqual(get_field_border_color(False), FIELD_BORDER_COLOR)
        surface = _create_field_surface(self.field, harvest_ready=False)
        self.assertEqual(surface.get_at((0, 0))[:3], FIELD_BORDER_COLOR)

    def test_harvest_ready_field_uses_golden_brown_border(self):
        self.assertEqual(
            get_field_border_color(True), FIELD_HARVEST_READY_BORDER_COLOR,
        )
        surface = _create_field_surface(self.field, harvest_ready=True)
        self.assertEqual(
            surface.get_at((0, 0))[:3], FIELD_HARVEST_READY_BORDER_COLOR,
        )

    def test_late_harvest_field_uses_red_border(self):
        self.field["late_harvest_active"] = True
        self.assertEqual(
            get_field_border_color(True, True),
            FIELD_LATE_HARVEST_BORDER_COLOR,
        )
        surface = _create_field_surface(self.field, harvest_ready=True)
        self.assertEqual(
            surface.get_at((0, 0))[:3], FIELD_LATE_HARVEST_BORDER_COLOR,
        )

    def test_spraying_marker_uses_the_fixed_third_position(self):
        self.field.update({"growth": 20, "sprayed": True})
        surface = _create_field_surface(self.field)
        start_x, marker_y = FIELD_STATUS_MARKER_POSITION
        marker_x = start_x + 2 * FIELD_STATUS_MARKER_SPACING
        self.assertEqual(
            SPRAYED_MARKER_COLOR,
            surface.get_at((marker_x, marker_y))[:3],
        )


if __name__ == "__main__":
    unittest.main()
