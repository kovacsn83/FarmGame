from dataclasses import dataclass

from constants import GRASS, ROAD, ROAD_BUILD_COST
from game_logger import log
from money_format import format_money


ROAD_DRAG_AXIS_HORIZONTAL = "horizontal"
ROAD_DRAG_AXIS_VERTICAL = "vertical"
ROAD_DRAG_LOCK_THRESHOLD_TILES = 1


def calculate_road_tiles(start_tile, end_tile, axis=None):
    """Egy kezdő- és végpont között egyenes, zárt csempelista készül."""
    start_row, start_col = start_tile
    end_row, end_col = end_tile
    if axis is None:
        col_distance = abs(end_col - start_col)
        row_distance = abs(end_row - start_row)
        axis = (
            ROAD_DRAG_AXIS_HORIZONTAL
            if col_distance >= row_distance
            else ROAD_DRAG_AXIS_VERTICAL
        )

    if axis == ROAD_DRAG_AXIS_HORIZONTAL:
        first_col, last_col = sorted((start_col, end_col))
        return [(start_row, col) for col in range(first_col, last_col + 1)]

    first_row, last_row = sorted((start_row, end_row))
    return [(row, start_col) for row in range(first_row, last_row + 1)]


def is_valid_road_tile(world, row, col):
    """A meglévő út átjárható, új út pedig kizárólag füves mezőre kerülhet."""
    return (
        0 <= row < len(world)
        and 0 <= col < len(world[row])
        and world[row][col] in (GRASS, ROAD)
    )


def validate_road_segment(world, tiles):
    """Visszaadja az új és a tiltott csempéket, egyetlen validációs pontként."""
    new_tiles = []
    invalid_tiles = []
    for row, col in tiles:
        if not is_valid_road_tile(world, row, col):
            invalid_tiles.append((row, col))
        elif world[row][col] == GRASS:
            new_tiles.append((row, col))
    return new_tiles, invalid_tiles


def build_road_segment(world, tiles, economy, road_built_handler=None):
    """A teljes útszakaszt atomi műveletként ellenőrzi és építi meg."""
    new_tiles, invalid_tiles = validate_road_segment(world, tiles)
    if invalid_tiles:
        log("Az útszakasz tiltott területen halad át.", "Road")
        return False, 0, 0.0

    total_cost = len(new_tiles) * ROAD_BUILD_COST
    if not economy.can_build(total_cost):
        return False, 0, total_cost
    if not new_tiles:
        return True, 0, 0.0
    if not economy.spend(total_cost):
        return False, 0, total_cost

    for row, col in new_tiles:
        world[row][col] = ROAD
    if road_built_handler is not None:
        road_built_handler(len(new_tiles))
    log(
        f"{len(new_tiles)} új út csempe megépítve. "
        f"Költség: {format_money(total_cost)}.",
        "Road",
    )
    return True, len(new_tiles), total_cost


@dataclass
class RoadDragState:
    """Az egyetlen folyamatban lévő, irányzárral kezelt úthúzást tárolja."""

    active: bool = False
    start_tile: tuple | None = None
    end_tile: tuple | None = None
    axis: str | None = None

    def begin(self, tile):
        self.active = True
        self.start_tile = tuple(tile)
        self.end_tile = tuple(tile)
        self.axis = None

    def update(self, tile):
        if not self.active:
            return False
        self.end_tile = tuple(tile)
        if self.axis is None:
            start_row, start_col = self.start_tile
            end_row, end_col = self.end_tile
            col_distance = abs(end_col - start_col)
            row_distance = abs(end_row - start_row)
            if max(col_distance, row_distance) >= ROAD_DRAG_LOCK_THRESHOLD_TILES:
                self.axis = (
                    ROAD_DRAG_AXIS_HORIZONTAL
                    if col_distance >= row_distance
                    else ROAD_DRAG_AXIS_VERTICAL
                )
        return True

    @property
    def tiles(self):
        if not self.active or self.start_tile is None or self.end_tile is None:
            return []
        return calculate_road_tiles(self.start_tile, self.end_tile, self.axis)

    def cancel(self):
        self.active = False
        self.start_tile = None
        self.end_tile = None
        self.axis = None
