import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from field_automation import (
    AUTOMATED_FIELD_FERTILIZING_UPGRADE,
    AUTOMATED_FIELD_WATERING_UPGRADE,
    run_field_automation,
)
from game_logger import get_logger
from game_rules import UPGRADES
from tractor import TASK_FERTILIZING, TASK_WATERING


class RecordingVehicleManager:
    """A koordinátor publikus request-hívásait és duplikációvédelmét rögzíti."""

    def __init__(self):
        self.pending = set()
        self.created = []

    def _start(self, field, task_type, source):
        key = (id(field), task_type)
        if key in self.pending:
            return False
        self.pending.add(key)
        self.created.append((field, task_type, source))
        return True

    def start_watering(self, world, buildings, economy, field,
                       current_ticks=None, source="manual"):
        return self._start(field, TASK_WATERING, source)

    def start_fertilizing(self, world, buildings, economy, field,
                          current_ticks=None, source="manual"):
        return self._start(field, TASK_FERTILIZING, source)


class FieldAutomationTests(unittest.TestCase):
    def setUp(self):
        self.fields = [{"row": 2, "col": 3, "crop": "wheat"}]
        self.vehicles = RecordingVehicleManager()
        get_logger().reset()

    def run_automation(self, upgrades):
        return run_field_automation(
            [[0]], [], object(), self.fields, self.vehicles, set(upgrades),
            current_ticks=100,
        )

    def test_upgrade_catalog_has_order_prices_and_descriptions(self):
        upgrade_ids = list(UPGRADES)
        feeding = upgrade_ids.index("automated_animal_feeding")
        watering = upgrade_ids.index("automated_animal_watering")
        field_watering = upgrade_ids.index(AUTOMATED_FIELD_WATERING_UPGRADE)
        field_fertilizing = upgrade_ids.index(AUTOMATED_FIELD_FERTILIZING_UPGRADE)
        self.assertLess(feeding, watering)
        self.assertLess(watering, field_watering)
        self.assertLess(field_watering, field_fertilizing)
        for upgrade_id in (
                AUTOMATED_FIELD_WATERING_UPGRADE,
                AUTOMATED_FIELD_FERTILIZING_UPGRADE):
            self.assertEqual(UPGRADES[upgrade_id]["price"], 20000)
            self.assertTrue(UPGRADES[upgrade_id]["description"])

    def test_disabled_automation_creates_nothing(self):
        self.assertEqual(self.run_automation([]), 0)
        self.assertEqual(self.vehicles.created, [])

    def test_watering_upgrade_creates_automatic_watering_only(self):
        self.assertEqual(
            self.run_automation([AUTOMATED_FIELD_WATERING_UPGRADE]), 1,
        )
        self.assertEqual(
            [(task_type, source) for _, task_type, source in self.vehicles.created],
            [(TASK_WATERING, "automatic")],
        )

    def test_fertilizing_upgrade_creates_automatic_fertilizing_only(self):
        self.assertEqual(
            self.run_automation([AUTOMATED_FIELD_FERTILIZING_UPGRADE]), 1,
        )
        self.assertEqual(self.vehicles.created[0][1:], (
            TASK_FERTILIZING, "automatic",
        ))

    def test_repeated_check_does_not_duplicate_either_task_type(self):
        upgrades = {
            AUTOMATED_FIELD_WATERING_UPGRADE,
            AUTOMATED_FIELD_FERTILIZING_UPGRADE,
        }
        self.assertEqual(self.run_automation(upgrades), 2)
        self.assertEqual(self.run_automation(upgrades), 0)
        self.assertEqual(len(self.vehicles.created), 2)

    def test_watering_and_fertilizing_can_coexist_on_same_field(self):
        self.assertEqual(self.run_automation({
            AUTOMATED_FIELD_WATERING_UPGRADE,
            AUTOMATED_FIELD_FERTILIZING_UPGRADE,
        }), 2)
        self.assertEqual(
            {task_type for _, task_type, _ in self.vehicles.created},
            {TASK_WATERING, TASK_FERTILIZING},
        )

    def test_only_successful_automatic_requests_are_logged(self):
        upgrades = {AUTOMATED_FIELD_WATERING_UPGRADE}
        self.run_automation(upgrades)
        self.run_automation(upgrades)
        entries = get_logger().entries
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].category, "Automation")
        self.assertIn("Veteményes #1", entries[0].message)


if __name__ == "__main__":
    unittest.main()
