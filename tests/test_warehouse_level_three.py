import os
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from buildings import (
    get_warehouse_capacity, get_total_capacity, get_total_inventory,
    get_building_maintenance_base, place_building, remove_building, store_item,
)
from constants import GRASS
from economy import Economy
from financial_history import EXPENSE_UPGRADE
from game_rules import BUILDING_LIMITS, UPGRADES
from game_state import GameState
from save_system import save_game, load_game
from time_system import GameTime


class WarehouseLevelThreeTests(unittest.TestCase):
    def setUp(self):
        self.state = GameState([[GRASS] * 45 for _ in range(40)], [], [],
                               Economy(20000), GameTime(start_ticks=0))
        self.house = place_building(self.state.world, self.state.buildings, 15, 2, "farmhouse")
        self.warehouses = [place_building(self.state.world, self.state.buildings,
                                        5, 2 + i * 10, "warehouse") for i in range(2)]

    def upgrade(self):
        self.house["farmhouse_level"] = 3
        self.state.purchased_upgrades.add("warehouse_level_2")
        self.state.synchronize_processing_upgrades()
        self.assertTrue(self.state.economy.purchase_upgrade(self.state, "warehouse_level_3"))

    def test_prerequisites_cost_and_financial_value(self):
        economy = self.state.economy
        for house_level, level_two in ((1, False), (2, True), (3, False)):
            self.house["farmhouse_level"] = house_level
            self.state.purchased_upgrades = {"warehouse_level_2"} if level_two else set()
            self.assertFalse(economy.purchase_upgrade(self.state, "warehouse_level_3"))
            self.assertEqual(economy.money, 20000)
        self.house["farmhouse_level"] = 3
        self.state.purchased_upgrades.add("warehouse_level_2")
        self.state.synchronize_processing_upgrades()
        value_before = economy.calculate_net_farm_value(self.state)
        upgrades_before = economy.get_farm_value_breakdown(self.state)["upgrades"]
        economy.money = 4999
        self.assertFalse(economy.purchase_upgrade(self.state, "warehouse_level_3"))
        economy.money = 20000
        self.upgrade()
        self.assertEqual(economy.money, 15000)
        self.assertEqual(economy.calculate_net_farm_value(self.state), value_before)
        self.assertEqual(economy.get_farm_value_breakdown(self.state)["upgrades"], upgrades_before + 5000)
        entry = economy.financial_history_save_record()[-1]
        self.assertEqual((entry["category"], entry["amount"]), (EXPENSE_UPGRADE, 5000))
        self.assertFalse(economy.purchase_upgrade(self.state, "warehouse_level_3"))
        self.assertEqual(economy.money, 15000)
        self.assertEqual(UPGRADES["warehouse_level_3"]["requires"], "warehouse_level_2")

    def test_capacity_inventory_new_building_limit_and_maintenance(self):
        self.assertEqual(get_warehouse_capacity(), 500)
        self.assertEqual(get_warehouse_capacity({"warehouse_level_2"}), 1000)
        self.assertEqual(get_warehouse_capacity({"warehouse_level_2", "warehouse_level_3"}), 1500)
        store_item(self.state.buildings, "wheat", 900)
        inventory = deepcopy(get_total_inventory(self.state.buildings))
        self.upgrade()
        self.assertEqual(get_total_capacity(self.state.buildings), 3000)
        self.assertEqual(get_total_inventory(self.state.buildings), inventory)
        for warehouse in self.warehouses:
            self.assertEqual(warehouse["capacity"], 1500)
            self.assertEqual(get_building_maintenance_base(warehouse), 5000)
        self.assertEqual(BUILDING_LIMITS["warehouse"], 2)
        self.assertIsNone(place_building(self.state.world, self.state.buildings, 5, 22, "warehouse"))
        self.assertTrue(remove_building(self.state.world, self.state.buildings, self.warehouses[0]))
        new = place_building(self.state.world, self.state.buildings, 5, 22, "warehouse")
        self.state.synchronize_processing_upgrades()
        self.assertEqual(new["capacity"], 1500)
        self.assertEqual(get_total_inventory(self.state.buildings), inventory)
        self.assertEqual(get_total_capacity(self.state.buildings), 3000)

    def test_demolition_full_storage_and_save_load(self):
        plant = place_building(self.state.world, self.state.buildings, 25, 20, "processing_plant")
        self.upgrade()
        self.assertEqual(plant["processing_capacity"], 200)
        self.assertTrue(store_item(self.state.buildings, "wheat", 2500))
        before = deepcopy((self.state.world, self.state.buildings))
        self.assertFalse(remove_building(self.state.world, self.state.buildings, self.warehouses[0]))
        self.assertEqual((self.state.world, self.state.buildings), before)
        self.assertFalse(store_item(self.state.buildings, "wheat", 501))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "warehouse_three.json"
            self.assertTrue(save_game(self.state, path))
            self.assertTrue(load_game(self.state, path))
        self.assertEqual(get_total_capacity(self.state.buildings), 3000)
        self.assertEqual(get_total_inventory(self.state.buildings)["wheat"], 2500)
        self.assertIn("warehouse_level_3", self.state.purchased_upgrades)
