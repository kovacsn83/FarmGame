import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import pygame

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import player_profile
from player_profile import (
    MAX_PLAYER_NAME_LENGTH, PlayerProfileValidationError,
    create_player_profile, load_player_profile, update_player_name,
    validate_player_name,
)
from screen_layout import set_screen_size
from startup_ui import PlayerNamePrompt


class PlayerProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.profile_path = Path(self.temporary_directory.name) / "player.json"
        self.path_patch = patch.object(
            player_profile, "get_player_profile_path",
            return_value=self.profile_path,
        )
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.temporary_directory.cleanup()

    def test_missing_profile_returns_none_without_creating_a_file(self):
        self.assertIsNone(load_player_profile())
        self.assertFalse(self.profile_path.exists())

    def test_profile_is_valid_json_with_uuid_version_and_iso_timestamp(self):
        profile = create_player_profile("  Nagy Norbert  ")
        stored = json.loads(self.profile_path.read_text(encoding="utf-8"))
        self.assertEqual(profile.player_name, "Nagy Norbert")
        self.assertEqual(stored["profile_version"], 1)
        self.assertEqual(uuid.UUID(stored["player_id"]).version, 4)
        self.assertIn("T", stored["created_at"])

    def test_restart_loads_the_same_name_and_id(self):
        created = create_player_profile("Árvíztűrő")
        loaded = load_player_profile()
        self.assertEqual(loaded.player_id, created.player_id)
        self.assertEqual(loaded.player_name, "Árvíztűrő")

    def test_existing_profile_is_never_silently_replaced(self):
        created = create_player_profile("Első")
        with self.assertRaises(player_profile.PlayerProfileError):
            create_player_profile("Második")
        self.assertEqual(load_player_profile().player_id, created.player_id)

    def test_name_change_keeps_player_id_and_created_at(self):
        created = create_player_profile("Norbi")
        updated = update_player_name(created, "Norbert")
        self.assertEqual(updated.player_id, created.player_id)
        self.assertEqual(updated.created_at, created.created_at)
        self.assertEqual(load_player_profile().player_name, "Norbert")

    def test_name_validation(self):
        for invalid in ("", "   ", "x" * (MAX_PLAYER_NAME_LENGTH + 1)):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_player_name(invalid)
        self.assertEqual(validate_player_name("  Nagy Norbert  "), "Nagy Norbert")

    def test_invalid_json_and_incomplete_profile_are_diagnosable(self):
        for content in ("{broken", '{"profile_version": 1}'):
            with self.subTest(content=content):
                self.profile_path.write_text(content, encoding="utf-8")
                with self.assertRaises(PlayerProfileValidationError):
                    load_player_profile()

    def test_explicit_recovery_archives_corrupt_file(self):
        self.profile_path.write_text("{broken", encoding="utf-8")
        recovered = create_player_profile("Új játékos", recover_corrupt=True)
        backups = list(self.profile_path.parent.glob("player.corrupt-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{broken")
        self.assertEqual(load_player_profile().player_id, recovered.player_id)

    def test_atomic_save_leaves_no_temporary_file(self):
        create_player_profile("Teszt")
        self.assertFalse((self.profile_path.parent / ".player.json.tmp").exists())


class PlayerNamePromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        set_screen_size(800, 600)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_prompt_rejects_whitespace_and_accepts_trimmed_unicode_name(self):
        prompt = PlayerNamePrompt()
        prompt.text_input.text = "   "
        click = lambda: pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": prompt.continue_rect.center},
        )
        prompt.handle_event(click())
        self.assertIsNone(prompt.take_submission())
        self.assertIsNotNone(prompt.validation_error)
        prompt.text_input.text = "  Árvíztűrő  "
        prompt.handle_event(click())
        self.assertEqual(prompt.take_submission(), "Árvíztűrő")
        prompt.close()


if __name__ == "__main__":
    unittest.main()
