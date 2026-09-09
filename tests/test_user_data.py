import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import main as main_module
import user_data


class UserDataTests(unittest.TestCase):
    def test_local_app_data_paths_and_idempotent_initialization(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
                os.environ, {"LOCALAPPDATA": directory}):
            root = Path(directory) / "FarmGame"
            self.assertEqual(user_data.get_user_data_dir(), root)
            self.assertEqual(user_data.get_saves_dir(), root / "saves")
            self.assertEqual(user_data.get_logs_dir(), root / "logs")
            self.assertEqual(user_data.get_screenshots_dir(), root / "screenshots")
            self.assertEqual(user_data.get_player_profile_path(), root / "player.json")
            self.assertEqual(user_data.get_settings_path(), root / "settings.json")
            self.assertEqual(user_data.initialize_user_data(), root)
            self.assertEqual(user_data.initialize_user_data(), root)
            self.assertTrue(root.is_dir())
            for name in ("saves", "logs", "screenshots"):
                self.assertTrue((root / name).is_dir())
            self.assertFalse((root / "player.json").exists())
            self.assertFalse((root / "settings.json").exists())

    def test_missing_local_app_data_uses_home_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
                os.environ, {}, clear=True), patch.object(
                    user_data.Path, "home", return_value=Path(directory)):
            self.assertEqual(
                user_data.get_user_data_dir(), Path(directory) / ".farmgame")
            user_data.initialize_user_data()
            self.assertTrue(user_data.get_saves_dir().is_dir())

    def test_path_helpers_do_not_create_files_or_directories(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
                os.environ, {"LOCALAPPDATA": directory}):
            root = Path(directory) / "FarmGame"
            user_data.get_saves_dir()
            user_data.get_player_profile_path()
            user_data.get_settings_path()
            self.assertFalse(root.exists())

    def test_initialization_failure_has_clear_error(self):
        with patch.object(user_data.Path, "mkdir", side_effect=OSError("denied")):
            with self.assertRaisesRegex(
                    user_data.UserDataInitializationError,
                    "felhasználói adatkönyvtára nem hozható létre"):
                user_data.initialize_user_data()

    def test_main_initializes_before_pygame_and_stops_cleanly_on_failure(self):
        error = user_data.UserDataInitializationError("test failure")
        with (
            patch.object(main_module, "initialize_user_data", side_effect=error) as initialize,
            patch.object(main_module.pygame, "init") as pygame_init,
            patch.object(main_module.get_logger(), "log") as log,
        ):
            main_module.main()
        initialize.assert_called_once_with()
        pygame_init.assert_not_called()
        log.assert_called_once_with(error, "UserData", level="ERROR")

    def test_assets_keep_their_application_resource_location(self):
        from asset_loader import get_asset_root
        self.assertEqual(get_asset_root(), ROOT / "assets")
