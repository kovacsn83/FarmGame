"""Build and verify the portable FarmGame Windows release package."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = PROJECT_ROOT / "src"
BUILD_ROOT = PROJECT_ROOT / "build"
DIST_ROOT = PROJECT_ROOT / "dist"
APP_ROOT = DIST_ROOT / "FarmGame"
sys.path.insert(0, str(SOURCE_ROOT))

from game_version import GAME_VERSION, RELEASE_STAGE

ARCHIVE_PATH = DIST_ROOT / f"FarmGame-{GAME_VERSION}-Windows.zip"
RELEASE_README = PROJECT_ROOT / "packaging" / "README-Windows.txt"
FORBIDDEN_NAMES = {".env", "player.json", "results.json", "savegame.json"}
FORBIDDEN_SUFFIXES = {".db", ".pem", ".sqlite", ".sqlite3"}
FORBIDDEN_CONTENT_MARKERS = (
    b"DATABASE_URL=",
    b"postgresql://",
    b"github_pat_",
    b"ghp_",
    b"RAILWAY_TOKEN=",
)
REQUIRED_ASSETS = (
    Path("images/splash/kn_app_studio.png"),
    Path("images/icons/24/cursor_24.png"),
    Path("images/icons/24/spraying_24.png"),
    Path("images/terrain/grass/grass_01.png"),
)


def _safe_clean(path):
    resolved = path.resolve()
    if resolved.parent != PROJECT_ROOT or resolved.name not in {"build", "dist"}:
        raise RuntimeError(f"Unsafe build cleanup target: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _run_pyinstaller():
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
         str(PROJECT_ROOT / "FarmGame.spec")],
        cwd=PROJECT_ROOT, check=True,
    )


def _asset_root():
    direct = APP_ROOT / "assets"
    bundled = APP_ROOT / "_internal" / "assets"
    return direct if direct.is_dir() else bundled


def _is_forbidden_parts(parts):
    lowered_parts = {part.lower() for part in parts}
    name = parts[-1].lower()
    suffix = Path(name).suffix.lower()
    is_certifi_ca_bundle = name == "cacert.pem" and "certifi" in lowered_parts
    return (
        bool({"server", "tests", ".git"} & lowered_parts)
        or name in FORBIDDEN_NAMES
        or (suffix in FORBIDDEN_SUFFIXES and not is_certifi_ca_bundle)
    )


def _is_forbidden(path, root):
    return _is_forbidden_parts(path.relative_to(root).parts)


def _verify_release_tree():
    executable = APP_ROOT / "FarmGame.exe"
    if not executable.is_file():
        raise RuntimeError(f"Missing executable: {executable}")
    assets = _asset_root()
    for relative_path in REQUIRED_ASSETS:
        path = assets / relative_path
        if not path.is_file():
            raise RuntimeError(f"Missing runtime asset: {path}")
    for path in APP_ROOT.rglob("*"):
        if path.is_file() and _is_forbidden(path, APP_ROOT):
            raise RuntimeError(f"Forbidden release file: {path}")


def _write_archive():
    readme_text = RELEASE_README.read_text(encoding="utf-8").format(
        GAME_VERSION=GAME_VERSION, RELEASE_STAGE=RELEASE_STAGE,
    )
    (APP_ROOT / "README.txt").write_text(readme_text, encoding="utf-8")
    shutil.copy2(PROJECT_ROOT / "LICENSE", APP_ROOT / "LICENSE.txt")
    with zipfile.ZipFile(ARCHIVE_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(APP_ROOT.rglob("*")):
            if path.is_file():
                archive.write(path, Path("FarmGame") / path.relative_to(APP_ROOT))


def _verify_archive():
    if not ARCHIVE_PATH.is_file():
        raise RuntimeError(f"Missing release archive: {ARCHIVE_PATH}")
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        names = archive.namelist()
        if "FarmGame/FarmGame.exe" not in names:
            raise RuntimeError("The ZIP does not contain FarmGame/FarmGame.exe")
        for name in names:
            path = Path(name)
            if _is_forbidden_parts(path.parts):
                raise RuntimeError(f"Forbidden ZIP entry: {name}")
            if name.endswith("/"):
                continue
            content = archive.read(name).lower()
            for marker in FORBIDDEN_CONTENT_MARKERS:
                if marker.lower() in content:
                    raise RuntimeError(
                        f"Potential secret marker {marker!r} in ZIP entry: {name}"
                    )


def main():
    if os.name != "nt":
        raise RuntimeError("The Windows release must be built on Windows.")
    _safe_clean(BUILD_ROOT)
    _safe_clean(DIST_ROOT)
    _run_pyinstaller()
    _verify_release_tree()
    _write_archive()
    _verify_archive()
    size_mb = ARCHIVE_PATH.stat().st_size / (1024 * 1024)
    print(f"Windows release ready: {APP_ROOT}")
    print(f"Archive ready: {ARCHIVE_PATH} ({size_mb:.2f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
