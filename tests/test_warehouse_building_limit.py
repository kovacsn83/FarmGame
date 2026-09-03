import tempfile
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import test_warehouse_upgrade as upgrade_tests
from buildings import place_building, remove_building, can_place_building, get_total_capacity
from game_rules import can_build_more, BUILDING_LIMITS
from save_system import save_game, load_game
from screen_layout import set_screen_size
from ui import BuildingSelectionPanel
import pygame


class WarehouseBuildingLimitTests(upgrade_tests.WarehouseUpgradeTests):
    def test_build_guard_no_mutation_and_demolition_reopens_card(self):
        for warehouse in self.warehouses:
            self.assertTrue(remove_building(self.world,self.buildings,warehouse))
        from constants import ROAD
        self.world[4] = [ROAD] * len(self.world[4])
        for count in (0,1,2):
            self.assertEqual(can_build_more(self.buildings,"warehouse"),count<2)
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/"count.json"
                self.assertTrue(save_game(self.state,path))
                self.assertTrue(load_game(self.state,path))
            if count<2:
                self.assertTrue(can_place_building(self.world,self.buildings,5,2+10*count,"warehouse"))
                self.assertIsNotNone(place_building(self.world,self.buildings,5,2+10*count,"warehouse"))
        before=deepcopy((self.world,self.buildings,self.economy.money,self.economy.financial_history_save_record()))
        self.assertFalse(can_place_building(self.world,self.buildings,5,22,"warehouse"))
        self.assertIsNone(place_building(self.world,self.buildings,5,22,"warehouse"))
        self.assertEqual(before,(self.world,self.buildings,self.economy.money,self.economy.financial_history_save_record()))
        warehouse=next(b for b in self.buildings if b["type"]=="warehouse")
        self.assertTrue(remove_building(self.world,self.buildings,warehouse))
        self.assertTrue(can_build_more(self.buildings,"warehouse"))
        self.assertIsNotNone(place_building(self.world,self.buildings,5,22,"warehouse"))
        self.assertEqual(get_total_capacity(self.buildings),1000)
        self.assertEqual(BUILDING_LIMITS["garage"],3)
        self.assertEqual(BUILDING_LIMITS["processing_plant"],2)

    def test_menu_count_and_disabled_selection(self):
        pygame.display.init()
        pygame.font.init()
        set_screen_size(1000,1000)
        panel=BuildingSelectionPanel()
        panel.open(self.state)
        with patch.object(panel,"draw_text",wraps=panel.draw_text) as draw:
            panel.draw(pygame.Surface((1000,1000)),pygame.font.Font(None,20),self.state)
        self.assertIn("Megépítve: 2 / 2",[c.args[2] for c in draw.call_args_list])
        self.assertIn("Maximum elérve",[c.args[2] for c in draw.call_args_list])
        pos=panel.card_rects["warehouse"].center
        self.assertTrue(panel.content_rect.collidepoint(pos))
        self.assertTrue(panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos)))
        self.assertIsNone(panel.take_selection())
        self.assertTrue(panel.visible)
        self.assertEqual(panel.pending_limit_message,"Legfeljebb 2 Raktár építhető.")
