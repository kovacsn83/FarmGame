import tempfile
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import test_garage_fleet as fleet_tests
from buildings import place_building, remove_building, can_place_building, apply_garage_upgrades
from game_rules import can_build_more, BUILDING_LIMITS
from game_state import GameState
from time_system import GameTime
from ui import BuildingSelectionPanel
from screen_layout import set_screen_size
from save_system import save_game, load_game
import pygame


class GarageBuildingLimitTests(fleet_tests.GarageFleetTests):
    def test_zero_to_three_then_rejection_and_rebuild(self):
        for garage in list(self.garages):
            remove_building(self.world, self.buildings, garage)
        state = GameState(self.world, [], self.buildings, self.economy, GameTime(start_ticks=0), vehicles=self.manager)
        for count in range(3):
            self.assertTrue(can_build_more(self.buildings, "garage"))
            col = 2 + 10 * count
            self.assertTrue(can_place_building(self.world, self.buildings, 5, col, "garage"))
            self.assertIsNotNone(place_building(self.world, self.buildings, 5, col, "garage"))
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "limit.json"
                self.assertTrue(save_game(state, path))
                self.assertTrue(load_game(state, path))
        before = deepcopy((self.world, self.buildings, self.economy.money, self.economy.financial_history_save_record()))
        self.assertFalse(can_place_building(self.world, self.buildings, 5, 32, "garage"))
        self.assertIsNone(place_building(self.world, self.buildings, 5, 32, "garage"))
        self.assertEqual(before, (self.world, self.buildings, self.economy.money, self.economy.financial_history_save_record()))
        garage = self.buildings[0]
        self.assertTrue(self.manager.prepare_garage_demolition(self.world, self.buildings, garage))
        self.assertTrue(remove_building(self.world, self.buildings, garage))
        self.assertTrue(can_build_more(self.buildings, "garage"))
        self.assertIsNotNone(place_building(self.world, self.buildings, 5, 32, "garage"))
        self.assertEqual(BUILDING_LIMITS["processing_plant"], 2)
        self.assertTrue(can_build_more(self.buildings, "warehouse"))

    def test_card_shows_limit_and_does_not_select(self):
        pygame.display.init()
        pygame.font.init()
        set_screen_size(1000, 1000)
        state = GameState(self.world, [], self.buildings, self.economy, GameTime(start_ticks=0), vehicles=self.manager)
        panel = BuildingSelectionPanel()
        panel.open(state)
        panel.scroll_offset = 120
        with patch.object(panel, "draw_text", wraps=panel.draw_text) as text:
            panel.draw(pygame.Surface((1000,1000)), pygame.font.Font(None, 20), state)
        self.assertIn("Megépítve: 3 / 3", [call.args[2] for call in text.call_args_list])
        self.assertIn("Maximum elérve", [call.args[2] for call in text.call_args_list])
        position = panel.card_rects["garage"].center
        self.assertTrue(panel.content_rect.collidepoint(position))
        panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position))
        self.assertIsNone(panel.take_selection())
        self.assertTrue(panel.visible)
        self.assertEqual(panel.pending_limit_message, "Legfeljebb 3 Garázs építhető.")

    def test_capacity_levels_and_demolition_protection(self):
        for upgrades, expected in ((set(),12), ({"garage_level_2"},24), ({"garage_level_2","garage_level_3"},36)):
            apply_garage_upgrades(self.buildings, upgrades)
            self.assertEqual(self.manager.fleet_capacity(self.buildings)["capacity"], expected)
            self.assertFalse(can_build_more(self.buildings, "garage"))
        for _ in range(23):
            self.assertTrue(self.buy())
        self.assertTrue(self.manager.prepare_garage_demolition(self.world, self.buildings, self.garages[0]))
        for _ in range(4):
            self.assertTrue(self.buy())
        self.assertFalse(self.manager.prepare_garage_demolition(self.world, self.buildings, self.garages[0]))
