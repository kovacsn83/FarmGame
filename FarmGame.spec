# -*- mode: python ; coding: utf-8 -*-
"""Reproducible Windows onedir build for the FarmGame client."""

import sys
from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable,
    VarFileInfo, VarStruct, VSVersionInfo,
)

PROJECT_ROOT = Path(SPECPATH).resolve()
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from game_version import GAME_VERSION


def _windows_version_tuple(version):
    parts = tuple(int(part) for part in version.split("."))
    return (*parts, *([0] * (4 - len(parts))))[:4]


WINDOWS_VERSION = _windows_version_tuple(GAME_VERSION)
VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=WINDOWS_VERSION, prodvers=WINDOWS_VERSION, mask=0x3F,
        flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0),
    ),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "KN App Studio"),
            StringStruct("FileDescription", "FarmGame"),
            StringStruct("FileVersion", GAME_VERSION),
            StringStruct("InternalName", "FarmGame"),
            StringStruct("OriginalFilename", "FarmGame.exe"),
            StringStruct("ProductName", "FarmGame"),
            StringStruct("ProductVersion", GAME_VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

a = Analysis(
    [str(SOURCE_ROOT / "main.py")], pathex=[str(SOURCE_ROOT)],
    binaries=[], datas=[(str(PROJECT_ROOT / "assets"), "assets")],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["alembic", "fastapi", "psycopg", "sqlalchemy", "uvicorn"],
    noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="FarmGame",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
    version=VERSION_INFO,
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[],
    name="FarmGame",
)
