"""Compact, non-interactive overview of the entire farm and camera viewport."""
import pygame

from constants import GRASS, ROAD, FIELD, BUILDING
from screen_layout import get_play_area_rect


TILE_COLORS = {GRASS: (91, 143, 70), ROAD: (165, 145, 104),
               FIELD: (139, 106, 62), BUILDING: (105, 111, 105)}
BUILDING_COLORS = {"farmhouse": (184, 76, 43), "pond": (66, 146, 169),
                   "orchard": (45, 112, 52), "animal_pen": (155, 125, 74)}


def get_minimap_rect(world):
    area = get_play_area_rect()
    rows = len(world)
    cols = len(world[0]) if rows else 0
    if not rows or not cols or area.width < 80 or area.height < 80:
        return pygame.Rect(0, 0, 0, 0)
    scale = min(220 / cols, 176 / rows,
                (area.width - 24) / cols, (area.height - 24) / rows)
    rect = pygame.Rect(0, 0, max(1, round(cols * scale)),
                       max(1, round(rows * scale)))
    rect.bottomright = (area.right - 12, area.bottom - 12)
    return rect


def get_viewport_rect(rect, camera):
    if not camera.world_width or not camera.world_height:
        return pygame.Rect(rect.topleft, (0, 0))
    sx = rect.width / camera.world_width
    sy = rect.height / camera.world_height
    left = rect.left + round(camera.camera_x * sx)
    top = rect.top + round(camera.camera_y * sy)
    right = rect.left + round((camera.camera_x + camera.viewport_width) * sx)
    bottom = rect.top + round((camera.camera_y + camera.viewport_height) * sy)
    return pygame.Rect(left, top, right - left, bottom - top).clip(rect)


def draw_minimap(screen, world, buildings, camera):
    rect = get_minimap_rect(world)
    if not rect.width:
        return
    # One pixel per tile keeps the overview cheap and independent of sprites.
    overview = pygame.Surface((len(world[0]), len(world)))
    for row, tiles in enumerate(world):
        for col, tile in enumerate(tiles):
            overview.set_at((col, row), TILE_COLORS.get(tile, TILE_COLORS[GRASS]))
    for building in buildings:
        pygame.draw.rect(overview, BUILDING_COLORS.get(building["type"],
                         TILE_COLORS[BUILDING]),
                         (building["col"], building["row"],
                          building["width"], building["height"]))
    pygame.draw.rect(screen, (32, 37, 30), rect.inflate(6, 6))
    screen.blit(pygame.transform.scale(overview, rect.size), rect)
    pygame.draw.rect(screen, (255, 244, 162), get_viewport_rect(rect, camera), 2)
