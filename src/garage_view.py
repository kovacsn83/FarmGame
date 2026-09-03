"""Read-only presentation helpers for real garage parking slots."""
from math import ceil

import pygame
from buildings import get_garage_parking_position
from world import tile_to_world_center


PARKING_SLOT_SIZE = 36
PARKING_SLOT_GAP = 4


def parking_view_height(capacity):
    columns = 2 if capacity <= 4 else 4
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


def is_world_visible(asset):
    """Reconstruct visibility from saved movement state; never alter simulation."""
    if getattr(asset, "is_attached", False):
        return is_world_visible(asset.attached_to)
    if asset.world_x is None or asset.world_y is None:
        return False
    if is_parked_in_garage(asset):
        return False
    if (getattr(asset, "parking_building_type", None) == "garage"
            and getattr(asset, "state", None) in ("leaving_parking", "entering_parking")):
        if asset.row is None or asset.col is None:
            return False
        # row/col identifies the actual departure/arrival road even if home
        # was reassigned by compaction while the vehicle was travelling.
        road_position = tile_to_world_center(asset.row, asset.col)
        return all(abs(actual - expected) < 0.001
                   for actual, expected in zip((asset.world_x, asset.world_y), road_position))
    return True


def parking_slot_rects(rect, capacity):
    """Compact square bays centered in the available view, in slot-ID order."""
    columns = 2 if capacity <= 4 else 4
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
