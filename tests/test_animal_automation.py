import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from animal_automation import (
    AUTOMATED_FEEDING_UPGRADE, AUTOMATED_WATERING_UPGRADE,
    get_automation_threshold, run_weekly_animal_supply_automation,
)
from animal_troughs import FOOD_STOCK_KEY, WATER_STOCK_KEY
from economy import Economy
from game_logger import get_logger
from game_rules import UPGRADES
from game_state import GameState
from save_system import load_game, save_game
from time_system import GameTime


class RecordingVehicleManager:
    def __init__(self):
        self.calls = []
        self.pending = set()

    def start_trough_supply(
            self, world, buildings, economy, animals, trough,
            current_ticks=None):
        anchor = min(
            trough["group"], key=lambda pen: (pen["row"], pen["col"]),
        )
        key = (trough["type"], anchor["row"], anchor["col"])
        if key in self.pending:
            return False
        self.pending.add(key)
        self.calls.append((trough["type"], anchor["row"], anchor["col"]))
        return True


class AnimalAutomationTests(unittest.TestCase):
    def setUp(self):
        self.world = [[0] * 20 for _ in range(20)]
        self.pen = {
            "type": "animal_pen", "row": 2, "col": 2,
            "width": 4, "height": 4,
        }
        self.buildings = [self.pen]
        self.animals = [
            {"type": "cattle", "pen_row": 2, "pen_col": 2,
             "row": 2, "col": 2},
            {"type": "cattle", "pen_row": 2, "pen_col": 2,
             "row": 2, "col": 3},
        ]
        self.economy = Economy()
        self.vehicles = RecordingVehicleManager()
        get_logger().reset()

    def run_automation(self, upgrades):
        return run_weekly_animal_supply_automation(
            self.world, self.buildings, self.economy, self.animals,
            self.vehicles, set(upgrades), current_ticks=100,
        )

    def test_upgrade_catalog_contains_both_twenty_thousand_dollar_upgrades(self):
        self.assertEqual(UPGRADES[AUTOMATED_FEEDING_UPGRADE]["price"], 20000)
        self.assertEqual(UPGRADES[AUTOMATED_WATERING_UPGRADE]["price"], 20000)

    def test_threshold_is_two_weeks_and_scales_with_animal_count(self):
        self.assertEqual(get_automation_threshold(1), 2)
        self.assertEqual(get_automation_threshold(4), 8)
        self.assertEqual(get_automation_threshold(24), 48)

    def test_next_check_uses_changed_animal_count(self):
        self.pen[FOOD_STOCK_KEY] = 5
        self.assertEqual(self.run_automation([AUTOMATED_FEEDING_UPGRADE]), 0)
        self.animals.append({
            "type": "cattle", "pen_row": 2, "pen_col": 2,
            "row": 3, "col": 2,
        })
        self.assertEqual(self.run_automation([AUTOMATED_FEEDING_UPGRADE]), 1)

    def test_feed_starts_at_or_below_threshold_but_not_above_it(self):
        self.pen[FOOD_STOCK_KEY] = 4
        self.assertEqual(self.run_automation([AUTOMATED_FEEDING_UPGRADE]), 1)
        self.assertEqual(self.vehicles.calls[0][0], "food")

        self.vehicles = RecordingVehicleManager()
        self.pen[FOOD_STOCK_KEY] = 5
        self.assertEqual(self.run_automation([AUTOMATED_FEEDING_UPGRADE]), 0)

    def test_water_starts_independently_from_feed(self):
        self.pen[FOOD_STOCK_KEY] = 8
        self.pen[WATER_STOCK_KEY] = 4
        created = self.run_automation([
            AUTOMATED_FEEDING_UPGRADE, AUTOMATED_WATERING_UPGRADE,
        ])
        self.assertEqual(created, 1)
        self.assertEqual(self.vehicles.calls, [("water", 2, 2)])

    def test_no_upgrade_and_empty_pen_create_no_tasks(self):
        self.assertEqual(self.run_automation([]), 0)
        self.animals.clear()
        self.assertEqual(self.run_automation([AUTOMATED_FEEDING_UPGRADE]), 0)

    def test_duplicate_weekly_check_does_not_duplicate_pending_task(self):
        self.assertEqual(self.run_automation([AUTOMATED_FEEDING_UPGRADE]), 1)
        self.assertEqual(self.run_automation([AUTOMATED_FEEDING_UPGRADE]), 0)
        self.assertEqual(len(self.vehicles.calls), 1)

    def test_multiple_pens_are_evaluated_independently(self):
        second_pen = {
            "type": "animal_pen", "row": 10, "col": 10,
            "width": 4, "height": 4,
        }
        self.buildings.append(second_pen)
        self.animals.append({
            "type": "pig", "pen_row": 10, "pen_col": 10,
            "row": 10, "col": 10,
        })
        self.pen[FOOD_STOCK_KEY] = 5
        second_pen[FOOD_STOCK_KEY] = 2
        self.assertEqual(self.run_automation([AUTOMATED_FEEDING_UPGRADE]), 1)
        self.assertEqual(self.vehicles.calls, [("food", 10, 10)])

    def test_successful_creation_uses_automation_log_category(self):
        self.run_automation([AUTOMATED_FEEDING_UPGRADE])
        entry = get_logger().entries[-1]
        self.assertEqual(entry.category, "Automation")
        self.assertIn("Automatikus etetés", entry.message)

    def test_upgrades_round_trip_through_existing_save_format(self):
        state = GameState(
            [[0]], [], [], self.economy, GameTime(start_ticks=0),
            purchased_upgrades={
                AUTOMATED_FEEDING_UPGRADE, AUTOMATED_WATERING_UPGRADE,
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "automation.json"
            self.assertTrue(save_game(state, path))
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn(
                AUTOMATED_FEEDING_UPGRADE, saved["purchased_upgrades"],
            )
            state.purchased_upgrades.clear()
            self.assertTrue(load_game(state, path))
        self.assertEqual(state.purchased_upgrades, {
            AUTOMATED_FEEDING_UPGRADE, AUTOMATED_WATERING_UPGRADE,
        })


if __name__ == "__main__":
    unittest.main()
