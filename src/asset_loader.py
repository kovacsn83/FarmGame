import sys
from functools import lru_cache
from pathlib import Path

import pygame


TOOLBAR_ICON_DIRECTORY = Path("images") / "icons" / "24"
HUD_ICON_DIRECTORY = Path("images") / "icons" / "20"
GRASS_TILE_DIRECTORY = Path("images") / "terrain" / "grass"
QUEST_ICON_DIRECTORY = Path("images") / "quests" / "100"
SPLASH_IMAGE_DIRECTORY = Path("images") / "splash"
GRASS_TILE_COUNT = 8

TIME_SPEED_ICON_FILES = {
    0: "time_pause_20.png",
    1: "time_speed_1x_20.png",
    2: "time_speed_2x_20.png",
    3: "time_speed_3x_20.png",
}


def get_asset_root():
    """Fejlesztéskor és csomagolt futtatáskor is feloldja az assetek gyökerét."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is not None:
        return Path(bundle_root) / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


def toolbar_icon_path(filename):
    """A 24 pixeles toolbar-ikon projektfüggetlen relatív útvonalát adja vissza."""
    return TOOLBAR_ICON_DIRECTORY / filename


@lru_cache(maxsize=None)
def load_image(asset_path):
    """Egy átlátszó képet egyszer tölt be a közös assetgyökérből."""
    if not asset_path:
        return None

    path = get_asset_root() / Path(asset_path)
    try:
        return pygame.image.load(path.as_posix()).convert_alpha()
    except (OSError, pygame.error):
        print(f"Az asset nem tölthető be: {path}")
        return None


@lru_cache(maxsize=None)
def load_icon(icon_path, size):
    """Ikont tölt be és szükség esetén a kért méretre igazítja."""
    icon = load_image(icon_path)
    if icon is None:
        return None
    if icon.get_size() != (size, size):
        icon = pygame.transform.smoothscale(icon, (size, size))
    return icon


def load_toolbar_icons(tool_definitions, size):
    """Eszközazonosító szerint előkészíti a toolbar opcionális ikonjait."""
    return {
        tool["tool"]: load_icon(tool.get("icon_path"), size)
        for tool in tool_definitions
    }


def load_time_speed_icons(size=20):
    """Egyszer betölti a HUD idősebesség-ikonjait, átméretezés nélkül."""
    icons = {}
    for time_speed, filename in TIME_SPEED_ICON_FILES.items():
        icon_path = HUD_ICON_DIRECTORY / filename
        icon = load_image(icon_path)
        if icon is not None and icon.get_size() != (size, size):
            print(
                f"Az idősebesség-ikon mérete hibás: "
                f"{get_asset_root() / icon_path} "
                f"({icon.get_width()}x{icon.get_height()})"
            )
            icon = None
        icons[time_speed] = icon
    return icons


def load_hud_menu_icon(size=20):
    """A HUD menügombját a közös, gyorsítótárazott ikonbetöltővel készíti elő."""
    return load_icon(HUD_ICON_DIRECTORY / "dropdown_menu_20.png", size)


def load_hud_calendar_icon(size=20):
    """A Gazdálkodási naptár ikonját a közös HUD-méretben tölti be."""
    return load_icon(HUD_ICON_DIRECTORY / "calendar-20.png", size)


def load_quest_icon(size=100):
    """A Quest prototípus 100 pixeles képét a közös assetbetöltővel tölti be."""
    return load_icon(QUEST_ICON_DIRECTORY / "Tutorial-100.jpg", size)


def load_splash_image():
    """A KN App Studio indítóképet eredeti képarányával tölti be."""
    return load_image(SPLASH_IMAGE_DIRECTORY / "kn_app_studio.png")


def grass_tile_paths():
    """Determinista sorrendben adja vissza a nyolc füves csempe útvonalát."""
    return [
        GRASS_TILE_DIRECTORY / f"grass_{index:02d}.png"
        for index in range(1, GRASS_TILE_COUNT + 1)
    ]


def load_grass_tiles(tile_size):
    """Egyszer betölti a füves csempéket; hibánál az adott elem None marad."""
    tiles = []
    for tile_path in grass_tile_paths():
        tile = load_image(tile_path)
        if tile is not None and tile.get_size() != (tile_size, tile_size):
            print(
                f"A füves csempe mérete hibás: {get_asset_root() / tile_path} "
                f"({tile.get_width()}x{tile.get_height()})"
            )
            tile = None
        tiles.append(tile)
    return tiles
