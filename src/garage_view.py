"""Read-only presentation helpers for real garage parking slots."""
from math import ceil, sqrt

import pygame
from buildings import get_garage_parking_position


def is_parked_in_garage(asset, garage=None):
    assigned = asset.assigned_parking_building
    if (assigned is None or assigned.get("type") != "garage"
            or (garage is not None and assigned is not garage)
            or asset.parking_slot_id is None):
        return False
    if getattr(asset, "is_attached", False):
        return False
    if hasattr(asset, "is_idle") and not asset.is_idle:
        return False
    position = get_garage_parking_position(assigned, asset.parking_slot_id)
    return all(actual is not None and abs(actual - expected) < 0.01
               for actual, expected in zip((asset.world_x, asset.world_y), position))


def parking_slot_rects(rect, capacity):
    """Capacity-driven grid; slot IDs, never vehicle list order, define positions."""
    columns = max(1, ceil(sqrt(capacity)))
    rows = max(1, ceil(capacity / columns))
    return [pygame.Rect(
        rect.x + (index % columns) * rect.width // columns + 4,
        rect.y + (index // columns) * rect.height // rows + 4,
        rect.width // columns - 8, rect.height // rows - 8,
    ) for index in range(capacity)]


def parked_sprite(asset):
    """Reuse the exact cached world sprite without changing position or facing."""
    getter = getattr(asset, "_get_vehicle_sprite", None)
    return getter() if getter else asset._get_sprite()
