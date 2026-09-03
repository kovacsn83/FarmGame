import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from economy import Economy
from financial_history import EXPENSE_UPGRADE
from processing import initialize_processing_plant, start_processing_batch
from game_rules import UPGRADES, get_upgrade_status, get_upgrade_tree_columns
from game_state import GameState
from save_system import load_game, save_game
from time_system import GameTime


class UpgradeDependencyTests(unittest.TestCase):
    def make_state(self, level=1, purchased=()):
        economy = Economy(200000)
        state = GameState(
            [[0]], [], [{"type": "farmhouse", "farmhouse_level": level}],
            economy, GameTime(start_ticks=0),
            purchased_upgrades=set(purchased),
        )
        return state, economy

    def test_tree_metadata_is_complete_and_extensible(self):
        self.assertEqual(len(get_upgrade_tree_columns()), 3)
        for upgrade in UPGRADES.values():
            self.assertIn("tree_column", upgrade)
            self.assertIn("tree_order", upgrade)

    def test_farmhouse_one_branch_must_be_bought_in_order(self):
        state, economy = self.make_state()
        starting_money = economy.money
        self.assertFalse(economy.purchase_upgrade(
            state, "automated_animal_watering",
        ))
        self.assertEqual(starting_money, economy.money)
        self.assertTrue(economy.purchase_upgrade(state, "unlock_field_6x6"))
        self.assertEqual(
            starting_money - UPGRADES["unlock_field_6x6"]["price"],
            economy.money,
        )
        self.assertTrue(economy.purchase_upgrade(
            state, "automated_animal_watering",
        ))
        self.assertTrue(economy.purchase_upgrade(
            state, "automated_animal_feeding",
        ))

    def test_farmhouse_two_branch_requires_level_and_predecessors(self):
        state, economy = self.make_state()
        self.assertFalse(economy.purchase_upgrade(state, "unlock_field_8x8"))
        self.assertTrue(economy.purchase_upgrade(state, "farmhouse_level_2"))
        for upgrade_id in (
                "unlock_field_8x8",
                "automated_field_watering",
                "automated_field_fertilizing",
                "automated_field_spraying"):
            self.assertTrue(economy.purchase_upgrade(state, upgrade_id))

    def test_farmhouse_three_requires_level_two(self):
        state, economy = self.make_state()
        self.assertFalse(economy.purchase_upgrade(state, "farmhouse_level_3"))
        self.assertTrue(economy.purchase_upgrade(state, "farmhouse_level_2"))
        self.assertTrue(economy.purchase_upgrade(state, "farmhouse_level_3"))

    def test_automatic_harvesting_requires_farmhouse_three(self):
        state, economy = self.make_state(level=2)
        self.assertFalse(economy.purchase_upgrade(
            state, "automated_field_harvesting",
        ))
        state.buildings[0]["farmhouse_level"] = 3
        before = economy.money
        self.assertTrue(economy.purchase_upgrade(
            state, "automated_field_harvesting",
        ))
        self.assertEqual(economy.money, before - 30000)
        self.assertFalse(economy.purchase_upgrade(
            state, "automated_field_harvesting",
        ))

    def test_legacy_purchased_child_remains_completed_without_parent(self):
        purchased = {"automated_field_spraying"}
        self.assertEqual(
            "Kifejlesztve",
            get_upgrade_status(
                "automated_field_spraying", purchased, farmhouse_level=1,
            ),
        )
        state, _economy = self.make_state(purchased=purchased)
        state.buildings.clear()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-upgrade-tree.json"
            self.assertTrue(save_game(state, path))
            state.purchased_upgrades.clear()
            self.assertTrue(load_game(state, path))
        self.assertIn("automated_field_spraying", state.purchased_upgrades)

    def test_processing_upgrade_requires_level_and_harvesting(self):
        upgrade_id = "processing_plant_level_2"
        for level, purchased in ((1, ()), (2, ("automated_field_harvesting",)), (3, ())):
            with self.subTest(level=level, purchased=purchased):
                state, economy = self.make_state(level, purchased)
                self.assertTrue(get_upgrade_status(upgrade_id, purchased, level).startswith("Zárolt"))
                self.assertFalse(economy.purchase_upgrade(state, upgrade_id))
                self.assertEqual(economy.money, 200000)
        state, economy = self.make_state(3, ("automated_field_harvesting",))
        self.assertEqual(get_upgrade_status(upgrade_id, state.purchased_upgrades, 3), "Fejleszthető")
        economy.money = 5999
        self.assertFalse(economy.purchase_upgrade(state, upgrade_id))
        economy.money = 6000
        before = economy.get_farm_value_breakdown(state)["upgrades"]
        self.assertTrue(economy.purchase_upgrade(state, upgrade_id))
        self.assertEqual(economy.money, 0)
        self.assertEqual(economy.get_farm_value_breakdown(state)["upgrades"], before + 6000)
        entry = economy.financial_history[-1]
        self.assertEqual((entry["category"], entry["subcategory"], entry["amount"]), (EXPENSE_UPGRADE, upgrade_id, 6000))
        self.assertEqual(get_upgrade_status(upgrade_id, state.purchased_upgrades, 3), "Kifejlesztve")
        self.assertFalse(economy.purchase_upgrade(state, upgrade_id))

    def test_processing_upgrade_roundtrip_and_legacy_default(self):
        upgrade_id = "processing_plant_level_2"
        state, economy = self.make_state(3, ("automated_field_harvesting",))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "upgrade.json"
            farmhouse = state.buildings.pop()
            self.assertTrue(save_game(state, path))
            state.purchased_upgrades.add(upgrade_id)
            self.assertTrue(load_game(state, path))
            self.assertNotIn(upgrade_id, state.purchased_upgrades)
            state.buildings.append(farmhouse)
            self.assertTrue(economy.purchase_upgrade(state, upgrade_id))
            state.buildings.clear()
            self.assertTrue(save_game(state, path))
            state.purchased_upgrades.clear()
            self.assertTrue(load_game(state, path))
            self.assertIn(upgrade_id, state.purchased_upgrades)

    def test_processing_upgrade_expands_storage_but_keeps_single_line_limit(self):
        state, economy = self.make_state(3, ("automated_field_harvesting",))
        plant = initialize_processing_plant({"type": "processing_plant"})
        state.buildings.append(plant)
        self.assertTrue(economy.purchase_upgrade(state, "processing_plant_level_2"))
        plant["processing_inventory"]["tomato"] = 20
        self.assertEqual(start_processing_batch(plant, 1), 5)
        self.assertEqual(plant["processing_capacity"], 400)


if __name__ == "__main__":
    unittest.main()
