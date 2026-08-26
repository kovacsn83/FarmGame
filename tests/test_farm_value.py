import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bank import BankSystem
from buildings import place_building, remove_building
from constants import GRASS, ROAD
from economy import Economy
from game_state import GameState
from save_system import load_game, save_game
from screen_layout import set_screen_size
from time_system import GameTime
from ui import FinancialSummaryPanel
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


class FarmValueTests(unittest.TestCase):
    def setUp(self):
        self.world = [[GRASS for _ in range(50)] for _ in range(40)]
        self.world[0][0] = ROAD
        self.fields = [{"field_type": "field_4x4"}]
        self.buildings = []
        self.farmhouse = place_building(
            self.world, self.buildings, 2, 2, "farmhouse",
        )
        self.farmhouse["farmhouse_level"] = 3
        self.warehouse = place_building(
            self.world, self.buildings, 15, 2, "warehouse",
        )
        self.orchard = place_building(
            self.world, self.buildings, 15, 12, "orchard",
        )
        self.processing_plant = place_building(
            self.world, self.buildings, 24, 2, "processing_plant",
        )
        self.garage = place_building(
            self.world, self.buildings, 24, 12, "garage",
        )
        self.warehouse["inventory"]["wheat"] = 2
        self.warehouse["inventory"]["apple"] = 3
        self.processing_plant["processing_inventory"].update({
            "canned_tomato": 2,
            "tomato": 1,
            "unknown_internal_item": 99,
        })
        self.orchard["trees"] = [
            {"type": "apple"},
            {"type": "cherry"},
        ]
        self.animals = [{"type": "cattle"}, {"type": "pig"}]
        self.economy = Economy(1000)
        self.vehicles = VehicleManager()
        self.vehicles._create_managed_asset(
            VehicleType.TRACTOR, self.garage, 0,
        )
        self.vehicles._create_managed_asset(
            VehicleType.TRAILER, self.garage, 1,
        )
        self.bank = BankSystem(self.economy)
        self.bank.loan.active_loan = True
        self.bank.loan.remaining_balance_cents = 1_160_000
        self.state = GameState(
            self.world, self.fields, self.buildings, self.economy,
            GameTime(start_ticks=0),
            purchased_upgrades={
                "farmhouse_level_2", "farmhouse_level_3",
                "unlock_field_6x6", "automated_animal_feeding",
            },
            tractor=self.vehicles, vehicles=self.vehicles,
            animals=self.animals, bank_system=self.bank,
        )

    def test_all_current_assets_use_central_catalog_prices(self):
        breakdown = self.economy.get_farm_value_breakdown(self.state)
        self.assertEqual(19270, breakdown["built_objects"])
        self.assertEqual(22000, breakdown["upgrades"])
        self.assertEqual(350, breakdown["animals"])
        self.assertEqual(350, breakdown["fruit_trees"])
        self.assertEqual(50, breakdown["warehouse_inventory"])
        self.assertEqual(80, breakdown["processing_inventory"])
        self.assertEqual(800, breakdown["vehicles"])
        self.assertEqual(1000, breakdown["money"])
        self.assertEqual(11600, breakdown["loan_balance"])
        self.assertEqual(32300, breakdown["total"])
        self.assertEqual(
            breakdown["total"],
            self.economy.calculate_net_farm_value(self.state),
        )

    def test_demolition_slaughter_and_inventory_changes_are_immediate(self):
        initial = self.economy.calculate_net_farm_value(self.state)
        remove_building(self.world, self.buildings, self.processing_plant)
        without_plant = self.economy.calculate_net_farm_value(self.state)
        self.assertEqual(3080, initial - without_plant)

        self.animals.pop()
        without_pig = self.economy.calculate_net_farm_value(self.state)
        self.assertEqual(150, without_plant - without_pig)

        self.world[0][0] = GRASS
        without_road = self.economy.calculate_net_farm_value(self.state)
        self.assertEqual(20, without_pig - without_road)

    def test_loan_principal_and_remaining_interest_are_not_double_counted(self):
        self.bank.loan.active_loan = False
        self.bank.loan.remaining_balance_cents = 0
        before = self.economy.calculate_net_farm_value(self.state)
        self.assertTrue(self.bank.take_loan(1))
        after = self.economy.calculate_net_farm_value(self.state)
        self.assertEqual(-1600, after - before)

        before_payment = after
        self.bank.apply_weekly_repayment()
        self.assertEqual(
            before_payment,
            self.economy.calculate_net_farm_value(self.state),
        )

        self.bank.loan.remaining_balance_cents = 14_500
        self.bank.loan.remaining_weeks = 1
        before_final_payment = self.economy.calculate_net_farm_value(self.state)
        self.bank.apply_weekly_repayment()
        self.assertFalse(self.bank.active_loan)
        self.assertEqual(0, self.bank.loan.remaining_balance_cents)
        self.assertEqual(
            before_final_payment,
            self.economy.calculate_net_farm_value(self.state),
        )

    def test_negative_money_reduces_the_value(self):
        before = self.economy.calculate_net_farm_value(self.state)
        self.economy.money = -500
        after = self.economy.calculate_net_farm_value(self.state)
        self.assertEqual(-1500, after - before)

    def test_value_is_recalculated_after_save_load(self):
        self.fields.clear()
        self.animals.clear()
        self.orchard["trees"].clear()
        self.processing_plant["processing_inventory"].pop(
            "unknown_internal_item"
        )
        self.bank.loan.active_loan = False
        self.bank.loan.active_loan_tier = 0
        self.bank.loan.remaining_balance_cents = 0
        self.bank.loan.remaining_weeks = 0
        expected = self.economy.calculate_net_farm_value(self.state)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "farm-value.json"
            self.assertTrue(save_game(self.state, path))
            self.economy.money = -99999
            self.warehouse["inventory"]["apple"] = 0
            self.assertTrue(load_game(self.state, path))
        self.assertEqual(
            expected, self.economy.calculate_net_farm_value(self.state),
        )


class FarmValuePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.font = pygame.font.SysFont(None, 24)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_value_is_centered_between_header_and_columns(self):
        screen = pygame.display.set_mode((1200, 800))
        set_screen_size(1200, 800)
        world = [[GRASS for _ in range(10)] for _ in range(10)]
        economy = Economy(12345)
        state = GameState(
            world, [], [], economy, GameTime(start_ticks=0),
            vehicles=VehicleManager(), bank_system=BankSystem(economy),
        )
        panel = FinancialSummaryPanel()
        panel.open()
        panel.draw(screen, self.font, economy, state)

        self.assertEqual(12345, panel.last_farm_value)
        self.assertEqual(panel.rect.centerx, panel.farm_value_rect.centerx)
        self.assertLess(
            panel.farm_value_rect.bottom,
            panel._layout_rects()["income_heading"].top,
        )
        self.assertLess(panel.farm_value_rect.right, panel.bank_button_rect.left)


if __name__ == "__main__":
    unittest.main()
