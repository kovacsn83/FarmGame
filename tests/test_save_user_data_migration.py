import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import save_system
from game_version import GAME_VERSION
from simulation import SimulationBot


class SaveUserDataMigrationTests(unittest.TestCase):
    def test_slot_save_overwrite_metadata_and_load_use_user_data(self):
        with tempfile.TemporaryDirectory() as directory:
            saves = Path(directory) / "user" / "saves"
            with patch.object(save_system, "get_saves_dir", return_value=saves):
                original = SimulationBot(201)
                original.state.economy.money = 123
                self.assertTrue(save_system.save_game_to_slot(
                    original.state, 2, "Első név", "2026-09-09 09:00"))
                path = saves / "save_slot_2.json"
                self.assertTrue(path.is_file())
                first_schema = json.loads(path.read_text(encoding="utf-8"))[
                    "game_state"]["save_version"]
                first_metadata = json.loads(path.read_text(encoding="utf-8"))[
                    "metadata"]
                self.assertEqual(first_metadata["game_version"], GAME_VERSION)
                self.assertEqual(first_metadata["save_version"], first_schema)
                original.state.economy.money = 456
                self.assertTrue(save_system.save_game_to_slot(
                    original.state, 2, "Felülírt", "2026-09-09 09:01"))
                metadata = save_system.get_slot_metadata(2)
                self.assertEqual(metadata["save_name"], "Felülírt")
                restored = SimulationBot(202)
                self.assertTrue(save_system.load_game_from_slot(restored.state, 2))
                self.assertEqual(restored.state.economy.money, 456)
                self.assertEqual(first_schema, save_system.SAVE_VERSION)
                self.assertEqual(
                    json.loads(path.read_text(encoding="utf-8"))[
                        "game_state"]["save_version"], first_schema)

    def test_legacy_and_different_game_versions_remain_loadable(self):
        with tempfile.TemporaryDirectory() as directory:
            saves = Path(directory) / "saves"
            with patch.object(save_system, "get_saves_dir", return_value=saves):
                original = SimulationBot(205)
                self.assertTrue(save_system.save_game_to_slot(
                    original.state, 1, "Legacy", "2026-09-09 10:00"))
                path = saves / "save_slot_1.json"
                document = json.loads(path.read_text(encoding="utf-8"))
                document["metadata"].pop("game_version")
                path.write_text(json.dumps(document), encoding="utf-8")
                self.assertIsNone(save_system.get_slot_metadata(1)["game_version"])
                self.assertTrue(save_system.load_game_from_slot(
                    SimulationBot(206).state, 1))

                document["metadata"]["game_version"] = "9.9.9"
                path.write_text(json.dumps(document), encoding="utf-8")
                self.assertEqual(
                    save_system.get_slot_metadata(1)["game_version"], "9.9.9")
                self.assertTrue(save_system.load_game_from_slot(
                    SimulationBot(207).state, 1))

    def test_legacy_slots_copy_once_without_deletion_or_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            legacy = base / "project" / "saves"
            destination = base / "user" / "saves"
            legacy.mkdir(parents=True)
            destination.mkdir(parents=True)
            legacy_one = legacy / "save_slot_1.json"
            legacy_two = legacy / "save_slot_2.json"
            legacy_one.write_bytes(b"legacy-one")
            legacy_two.write_bytes(b"legacy-two")
            destination_two = destination / "save_slot_2.json"
            destination_two.write_bytes(b"new-two")
            with (
                patch.object(save_system, "get_saves_dir", return_value=destination),
                patch.object(save_system, "log") as log,
            ):
                self.assertEqual(save_system.migrate_legacy_saves(legacy), 1)
                self.assertEqual(save_system.migrate_legacy_saves(legacy), 0)
            self.assertEqual((destination / "save_slot_1.json").read_bytes(), b"legacy-one")
            self.assertEqual(destination_two.read_bytes(), b"new-two")
            self.assertEqual(legacy_one.read_bytes(), b"legacy-one")
            self.assertEqual(legacy_two.read_bytes(), b"legacy-two")
            self.assertEqual(
                sorted(path.name for path in destination.iterdir()),
                ["save_slot_1.json", "save_slot_2.json"],
            )
            self.assertTrue(any(
                "cél már létezik: save_slot_2.json" in str(call)
                for call in log.call_args_list
            ))

    def test_legacy_single_save_is_converted_and_loadable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            legacy = base / "project" / "saves"
            destination = base / "user" / "saves"
            legacy.mkdir(parents=True)
            original = SimulationBot(203)
            original.state.economy.money = 789
            self.assertTrue(save_system.save_game(
                original.state, legacy / "savegame.json"))
            before = (legacy / "savegame.json").read_bytes()
            with patch.object(
                    save_system, "get_saves_dir", return_value=destination):
                self.assertEqual(save_system.migrate_legacy_saves(legacy), 0)
                slots = save_system.get_save_slots()
                self.assertEqual(slots[0]["status"], "valid")
                self.assertEqual(slots[0]["save_name"], "Korábbi mentés")
                restored = SimulationBot(204)
                self.assertTrue(save_system.load_game_from_slot(restored.state, 1))
                self.assertEqual(restored.state.economy.money, 789)
            self.assertEqual((legacy / "savegame.json").read_bytes(), before)

    def test_working_directory_does_not_affect_slot_path(self):
        with tempfile.TemporaryDirectory() as directory:
            saves = Path(directory) / "absolute" / "saves"
            with patch.object(save_system, "get_saves_dir", return_value=saves):
                self.assertEqual(
                    save_system.get_slot_path(8), saves / "save_slot_8.json")

    def test_write_failure_is_reported_without_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            blocked_parent = Path(directory) / "not-a-directory"
            blocked_parent.write_text("occupied", encoding="utf-8")
            target = blocked_parent / "save.json"
            with patch.object(save_system, "log") as log:
                self.assertFalse(save_system._atomic_write_json(target, {"ok": True}))
            self.assertTrue(any(
                "Mentési fájl írása sikertelen" in str(call)
                for call in log.call_args_list
            ))
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
