import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from save_system import _repair_legacy_processing_references


class LegacyProcessingReferenceTests(unittest.TestCase):
    def sample(self):
        ref = {"kind": "building", "index": 1}
        return {"buildings": [
            {"type": "processing_plant", "row": 4, "col": 26, "width": 6, "height": 5},
            {"type": "animal_pen"},
        ], "vehicle_runtime": {"tasks": [{
            "task_type": "processing_supply", "field": ref,
            "target_group": [dict(ref)], "route_source_to_target": [[9, 26]],
            "resource_reserved": True, "remaining_payload": 5,
        }]}}

    def test_route_proven_target_is_repaired_once_without_changing_cargo(self):
        data = self.sample()
        _repair_legacy_processing_references(data)
        task = data["vehicle_runtime"]["tasks"][0]
        self.assertEqual(task["field"]["index"], 0)
        self.assertEqual(task["target_group"], [task["field"]])
        self.assertTrue(task["resource_reserved"])
        self.assertEqual(task["remaining_payload"], 5)
        snapshot = copy.deepcopy(data)
        _repair_legacy_processing_references(data)
        self.assertEqual(data, snapshot)

    def test_unproven_target_is_not_guessed(self):
        data = self.sample()
        data["vehicle_runtime"]["tasks"][0]["route_source_to_target"] = [[1, 1]]
        snapshot = copy.deepcopy(data)
        _repair_legacy_processing_references(data)
        self.assertEqual(data, snapshot)

    def test_ambiguous_destination_is_not_repaired(self):
        data = self.sample()
        data["buildings"].append(dict(data["buildings"][0]))
        _repair_legacy_processing_references(data)
        self.assertEqual(data["vehicle_runtime"]["tasks"][0]["field"]["index"], 1)
