"""Read-only presentation helpers for real garage parking slots."""
from math import ceil, sqrt

import pygame
from buildings import get_garage_parking_position


PARKING_SLOT_SIZE = 36
PARKING_SLOT_GAP = 4


def parking_view_height(capacity):
    columns = max(1, ceil(sqrt(capacity)))
    rows = max(1, ceil(capacity / columns))
    return rows * (PARKING_SLOT_SIZE + PARKING_SLOT_GAP) + PARKING_SLOT_GAP


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
    """Compact square bays centered in the available view, in slot-ID order."""
    columns = max(1, ceil(sqrt(capacity)))
    rows = max(1, ceil(capacity / columns))
    gap = PARKING_SLOT_GAP
    size = max(1, min(PARKING_SLOT_SIZE,
                     (rect.width - (columns + 1) * gap) // columns,
                     (rect.height - (rows + 1) * gap) // rows))
    left = rect.centerx - (columns * size + (columns - 1) * gap) // 2
    top = rect.centery - (rows * size + (rows - 1) * gap) // 2
    return [pygame.Rect(
        left + (index % columns) * (size + gap),
        top + (index // columns) * (size + gap),
        size, size,
    ) for index in range(capacity)]


def parked_sprite(asset):
    """Reuse the exact cached world sprite without changing position or facing."""
    getter = getattr(asset, "_get_vehicle_sprite", None)
    return getter() if getter else asset._get_sprite()
