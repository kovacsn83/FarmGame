import ast
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import asset_loader
import main as main_module
import user_data
from scripts import build_windows


class WindowsBuildTests(unittest.TestCase):
    def test_python_asset_root_is_repository_assets(self):
        self.assertEqual(asset_loader.get_asset_root(), ROOT / "assets")

    def test_bundled_asset_root_uses_single_meipass_location(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.object(sys, "_MEIPASS", temporary_directory, create=True):
                self.assertEqual(
                    asset_loader.get_asset_root(),
                    Path(temporary_directory) / "assets",
                )

    def test_build_script_and_spec_are_valid_python(self):
        ast.parse((ROOT / "scripts" / "build_windows.py").read_text("utf-8"))
        ast.parse((ROOT / "FarmGame.spec").read_text("utf-8"))

    def test_secret_scan_allows_only_the_public_certifi_ca_bundle(self):
        self.assertFalse(build_windows._is_forbidden_parts(
            ("FarmGame", "_internal", "certifi", "cacert.pem"),
        ))
        self.assertTrue(build_windows._is_forbidden_parts(
            ("FarmGame", "private-key.pem"),
        ))
        self.assertTrue(build_windows._is_forbidden_parts(
            ("FarmGame", "player.json"),
        ))

    def test_crash_log_uses_user_data_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                patch.dict("os.environ", {"LOCALAPPDATA": temporary_directory}),
                patch.object(main_module, "main", side_effect=RuntimeError("boom")),
            ):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    main_module.run_with_crash_logging()
                crash_log = user_data.get_logs_dir() / "crash.log"
            self.assertTrue(crash_log.is_file())
            self.assertIn("RuntimeError: boom", crash_log.read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
