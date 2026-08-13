import pygame

from animals import can_place_animal
from constants import (
    BUILDING, COLOR_FIELD, COLOR_GRASS, COLOR_GRID, COLOR_PREVIEW_ERROR,
    COLOR_PREVIEW_OK, FIELD, FIELD_SIZE, GRASS, GRID_COLS,
    GRID_ROWS, ROAD, TILE_SIZE,
    TOOL_ANIMAL_HUSBANDRY, TOOL_BUILD, TOOL_BULLDOZER, TOOL_HARVEST,
    TOOL_FERTILIZE, TOOL_INSPECT, TOOL_PLANT, TOOL_ROAD,
    TOOL_WATERING,
)
from buildings import (
    BUILD_OPTIONS, BUILDING_TYPES, can_place_building, find_building_data,
    get_animal_pen_tiles, get_orchard_tiles,
)
from building_renderers import (
    draw_procedural_buildings, has_procedural_renderer,
)
from fields import can_place_field, find_field_data, is_field
from field_renderer import draw_field
from road_renderer import draw_road_tile
from road_building import is_valid_road_tile
from game_rules import FIELD_TYPES
from screen_layout import get_play_area_rect, screen_to_world, world_to_screen


def create_world():
    return [[GRASS for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]


def get_grass_tile_index(row, col, tile_count):
    """Gyors, determinisztikus egészszámos pszeudozajt képez a koordinátákból."""
    if tile_count <= 0:
        return None

    value = (row * 374761393 + col * 668265263) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
    value ^= value >> 16
    return value % tile_count


def _draw_grass_texture(screen, grass_tiles, row, col):
    """A koordinátához tartozó normál világ-fűcsempét rajzolja ki."""
    if not grass_tiles:
        return False
    tile_index = get_grass_tile_index(row, col, len(grass_tiles))
    grass_tile = grass_tiles[tile_index]
    if grass_tile is None:
        return False
    screen.blit(
        grass_tile,
        world_to_screen(col * TILE_SIZE, row * TILE_SIZE),
    )
    return True


def screen_to_grid(mouse_x, mouse_y, world=None):
    """A játéktéren belüli képernyőpozíciót rácskoordinátává alakítja."""
    if not get_play_area_rect().collidepoint(mouse_x, mouse_y):
        return -1, -1
    world_x, world_y = screen_to_world(mouse_x, mouse_y)
    row, col = int(world_y) // TILE_SIZE, int(world_x) // TILE_SIZE
    rows = len(world) if world is not None else GRID_ROWS
    cols = len(world[0]) if world and world[0] else GRID_COLS
    if not (0 <= row < rows and 0 <= col < cols):
        return -1, -1
    return row, col


def tile_to_world_center(row, col):
    """Egy rácsmező középpontját adja vissza játéktéri világkoordinátákban."""
    return (
        float(col * TILE_SIZE + TILE_SIZE / 2),
        float(row * TILE_SIZE + TILE_SIZE / 2),
    )


def draw_world(
        screen, world, fields, buildings, grass_tiles=None,
        harvest_availability=None):
    pygame.draw.rect(screen, COLOR_GRASS, get_play_area_rect())
    play_area = get_play_area_rect()
    first_x, first_y = screen_to_world(play_area.left, play_area.top)
    last_x, last_y = screen_to_world(play_area.right, play_area.bottom)
    start_row = max(0, int(first_y) // TILE_SIZE - 1)
    start_col = max(0, int(first_x) // TILE_SIZE - 1)
    end_row = min(len(world), int(last_y) // TILE_SIZE + 2)
    end_col = min(len(world[0]) if world else 0, int(last_x) // TILE_SIZE + 2)

    # Csak a látható csempék rajzolódnak; a szimuláció ettől független.
    for row in range(start_row, end_row):
        for col in range(start_col, end_col):
            if world[row][col] == GRASS:
                if _draw_grass_texture(screen, grass_tiles, row, col):
                    continue
                color = COLOR_GRASS
            elif world[row][col] == ROAD:
                draw_road_tile(screen, world, row, col)
                continue
            elif world[row][col] == FIELD:
                color = COLOR_FIELD
                field = find_field_data(fields, row, col)
                if field and field["crop"] is not None:
                    color = (70, 150, 60)
            elif world[row][col] == BUILDING:
                building = find_building_data(buildings, row, col)
                building_type = building["type"]
                building_config = BUILDING_TYPES[building_type]
                if building_config.get("draw_grass_underlay"):
                    if _draw_grass_texture(screen, grass_tiles, row, col):
                        continue
                    color = COLOR_GRASS
                elif has_procedural_renderer(building_type):
                    continue
                elif building_type == "animal_pen" and _draw_grass_texture(
                        screen, grass_tiles, row, col):
                    continue
                else:
                    color = building_config["color"]

            screen_x, screen_y = world_to_screen(
                col * TILE_SIZE, row * TILE_SIZE,
            )
            rect = pygame.Rect(
                screen_x,
                screen_y,
                TILE_SIZE,
                TILE_SIZE,
            )
            pygame.draw.rect(screen, color, rect)

    # A tile-alap kirajzolástól külön minden látható veteményes egyszer készül el.
    for field in fields:
        width = field.get("width", FIELD_SIZE)
        height = field.get("height", FIELD_SIZE)
        if (field["row"] < end_row
                and field["row"] + height > start_row
                and field["col"] < end_col
                and field["col"] + width > start_col):
            harvest_ready = bool(
                harvest_availability is not None
                and harvest_availability(field) is None
            )
            draw_field(screen, field, harvest_ready)

    draw_procedural_buildings(screen, buildings)


def draw_animal_pen_fences(screen, buildings):
    """A karámtile-ok kizárólagos külső határára rajzol kerítést."""
    _draw_merged_area_fence(screen, get_animal_pen_tiles(buildings))


def draw_orchard_fences(screen, buildings):
    """Az összefüggő Gyümölcsösök közös külső kerítését rajzolja."""
    _draw_merged_area_fence(screen, get_orchard_tiles(buildings))


def _draw_merged_area_fence(screen, area_tiles):
    """Csak egy területszerű objektum rácsának külső éleit keríti körbe."""
    fence_color = (112, 72, 38)
    fence_width = 4
    for row, col in area_tiles:
        left, top = world_to_screen(col * TILE_SIZE, row * TILE_SIZE)
        right = left + TILE_SIZE
        bottom = top + TILE_SIZE
        if (row - 1, col) not in area_tiles:
            pygame.draw.line(
                screen, fence_color, (left, top), (right, top), fence_width,
            )
        if (row + 1, col) not in area_tiles:
            pygame.draw.line(
                screen, fence_color, (left, bottom), (right, bottom), fence_width,
            )
        if (row, col - 1) not in area_tiles:
            pygame.draw.line(
                screen, fence_color, (left, top), (left, bottom), fence_width,
            )
        if (row, col + 1) not in area_tiles:
            pygame.draw.line(
                screen, fence_color, (right, top), (right, bottom), fence_width,
            )


def draw_grid(screen, world, selected_tool, selected_building, mouse_row, mouse_col):
    hidden_grid_tools = (
        TOOL_INSPECT, TOOL_PLANT, TOOL_WATERING, TOOL_FERTILIZE, TOOL_HARVEST,
    )
    if mouse_row >= 0 and selected_tool not in hidden_grid_tools:
        start_row, end_row = mouse_row - 2, mouse_row + 2
        start_col, end_col = mouse_col - 2, mouse_col + 2

        if selected_tool == TOOL_BUILD and selected_building in BUILD_OPTIONS:
            option = BUILD_OPTIONS[selected_building]
            width, height = option["width"], option["height"]
            end_row = mouse_row + height + 1
            end_col = mouse_col + width + 1

        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                if (row < 0 or row >= len(world) or col < 0
                        or not world or col >= len(world[row])):
                    continue
                screen_x, screen_y = world_to_screen(
                    col * TILE_SIZE, row * TILE_SIZE,
                )
                rect = pygame.Rect(
                    screen_x,
                    screen_y,
                    TILE_SIZE,
                    TILE_SIZE,
                )
                pygame.draw.rect(screen, COLOR_GRID, rect, 1)


def draw_preview_rect(screen, row, col, width, height, color):
    screen_x, screen_y = world_to_screen(col * TILE_SIZE, row * TILE_SIZE)
    rect = pygame.Rect(screen_x, screen_y,
                       TILE_SIZE * width, TILE_SIZE * height)
    pygame.draw.rect(screen, color, rect, 3)


def draw_preview(
        screen, world, fields, buildings, animals, selected_tool,
        selected_building, selected_animal, mouse_row, mouse_col,
        road_preview_tiles=None):
    if selected_tool == TOOL_ROAD and mouse_row >= 0:
        preview_tiles = road_preview_tiles or [(mouse_row, mouse_col)]
        for row, col in preview_tiles:
            color = (
                COLOR_PREVIEW_OK
                if is_valid_road_tile(world, row, col)
                else COLOR_PREVIEW_ERROR
            )
            draw_preview_rect(screen, row, col, 1, 1, color)

    if (selected_tool == TOOL_BUILD and selected_building in FIELD_TYPES
            and mouse_row >= 0):
        field_type = FIELD_TYPES[selected_building]
        color = (COLOR_PREVIEW_OK if can_place_field(
                     world, mouse_row, mouse_col,
                     field_type["width"], field_type["height"])
                 else COLOR_PREVIEW_ERROR)
        draw_preview_rect(
            screen, mouse_row, mouse_col,
            field_type["width"], field_type["height"], color,
        )

    if (selected_tool == TOOL_BUILD
            and selected_building in BUILDING_TYPES
            and mouse_row >= 0):
        building_type = selected_building
        building = BUILDING_TYPES[building_type]
        color = (COLOR_PREVIEW_OK
                 if can_place_building(
                     world, buildings, mouse_row, mouse_col, building_type,
                     animals=animals)
                 else COLOR_PREVIEW_ERROR)
        draw_preview_rect(
            screen, mouse_row, mouse_col, building["width"], building["height"], color
        )

    if selected_tool == TOOL_ANIMAL_HUSBANDRY and mouse_row >= 0:
        color = (
            COLOR_PREVIEW_OK
            if can_place_animal(
                animals, buildings, mouse_row, mouse_col, selected_animal,
            )
            else COLOR_PREVIEW_ERROR
        )
        draw_preview_rect(screen, mouse_row, mouse_col, 1, 1, color)

    if selected_tool == TOOL_BULLDOZER and mouse_row >= 0:
        building = find_building_data(buildings, mouse_row, mouse_col)
        if building:
            draw_preview_rect(
                screen, building["row"], building["col"], building["width"],
                building["height"], COLOR_PREVIEW_OK,
            )
        elif is_field(world, mouse_row, mouse_col):
            field = find_field_data(fields, mouse_row, mouse_col)
            if field:
                draw_preview_rect(
                    screen, field["row"], field["col"],
                    field.get("width", FIELD_SIZE),
                    field.get("height", FIELD_SIZE), COLOR_PREVIEW_OK,
                )
        else:
            draw_preview_rect(screen, mouse_row, mouse_col, 1, 1, COLOR_PREVIEW_OK)
