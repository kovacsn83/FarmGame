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
        expected_dependencies = {
            "unlock_field_8x8": "unlock_field_6x6",
            "garage_level_3": "garage_level_2",
            "warehouse_level_3": "warehouse_level_2",
        }
        for upgrade_id, upgrade in UPGRADES.items():
            self.assertIn("tree_column", upgrade)
            self.assertIn("tree_order", upgrade)
            if upgrade.get("target_level") is None:
                self.assertEqual(
                    upgrade["required_farmhouse_level"],
                    upgrade["tree_column"],
                    upgrade_id,
                )
                self.assertEqual(
                    upgrade.get("requires"),
                    expected_dependencies.get(upgrade_id),
                    upgrade_id,
                )

    def test_farmhouse_one_upgrades_are_independent(self):
        state, economy = self.make_state()
        starting_money = economy.money
        upgrade_ids = (
            "automated_animal_feeding", "automated_animal_watering",
            "automated_field_watering", "unlock_field_6x6",
        )
        for upgrade_id in upgrade_ids:
            self.assertEqual(
                get_upgrade_status(upgrade_id, state.purchased_upgrades, 1),
                "Fejleszthető",
            )
            self.assertTrue(economy.purchase_upgrade(state, upgrade_id))
        self.assertEqual(
            economy.money,
            starting_money - sum(UPGRADES[item]["price"] for item in upgrade_ids),
        )

    def test_farmhouse_two_upgrades_and_field_size_dependency(self):
        state, economy = self.make_state()
        self.assertFalse(economy.purchase_upgrade(state, "unlock_field_8x8"))
        self.assertTrue(economy.purchase_upgrade(state, "farmhouse_level_2"))
        for upgrade_id in (
                "automated_field_spraying", "garage_level_2",
                "warehouse_level_2", "automated_field_fertilizing"):
            self.assertEqual(
                get_upgrade_status(
                    upgrade_id, state.purchased_upgrades, farmhouse_level=2,
                ),
                "Fejleszthető",
            )
            self.assertTrue(economy.purchase_upgrade(state, upgrade_id))
        self.assertTrue(get_upgrade_status(
            "unlock_field_8x8", state.purchased_upgrades, 2,
        ).startswith("Zárolt: előbb 6x6-os veteményes"))
        self.assertFalse(economy.purchase_upgrade(state, "unlock_field_8x8"))
        self.assertTrue(economy.purchase_upgrade(state, "unlock_field_6x6"))
        self.assertTrue(economy.purchase_upgrade(state, "unlock_field_8x8"))

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

    def test_farmhouse_three_keeps_only_matching_level_dependencies(self):
        upgrade_ids = (
            "warehouse_level_3", "garage_level_3",
            "processing_plant_level_2", "automated_field_harvesting",
        )
        state, economy = self.make_state(2)
        for upgrade_id in upgrade_ids:
            self.assertTrue(get_upgrade_status(
                upgrade_id, set(), farmhouse_level=2,
            ).startswith("Zárolt: Farmház III."))
            self.assertFalse(economy.purchase_upgrade(state, upgrade_id))
        state.buildings[0]["farmhouse_level"] = 3
        for upgrade_id in ("processing_plant_level_2", "automated_field_harvesting"):
            self.assertEqual(
                get_upgrade_status(upgrade_id, state.purchased_upgrades, 3),
                "Fejleszthető",
            )
            self.assertTrue(economy.purchase_upgrade(state, upgrade_id))
        for child_id, parent_id in (
                ("garage_level_3", "garage_level_2"),
                ("warehouse_level_3", "warehouse_level_2")):
            self.assertTrue(get_upgrade_status(
                child_id, state.purchased_upgrades, 3,
            ).startswith(f"Zárolt: előbb {UPGRADES[parent_id]['name']}"))
            self.assertFalse(economy.purchase_upgrade(state, child_id))
            self.assertTrue(economy.purchase_upgrade(state, parent_id))
            self.assertTrue(economy.purchase_upgrade(state, child_id))

    def test_processing_upgrade_requires_level_but_not_harvesting(self):
        upgrade_id = "processing_plant_level_2"
        for level, purchased in ((1, ()), (2, ("automated_field_harvesting",))):
            with self.subTest(level=level, purchased=purchased):
                state, economy = self.make_state(level, purchased)
                self.assertTrue(get_upgrade_status(upgrade_id, purchased, level).startswith("Zárolt"))
                self.assertFalse(economy.purchase_upgrade(state, upgrade_id))
                self.assertEqual(economy.money, 200000)
        state, economy = self.make_state(3)
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
