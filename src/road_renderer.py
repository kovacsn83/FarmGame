import pygame

from constants import ROAD, TILE_SIZE
from screen_layout import world_to_screen


ROAD_UP = 1
ROAD_RIGHT = 2
ROAD_DOWN = 4
ROAD_LEFT = 8

ROAD_BASE_COLOR = (133, 112, 86)
ROAD_COMPACTED_COLOR = (148, 126, 97)
ROAD_TRACK_COLOR = (101, 82, 65)
ROAD_DARK_PATCH_COLOR = (116, 94, 72)
ROAD_LIGHT_PATCH_COLOR = (157, 136, 106)
ROAD_STONE_COLOR = (105, 100, 89)
ROAD_EDGE_DARK_COLOR = (91, 77, 59)
ROAD_EDGE_LIGHT_COLOR = (169, 146, 110)
ROAD_GRASS_DETAIL_COLOR = (47, 126, 45)
ROAD_TRACK_WIDTH = 2
ROAD_TEXTURE_VARIANTS = 4

_ROAD_SURFACE_CACHE = {}


def get_road_neighbor_mask(world, row, col):
    """A felső, jobb, alsó és bal szomszédot négy bites maszkká alakítja."""
    if not world or not (0 <= row < len(world) and 0 <= col < len(world[row])):
        return 0
    mask = 0
    if row > 0 and world[row - 1][col] == ROAD:
        mask |= ROAD_UP
    if col + 1 < len(world[row]) and world[row][col + 1] == ROAD:
        mask |= ROAD_RIGHT
    if row + 1 < len(world) and col < len(world[row + 1]) and world[row + 1][col] == ROAD:
        mask |= ROAD_DOWN
    if col > 0 and world[row][col - 1] == ROAD:
        mask |= ROAD_LEFT
    return mask


def _stable_value(row, col, salt=0):
    value = (
        (row + 1) * 73856093
        ^ (col + 1) * 19349663
        ^ (salt + 1) * 83492791
    ) & 0xFFFFFFFF
    value ^= value >> 16
    return value


def _connected(mask, direction):
    return bool(mask & direction)


