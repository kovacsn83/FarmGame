import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pygame

from screen_layout import set_screen_size
from ui import InfoPanel
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class GaragePopupLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1500, 1000))
        set_screen_size(1500, 1000)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.garage = {
            "type": "garage", "row": 2, "col": 2,
            "width": 4, "height": 4,
        }
        self.other_garage = {
            "type": "garage", "row": 2, "col": 10,
            "width": 4, "height": 4,
        }
        self.manager = VehicleManager()
        self.tractor = self.manager._create_managed_asset(
            VehicleType.TRACTOR, self.garage, 0,
        )
        self.water_tank = self.manager._create_managed_asset(
            VehicleType.WATER_TANK, self.garage, 1,
        )
        self.trailer = self.manager._create_managed_asset(
            VehicleType.TRAILER, self.garage, 2,
        )
        self.combine = self.manager._create_managed_asset(
            VehicleType.COMBINE, self.garage, 3,
        )
        self.manager._create_managed_asset(
            VehicleType.TRACTOR, self.other_garage, 0,
        )
        self.panel = InfoPanel()
        self.panel.open_for_building(self.garage)
        self.state = type("State", (), {"vehicles": self.manager})()

    def _drawn_texts(self):
        texts = []
        with patch.object(
            self.panel, "draw_text",
            side_effect=lambda screen, font, text, x, y: texts.append(text),
        ):
            self.panel.draw(
                pygame.display.get_surface(), pygame.font.Font(None, 20),
                self.state,
            )
        return texts

    def test_parking_list_precedes_the_fleet_counts(self):
        texts = self._drawn_texts()
        parking_index = texts.index("Parkoló eszközök:")
        fleet_index = texts.index("Járműállomány:")

        self.assertLess(texts.index("Parkolóhelyek: 4 / 4"), parking_index)
        self.assertLess(texts.index("Szabad hely: 0"), parking_index)
        self.assertLess(parking_index, texts.index("• Traktor #1"))
        self.assertLess(texts.index("• Kombájn #4"), fleet_index)
        self.assertLess(fleet_index, texts.index("Traktorok: 2"))
        self.assertIn("• Locsolótartály #2 – Garázsban", texts)
        self.assertIn("• Pótkocsi #3 – Garázsban", texts)
        self.assertIn("Kombájnok: 1", texts)
        self.assertIn("Gyümölcs szüretelőgépek: 0", texts)
        self.assertIn("Locsolótartályok: 1", texts)
        self.assertIn("Pótkocsik: 1", texts)

    def test_redraw_uses_current_garage_assets_without_changing_panel_size(self):
        initial_texts = self._drawn_texts()
        initial_height = self.panel.rect.height
        self.assertIn("• Pótkocsi #3 – Garázsban", initial_texts)

        self.trailer.assigned_parking_building = self.other_garage
        self.trailer.parking_slot_id = 1
        updated_texts = self._drawn_texts()

        self.assertNotIn("• Pótkocsi #3 – Garázsban", updated_texts)
        self.assertIn("Parkolóhelyek: 3 / 4", updated_texts)
        self.assertIn("Szabad hely: 1", updated_texts)
        self.assertIn("Pótkocsik: 1", updated_texts)
        self.assertEqual(initial_height - 24, self.panel.rect.height)
        self.assertEqual(
            {
                VehicleType.TRACTOR, VehicleType.COMBINE,
                VehicleType.FRUIT_HARVESTER, VehicleType.WATER_TANK,
                VehicleType.TRAILER,
            },
            set(self.panel.garage_purchase_rects),
        )


if __name__ == "__main__":
    unittest.main()
