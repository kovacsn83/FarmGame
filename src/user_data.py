"""Writable per-user paths, independent from application resources.

Application resources (images, fonts, and configuration defaults) remain part
of the installed game and are read-only. Mutable user data belongs below the
current user's FarmGame data directory. SaveSystem migration is intentionally
not performed here; the exposed saves path is preparation for that later step.
"""

import os
from pathlib import Path


APPLICATION_DIRECTORY_NAME = "FarmGame"
LOCAL_APP_DATA_ENVIRONMENT_VARIABLE = "LOCALAPPDATA"
FALLBACK_DIRECTORY_NAME = ".farmgame"


class UserDataInitializationError(RuntimeError):
    """Raised with a player-readable message when directories cannot be made."""


def get_user_data_dir():
    """Return the writable FarmGame root for the current user as a Path."""
    local_app_data = os.environ.get(LOCAL_APP_DATA_ENVIRONMENT_VARIABLE)
    if local_app_data and local_app_data.strip():
        return Path(local_app_data.strip()).expanduser() / APPLICATION_DIRECTORY_NAME
    return Path.home() / FALLBACK_DIRECTORY_NAME


def get_saves_dir():
    return get_user_data_dir() / "saves"


def get_logs_dir():
    return get_user_data_dir() / "logs"


def get_screenshots_dir():
    return get_user_data_dir() / "screenshots"


def get_player_profile_path():
    """Return the future profile path without creating the file."""
    return get_user_data_dir() / "player.json"


def get_challenge_results_path():
    """Return the persistent local Challenge result collection path."""
    return get_user_data_dir() / "challenge" / "results.json"


def get_settings_path():
    """Return the future settings path without creating the file."""
    return get_user_data_dir() / "settings.json"


def initialize_user_data():
    """Create all currently required directories once, safely and idempotently."""
    directories = (
        get_user_data_dir(), get_saves_dir(), get_logs_dir(),
        get_screenshots_dir(),
    )
    try:
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise UserDataInitializationError(
            f"A FarmGame felhasználói adatkönyvtára nem hozható létre: "
            f"{directory} ({error})"
        ) from None
    return directories[0]
