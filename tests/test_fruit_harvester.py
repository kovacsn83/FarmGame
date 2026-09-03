import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constants import FRUIT_HARVESTER_PURCHASE_PRICE, GRASS, ROAD
from economy import Economy
from maintenance import calculate_weekly_maintenance
from tractor import FruitHarvester
from ui import InfoPanel
from vehicle_manager import VehicleManager
from vehicle_types import VEHICLE_TYPE_DEFINITIONS, VehicleType


class FruitHarvesterTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        self.world = [[GRASS for _ in range(30)] for _ in range(30)]
        self.garage = {
            "type": "garage", "row": 2, "col": 2,
            "width": 4, "height": 4,
        }
        self.buildings = [self.garage]
        for col in range(2, 6):
            self.world[1][col] = ROAD
        self.manager = VehicleManager()
        self.economy = Economy(1000)

    def test_catalog_defines_self_propelled_apple_harvester(self):
        definition = VEHICLE_TYPE_DEFINITIONS[VehicleType.FRUIT_HARVESTER]
        self.assertEqual("Gyümölcs szüretelőgép", definition["name"])
        self.assertEqual(500, FRUIT_HARVESTER_PURCHASE_PRICE)
        self.assertEqual(500, definition["purchase_price"])
        self.assertTrue(definition["self_propelled"])
        self.assertFalse(definition["towable"])
        self.assertEqual(("orchard_harvest",), definition["supported_tasks"])
        self.assertEqual(
            ("apple", "cherry", "plum"),
            definition["supported_tree_types"],
        )

    def test_purchase_registers_and_parks_the_vehicle(self):
        self.assertTrue(self.manager.purchase_fruit_harvester(
            self.world, self.buildings, self.economy, self.garage,
        ))
        self.assertEqual(500, self.economy.money)
        self.assertEqual(1, self.manager.count_by_type(
            VehicleType.FRUIT_HARVESTER,
        ))
        vehicle = self.manager.vehicles[0]
        self.assertIsInstance(vehicle, FruitHarvester)
        self.assertIs(vehicle.assigned_parking_building, self.garage)
        self.assertEqual(0, vehicle.parking_slot_id)
        self.assertTrue(vehicle.is_idle)
        self.assertIsNotNone(vehicle.world_x)
        self.assertTrue(vehicle.supports_task("orchard_harvest"))
        self.assertFalse(vehicle.supports_task("harvest"))

    def test_maintenance_uses_the_common_ten_percent_rule(self):
        self.manager.purchase_fruit_harvester(
            self.world, self.buildings, self.economy, self.garage,
        )
        self.assertAlmostEqual(
            calculate_weekly_maintenance(500), self.manager.weekly_cost,
        )

    def test_garage_purchase_list_contains_the_vehicle(self):
        panel = InfoPanel()
        panel.open_for_building(self.garage)
        game_state = type("State", (), {"vehicles": self.manager, "buildings": self.buildings})()
        surface = pygame.Surface((1500, 1000))
        font = pygame.font.Font(None, 20)
        panel.draw(surface, font, game_state)
        self.assertIn(
            VehicleType.FRUIT_HARVESTER, panel.garage_purchase_rects,
        )

    def test_sprite_is_cached_yellow_and_matches_combine_canvas(self):
        vehicle = FruitHarvester(1)
        sprite = vehicle._get_vehicle_sprite()
        self.assertEqual((24, 24), sprite.get_size())
        self.assertIs(sprite, vehicle._get_vehicle_sprite())
        yellow_pixels = sum(
            1 for x in range(sprite.get_width())
            for y in range(sprite.get_height())
            if sprite.get_at((x, y))[:3] == (222, 176, 43)
        )
        self.assertGreater(yellow_pixels, 10)

    def test_vehicle_record_restores_as_fruit_harvester(self):
        self.manager.purchase_fruit_harvester(
            self.world, self.buildings, self.economy, self.garage,
        )
        records = self.manager.save_records()
        restored = VehicleManager()
        restored.reset_for_loaded_game(
            self.world, [], self.buildings, records,
        )
        self.assertEqual(1, len(restored.vehicles))
        self.assertIsInstance(restored.vehicles[0], FruitHarvester)
        self.assertEqual(
            VehicleType.FRUIT_HARVESTER,
            restored.vehicles[0].vehicle_type,
        )
        self.assertIs(restored.vehicles[0].assigned_parking_building, self.garage)


if __name__ == "__main__":
    unittest.main()
