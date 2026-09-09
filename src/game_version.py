"""A FarmGame kézzel kezelt kiadási verziójának egyetlen igazságforrása."""


GAME_VERSION = "0.1.0"
RELEASE_STAGE = "Alpha"


def get_game_version():
    return GAME_VERSION


def get_game_version_tuple():
    """Összehasonlítható (major, minor, patch) alakot ad külső csomag nélkül."""
    return tuple(int(part) for part in GAME_VERSION.split("."))


def get_version_display():
    return f"{RELEASE_STAGE} v{GAME_VERSION}"


def get_full_version_display():
    return f"FarmGame {get_version_display()}"
