"""Small cached environment primitives; no world or save-state ownership."""
from functools import lru_cache

import pygame

from constants import TILE_SIZE
from screen_layout import world_to_screen


ENVIRONMENT_SHADOW = (48, 56, 45, 64)
FENCE_COLOR = (112, 72, 38)
FENCE_LIGHT = (142, 104, 65)
FENCE_PADDING = 2


@lru_cache(maxsize=16)
def _fence_tile(mask):
    """Bake short upper-right shadows and two-pixel timber once per mask."""
    surface = pygame.Surface((TILE_SIZE + 4, TILE_SIZE + 4), pygame.SRCALPHA)
    p, end = FENCE_PADDING, FENCE_PADDING + TILE_SIZE
    edges = (((p, p), (end, p)), ((end, p), (end, end)),
             ((p, end), (end, end)), ((p, p), (p, end)))
    for bit, (start, stop) in enumerate(edges):
        if mask & (1 << bit):
            pygame.draw.line(surface, ENVIRONMENT_SHADOW,
                             (start[0] + 1, start[1] - 1),
                             (stop[0] + 1, stop[1] - 1), 2)
    for bit, (start, stop) in enumerate(edges):
        if mask & (1 << bit):
            pygame.draw.line(surface, FENCE_COLOR, start, stop, 2)
            # Sparse material light; leave the actual boundary easy to read.
            if bit == 2:
                pygame.draw.line(surface, FENCE_LIGHT, (p + 3, end + 1), (end - 3, end + 1))
            elif bit == 3:
                pygame.draw.line(surface, FENCE_LIGHT, (p - 1, p + 3), (p - 1, end - 3))
    return surface


@lru_cache(maxsize=8)
def _boundary_tiles(tiles):
    result = []
    for row, col in sorted(tiles):
        mask = sum(1 << bit for bit, (dr, dc) in enumerate(
            ((-1, 0), (0, 1), (1, 0), (0, -1)))
            if (row + dr, col + dc) not in tiles)
        if mask:
            result.append((row, col, mask))
    return tuple(result)


def draw_area_fence(screen, area_tiles):
    """Only the outer boundary survives merging; layout changes invalidate by value."""
    clip = screen.get_clip()
    for row, col, mask in _boundary_tiles(frozenset(area_tiles)):
        x, y = world_to_screen(col * TILE_SIZE, row * TILE_SIZE)
        rect = pygame.Rect(round(x) - FENCE_PADDING, round(y) - FENCE_PADDING,
                           TILE_SIZE + 4, TILE_SIZE + 4)
        if clip.colliderect(rect):
            screen.blit(_fence_tile(mask), rect)
