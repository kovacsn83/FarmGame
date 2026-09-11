import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import save_system
from challenge import ChallengeManager, ChallengeStatus
from game_identity import generate_game_id, is_valid_game_id
from game_version import GAME_VERSION
from notification_system import NotificationManager
from simulation import SimulationBot


PROFILE = SimpleNamespace(player_id="same-player", player_name="Norbi")
WEEK_10_52 = 9 * 52 + 51
WEEK_11_1 = 10 * 52


def state_with_identity(seed):
    bot = SimulationBot(seed)
    bot.state.game_id = generate_game_id()
    bot.state.challenge_manager = ChallengeManager(
        PROFILE, NotificationManager(start_ticks=0),
    )
    return bot.state


class GameIdentityTests(unittest.TestCase):
    def test_each_new_farm_gets_a_distinct_uuid_for_the_same_player(self):
        first = state_with_identity(800)
        second = state_with_identity(801)
        self.assertTrue(is_valid_game_id(first.game_id))
        self.assertEqual(uuid.UUID(first.game_id).version, 4)
        self.assertNotEqual(first.game_id, second.game_id)
        self.assertEqual(PROFILE.player_id, "same-player")

    def test_same_farm_saved_to_two_slots_keeps_one_game_id(self):
        state = state_with_identity(802)
        original_id = state.game_id
        with tempfile.TemporaryDirectory() as directory, patch.object(
                save_system, "get_saves_dir", return_value=Path(directory)):
            self.assertTrue(save_system.save_game_to_slot(state, 1, "Első"))
            self.assertTrue(save_system.save_game_to_slot(state, 2, "Második"))
            for slot in (1, 2):
                document = json.loads(
                    (Path(directory) / f"save_slot_{slot}.json").read_text()
                )
                self.assertEqual(document["game_state"]["game_id"], original_id)
            self.assertEqual(state.game_id, original_id)

    def test_load_restores_the_saved_id_across_sessions_and_versions(self):
        original = state_with_identity(803)
        original_id = original.game_id
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "farm.json"
            self.assertTrue(save_system.save_game(original, path))
            restored = state_with_identity(804)
            self.assertNotEqual(restored.game_id, original_id)
            with patch("game_version.GAME_VERSION", "9.9.9"):
                self.assertTrue(save_system.load_game(restored, path))
            self.assertEqual(restored.game_id, original_id)

    def test_legacy_save_gets_one_id_and_next_save_persists_it(self):
        original = state_with_identity(805)
        with tempfile.TemporaryDirectory() as directory:
            legacy_path = Path(directory) / "legacy.json"
            self.assertTrue(save_system.save_game(original, legacy_path))
            document = json.loads(legacy_path.read_text())
            document.pop("game_id")
            legacy_path.write_text(json.dumps(document), encoding="utf-8")

            restored = SimulationBot(806).state
            restored.challenge_manager = ChallengeManager(PROFILE)
            self.assertTrue(save_system.load_game(restored, legacy_path))
            assigned_id = restored.game_id
            self.assertTrue(is_valid_game_id(assigned_id))
            self.assertTrue(save_system.save_game(restored, legacy_path))
            self.assertEqual(
                json.loads(legacy_path.read_text())["game_id"], assigned_id)

    def test_invalid_game_id_recovers_without_crashing(self):
        original = state_with_identity(807)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            self.assertTrue(save_system.save_game(original, path))
            document = json.loads(path.read_text())
            document["game_id"] = 123
            path.write_text(json.dumps(document), encoding="utf-8")
            restored = SimulationBot(808).state
            restored.challenge_manager = ChallengeManager(PROFILE)
            self.assertTrue(save_system.load_game(restored, path))
            self.assertTrue(is_valid_game_id(restored.game_id))

    def test_completed_legacy_challenge_receives_the_farm_id(self):
        original = state_with_identity(809)
        original.challenge_manager.handle_week_transition(
            WEEK_10_52, WEEK_11_1, original,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-challenge.json"
            self.assertTrue(save_system.save_game(original, path))
            document = json.loads(path.read_text())
            document.pop("game_id")
            document["ten_year_challenge"]["result"].pop("game_id")
            path.write_text(json.dumps(document), encoding="utf-8")
            restored = SimulationBot(810).state
            restored.challenge_manager = ChallengeManager(PROFILE)
            self.assertTrue(save_system.load_game(restored, path))
            self.assertEqual(
                restored.challenge_manager.result.game_id, restored.game_id)

    def test_legacy_ineligible_farm_also_gets_an_id(self):
        original = state_with_identity(811)
        original.game_time.elapsed_weeks = WEEK_11_1
        original.challenge_manager.status = ChallengeStatus.LEGACY_INELIGIBLE
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ineligible.json"
            self.assertTrue(save_system.save_game(original, path))
            document = json.loads(path.read_text())
            document.pop("game_id")
            path.write_text(json.dumps(document), encoding="utf-8")
            restored = SimulationBot(812).state
            restored.challenge_manager = ChallengeManager(PROFILE)
            self.assertTrue(save_system.load_game(restored, path))
            self.assertTrue(is_valid_game_id(restored.game_id))
            self.assertEqual(
                restored.challenge_manager.status,
                ChallengeStatus.LEGACY_INELIGIBLE,
            )

    def test_public_version_and_save_schema_do_not_change(self):
        self.assertEqual(GAME_VERSION, "0.1.2")
        self.assertEqual(save_system.SAVE_VERSION, 4)


if __name__ == "__main__":
    unittest.main()
