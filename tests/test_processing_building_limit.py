import os
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pygame
from buildings import place_building, remove_building, can_place_building
from constants import GRASS, ROAD
from economy import Economy
from game_rules import BUILDING_LIMITS, can_build_more
from game_state import GameState
from processing import PROCESSING_UPGRADE_ID, get_processing_lines
from save_system import save_game, load_game
from screen_layout import set_screen_size
from time_system import GameTime
from ui import BuildingSelectionPanel


class ProcessingBuildingLimitTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        pygame.display.init()
        set_screen_size(1000, 900)
        self.world = [[GRASS] * 50 for _ in range(40)]
        self.buildings = []
        self.state = GameState(self.world, [], self.buildings, Economy(), GameTime(start_ticks=0))

    def add(self, index):
        return place_building(self.world, self.buildings, 5, 2 + index * 10, "processing_plant")

    def test_limit_validates_preview_and_actual_build_without_mutation(self):
        self.world[4][22] = ROAD
        for count in range(BUILDING_LIMITS["processing_plant"]):
            self.assertTrue(can_build_more(self.buildings, "processing_plant"))
            self.assertTrue(can_place_building(self.world, self.buildings, 5, 22, "processing_plant"))
            self.assertIsNotNone(self.add(count))
        before = deepcopy((self.world, self.buildings, self.state.economy.money))
        self.assertFalse(can_place_building(self.world, self.buildings, 5, 22, "processing_plant"))
        self.assertIsNone(self.add(2))
        self.assertEqual(before, (self.world, self.buildings, self.state.economy.money))
        self.assertTrue(can_build_more(self.buildings, "garage"))
        self.assertTrue(can_build_more(self.buildings, "warehouse"))

    def test_ui_blocks_selection_and_demolition_immediately_reenables(self):
        self.add(0)
        plant = self.add(1)
        panel = BuildingSelectionPanel()
        panel.open(self.state)
        panel.scroll_offset = 10000
        panel._update_layout()
        pos = panel.card_rects["processing_plant"].center
        self.assertTrue(panel.content_rect.collidepoint(pos))
        self.assertTrue(panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)))
        self.assertIsNone(panel.take_selection())
        self.assertTrue(panel.visible)
        self.assertIn("2", panel.pending_limit_message)
        self.assertTrue(remove_building(self.world, self.buildings, plant))
        panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        self.assertEqual(panel.take_selection(), "processing_plant")
        self.assertIsNotNone(self.add(1))

    def test_menu_text_resolutions_and_wheel_never_select(self):
        self.add(0)
        self.add(1)
        for size in ((1000, 900), (640, 480), (400, 600)):
            set_screen_size(*size)
            panel = BuildingSelectionPanel()
            panel.open(self.state)
            screen = pygame.Surface(size)
            font = pygame.font.SysFont("Arial", 16, bold=True)
            with patch.object(panel, "draw_text", wraps=panel.draw_text) as draw:
                panel.draw(screen, font, self.state)
            texts = [call.args[2] for call in draw.call_args_list]
            self.assertIn("Megépítve: 2 / 2", texts)
            self.assertIn("Maximum elérve", texts)
            panel.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-100))
            self.assertGreater(panel.scroll_offset, 0)
            pos = panel.card_rects["processing_plant"].center
            for button in (2, 3, 4, 5):
                panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=pos))
                self.assertIsNone(panel.take_selection())

    def test_save_load_counts_and_global_upgrade(self):
        initial_value = self.state.economy.calculate_net_farm_value(self.state)
        for count in (0, 1, 2):
            if count:
                self.add(count - 1)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "limit.json"
                self.assertTrue(save_game(self.state, path))
                self.assertTrue(load_game(self.state, path))
            self.assertEqual(len(self.buildings), count)
            self.assertEqual(self.state.economy.calculate_net_farm_value(self.state),
                             initial_value + count * 3000)
            self.assertEqual(can_build_more(self.buildings, "processing_plant"), count < 2)
        self.state.purchased_upgrades.add(PROCESSING_UPGRADE_ID)
        self.state.synchronize_processing_upgrades()
        for plant in self.buildings:
            self.assertEqual(len(get_processing_lines(plant)), 2)
            self.assertEqual(plant["processing_capacity"], 400)


if __name__ == "__main__":
    unittest.main()
