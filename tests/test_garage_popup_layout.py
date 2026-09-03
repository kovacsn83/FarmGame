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
        from buildings import get_garage_parking_position
        for asset in self.manager.managed_assets:
            asset.world_x, asset.world_y = get_garage_parking_position(
                asset.assigned_parking_building, asset.parking_slot_id)
        self.panel.open_for_building(self.garage)
        self.state = type("State", (), {"vehicles": self.manager})()

    def _drawn_entries(self):
        entries = []
        with patch.object(
            self.panel, "draw_text",
            side_effect=lambda screen, font, text, x, y: entries.append(
                (text, x, y)
            ),
        ):
            self.panel.draw(
                pygame.display.get_surface(), pygame.font.Font(None, 20),
                self.state,
            )
        return entries

    def _drawn_texts(self):
        return [text for text, _x, _y in self._drawn_entries()]

    def test_graphical_parking_precedes_counts_and_has_no_duplicate_list(self):
        texts = self._drawn_texts()
        self.assertLess(texts.index("Parkolónézet"), texts.index("Parkolóhelyek: 4 / 4"))
        self.assertNotIn("Parkoló eszközök:", texts)
        self.assertEqual(len(self.panel.garage_slot_rects), 4)
        self.assertEqual(set(self.panel.garage_parked_assets), {0, 1, 2, 3})
        self.assertIn("• Traktorok: 2", texts)
        self.assertIn("• Kombájnok: 1", texts)
        self.assertIn("• Pótkocsik: 1", texts)

    def test_fleet_rows_remain_indented(self):
        positions = {text: x for text, x, _ in self._drawn_entries()}
        self.assertGreater(positions["• Traktorok: 2"], positions["Járműállomány:"])

    def test_departure_and_return_refresh_without_mutating_slots(self):
        self._drawn_texts()
        initial_height = self.panel.rect.height
        self.tractor.state = "moving"
        self._drawn_texts()
        self.assertNotIn(0, self.panel.garage_parked_assets)
        self.assertEqual(self.tractor.parking_slot_id, 0)
        self.tractor.state = "idle"
        self._drawn_texts()
        self.assertIs(self.panel.garage_parked_assets[0], self.tractor)
        self.assertEqual(initial_height, self.panel.rect.height)
        self.assertEqual(len(self.panel.garage_purchase_rects), 5)

    def test_all_sprites_hidden_only_when_parked_and_grid_extensible(self):
        from garage_view import is_parked_in_garage, parked_sprite, parking_slot_rects
        harvester = self.manager._create_managed_asset(VehicleType.FRUIT_HARVESTER, self.other_garage, 1)
        from buildings import get_garage_parking_position
        harvester.world_x, harvester.world_y = get_garage_parking_position(self.other_garage, 1)
        for asset in self.manager.managed_assets:
            self.assertTrue(is_parked_in_garage(asset))
            self.assertGreater(parked_sprite(asset).get_bounding_rect().width, 0)
            screen = pygame.Surface((500, 500), pygame.SRCALPHA)
            asset.draw(screen)
            self.assertEqual(screen.get_bounding_rect().width, 0)
            asset.world_x += 50
            self.assertFalse(is_parked_in_garage(asset))
        for capacity in (4, 8, 12, 16):
            rects = parking_slot_rects(pygame.Rect(0, 0, 400, 240), capacity)
            self.assertEqual(len(rects), capacity)
            self.assertTrue(all(not a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:]))

    def test_scroll_and_close_consume_events_without_purchase(self):
        set_screen_size(640, 480)
        self._drawn_texts()
        self.assertLessEqual(self.panel.rect.bottom, 480)
        self.assertTrue(self.panel.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-3)))
        self.assertGreater(self.panel.garage_scroll, 0)
        self._drawn_texts()
        self.assertIsNone(self.panel.take_vehicle_purchase())
        self.assertTrue(self.panel.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)))
        self.assertFalse(self.panel.visible)
        self.panel.open_for_building(self.garage)
        self._drawn_texts()
        self.assertTrue(self.panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))))
        self.assertFalse(self.panel.visible)
        set_screen_size(1500, 1000)


if __name__ == "__main__":
    unittest.main()
