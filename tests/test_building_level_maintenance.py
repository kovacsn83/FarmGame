import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from buildings import get_building_maintenance_base, place_building
from constants import GRASS
from economy import Economy
from game_state import GameState
from save_system import load_game, save_game
from time_system import GameTime


class BuildingLevelMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.state = GameState(
            [[GRASS] * 45 for _ in range(40)], [], [],
            Economy(), GameTime(start_ticks=0),
        )
        for index, kind in enumerate(("garage", "warehouse", "processing_plant")):
            place_building(self.state.world, self.state.buildings, 5, 2 + index * 12, kind)
        self.state.synchronize_processing_upgrades()

    def bases(self):
        return [get_building_maintenance_base(b) for b in self.state.buildings]

    def upgrade(self):
        self.state.purchased_upgrades.update((
            "garage_level_2", "warehouse_level_2", "processing_plant_level_2",
        ))
        self.state.synchronize_processing_upgrades()

    def test_levels_weekly_costs_and_new_buildings(self):
        self.assertEqual(self.bases(), [500, 500, 3000])
        self.upgrade()
        self.assertEqual(self.bases(), [3000, 2000, 6000])
        self.state.purchased_upgrades.add("garage_level_3")
        self.state.synchronize_processing_upgrades()
        self.assertEqual(self.bases(), [6000, 2000, 6000])
        economy = self.state.economy
        self.assertAlmostEqual(economy.calculate_weekly_costs(
            self.state.world, self.state.buildings), 14000 * 0.1 / 52)
        for index, kind in enumerate(("garage", "warehouse", "processing_plant")):
            place_building(self.state.world, self.state.buildings, 15, 2 + index * 12, kind)
        self.state.synchronize_processing_upgrades()
        self.assertEqual(self.bases(), [6000, 2000, 6000] * 2)
        self.assertAlmostEqual(economy.calculate_weekly_costs(
            self.state.world, self.state.buildings), 28000 * 0.1 / 52)
        before = economy.money
        expected = 28000 * 0.1 / 52
        self.assertAlmostEqual(economy.apply_weekly_costs(
            self.state.world, self.state.buildings), expected)
        self.assertAlmostEqual(economy.money, before - expected)
        self.assertAlmostEqual(economy.financial_history_save_record()[-1]["amount"], expected)

    def test_asset_valuation_is_independent(self):
        before = self.state.economy.get_farm_value_breakdown(self.state)["built_objects"]
        self.upgrade()
        self.assertEqual(self.state.economy.get_farm_value_breakdown(self.state)["built_objects"], before)

    def test_save_load_derives_levels_without_schema_change(self):
        for upgraded in (False, True):
            if upgraded:
                self.upgrade()
            expected = self.bases()
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "maintenance.json"
                self.assertTrue(save_game(self.state, path))
                serialized = json.loads(path.read_text(encoding="utf-8"))
                self.assertNotIn("_warehouse_level", json.dumps(serialized))
                self.assertNotIn("_processing_plant_level", json.dumps(serialized))
                self.assertTrue(load_game(self.state, path))
            self.assertEqual(self.bases(), expected)

    def test_farmhouse_and_other_buildings_unchanged(self):
        for level, expected in ((1, 1000), (2, 5000), (3, 15000)):
            self.assertEqual(get_building_maintenance_base({
                "type": "farmhouse", "farmhouse_level": level}), expected)
        for kind, expected in (("market", 500), ("animal_pen", 400), ("pond", 500), ("orchard", 200)):
            self.assertEqual(get_building_maintenance_base({"type": kind}), expected)
