import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_supply_tasks as supply_fixture
from constants import BUILDING
from processing import initialize_processing_plant
from save_system import (
    load_game, save_game, load_game_from_slot, save_game_to_slot,
    _migrate_save_schema, create_save_state_signature,
)


class RuntimeValidationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = supply_fixture.SupplyTaskIntegrationTests()
        self.fixture.setUp()
        f = self.fixture
        self.state = f._prepare_valid_save_state()
        self.assertTrue(f.manager.start_trough_supply(
            f.world, f.buildings, f.economy, f.animals,
            {"type": "food", "group": [f.pen]}, current_ticks=0))
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "runtime.json"
        self.assertTrue(save_game(self.state, self.path))
        self.document = json.loads(self.path.read_text(encoding="utf-8"))

    def load_document(self, document):
        self.path.write_text(json.dumps(document), encoding="utf-8")
        return load_game(self.state, self.path)

    def reject(self, mutate):
        document = copy.deepcopy(self.document)
        mutate(document["vehicle_runtime"])
        before = copy.deepcopy(self.fixture.manager.runtime_save_record(
            self.state.fields, self.state.buildings))
        world = copy.deepcopy(self.state.world)
        buildings = copy.deepcopy(self.state.buildings)
        money = self.state.economy.money
        time = self.state.game_time.elapsed_weeks
        signature = create_save_state_signature(self.state)
        self.assertFalse(self.load_document(document))
        self.assertEqual(world, self.state.world)
        self.assertEqual(buildings, self.state.buildings)
        self.assertEqual(money, self.state.economy.money)
        self.assertEqual(time, self.state.game_time.elapsed_weeks)
        self.assertEqual(signature, create_save_state_signature(self.state))
        self.assertEqual(before, self.fixture.manager.runtime_save_record(
            self.state.fields, self.state.buildings))

    def test_bad_next_path_index_preserves_live_game(self):
        self.reject(lambda r: r["assets"][0].update(next_path_index="hibás"))

    def test_bad_route_point_preserves_live_game(self):
        self.reject(lambda r: r["tasks"][0].update(return_route=[[1]]))

    def test_duplicate_task_id_preserves_live_game(self):
        self.reject(lambda r: r["tasks"].append(copy.deepcopy(r["tasks"][0])))

    def test_same_task_on_two_vehicles_is_rejected(self):
        def mutate(runtime):
            vehicle = copy.deepcopy(self.document["tractors"][0])
            vehicle.update(id=90, slot_id=3)
            # The document used by reject must include the extra real asset.
            self.extra_vehicle = vehicle
            extra = copy.deepcopy(runtime["assets"][0])
            extra["id"] = 90
            runtime["assets"].append(extra)
        document = copy.deepcopy(self.document)
        mutate(document["vehicle_runtime"])
        document["tractors"].append(self.extra_vehicle)
        self.assertFalse(self.load_document(document))

    def test_invalid_positions_states_and_references(self):
        for changes in ({"row": -1}, {"world_x": float("inf")},
                        {"state": "unknown"}, {"path": [[0, "x"]]}):
            with self.subTest(changes=changes):
                self.reject(lambda r: r["assets"][0].update(changes))
        self.reject(lambda r: r["tasks"][0].update(
            field={"kind": "building", "index": 999}))

    def test_malformed_nested_values_are_controlled_rejections(self):
        for changes in ({"task_type": []}, {"target_group": [None]},
                        {"implement": []}, {"creation_order": "x"},
                        {"creation_order": None}):
            with self.subTest(changes=changes):
                self.reject(lambda r: r["tasks"][0].update(changes))

    def test_invalid_slot_runtime_preserves_existing_state(self):
        with patch("save_system.get_saves_dir", return_value=Path(self.directory.name)):
            self.assertTrue(save_game_to_slot(self.state, 1, "Runtime"))
            path = Path(self.directory.name) / "save_slot_1.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["game_state"]["vehicle_runtime"]["assets"][0]["next_path_index"] = "x"
            path.write_text(json.dumps(document), encoding="utf-8")
            before = copy.deepcopy(self.state.buildings)
            tractor = self.fixture.manager.tractors[0]
            self.assertFalse(load_game_from_slot(self.state, 1))
            self.assertEqual(before, self.state.buildings)
            self.assertIs(tractor, self.fixture.manager.tractors[0])

    def test_duplicate_queue_and_bad_attachment_are_rejected(self):
        self.reject(lambda r: r.update(queue=[1, 1]))
        self.reject(lambda r: r["assets"][0].update(attached_implement_id=999))

    def test_elapsed_loading_timer_can_be_negative(self):
        self.document["vehicle_runtime"]["tasks"][0]["remaining_wait_ms"] = -40
        self.assertTrue(self.load_document(self.document))

    def test_current_active_save_loads_normally(self):
        self.assertTrue(self.load_document(self.document))
        self.assertIsNotNone(self.fixture.manager.tractors[0].current_task)

    def plant_document(self):
        document = copy.deepcopy(self.document)
        plant = {"type": "processing_plant", "row": 25, "col": 25,
                 "width": 6, "height": 5}
        initialize_processing_plant(plant)
        document["buildings"].append(plant)
        for row in range(25, 30):
            for col in range(25, 31):
                document["world"][row][col] = BUILDING
        runtime = document["vehicle_runtime"]
        runtime["tasks"][0].update(
            field={"kind": "building", "index": 4}, target_group=[],
            source_building={"kind": "building", "index": 1},
            task_type="processing_supply")
        return document

    def insert_market(self, document, index, col):
        market = {"type": "market", "row": 30, "col": col,
                  "width": 4, "height": 3}
        document["buildings"].insert(index, market)
        for row in range(30, 33):
            for column in range(col, col + 4):
                document["world"][row][column] = BUILDING
        runtime = document["vehicle_runtime"]
        for task in runtime["tasks"]:
            for key in ("field", "pond", "source_building"):
                ref = task.get(key)
                if ref and ref["kind"] == "building" and ref["index"] >= index:
                    ref["index"] += 1

    def test_market_before_plant_keeps_active_task(self):
        document = self.plant_document()
        self.insert_market(document, 2, 5)
        self.assertTrue(self.load_document(document))
        task = self.fixture.manager.tractors[0].current_task
        self.assertIs(task.field, self.state.buildings[4])
        self.assertIs(task.source_building, self.state.buildings[1])

    def test_multiple_markets_remap_all_building_references(self):
        document = self.plant_document()
        self.insert_market(document, 2, 5)
        self.insert_market(document, 1, 12)
        self.assertTrue(self.load_document(document))
        task = self.fixture.manager.tractors[0].current_task
        self.assertIs(task.field, self.state.buildings[4])
        self.assertIs(task.source_building, self.state.buildings[1])

    def test_group_and_asset_references_are_remapped(self):
        document = self.plant_document()
        self.insert_market(document, 2, 5)
        runtime = document["vehicle_runtime"]
        runtime["tasks"][0]["target_group"] = [{"kind": "building", "index": 5}]
        runtime["assets"][0]["unreachable_parking_building"] = {
            "kind": "building", "index": 3}
        self.assertTrue(self.load_document(document))
        task = self.fixture.manager.tractors[0].current_task
        self.assertIs(task.target_group[0], self.state.buildings[4])
        self.assertIs(self.fixture.manager.tractors[0]._unreachable_parking_building,
                      self.state.buildings[2])

    def test_removed_market_source_is_dropped_safely(self):
        document = self.plant_document()
        self.insert_market(document, 2, 5)
        document["vehicle_runtime"]["tasks"][0]["source_building"] = {
            "kind": "building", "index": 2}
        self.assertTrue(self.load_document(document))
        self.assertIsNone(self.fixture.manager.tractors[0].current_task)

    def test_removed_market_target_is_dropped_safely(self):
        document = self.plant_document()
        self.insert_market(document, 2, 5)
        document["vehicle_runtime"]["tasks"][0]["field"]["index"] = 2
        self.assertTrue(self.load_document(document))
        self.assertIsNone(self.fixture.manager.tractors[0].current_task)
        self.assertFalse(self.fixture.manager.task_queue)

    def test_migration_is_idempotent_and_resaved_game_loads(self):
        document = self.plant_document()
        self.insert_market(document, 2, 5)
        self.assertTrue(_migrate_save_schema(document))
        first = copy.deepcopy(document)
        self.assertTrue(_migrate_save_schema(document))
        self.assertEqual(first, document)
        self.assertTrue(self.load_document(document))
        self.assertTrue(save_game(self.state, self.path))
        self.assertTrue(load_game(self.state, self.path))
