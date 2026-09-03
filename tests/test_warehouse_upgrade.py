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
from buildings import place_building, remove_building, get_total_capacity, get_total_inventory, get_free_capacity, store_item
from constants import GRASS
from economy import Economy
from game_state import GameState
from game_rules import get_upgrade_status
from time_system import GameTime
from save_system import save_game, load_game
from financial_history import EXPENSE_UPGRADE
from processing import apply_processing_upgrades
from ui import draw_economy_hud


class WarehouseUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.world = [[GRASS]*45 for _ in range(40)]
        self.buildings = []
        self.warehouses = [place_building(self.world,self.buildings,5,2+10*i,"warehouse") for i in range(2)]
        self.house = place_building(self.world,self.buildings,15,2,"farmhouse")
        self.economy = Economy()
        self.economy.money = 10000
        self.state = GameState(self.world,[],self.buildings,self.economy,GameTime(start_ticks=0))

    def upgrade(self):
        self.house["farmhouse_level"] = 2
        self.assertTrue(self.economy.purchase_upgrade(self.state,"warehouse_level_2"))

    def test_cost_prerequisite_inventory_value_and_new_warehouse(self):
        self.assertTrue(get_upgrade_status("warehouse_level_2",set(),1).startswith("Zárolt"))
        self.assertFalse(self.economy.purchase_upgrade(self.state,"warehouse_level_2"))
        store_item(self.buildings,"wheat",900)
        before = deepcopy([w["inventory"] for w in self.warehouses])
        self.house["farmhouse_level"] = 2
        value = self.economy.calculate_net_farm_value(self.state)
        self.assertEqual(get_total_capacity(self.buildings),1000)
        self.upgrade()
        self.assertEqual(self.economy.money,8000)
        self.assertEqual(self.economy.calculate_net_farm_value(self.state),value)
        self.assertEqual([w["inventory"] for w in self.warehouses],before)
        self.assertEqual(get_total_capacity(self.buildings),2000)
        record = self.economy.financial_history_save_record()[-1]
        self.assertEqual((record["category"],record["amount"]), (EXPENSE_UPGRADE,2000))
        self.assertFalse(self.economy.purchase_upgrade(self.state,"warehouse_level_2"))
        self.assertTrue(remove_building(self.world,self.buildings,self.warehouses[-1]))
        new = place_building(self.world,self.buildings,25,2,"warehouse")
        self.state.synchronize_processing_upgrades()
        self.assertEqual(new["capacity"],1000)
        self.assertEqual(get_total_capacity(self.buildings),2000)

    def test_full_capacity_rejects_whole_delivery(self):
        self.upgrade()
        self.assertTrue(store_item(self.buildings,"wheat",1995))
        before = deepcopy(get_total_inventory(self.buildings))
        self.assertEqual(get_free_capacity(self.buildings),5)
        self.assertFalse(store_item(self.buildings,"wheat",10))
        self.assertEqual(get_total_inventory(self.buildings),before)

    def test_demolition_capacity_guard_and_safe_transfer(self):
        self.upgrade()
        store_item(self.buildings,"wheat",1600)
        before = deepcopy((self.world,self.buildings))
        self.assertFalse(remove_building(self.world,self.buildings,self.warehouses[0]))
        self.assertEqual((self.world,self.buildings),before)
        self.warehouses[0]["inventory"]["wheat"] = 300
        inventory = deepcopy(get_total_inventory(self.buildings))
        self.assertTrue(remove_building(self.world,self.buildings,self.warehouses[0]))
        self.assertEqual(get_total_capacity(self.buildings),1000)
        self.assertEqual(get_total_inventory(self.buildings),inventory)

    def test_save_load_with_over_500_stock_and_legacy(self):
        for upgraded in (False,True):
            if upgraded:
                self.upgrade()
            store_item(self.buildings,"wheat",400)
            if upgraded:
                store_item(self.buildings,"wheat",1000)
            expected = deepcopy(get_total_inventory(self.buildings))
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/"warehouse.json"
                self.assertTrue(save_game(self.state,path))
                self.assertTrue(load_game(self.state,path))
            self.house=next(b for b in self.buildings if b["type"]=="farmhouse")
            self.assertEqual(get_total_inventory(self.buildings),expected)
            self.assertEqual(get_total_capacity(self.buildings),2000 if upgraded else 1000)

    def test_processing_storage_unchanged_and_hud(self):
        plant=place_building(self.world,self.buildings,25,20,"processing_plant")
        self.state.purchased_upgrades.add("processing_plant_level_2")
        self.state.synchronize_processing_upgrades()
        self.upgrade()
        self.assertEqual(plant["processing_capacity"],400)
        pygame.font.init()
        pygame.display.init()
        screen=pygame.Surface((1000,900))
        font=pygame.font.Font(None,20)
        with patch("ui.get_total_capacity", wraps=get_total_capacity) as capacity:
            draw_economy_hud(screen,font,self.buildings,self.economy)
            capacity.assert_called()