def _draw_road_base(surface, mask, variant):
    surface.fill(ROAD_BASE_COLOR)
    pygame.draw.rect(surface, ROAD_COMPACTED_COLOR, (2, 2, TILE_SIZE - 4, TILE_SIZE - 4))
    if _connected(mask, ROAD_UP):
        pygame.draw.rect(surface, ROAD_COMPACTED_COLOR, (2, 0, TILE_SIZE - 4, TILE_SIZE // 2))
    if _connected(mask, ROAD_RIGHT):
        pygame.draw.rect(surface, ROAD_COMPACTED_COLOR, (TILE_SIZE // 2, 2, TILE_SIZE // 2, TILE_SIZE - 4))
    if _connected(mask, ROAD_DOWN):
        pygame.draw.rect(surface, ROAD_COMPACTED_COLOR, (2, TILE_SIZE // 2, TILE_SIZE - 4, TILE_SIZE // 2))
    if _connected(mask, ROAD_LEFT):
        pygame.draw.rect(surface, ROAD_COMPACTED_COLOR, (0, 2, TILE_SIZE // 2, TILE_SIZE - 4))

    # A nem csatlakozó széleken finom, koordinált szabálytalanság marad.
    wobble = variant % 2
    if not _connected(mask, ROAD_UP):
        pygame.draw.line(surface, ROAD_EDGE_DARK_COLOR, (0, 1 + wobble), (TILE_SIZE - 1, 1), 1)
    if not _connected(mask, ROAD_RIGHT):
        pygame.draw.line(surface, ROAD_EDGE_DARK_COLOR, (TILE_SIZE - 2, 0), (TILE_SIZE - 2 - wobble, TILE_SIZE - 1), 1)
    if not _connected(mask, ROAD_DOWN):
        pygame.draw.line(surface, ROAD_EDGE_LIGHT_COLOR, (0, TILE_SIZE - 2), (TILE_SIZE - 1, TILE_SIZE - 2 - wobble), 1)
    if not _connected(mask, ROAD_LEFT):
        pygame.draw.line(surface, ROAD_EDGE_LIGHT_COLOR, (1, 0), (1 + wobble, TILE_SIZE - 1), 1)


def _draw_horizontal_tracks(surface):
    for y in (7, 13):
        pygame.draw.line(surface, ROAD_TRACK_COLOR, (0, y), (TILE_SIZE, y), ROAD_TRACK_WIDTH)


def _draw_vertical_tracks(surface):
    for x in (7, 13):
        pygame.draw.line(surface, ROAD_TRACK_COLOR, (x, 0), (x, TILE_SIZE), ROAD_TRACK_WIDTH)


CORNER_TRACK_POINTS = {
    ROAD_UP | ROAD_RIGHT: (
        ((7, 0), (7, 5), (9, 8), (12, 11), (15, 13), (20, 13)),
        ((13, 0), (13, 4), (14, 6), (16, 7), (20, 7)),
    ),
    ROAD_RIGHT | ROAD_DOWN: (
        ((20, 7), (15, 7), (12, 9), (9, 12), (7, 15), (7, 20)),
        ((20, 13), (16, 13), (14, 14), (13, 16), (13, 20)),
    ),
    ROAD_DOWN | ROAD_LEFT: (
        ((13, 20), (13, 15), (11, 12), (8, 9), (5, 7), (0, 7)),
        ((7, 20), (7, 16), (6, 14), (4, 13), (0, 13)),
    ),
    ROAD_LEFT | ROAD_UP: (
        ((0, 13), (5, 13), (8, 11), (11, 8), (13, 5), (13, 0)),
        ((0, 7), (4, 7), (6, 6), (7, 4), (7, 0)),
    ),
}


def _draw_corner_tracks(surface, mask):
    for points in CORNER_TRACK_POINTS[mask]:
        pygame.draw.lines(surface, ROAD_TRACK_COLOR, False, points, ROAD_TRACK_WIDTH)


def _draw_arm_tracks(surface, direction, stop_at_center=True):
    near, far = (7, 13) if stop_at_center else (5, 15)
    if direction == ROAD_UP:
        for x in (7, 13):
            pygame.draw.line(surface, ROAD_TRACK_COLOR, (x, 0), (x, near), ROAD_TRACK_WIDTH)
    elif direction == ROAD_RIGHT:
        for y in (7, 13):
            pygame.draw.line(surface, ROAD_TRACK_COLOR, (far, y), (TILE_SIZE, y), ROAD_TRACK_WIDTH)
    elif direction == ROAD_DOWN:
        for x in (7, 13):
            pygame.draw.line(surface, ROAD_TRACK_COLOR, (x, far), (x, TILE_SIZE), ROAD_TRACK_WIDTH)
    elif direction == ROAD_LEFT:
        for y in (7, 13):
            pygame.draw.line(surface, ROAD_TRACK_COLOR, (0, y), (near, y), ROAD_TRACK_WIDTH)


def _draw_dead_end_tracks(surface, direction):
    _draw_arm_tracks(surface, direction, stop_at_center=False)
    if direction in (ROAD_UP, ROAD_DOWN):
        for x in (7, 13):
            pygame.draw.circle(surface, ROAD_TRACK_COLOR, (x, 10), 1)
    else:
        for y in (7, 13):
            pygame.draw.circle(surface, ROAD_TRACK_COLOR, (10, y), 1)


def _draw_junction_tracks(surface, mask):
    for direction in (ROAD_UP, ROAD_RIGHT, ROAD_DOWN, ROAD_LEFT):
        if _connected(mask, direction):
            _draw_arm_tracks(surface, direction)
    pygame.draw.circle(surface, ROAD_COMPACTED_COLOR, (10, 10), 5)
    pygame.draw.circle(surface, ROAD_LIGHT_PATCH_COLOR, (10, 10), 3)


def _draw_isolated_tracks(surface):
    pygame.draw.ellipse(surface, ROAD_LIGHT_PATCH_COLOR, (4, 3, 12, 14))
    pygame.draw.line(surface, ROAD_TRACK_COLOR, (7, 5), (7, 15), ROAD_TRACK_WIDTH)
    pygame.draw.line(surface, ROAD_TRACK_COLOR, (13, 5), (13, 15), ROAD_TRACK_WIDTH)


def _draw_tracks(surface, mask):
    connection_count = mask.bit_count()
    if connection_count == 0:
        _draw_isolated_tracks(surface)
    elif connection_count == 1:
        _draw_dead_end_tracks(surface, mask)
    elif connection_count >= 3:
        _draw_junction_tracks(surface, mask)
    elif mask == ROAD_LEFT | ROAD_RIGHT:
        _draw_horizontal_tracks(surface)
    elif mask == ROAD_UP | ROAD_DOWN:
        _draw_vertical_tracks(surface)
    else:
        _draw_corner_tracks(surface, mask)


def _draw_road_edge_details(surface, mask, variant):
    for index in range(3):
        value = _stable_value(variant, mask, index)
        x = 3 + value % (TILE_SIZE - 6)
        y = 3 + (value // 17) % (TILE_SIZE - 6)
        color = ROAD_DARK_PATCH_COLOR if index % 2 == 0 else ROAD_LIGHT_PATCH_COLOR
        pygame.draw.circle(surface, color, (x, y), 1 + (value % 2))
    stone_value = _stable_value(variant, mask, 41)
    pygame.draw.circle(
        surface, ROAD_STONE_COLOR,
        (4 + stone_value % 12, 4 + (stone_value // 13) % 12), 1,
    )

    open_edges = [
        direction for direction in (ROAD_UP, ROAD_RIGHT, ROAD_DOWN, ROAD_LEFT)
        if not _connected(mask, direction)
    ]
    if open_edges:
        edge = open_edges[variant % len(open_edges)]
        position = 4 + (_stable_value(variant, mask, 73) % 12)
        if edge == ROAD_UP:
            point = (position, 1)
        elif edge == ROAD_RIGHT:
            point = (TILE_SIZE - 2, position)
        elif edge == ROAD_DOWN:
            point = (position, TILE_SIZE - 2)
        else:
            point = (1, position)
        pygame.draw.circle(surface, ROAD_GRASS_DETAIL_COLOR, point, 1)


def _create_road_surface(mask, variant):
    surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
    _draw_road_base(surface, mask, variant)
    _draw_tracks(surface, mask)
    _draw_road_edge_details(surface, mask, variant)
    return surface


def get_road_surface(mask, row, col):
    variant = _stable_value(row, col) % ROAD_TEXTURE_VARIANTS
    key = mask, variant
    surface = _ROAD_SURFACE_CACHE.get(key)
    if surface is None:
        surface = _create_road_surface(mask, variant)
        _ROAD_SURFACE_CACHE[key] = surface
    return surface


def draw_road_tile(screen, world, row, col):
    mask = get_road_neighbor_mask(world, row, col)
    screen.blit(
        get_road_surface(mask, row, col),
        world_to_screen(col * TILE_SIZE, row * TILE_SIZE),
    )


def clear_road_render_cache():
    _ROAD_SURFACE_CACHE.clear()
