from collections import deque
from dataclasses import dataclass

import pygame

from animal_troughs import fill_group_trough
from constants import GRID_COLS, GRID_ROWS, ROAD, TILE_SIZE
from buildings import (
    BUILDING_TYPES, get_garage_parking_position, get_orchard_groups,
)
from crops import CROPS
from fields import (
    complete_harvest, fertilize_crop, plant_crop, spray_crop, water_crop,
)
from feed_supply import (
    deliver_feed_cargo, prepare_feed_supply, return_feed_cargo,
)
from game_logger import log
from inventory import get_inventory_item_name
from orchards import complete_tree_harvest, get_tree_in_slot
from processing import receive_processing_delivery, refund_processing_delivery
from world import tile_to_world_center
from screen_layout import world_to_screen
from vehicle_types import VEHICLE_TYPE_DEFINITIONS, VehicleType


TRACTOR_IDLE = "idle"
TRACTOR_MOVING_TO_FIELD = "moving_to_field"
TRACTOR_WORKING_FIELD = "working_field"
TRACTOR_LEAVING_FIELD = "leaving_field"
TRACTOR_MOVING_TO_NEXT_FIELD = "moving_to_next_field"
TRACTOR_RETURNING_HOME = "returning_home"
TRACTOR_ENTERING_PARKING = "entering_parking"
TRACTOR_LEAVING_PARKING = "leaving_parking"
TRACTOR_RELOCATING_TO_PARKING = "relocating_to_parking"
TRACTOR_AWAITING_ASSIGNMENT = "awaiting_assignment"
TRACTOR_MOVING_TO_POND = "moving_to_pond"
TRACTOR_FILLING_WATER = "filling_water"
TRACTOR_MOVING_TO_IMPLEMENT = "moving_to_implement"
TRACTOR_RETURNING_IMPLEMENT = "returning_implement"
TRACTOR_MOVING_TO_SUPPLY_SOURCE = "moving_to_supply_source"
TRACTOR_LOADING_SUPPLY = "loading_supply"
TRACTOR_MOVING_TO_TROUGH = "moving_to_trough"
TRACTOR_UNLOADING_SUPPLY = "unloading_supply"
TRACTOR_SELECTING_NEXT_TASK = "selecting_next_task"
TRACTOR_RETURNING_FEED_CARGO = "returning_feed_cargo"
TRACTOR_WORKING_ORCHARD = "working_orchard"

TRACTOR_STEP_INTERVAL_MS = 80
MAX_TRACTOR_STEPS_PER_UPDATE = 100
WATER_FILL_DURATION_MS = 800
FEED_LOAD_DURATION_MS = 1000
FEED_UNLOAD_DURATION_MS = 1000
WATER_UNLOAD_DURATION_MS = 800
ORCHARD_HARVEST_DURATION_MS = 1000
TRACTOR_COLOR = (220, 35, 35)
TRACTOR_BORDER_COLOR = (120, 20, 20)
TRACTOR_CAB_COLOR = (62, 68, 72)
TRACTOR_RIM_COLOR = (185, 190, 192)
COMBINE_BODY_COLOR = (38, 105, 55)
COMBINE_BODY_BORDER_COLOR = (25, 70, 38)
COMBINE_WHEEL_COLOR = (240, 198, 35)
COMBINE_CAB_COLOR = (65, 72, 72)
COMBINE_HEADER_COLOR = (190, 155, 30)
FRUIT_HARVESTER_BODY_COLOR = (222, 176, 43)
FRUIT_HARVESTER_BODY_DARK = (154, 111, 28)
FRUIT_HARVESTER_CAB_COLOR = (70, 78, 78)
FRUIT_HARVESTER_ARM_COLOR = (195, 145, 35)
FRUIT_HARVESTER_RIM_COLOR = (172, 176, 174)
WATER_TANK_BODY_COLOR = (174, 184, 187)
WATER_TANK_BODY_LIGHT = (211, 218, 219)
WATER_TANK_BODY_DARK = (105, 116, 120)
WATER_TANK_RIM_COLOR = (164, 169, 170)
WATER_TANK_FENDER_COLOR = (92, 100, 103)
TRAILER_WALL_COLOR = (104, 78, 54)
TRAILER_WALL_LIGHT = (137, 105, 72)
TRAILER_BED_COLOR = (166, 139, 101)
TRAILER_BORDER_COLOR = (58, 49, 40)
TRAILER_RIM_COLOR = (160, 164, 162)
TRAILER_ALFALFA_COLOR = (76, 132, 66)
TRAILER_CORN_COLOR = (190, 153, 54)
VEHICLE_TIRE_COLOR = (25, 25, 25)
VEHICLE_SHADOW_COLOR = (35, 35, 35, 55)
VEHICLE_SPRITE_SIZE = 24
VEHICLE_ROTATION_ANGLES = {
    "up": 0,
    "right": -90,
    "down": 180,
    "left": 90,
}
_VEHICLE_SPRITE_CACHE = {}
_VEHICLE_SHADOW_CACHE = {}

# A rögzített sorrend minden azonos pályán ugyanazt a BFS-útvonalat adja.
NEIGHBOR_OFFSETS = ((-1, 0), (0, 1), (1, 0), (0, -1))
PARKING_BUILDING_PRIORITY = ("garage", "farmhouse")
TASK_PLANTING = "plant"
TASK_FERTILIZING = "fertilize"
TASK_HARVESTING = "harvest"
TASK_WATERING = "watering"
TASK_SPRAYING = "spraying"
TASK_SUPPLY_FEED = "supply_feed"
TASK_SUPPLY_WATER = "supply_water"
TASK_ORCHARD_HARVEST = "orchard_harvest"
TASK_PROCESSING_SUPPLY = "processing_supply"


@dataclass
class FieldTask:
    """A közös járműsor egy mezőmunkáját és erőforrását tárolja."""

    field: dict
    crop: str | None = None
    payment: dict | None = None
    task_type: str = TASK_PLANTING
    buildings: list | None = None
    resource_reserved: bool = False
    resource_amount: int = 0
    entry_tile: tuple | None = None
    connection_road: tuple | None = None
    pond: dict | None = None
    implement: object | None = None
    required_vehicle_id: int | None = None
    route_to_implement: list | None = None
    route_to_source: list | None = None
    route_to_pond: list | None = None
    route_pond_to_field: list | None = None
    return_route: list | None = None
    route_implement_to_home: list | None = None
    implement_connection_road: tuple | None = None
    pond_connection_road: tuple | None = None
    remaining_wait_ms: int = 0
    source_building: dict | None = None
    target_group: list | None = None
    animals: list | None = None
    trough_type: str | None = None
    route_source_to_target: list | None = None
    loading_duration_ms: int = 0
    unloading_duration_ms: int = 0
    required_implement_type: VehicleType | None = None
    creation_order: int = 0
    status: str = "waiting"
    source_type: str | None = None
    manually_initiated: bool = True
    # A jelenlegi prototípusban egy munkamenet rakománya korlátlan. Ezek a
    # mezők később a valódi pótkocsi- és víztartály-kapacitást fogadják.
    capacity_limited: bool = False
    remaining_payload: int | None = None
    warehouse_amount: int = 0
    purchased_amount: int = 0
    purchase_cost: float = 0.0
    tree_slot: int | None = None
    tree_type: str | None = None
    orchard_entry_tile: tuple | None = None
    harvest_approach_position: tuple | None = None
    orchard_internal_path: list | None = None
    cargo_type: str | None = None


# Régi külső kiegészítések kompatibilitási típusa; az új kód FieldTaskot használ.
PlantingTask = FieldTask


def _is_inside(world, row, col):
    return (0 <= row < len(world) and 0 <= col < len(world[row]))


def find_road_path(world, start, target):
    """Négyirányú, kizárólag ROAD mezőkön haladó BFS útvonalat keres."""
    if start is None or target is None:
        return None
    if start == target:
        return [start] if world[start[0]][start[1]] == ROAD else None
    if (world[start[0]][start[1]] != ROAD
            or world[target[0]][target[1]] != ROAD):
        return None

    queue = deque([start])
    previous = {start: None}
    while queue:
        row, col = queue.popleft()
        for row_offset, col_offset in NEIGHBOR_OFFSETS:
            neighbor = row + row_offset, col + col_offset
            neighbor_row, neighbor_col = neighbor
            if (not _is_inside(world, neighbor_row, neighbor_col)
                    or neighbor in previous
                    or world[neighbor_row][neighbor_col] != ROAD):
                continue
            previous[neighbor] = (row, col)
            if neighbor == target:
                path = [neighbor]
                while previous[path[-1]] is not None:
                    path.append(previous[path[-1]])
                path.reverse()
                return path
            queue.append(neighbor)
    return None


def iter_perimeter_connections(area, world=None):
    """Rögzített kerületi sorrendben adja vissza a külső és belső mezőpárokat."""
    top = area["row"]
    left = area["col"]
    bottom = top + area["height"] - 1
    right = left + area["width"] - 1

    if top > 0:
        for col in range(left, right + 1):
            yield (top - 1, col), (top, col)
    world_rows = len(world) if world is not None else GRID_ROWS
    world_cols = len(world[0]) if world else GRID_COLS
    if right + 1 < world_cols:
        for row in range(top, bottom + 1):
            yield (row, right + 1), (row, right)
    if bottom + 1 < world_rows:
        for col in range(right, left - 1, -1):
            yield (bottom + 1, col), (bottom, col)
    if left > 0:
        for row in range(bottom, top - 1, -1):
            yield (row, left - 1), (row, left)


def find_building_parking(world, building):
    """Bármely épület első, determinisztikus kerületi ROAD mezőjét megkeresi."""
    if building is None:
        return None
    for road_tile, _ in iter_perimeter_connections(building, world):
        row, col = road_tile
        if world[row][col] == ROAD:
            return road_tile
    return None


def find_building_route(world, start, building):
    """A kezdő úttól egy épület legközelebbi elérhető kerületi útjáig vezet."""
    best_route = None
    best_road_tile = None
    if building is None:
        return None, None
    for road_tile, _ in iter_perimeter_connections(building, world):
        row, col = road_tile
        if world[row][col] != ROAD:
            continue
        route = find_road_path(world, start, road_tile)
        if route is not None and (
                best_route is None or len(route) < len(best_route)):
            best_route = route
            best_road_tile = road_tile
    return best_route, best_road_tile


def find_preferred_parking(world, buildings, excluded_building=None):
    """A központi prioritás alapján kiválasztja a traktor parkolóépületét."""
    parking_building = next(
        (
            building
            for building_type in PARKING_BUILDING_PRIORITY
            for building in buildings
            if (building["type"] == building_type
                and building is not excluded_building)
        ),
        None,
    )
    if parking_building is None:
        return None, None
    return parking_building, find_building_parking(world, parking_building)


def find_field_route(world, start, field):
    """A legrövidebb elérhető kerületi ROAD mezőt és belépési mezőt keresi."""
    best_route = None
    best_entry = None
    has_road_connection = False
    for road_tile, field_tile in iter_perimeter_connections(field, world):
        row, col = road_tile
        if world[row][col] != ROAD:
            continue
        has_road_connection = True
        route = find_road_path(world, start, road_tile)
        if route is not None and (
                best_route is None or len(route) < len(best_route)):
            best_route = route
            best_entry = field_tile
    return best_route, best_entry, has_road_connection


def create_field_work_path(field, entry_tile):
    """Az érkezési mezőtől induló kígyózó munkapályát készít."""
    top = field["row"]
    left = field["col"]
    width = field["width"]
    height = field["height"]

    # A támogatott méretek párosak. Ez a kígyózó kör bármely kerületi
    # mezőnél felnyitható, és minden tile-t pontosan egyszer érint.
    cycle = [(top + row, left) for row in range(height)]
    for row in range(height - 1, -1, -1):
        columns = (
            range(1, width) if (height - 1 - row) % 2 == 0
            else range(width - 1, 0, -1)
        )
        cycle.extend((top + row, left + col) for col in columns)

    start_index = cycle.index(entry_tile)
    return cycle[start_index:] + cycle[:start_index]


def _orchard_group_tiles(group):
    """Az összefüggő Gyümölcsös-rendszer minden belső csempéjét adja."""
    return {
        (row, col)
        for orchard in group
        for row in range(orchard["row"], orchard["row"] + orchard["height"])
        for col in range(orchard["col"], orchard["col"] + orchard["width"])
    }


def _orchard_tree_centers(group):
    """A gép számára tiltott fatörzs-középpontokat gyűjti össze."""
    return {
        (tree["row"] + 1, tree["col"] + 1)
        for orchard in group
        for tree in orchard.get("trees", [])
    }


def _find_tile_path(start, targets, allowed_tiles, blocked_tiles):
    """Rövid belső BFS-útvonalat keres a Gyümölcsös járható csempéin."""
    targets = set(targets)
    if start not in allowed_tiles or start in blocked_tiles or not targets:
        return None
    queue = deque([start])
    previous = {start: None}
    while queue:
        tile = queue.popleft()
        if tile in targets:
            path = [tile]
            while previous[path[-1]] is not None:
                path.append(previous[path[-1]])
            path.reverse()
            return path
        row, col = tile
        for row_offset, col_offset in NEIGHBOR_OFFSETS:
            neighbor = row + row_offset, col + col_offset
            if (
                neighbor not in allowed_tiles
                or neighbor in blocked_tiles
                or neighbor in previous
            ):
                continue
            previous[neighbor] = tile
            queue.append(neighbor)
    return None


def _find_orchard_recovery_route(world, buildings, start, parking_tile):
    """Sérült kijárati állapotnál biztonságos útvonalat keres a közútig.

    A normál szüreti munkamenet eltárolja a pontos gyümölcsös-kijáratot. Ez a
    helyreállító ág csak akkor fut, ha ez az adat hiányzik (például egy korábbi,
    hibás mentésben). A fatörzsek itt is tiltott csempék maradnak.
    """
    if start is None or parking_tile is None or buildings is None:
        return None
    group = next(
        (
            group for group in get_orchard_groups(buildings)
            if any(
                orchard["row"] <= start[0] < orchard["row"] + orchard["height"]
                and orchard["col"] <= start[1] < orchard["col"] + orchard["width"]
                for orchard in group
            )
        ),
        None,
    )
    if group is None:
        return None
    allowed = _orchard_group_tiles(group)
    blocked = _orchard_tree_centers(group)
    candidates = []
    for orchard in group:
        for road_tile, entry_tile in iter_perimeter_connections(orchard, world):
            road_row, road_col = road_tile
            if world[road_row][road_col] != ROAD or entry_tile in blocked:
                continue
            inside_route = _find_tile_path(start, {entry_tile}, allowed, blocked)
            road_route = find_road_path(world, road_tile, parking_tile)
            if inside_route is not None and road_route is not None:
                candidates.append(inside_route + road_route)
    return min(candidates, key=len) if candidates else None


def _orchard_approach_path(group, orchard, tree_slot, start):
    """A jelenlegi helytől a konkrét fa legközelebbi biztonságos oldaláig vezet."""
    tree = get_tree_in_slot(orchard, tree_slot)
    if tree is None:
        return None
    allowed = _orchard_group_tiles(group)
    blocked = _orchard_tree_centers(group)
    center = tree["row"] + 1, tree["col"] + 1
    approaches = {
        (center[0] + row_offset, center[1] + col_offset)
        for row_offset, col_offset in NEIGHBOR_OFFSETS
        if (
            (center[0] + row_offset, center[1] + col_offset) in allowed
            and (center[0] + row_offset, center[1] + col_offset) not in blocked
        )
    }
    return _find_tile_path(start, approaches, allowed, blocked)


class Vehicle:
    """Egy jármű közös állapotát, útvonalát és parkolását kezeli."""

    def __init__(self, vehicle_id=1, vehicle_type=VehicleType.TRACTOR):
        self.vehicle_id = vehicle_id
        self.vehicle_type = vehicle_type
        self.assigned_parking_building = None
        self.parking_slot_id = None
        self.row = None
        self.col = None
        self.world_x = None
        self.world_y = None
        self.path = []
        self.next_path_index = 0
        self.state = TRACTOR_IDLE
        self.current_task = None
        self.movement_accumulator_ms = 0.0
        self.last_update_ticks = None
        self._last_time_speed = None
        self.parking_tile = None
        self.parking_building_type = None
        self.parking_world_position = None
        self._state_after_parking_exit = None
        self._parking_arrival_reason = None
        self._unreachable_parking_building = None
        self.protected_road_tiles = set()
        # Kizárólag vizuális állapot, a mozgási logikát nem befolyásolja.
        self.facing_direction = "up"
        # Általános kapcsolódási pont a későbbi vontatott munkagépekhez.
        self.attached_implement = None
        # Gyümölcsösön belüli munka után ezen a kapun tér vissza az útra.
        self._orchard_exit_path = None
        self._orchard_exit_road = None

    def _find_preferred_parking(self, world, buildings):
        if self.assigned_parking_building in buildings:
            building = self.assigned_parking_building
            return building, find_building_parking(world, building)
        return find_preferred_parking(
            world, buildings, self._unreachable_parking_building,
        )

    def get_parking(self, world, buildings):
        """A traktor saját, aktuálisan érvényes parkolóhelyét adja vissza."""
        return self._find_preferred_parking(world, buildings)

    def _set_tile_position(self, row, col):
        """Egy helyen tartja szinkronban a játékmeneti és grafikai pozíciót."""
        if self.row is not None and self.col is not None:
            self._update_facing(row - self.row, col - self.col)
        self.row = row
        self.col = col
        self.world_x, self.world_y = tile_to_world_center(row, col)

    def _clear_position(self):
        self.row = None
        self.col = None
        self.world_x = None
        self.world_y = None

    def _set_world_position(self, world_x, world_y):
        """A grafikai pozíciót a játékmeneti tile módosítása nélkül állítja."""
        self.world_x = float(world_x)
        self.world_y = float(world_y)

    def _parking_world_position(self, parking_building, parking_tile):
        if parking_building is None or parking_tile is None:
            return None
        if parking_building["type"] == "garage":
            slot_id = self.parking_slot_id if self.parking_slot_id is not None else 0
            return get_garage_parking_position(parking_building, slot_id)
        return tile_to_world_center(*parking_tile)

    @staticmethod
    def _positions_match(first, second, tolerance=0.001):
        if first is None or second is None:
            return first is second
        return (
            abs(first[0] - second[0]) <= tolerance
            and abs(first[1] - second[1]) <= tolerance
        )

    def _move_world_toward(self, target, max_distance=TILE_SIZE):
        """Egy időzített lépést tesz a világkoordinátás cél felé."""
        delta_x = target[0] - self.world_x
        delta_y = target[1] - self.world_y
        self._update_facing(delta_y, delta_x)
        distance = (delta_x * delta_x + delta_y * delta_y) ** 0.5
        if distance <= max_distance:
            self._set_world_position(*target)
            return True
        scale = max_distance / distance
        self._set_world_position(
            self.world_x + delta_x * scale,
            self.world_y + delta_y * scale,
        )
        return False

    def _update_facing(self, row_delta, col_delta):
        """A legutóbbi elmozdulásból meghatározza a rajzolási irányt."""
        if abs(col_delta) > abs(row_delta):
            if col_delta:
                self.facing_direction = "right" if col_delta > 0 else "left"
        elif row_delta:
            self.facing_direction = "down" if row_delta > 0 else "up"

    @property
    def is_idle(self):
        return (
            self.state == TRACTOR_IDLE
            and self.current_task is None
        )

    @property
    def can_accept_task(self):
        """Parkoló vagy hazafelé tartó, feladat nélküli jármű munkába állhat."""
        return (
            self.current_task is None
            and self.attached_implement is None
            and self.state in (
                TRACTOR_IDLE, TRACTOR_RETURNING_HOME,
                TRACTOR_AWAITING_ASSIGNMENT,
            )
        )

    def supports_task(self, task_type):
        """Jelzi, hogy a járműtípus végrehajthatja-e a feladattípust."""
        definition = VEHICLE_TYPE_DEFINITIONS[self.vehicle_type]
        return task_type in definition.get("supported_tasks", ())

    @property
    def target_field(self):
        """Kompatibilis, csak olvasható hozzáférés az aktív célmezőhöz."""
        return self.current_task.field if self.current_task is not None else None

    @property
    def selected_crop(self):
        return self.current_task.crop if self.current_task is not None else None

    def ensure_idle_position(self, world, buildings):
        """Új játék vagy betöltés után a preferált parkolóba állítja a traktort."""
        if not self.is_idle or self.row is not None:
            return
        parking_building, parking_tile = self._find_preferred_parking(
            world, buildings,
        )
        self.parking_tile = parking_tile
        self.parking_building_type = (
            parking_building["type"] if parking_building is not None else None
        )
        self.parking_world_position = self._parking_world_position(
            parking_building, parking_tile,
        )
        if parking_tile is None:
            self._clear_position()
        else:
            self._set_tile_position(*parking_tile)
            self._set_world_position(*self.parking_world_position)

    def can_save(self, world, buildings):
        """Csak üres sorral és szabályos parkolóhelyen enged mentést."""
        if not self.is_idle:
            return False
        parking_building, parking_tile = self._find_preferred_parking(
            world, buildings,
        )
        if parking_building is None:
            return True
        return (
            parking_tile is not None
            and (self.row, self.col) == parking_tile
            and self._positions_match(
                (self.world_x, self.world_y),
                self._parking_world_position(parking_building, parking_tile),
            )
        )

    def request_parking_relocation(
            self, world, buildings, current_ticks=None,
            parking_building=None, parking_slot_id=0):
        """Sikeres Garázsépítéskor egyszer megkísérli az automatikus átköltözést."""
        vehicle_name = VEHICLE_TYPE_DEFINITIONS[self.vehicle_type]["name"].lower()
        log(f"Garázs megépült. A {vehicle_name} átköltözik.", "Vehicle")
        if parking_building is None:
            parking_building, parking_tile = find_preferred_parking(world, buildings)
        else:
            parking_tile = find_building_parking(world, parking_building)
        if (parking_building is None
                or parking_building["type"] != "garage"
                or parking_tile is None):
            self._print_relocation_error()
            return False

        current_tile = (self.row, self.col)
        if (current_tile[0] is None
                or world[current_tile[0]][current_tile[1]] != ROAD):
            current_tile = self.parking_tile
        route = find_road_path(world, current_tile, parking_tile)
        if route is None:
            self._unreachable_parking_building = parking_building
            self._print_relocation_error()
            return False

        self.assigned_parking_building = parking_building
        self.parking_slot_id = parking_slot_id
        parking_world_position = self._parking_world_position(
            parking_building, parking_tile,
        )
        if parking_world_position is None:
            self._print_relocation_error()
            return False

        self._unreachable_parking_building = None
        if self.current_task is not None or self.state in (
                TRACTOR_MOVING_TO_FIELD,
                TRACTOR_WORKING_FIELD,
                TRACTOR_LEAVING_FIELD,
                TRACTOR_MOVING_TO_NEXT_FIELD,
                TRACTOR_LEAVING_PARKING,
        ):
            # Az aktív munkafolyamat végén a meglévő frissítés már az új
            # elsődleges parkolót választja, ezért az útvonal érintetlen marad.
            return True

        self.parking_tile = parking_tile
        self.parking_building_type = parking_building["type"]
        self.parking_world_position = parking_world_position
        self.path = route
        self.next_path_index = 1
        self.state = TRACTOR_RELOCATING_TO_PARKING
        self.protected_road_tiles = set(route)
        self.protected_road_tiles.add(parking_tile)
        self._parking_arrival_reason = "relocation"
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks
        self.last_update_ticks = now
        self._last_time_speed = None
        log(f"A {vehicle_name} a Garázshoz tart.", "Vehicle")
        return True

    def _print_relocation_error(self):
        vehicle_name = VEHICLE_TYPE_DEFINITIONS[self.vehicle_type]["name"].lower()
        log(
            f"A {vehicle_name} nem tud eljutni a Garázshoz. "
            "Építs összefüggő utat a Garázsig.", "Vehicle",
        )

    def start_planting(
            self, world, buildings, economy, field, crop,
            current_ticks=None):
        """Kompatibilis közvetlen indítás; a közös sort a VehicleManager kezeli."""
        if self._contains_field(field):
            log("Ez a veteményes már traktorfeladatra vár.", "Planting")
            return False
        if field.get("crop") is not None or crop is None:
            return False
        if field.get("vehicle_task_status") is not None:
            log("Ez a veteményes már traktorfeladatra vár.", "Planting")
            return False
        if not economy.can_acquire_seed(buildings, crop):
            economy.report_seed_unavailable(buildings, crop)
            return False

        parking_building, parking_tile = self._find_preferred_parking(
            world, buildings,
        )
        if parking_building is None:
            log("Az ültetéshez Farmház szükséges.", "Planting")
            return False
        if parking_tile is None:
            building_name = BUILDING_TYPES[parking_building["type"]]["name"]
            log(
                f"A traktornak nincs útkapcsolata a {building_name} mellett.",
                "Planting",
            )
            return False

        if self.is_idle and self.row is None:
            self._set_tile_position(*parking_tile)
            self._set_world_position(*self._parking_world_position(
                parking_building, parking_tile,
            ))
        start_tile = (self.row, self.col) if self.is_idle else parking_tile
        road_path, _, has_connection = find_field_route(
            world, start_tile, field,
        )
        if not has_connection:
            log("A veteményes nem érhető el útról.", "Planting")
            return False
        if road_path is None:
            log(
                "A traktor nem talál útvonalat a veteményeshez.",
                "Planting",
            )
            return False

        payment = economy.reserve_seed(buildings, crop)
        if payment is None:
            return False
        task = FieldTask(
            field=field, crop=crop, payment=payment,
            task_type=TASK_PLANTING, buildings=buildings,
        )
        self.parking_tile = parking_tile
        self.parking_building_type = parking_building["type"]
        self.parking_world_position = self._parking_world_position(
            parking_building, parking_tile,
        )
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks

        if not self.can_accept_task or not self._activate_task(
                world, task, start_tile, now, first=self.is_idle):
            economy.refund_seed(payment, crop)
            log(
                "A traktor nem talál útvonalat a veteményeshez.",
                "Planting",
            )
            return False
        log("Ültetési feladat elindítva.", "Planting")
        return True

    def _contains_field(self, field):
        return self.current_task is not None and self.current_task.field is field

    def accept_task(self, world, buildings, task, current_ticks=None):
        """A közös sorból kiosztott feladatot a traktor saját állapotgépére köti."""
        if not self.can_accept_task or not self.supports_task(task.task_type):
            return False
        self._refresh_preferred_parking(world, buildings)
        if self.parking_tile is None:
            return False
        if self.row is None:
            self.ensure_idle_position(world, buildings)
        start_tile = (self.row, self.col)
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks
        was_idle = self.state == TRACTOR_IDLE
        return self._activate_task(
            world, task, start_tile, now, first=was_idle,
        )

    def accept_chained_task(self, task, route, reload_source=False):
        """Felcsatolt vontatmánnyal, új forráslátogatás nélkül folytat munkát."""
        if self.attached_implement is None or route is None:
            return False
        self.current_task = task
        task.status = "active"
        task.field["vehicle_task_status"] = "active"
        task.field["vehicle_task_type"] = task.task_type
        task.field.pop("vehicle_queue_position", None)
        self.path = route
        self.next_path_index = 1
        if reload_source:
            self.state = (
                TRACTOR_MOVING_TO_POND
                if task.task_type == TASK_WATERING
                else TRACTOR_MOVING_TO_SUPPLY_SOURCE
            )
        else:
            self.state = (
                TRACTOR_MOVING_TO_FIELD
                if task.task_type == TASK_WATERING
                else TRACTOR_MOVING_TO_TROUGH
            )
        self.protected_road_tiles.update(route)
        return True

    def finish_implement_session(self):
        """Láncolható feladat hiányában visszaindítja a vontatmányt a helyére."""
        task = self.current_task
        self.path = task.return_route
        self.next_path_index = 1
        self.state = TRACTOR_RETURNING_IMPLEMENT

    def _activate_task(self, world, task, start_road, now, first=False):
        if not self.supports_task(task.task_type):
            return False
        if task.task_type in (
                TASK_SUPPLY_FEED, TASK_SUPPLY_WATER, TASK_PROCESSING_SUPPLY):
            return self._activate_supply_task(task, start_road, now, first)
        if task.task_type == TASK_WATERING:
            return self._activate_watering_task(
                task, start_road, now, first,
            )
        if task.task_type == TASK_ORCHARD_HARVEST:
            return self._activate_orchard_task(
                world, task, start_road, now, first,
            )
        route, entry_tile, has_connection = find_field_route(
            world, start_road, task.field,
        )
        if not has_connection or route is None:
            return False
        return_route = find_road_path(world, route[-1], self.parking_tile)
        if return_route is None:
            return False

        self.current_task = task
        task.status = "active"
        task.entry_tile = entry_tile
        task.connection_road = route[-1]
        task.field["vehicle_task_status"] = "active"
        task.field["vehicle_task_type"] = task.task_type
        task.field.pop("vehicle_queue_position", None)
        self.path = route
        self.next_path_index = 1
        travel_state = (
            TRACTOR_MOVING_TO_FIELD if first or start_road == self.parking_tile
            else TRACTOR_MOVING_TO_NEXT_FIELD
        )
        road_world_position = tile_to_world_center(*start_road)
        if not self._positions_match(
                (self.world_x, self.world_y), road_world_position):
            self.state = TRACTOR_LEAVING_PARKING
            self._state_after_parking_exit = travel_state
        else:
            self.state = travel_state
            self._state_after_parking_exit = None
        if first:
            self.movement_accumulator_ms = 0.0
            self.last_update_ticks = now
            self._last_time_speed = None
        self.protected_road_tiles = set(route) | set(return_route)
        if self.parking_tile is not None:
            self.protected_road_tiles.add(self.parking_tile)
        return True

    def _activate_orchard_task(self, world, task, start_road, now, first):
        """Úton, majd a Gyümölcsös belsejében a konkrét fához irányít."""
        group = next(
            (items for items in get_orchard_groups(task.buildings)
             if task.field in items),
            None,
        )
        if group is None:
            return False
        group_tiles = _orchard_group_tiles(group)
        blocked = _orchard_tree_centers(group)

        if start_road in group_tiles:
            # Azonos összefüggő rendszer következő fájához nem tér vissza
            # az útra vagy a Garázsba, hanem közvetlenül odagurul.
            internal_path = _orchard_approach_path(
                group, task.field, task.tree_slot, start_road,
            )
            if internal_path is None:
                return False
            route = internal_path
            connection_road = self._orchard_exit_road
            entry_tile = (
                self._orchard_exit_path[-2]
                if self._orchard_exit_path and len(self._orchard_exit_path) >= 2
                else start_road
            )
            return_route = None
        else:
            candidates = []
            for orchard in group:
                for road_tile, entry in iter_perimeter_connections(
                        orchard, world):
                    road_row, road_col = road_tile
                    if world[road_row][road_col] != ROAD or entry in blocked:
                        continue
                    road_route = find_road_path(world, start_road, road_tile)
                    if road_route is None:
                        continue
                    inside_route = _orchard_approach_path(
                        group, task.field, task.tree_slot, entry,
                    )
                    if inside_route is None:
                        continue
                    home_route = find_road_path(
                        world, road_tile, self.parking_tile,
                    )
                    if home_route is None:
                        continue
                    candidates.append((
                        len(road_route) + len(inside_route), road_route,
                        inside_route, road_tile, entry, home_route,
                    ))
            if not candidates:
                return False
            (_, road_route, internal_path, connection_road, entry_tile,
             return_route) = min(candidates, key=lambda item: item[0])
            route = road_route + internal_path
        self.current_task = task
        task.status = "active"
        task.connection_road = connection_road
        task.return_route = return_route
        task.orchard_entry_tile = entry_tile
        task.harvest_approach_position = route[-1]
        task.orchard_internal_path = internal_path
        task.field["vehicle_task_status"] = "active"
        task.field["vehicle_task_type"] = task.task_type
        task.field.pop("vehicle_queue_position", None)
        self.path = route
        self.next_path_index = 1
        road_world_position = tile_to_world_center(*start_road)
        if not self._positions_match(
                (self.world_x, self.world_y), road_world_position):
            self.state = TRACTOR_LEAVING_PARKING
            self._state_after_parking_exit = TRACTOR_MOVING_TO_FIELD
        else:
            self.state = TRACTOR_MOVING_TO_FIELD
            self._state_after_parking_exit = None
        if first:
            self.movement_accumulator_ms = 0.0
            self.last_update_ticks = now
            self._last_time_speed = None
        self.protected_road_tiles = set(route) | set(return_route or [])
        # Láncolt szüretnél az eredeti közúti kijárat végig megmarad. Egy
        # pillanatnyi belső újratervezési hiba nem törölheti a már ismert
        # kijáratot, mert arra az utolsó fa után még szükség lesz.
        if connection_road is not None:
            self._orchard_exit_road = connection_road
        exit_inside = _find_tile_path(
            route[-1], {entry_tile}, group_tiles, blocked,
        )
        if exit_inside is not None and self._orchard_exit_road is not None:
            self._orchard_exit_path = exit_inside + [self._orchard_exit_road]
        if self.parking_tile is not None:
            self.protected_road_tiles.add(self.parking_tile)
        return True

    def _activate_watering_task(self, task, start_road, now, first):
        """A tartály felvételével kezdődő locsolási útvonalat aktiválja."""
        if (
            task.required_vehicle_id != self.vehicle_id
            or task.implement is None
            or not task.route_to_implement
            or not task.route_to_pond
            or not task.route_pond_to_field
            or not task.return_route
            or not task.route_implement_to_home
        ):
            return False
        self.current_task = task
        task.status = "active"
        task.field["vehicle_task_status"] = "active"
        task.field["vehicle_task_type"] = task.task_type
        task.field.pop("vehicle_queue_position", None)
        self.path = task.route_to_implement
        self.next_path_index = 1
        travel_state = TRACTOR_MOVING_TO_IMPLEMENT
        road_world_position = tile_to_world_center(*start_road)
        if not self._positions_match(
                (self.world_x, self.world_y), road_world_position):
            self.state = TRACTOR_LEAVING_PARKING
            self._state_after_parking_exit = travel_state
        else:
            self.state = travel_state
            self._state_after_parking_exit = None
        if first:
            self.movement_accumulator_ms = 0.0
            self.last_update_ticks = now
            self._last_time_speed = None
        self.protected_road_tiles = (
            set(task.route_to_implement)
            | set(task.route_to_pond)
            | set(task.route_pond_to_field)
            | set(task.return_route)
            | set(task.route_implement_to_home)
        )
        if self.parking_tile is not None:
            self.protected_road_tiles.add(self.parking_tile)
        log("A Traktor elindult a Locsolótartályért.", "Watering")
        return True

    def _activate_supply_task(self, task, start_road, now, first):
        """A vályúellátást a kijelölt vontatmány felvételével indítja."""
        if (
            task.required_vehicle_id != self.vehicle_id
            or task.implement is None
            or not task.route_to_implement
            or not task.route_to_source
            or not task.route_source_to_target
            or not task.return_route
            or not task.route_implement_to_home
        ):
            return False
        self.current_task = task
        task.field["vehicle_task_status"] = "active"
        task.field["vehicle_task_type"] = task.task_type
        task.field.pop("vehicle_queue_position", None)
        self.path = task.route_to_implement
        self.next_path_index = 1
        road_world_position = tile_to_world_center(*start_road)
        if not self._positions_match(
                (self.world_x, self.world_y), road_world_position):
            self.state = TRACTOR_LEAVING_PARKING
            self._state_after_parking_exit = TRACTOR_MOVING_TO_IMPLEMENT
        else:
            self.state = TRACTOR_MOVING_TO_IMPLEMENT
            self._state_after_parking_exit = None
        if first:
            self.movement_accumulator_ms = 0.0
            self.last_update_ticks = now
            self._last_time_speed = None
        self.protected_road_tiles = set().union(
            task.route_to_implement, task.route_to_source,
            task.route_source_to_target, task.return_route,
            task.route_implement_to_home,
        )
        implement_name = VEHICLE_TYPE_DEFINITIONS[
            task.implement.vehicle_type
        ]["name"]
        log(f"A Traktor elindult a {implement_name}ért.", "Supply")
        return True

    def _continue_after_implement_attachment(self, world, now):
        """A feladattípustól függő forráshoz irányítja a szerelvényt."""
        task = self.current_task
        if not task.implement.attach_to(self):
            self._cancel_implement_task_and_return(world, now)
            return
        implement_name = VEHICLE_TYPE_DEFINITIONS[
            task.implement.vehicle_type
        ]["name"]
        if task.task_type == TASK_WATERING:
            self.path = task.route_to_pond
            self.state = TRACTOR_MOVING_TO_POND
            category = "Watering"
        else:
            self.path = task.route_to_source
            self.state = TRACTOR_MOVING_TO_SUPPLY_SOURCE
            category = (
                "Processing"
                if task.task_type == TASK_PROCESSING_SUPPLY
                else "Supply"
            )
        self.next_path_index = 1
        log(f"A Traktor felcsatolta a {implement_name}t.", category)

    def update(
            self, world, buildings, economy, game_time,
            current_ticks=None):
        """Blokkolás nélkül végrehajtja az esedékes rácslépéseket."""
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks
        if self.is_idle:
            self.last_update_ticks = now
            self._last_time_speed = game_time.current_time_speed
            return False

        if self.last_update_ticks is None:
            self.last_update_ticks = now
        elapsed_ms = max(0, now - self.last_update_ticks)
        self.last_update_ticks = now

        current_time_speed = game_time.current_time_speed
        if (self._last_time_speed is not None
                and current_time_speed != self._last_time_speed):
            # A váltás előtti képkocka óta eltelt időt nem könyveljük az új
            # fokozatra. Így hosszú szünet után sincs hirtelen előreugrás.
            elapsed_ms = 0
        self._last_time_speed = current_time_speed

        speed_multiplier = game_time.time_speed_multiplier
        if speed_multiplier <= 0:
            return False

        # Korábbi hibás mentésből visszatérő, útvonal nélkül maradt
        # gyümölcsszüretelő automatikus helyreállítása.
        if self.state == TRACTOR_RETURNING_HOME and not self.path:
            self._begin_return_home(world, now, buildings)

        self.movement_accumulator_ms += elapsed_ms * speed_multiplier
        completed_work = False
        steps_processed = 0
        while (not self.is_idle
               and self.movement_accumulator_ms >= TRACTOR_STEP_INTERVAL_MS
               and steps_processed < MAX_TRACTOR_STEPS_PER_UPDATE):
            self.movement_accumulator_ms -= TRACTOR_STEP_INTERVAL_MS
            steps_processed += 1
            if self.state == TRACTOR_LEAVING_PARKING:
                road_position = tile_to_world_center(self.row, self.col)
                if self._move_world_toward(road_position):
                    self.state = self._state_after_parking_exit
                    self._state_after_parking_exit = None
                continue
            if self.state == TRACTOR_ENTERING_PARKING:
                if self._move_world_toward(self.parking_world_position):
                    self._finish_parking(world, economy, now)
                continue
            if self.state == TRACTOR_FILLING_WATER:
                self.current_task.remaining_wait_ms -= TRACTOR_STEP_INTERVAL_MS
                if self.current_task.remaining_wait_ms <= 0:
                    self.path = self.current_task.route_pond_to_field
                    self.next_path_index = 1
                    self.state = TRACTOR_MOVING_TO_FIELD
                    log(
                        "A Traktor feltöltötte a Locsolótartályt.",
                        "Watering",
                    )
                continue
            if self.state == TRACTOR_WORKING_ORCHARD:
                self.current_task.remaining_wait_ms -= TRACTOR_STEP_INTERVAL_MS
                if self.current_task.remaining_wait_ms <= 0:
                    completed_work = self._complete_orchard_work()
                continue
            if self.state in (TRACTOR_LOADING_SUPPLY, TRACTOR_UNLOADING_SUPPLY):
                self.current_task.remaining_wait_ms -= TRACTOR_STEP_INTERVAL_MS
                if self.current_task.remaining_wait_ms > 0:
                    continue
                task = self.current_task
                if self.state == TRACTOR_LOADING_SUPPLY:
                    if task.task_type == TASK_PROCESSING_SUPPLY:
                        trailer = task.implement
                        trailer.cargo_type = task.cargo_type
                        trailer.cargo_amount = task.resource_amount
                        task.remaining_payload = task.resource_amount
                        log(
                            f"Pótkocsi megrakodva: {trailer.cargo_amount} "
                            f"{get_inventory_item_name(trailer.cargo_type)}.",
                            "Processing",
                        )
                    elif task.task_type == TASK_SUPPLY_FEED:
                        transaction = prepare_feed_supply(
                            task.buildings, economy,
                            task.target_group, task.animals,
                        )
                        if not transaction.success:
                            task.field.pop("vehicle_task_status", None)
                            task.field.pop("vehicle_queue_position", None)
                            task.field.pop("vehicle_task_type", None)
                            task.status = "cancelled"
                            task.return_route = find_road_path(
                                world, (self.row, self.col),
                                task.implement_connection_road,
                            ) or [(self.row, self.col)]
                            self.path = []
                            self.next_path_index = 0
                            self.state = TRACTOR_SELECTING_NEXT_TASK
                            continue
                        trailer = task.implement
                        trailer.cargo_type = transaction.feed_type
                        trailer.cargo_amount = transaction.required_amount
                        task.remaining_payload = transaction.required_amount
                        task.warehouse_amount = transaction.warehouse_amount
                        task.purchased_amount = transaction.purchased_amount
                        task.purchase_cost = transaction.purchase_cost
                        log(
                            f"Pótkocsi megrakodva: "
                            f"{trailer.cargo_amount} "
                            f"{CROPS[trailer.cargo_type]['name']}.",
                            "Supply",
                        )
                    self.path = task.route_source_to_target
                    self.next_path_index = 1
                    self.state = TRACTOR_MOVING_TO_TROUGH
                    if task.task_type == TASK_PROCESSING_SUPPLY:
                        log("Alapanyag felrakodva.", "Processing")
                    else:
                        message = (
                            "Takarmány felrakodva."
                            if task.task_type == TASK_SUPPLY_FEED
                            else "Locsolótartály feltöltve."
                        )
                        log(message, "Supply")
                else:
                    if task.task_type == TASK_PROCESSING_SUPPLY:
                        delivered = receive_processing_delivery(
                            task.field, task.cargo_type,
                            task.implement.cargo_amount,
                        )
                        task.implement.cargo_type = "empty"
                        task.implement.cargo_amount = 0
                        task.remaining_payload = 0
                        task.resource_reserved = False
                        completed_work = delivered == task.resource_amount
                        if completed_work:
                            log(
                                f"{delivered} db {get_inventory_item_name(task.cargo_type)} "
                                "megérkezett a Feldolgozó üzembe.",
                                "Processing",
                            )
                    elif task.task_type == TASK_SUPPLY_FEED:
                        completed_work = (
                            task.field in task.buildings
                            and deliver_feed_cargo(
                                task.target_group, task.animals, task.implement,
                            ) > 0
                        )
                    else:
                        completed_work = fill_group_trough(
                            task.target_group, task.animals, task.trough_type,
                        )
                    task.field.pop("vehicle_task_status", None)
                    task.field.pop("vehicle_queue_position", None)
                    task.field.pop("vehicle_task_type", None)
                    task.status = "completed" if completed_work else "cancelled"
                    if (completed_work and task.task_type not in (
                            TASK_SUPPLY_FEED, TASK_PROCESSING_SUPPLY)):
                        message = (
                            "Etetővályú feltöltve."
                            if task.task_type == TASK_SUPPLY_FEED
                            else "Itatóvályú feltöltve."
                        )
                        log(message, "Supply")
                    if (
                        task.task_type == TASK_SUPPLY_FEED
                        and task.implement.cargo_amount > 0
                    ):
                        self._route_feed_cargo_back(world)
                    else:
                        self.path = []
                        self.next_path_index = 0
                        self.state = TRACTOR_SELECTING_NEXT_TASK
                continue
            if self.next_path_index < len(self.path):
                self._set_tile_position(*self.path[self.next_path_index])
                self.next_path_index += 1
                if (self.state == TRACTOR_WORKING_FIELD
                        and self.next_path_index == len(self.path)):
                    completed_work = self._complete_field_work(game_time)
                elif (self.state == TRACTOR_LEAVING_FIELD
                        and self.next_path_index == len(self.path)):
                    self._finish_leaving_field(
                        world, buildings, economy, now,
                    )
                elif (self.state == TRACTOR_RETURNING_HOME
                        and self.next_path_index == len(self.path)):
                    self._arrive_home(world, economy, now)
                elif (self.state == TRACTOR_RELOCATING_TO_PARKING
                        and self.next_path_index == len(self.path)):
                    self._arrive_home(world, economy, now)
                elif (self.state == TRACTOR_MOVING_TO_POND
                        and self.next_path_index == len(self.path)):
                    self.state = TRACTOR_FILLING_WATER
                    self.current_task.remaining_wait_ms = WATER_FILL_DURATION_MS
                elif (self.state == TRACTOR_MOVING_TO_IMPLEMENT
                        and self.next_path_index == len(self.path)):
                    self._continue_after_implement_attachment(world, now)
                elif (self.state == TRACTOR_MOVING_TO_SUPPLY_SOURCE
                        and self.next_path_index == len(self.path)):
                    self.state = TRACTOR_LOADING_SUPPLY
                    self.current_task.remaining_wait_ms = (
                        self.current_task.loading_duration_ms
                    )
                    if self.current_task.task_type == TASK_PROCESSING_SUPPLY:
                        source_name = (
                            "Piac" if self.current_task.source_type == "market"
                            else "Raktár"
                        )
                        log(
                            f"Traktor megérkezett a {source_name}hoz.",
                            "Processing",
                        )
                    elif self.current_task.task_type == TASK_SUPPLY_FEED:
                        log("Traktor megérkezett a Raktárhoz.", "Supply")
                    else:
                        log("Traktor megérkezett a Tóhoz.", "Supply")
                elif (self.state == TRACTOR_MOVING_TO_TROUGH
                        and self.next_path_index == len(self.path)):
                    self.state = TRACTOR_UNLOADING_SUPPLY
                    self.current_task.remaining_wait_ms = (
                        self.current_task.unloading_duration_ms
                    )
                elif (self.state == TRACTOR_RETURNING_IMPLEMENT
                        and self.next_path_index == len(self.path)):
                    self._return_implement_and_continue_home(world, now)
                elif (self.state == TRACTOR_RETURNING_FEED_CARGO
                        and self.next_path_index == len(self.path)):
                    self._finish_feed_cargo_return(world)
                continue

            if self.state in (
                    TRACTOR_MOVING_TO_FIELD,
                    TRACTOR_MOVING_TO_NEXT_FIELD):
                if self.current_task.task_type == TASK_ORCHARD_HARVEST:
                    self.state = TRACTOR_WORKING_ORCHARD
                    self.current_task.remaining_wait_ms = ORCHARD_HARVEST_DURATION_MS
                    continue
                self.path = create_field_work_path(
                    self.current_task.field, self.current_task.entry_tile,
                )
                self.next_path_index = 0
                self.state = TRACTOR_WORKING_FIELD
                continue
            if self.state == TRACTOR_RELOCATING_TO_PARKING:
                self._arrive_home(world, economy, now)
                continue
            if self.state == TRACTOR_MOVING_TO_POND:
                self.state = TRACTOR_FILLING_WATER
                self.current_task.remaining_wait_ms = WATER_FILL_DURATION_MS
                continue
            if self.state == TRACTOR_MOVING_TO_IMPLEMENT:
                self._continue_after_implement_attachment(world, now)
                continue
            if self.state == TRACTOR_MOVING_TO_SUPPLY_SOURCE:
                self.state = TRACTOR_LOADING_SUPPLY
                self.current_task.remaining_wait_ms = (
                    self.current_task.loading_duration_ms
                )
                continue
            if self.state == TRACTOR_MOVING_TO_TROUGH:
                self.state = TRACTOR_UNLOADING_SUPPLY
                self.current_task.remaining_wait_ms = (
                    self.current_task.unloading_duration_ms
                )
                continue
            if self.state == TRACTOR_RETURNING_IMPLEMENT:
                self._return_implement_and_continue_home(world, now)
                continue
            if self.state == TRACTOR_RETURNING_FEED_CARGO:
                self._finish_feed_cargo_return(world)
                continue
            if self.state == TRACTOR_SELECTING_NEXT_TASK:
                continue
        return completed_work

    def _complete_orchard_work(self):
        """Betárolja a konkrét fa termését, majd új feladatra vár."""
        task = self.current_task
        completed = complete_tree_harvest(
            task.buildings, task.field, task.tree_slot,
        )
        task.resource_reserved = False
        task.field.pop("vehicle_task_status", None)
        task.field.pop("vehicle_queue_position", None)
        task.field.pop("vehicle_task_type", None)
        task.status = "completed" if completed else "cancelled"
        self.current_task = None
        self.path = []
        self.next_path_index = 0
        self.state = TRACTOR_AWAITING_ASSIGNMENT
        self.protected_road_tiles = {(self.row, self.col)}
        return completed

    def _route_feed_cargo_back(self, world):
        """A célon maradt rakományt fizikailag visszaviszi a Raktárhoz."""
        route, _ = find_building_route(
            world, (self.row, self.col), self.current_task.source_building,
        )
        if route is None:
            log("A Pótkocsi rakománya nem juttatható vissza a Raktárhoz.", "Supply")
            self.current_task.return_route = find_road_path(
                world, (self.row, self.col),
                self.current_task.implement_connection_road,
            ) or [(self.row, self.col)]
            self.finish_implement_session()
            return
        self.path = route
        self.next_path_index = 1
        self.state = TRACTOR_RETURNING_FEED_CARGO
        self.protected_road_tiles.update(route)

    def _finish_feed_cargo_return(self, world):
        """A Raktárnál visszavételezi a megmaradt vagy megszakított rakományt."""
        task = self.current_task
        if return_feed_cargo(task.buildings, task.implement):
            task.return_route = find_road_path(
                world, (self.row, self.col), task.implement_connection_road,
            ) or [(self.row, self.col)]
            self.path = []
            self.next_path_index = 0
            self.state = TRACTOR_SELECTING_NEXT_TASK
            return
        task.return_route = find_road_path(
            world, (self.row, self.col), task.implement_connection_road,
        ) or [(self.row, self.col)]
        self.finish_implement_session()

    def _complete_field_work(self, game_time):
        task = self.current_task
        if task.task_type == TASK_FERTILIZING:
            # A korábban érvényesen kiadott feladat érés közben sem vész el.
            completed = fertilize_crop(
                task.field, task.buildings, allow_mature=True,
            )
            task.resource_reserved = False
            completion_message = "A trágyázás befejeződött."
        elif task.task_type == TASK_HARVESTING:
            completed = complete_harvest(
                task.field, task.buildings, task.crop, task.resource_amount,
                current_elapsed_week=game_time.elapsed_weeks,
            )
            task.resource_reserved = False
            completion_message = "Az aratás befejeződött."
        elif task.task_type == TASK_WATERING:
            completed = water_crop(task.field)
            completion_message = "A Veteményes sikeresen meglocsolva."
        elif task.task_type == TASK_SPRAYING:
            completed = spray_crop(task.field, allow_mature=True)
            completion_message = "Veteményes permetezve. +10% hozambónusz."
        else:
            completed = plant_crop(
                task.field, task.crop,
                current_elapsed_week=game_time.elapsed_weeks,
            )
            completion_message = "Az ültetés befejeződött."
        task.field.pop("vehicle_task_status", None)
        task.field.pop("vehicle_queue_position", None)
        task.field.pop("vehicle_task_type", None)
        task.status = "completed" if completed else "cancelled"

        # A kígyózó kör utolsó tile-ja az elsővel szomszédos, így innen
        # látható lépésekkel jutunk vissza ugyanahhoz a kapcsolódó úthoz.
        self.path = [task.entry_tile, task.connection_road]
        self.next_path_index = 0
        self.state = TRACTOR_LEAVING_FIELD
        if completed:
            log(
                completion_message,
                {
                    TASK_PLANTING: "Planting",
                    TASK_FERTILIZING: "Fertilizing",
                    TASK_HARVESTING: "Harvest",
                    TASK_WATERING: "Watering",
                    TASK_SPRAYING: "Spraying",
                }.get(task.task_type, "Vehicle"),
            )
        elif task.task_type == TASK_FERTILIZING:
            log(
                "A trágyázási feladat már nem hajtható végre.",
                "Fertilizing",
            )
        elif task.task_type == TASK_HARVESTING:
            log("Az aratási feladat már nem hajtható végre.", "Harvest")
        elif task.task_type == TASK_WATERING:
            log("A locsolási feladat már nem hajtható végre.", "Watering")
        elif task.task_type == TASK_SPRAYING:
            log("A permetezési feladat már nem hajtható végre.", "Spraying")
        if completed and task.task_type == TASK_WATERING:
            log("+10% hozam aktiválva.", "Watering")
        return completed

    def _finish_leaving_field(self, world, buildings, economy, now):
        if (
            self.current_task is not None
            and self.current_task.task_type == TASK_WATERING
            and self.attached_implement is not None
        ):
            # A Dispatcher előbb megpróbál azonos típusú következő célt adni.
            self.path = []
            self.next_path_index = 0
            self.state = TRACTOR_SELECTING_NEXT_TASK
            return
        self.current_task = None
        self._refresh_preferred_parking(world, buildings)
        # A közös Dispatcher ugyanebben az update-ben dönt a folytatásról.
        # Addig a traktor a mező kapcsolódó ROAD mezőjén marad.
        self.path = []
        self.next_path_index = 0
        self.state = TRACTOR_AWAITING_ASSIGNMENT
        self.protected_road_tiles = {(self.row, self.col)}

    def _return_implement_and_continue_home(self, world, now):
        """Lecsatolja a tartályt a saját helyén, majd hazaküldi a traktort."""
        task = self.current_task
        implement = self.attached_implement
        if implement is not None:
            implement.return_to_parking(world)
            implement_name = VEHICLE_TYPE_DEFINITIONS[
                implement.vehicle_type
            ]["name"]
            category = (
                "Supply" if task.task_type in (TASK_SUPPLY_FEED, TASK_SUPPLY_WATER)
                else "Processing" if task.task_type == TASK_PROCESSING_SUPPLY
                else "Watering"
            )
            log(f"A Traktor lecsatolta a {implement_name}t.", category)
        self.current_task = None
        self.path = task.route_implement_to_home
        self.next_path_index = 1
        self.state = TRACTOR_RETURNING_HOME
        if len(self.path) <= 1:
            self._arrive_home(world, None, now)

    def _cancel_implement_task_and_return(self, world, now):
        """Sikertelen felcsatolásnál felszabadítja a célt és hazatér."""
        task = self.current_task
        if task is not None:
            task.field.pop("vehicle_task_status", None)
            task.field.pop("vehicle_queue_position", None)
            task.field.pop("vehicle_task_type", None)
            if (
                task.task_type == TASK_PROCESSING_SUPPLY
                and task.resource_reserved
            ):
                refund_processing_delivery(
                    task.buildings, task.field, task.cargo_type,
                    task.resource_amount,
                )
                task.resource_reserved = False
        self.current_task = None
        if task is not None and task.task_type in (
                TASK_SUPPLY_FEED, TASK_SUPPLY_WATER, TASK_PROCESSING_SUPPLY):
            log("Az ellátási feladat nem indítható el.", "Supply")
        else:
            log("A locsolási feladat nem indítható el.", "Watering")
        self._begin_return_home(world, now)

    def _refresh_preferred_parking(self, world, buildings):
        """A következő parkolás előtt, teleportálás nélkül frissíti a célt."""
        parking_building, parking_tile = self._find_preferred_parking(
            world, buildings,
        )
        self.parking_tile = parking_tile
        self.parking_building_type = (
            parking_building["type"] if parking_building is not None else None
        )
        self.parking_world_position = self._parking_world_position(
            parking_building, parking_tile,
        )

    def _begin_return_home(self, world, now, buildings=None):
        vehicle_name = VEHICLE_TYPE_DEFINITIONS[self.vehicle_type]["name"]
        if self._orchard_exit_path and self._orchard_exit_road is not None:
            road_route = find_road_path(
                world, self._orchard_exit_road, self.parking_tile,
            )
            route = (
                self._orchard_exit_path + road_route[1:]
                if road_route is not None else None
            )
            self._orchard_exit_path = None
            self._orchard_exit_road = None
        else:
            route = find_road_path(world, (self.row, self.col), self.parking_tile)
            if route is None and self.vehicle_type == VehicleType.FRUIT_HARVESTER:
                route = _find_orchard_recovery_route(
                    world, buildings, (self.row, self.col), self.parking_tile,
                )
                if route is not None:
                    log(
                        "A Gyümölcs szüretelőgép kijárati útvonala "
                        "helyreállítva.",
                        "Vehicle",
                    )
        if route is None:
            # Az aktív feladathoz a visszautat végig védjük, ezért ez csak
            # sérült külső állapotnál fordulhat elő.
            log(
                f"A {vehicle_name.lower()} nem talál vissza a parkolóhelyére.",
                "Vehicle",
            )
            self.path = []
            self.next_path_index = 0
            self.state = TRACTOR_RETURNING_HOME
            return
        self.path = route
        self.next_path_index = 1
        self.state = TRACTOR_RETURNING_HOME
        self.protected_road_tiles = set(route)
        parking_name = BUILDING_TYPES[self.parking_building_type]["name"]
        log(f"A {vehicle_name} visszatér a {parking_name}hoz.", "Vehicle")
        if len(route) == 1:
            self._arrive_home(world, None, now)

    def begin_return_home(self, world, buildings=None, current_ticks=None):
        """A Dispatcher döntése után elindítja a saját parkolóhoz visszatérést."""
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks
        self._begin_return_home(world, now, buildings)

    def _arrive_home(self, world, economy, now):
        if self.state != TRACTOR_RELOCATING_TO_PARKING:
            self._parking_arrival_reason = "return"
        self._set_tile_position(*self.parking_tile)
        self.path = []
        self.next_path_index = 0
        self.protected_road_tiles.clear()
        if not self._positions_match(
                (self.world_x, self.world_y), self.parking_world_position):
            self.state = TRACTOR_ENTERING_PARKING
            return
        self._finish_parking(world, economy, now)

    def _finish_parking(self, world, economy, now):
        self._set_world_position(*self.parking_world_position)
        if self.attached_implement is not None:
            implement = self.attached_implement
            implement.return_to_parking(world)
            log("A Traktor lecsatolta a Locsolótartályt.", "Watering")
        vehicle_name = VEHICLE_TYPE_DEFINITIONS[self.vehicle_type]["name"].lower()
        if self._parking_arrival_reason == "relocation":
            log(f"A {vehicle_name} beparkolt a Garázsba.", "Vehicle")
        else:
            parking_name = BUILDING_TYPES[self.parking_building_type]["name"]
            log(f"A {vehicle_name} visszaért a {parking_name}hoz.", "Vehicle")
        self._parking_arrival_reason = None
        if self.parking_building_type == "garage":
            self._unreachable_parking_building = None
        self.state = TRACTOR_IDLE
        self._orchard_exit_path = None
        self._orchard_exit_road = None
        self.movement_accumulator_ms = 0.0

    def demolition_block_reason(self, row, col, building=None, field=None):
        if field is not None and field.get("vehicle_task_status") is not None:
            return "A veteményes traktorfeladat közben nem bontható."
        if (building is not None and building["type"] == "garage"
                and self.parking_building_type == "garage"
                and self.state in (
                    TRACTOR_IDLE,
                    TRACTOR_RELOCATING_TO_PARKING,
                    TRACTOR_RETURNING_HOME,
                    TRACTOR_ENTERING_PARKING,
                    TRACTOR_LEAVING_PARKING,
                )):
            return "A Garázs nem bontható, amíg egy jármű használja."
        if not self.is_idle:
            if (
                building is not None
                and self.current_task is not None
                and building is self.current_task.pond
            ):
                return "A Tó aktív locsolási feladat közben nem bontható."
            if (
                building is not None
                and self.current_task is not None
                and building is self.current_task.source_building
            ):
                return "Az ellátási forrás aktív járműfeladat közben nem bontható."
            if (
                building is not None
                and self.current_task is not None
                and self.current_task.target_group is not None
                and building in self.current_task.target_group
            ):
                return "A Karám aktív ellátási feladat közben nem bontható."
            if building is not None and building["type"] == "farmhouse":
                return "A Farmház aktív traktorfeladatok közben nem bontható."
            if (row, col) == self.parking_tile:
                return "A jármű parkolóhelye nem bontható."
            if (row, col) in self.protected_road_tiles:
                return "A jármű útvonalában lévő út nem bontható."
        elif (row, col) == (self.row, self.col) == self.parking_tile:
            return "A jármű parkolóhelye nem bontható."
        return None

    def reset(self, fields):
        """Betöltéskor elveti a nem mentett aktív és várakozó munkákat."""
        for field in fields:
            field.pop("vehicle_task_status", None)
            field.pop("vehicle_queue_position", None)
        self._clear_position()
        self.path = []
        self.next_path_index = 0
        self.state = TRACTOR_IDLE
        self.current_task = None
        self.movement_accumulator_ms = 0.0
        self.last_update_ticks = None
        self._last_time_speed = None
        self.parking_tile = None
        self.parking_building_type = None
        self.parking_world_position = None
        self._state_after_parking_exit = None
        self._parking_arrival_reason = None
        self._unreachable_parking_building = None
        self.protected_road_tiles.clear()
        self.facing_direction = "up"
        self.attached_implement = None
        self._orchard_exit_path = None
        self._orchard_exit_road = None

    def draw(self, screen):
        if self.world_x is None or self.world_y is None:
            return
        screen_x, screen_y = world_to_screen(self.world_x, self.world_y)
        center = (round(screen_x), round(screen_y))
        shadow_size = (
            (18, 8)
            if self.vehicle_type in (
                VehicleType.COMBINE, VehicleType.FRUIT_HARVESTER,
            )
            else (14, 7)
        )
        self._draw_vehicle_shadow(screen, center, shadow_size)

        rotated = self._get_vehicle_sprite()
        screen.blit(rotated, rotated.get_rect(center=center))

        if (self.state == TRACTOR_WORKING_FIELD
                and self.current_task is not None
                and self.current_task.task_type == TASK_FERTILIZING):
            # Visszafogott barna pontok jelzik az aktív trágyaszórást.
            for offset_x, offset_y in ((-7, -5), (7, -2), (-5, 7), (6, 6)):
                pygame.draw.circle(
                    screen,
                    (112, 74, 39),
                    (center[0] + offset_x, center[1] + offset_y),
                    2,
                )

    @staticmethod
    def _draw_vehicle_shadow(screen, center, size):
        """Finom, a járművel együtt mozgó talajárnyékot rajzol."""
        shadow = _VEHICLE_SHADOW_CACHE.get(size)
        if shadow is None:
            shadow = pygame.Surface(
                (size[0] + 4, size[1] + 4), pygame.SRCALPHA,
            )
            pygame.draw.ellipse(
                shadow, VEHICLE_SHADOW_COLOR, shadow.get_rect(),
            )
            _VEHICLE_SHADOW_CACHE[size] = shadow
        shadow_rect = shadow.get_rect(center=(center[0], center[1] + 3))
        screen.blit(shadow, shadow_rect)

    def _get_vehicle_sprite(self):
        """Egyszer elkészíti, majd gyorsítótárból adja a forgatott grafikát."""
        cache_key = (self.vehicle_type, self.facing_direction)
        rotated = _VEHICLE_SPRITE_CACHE.get(cache_key)
        if rotated is not None:
            return rotated
        sprite = pygame.Surface(
            (VEHICLE_SPRITE_SIZE, VEHICLE_SPRITE_SIZE), pygame.SRCALPHA,
        )
        if self.vehicle_type == VehicleType.COMBINE:
            self._draw_combine(sprite)
        elif self.vehicle_type == VehicleType.FRUIT_HARVESTER:
            self._draw_fruit_harvester(sprite)
        else:
            self._draw_tractor(sprite)
        rotated = pygame.transform.rotate(
            sprite, VEHICLE_ROTATION_ANGLES[self.facing_direction],
        )
        _VEHICLE_SPRITE_CACHE[cache_key] = rotated
        return rotated

    @staticmethod
    def _draw_wheel(surface, center, radius, rim_color):
        """Közös gumi–felni elemet rajzol mindkét járműhöz."""
        pygame.draw.circle(surface, VEHICLE_TIRE_COLOR, center, radius)
        pygame.draw.circle(surface, rim_color, center, max(1, radius - 1))

    @classmethod
    def _draw_tractor(cls, surface):
        """Kompakt, felülnézetes és felismerhető Traktort rajzol."""
        center_x = surface.get_width() // 2
        body = pygame.Rect(center_x - 4, 5, 8, 14)
        hood = pygame.Rect(center_x - 3, 3, 6, 8)
        cabin = pygame.Rect(center_x - 4, 11, 8, 7)

        # A nagy hátsó és kisebb első kerekek adják a jellegzetes sziluettet.
        for wheel_x in (body.left - 2, body.right + 1):
            cls._draw_wheel(surface, (wheel_x, 15), 3, TRACTOR_RIM_COLOR)
            cls._draw_wheel(surface, (wheel_x, 7), 2, TRACTOR_RIM_COLOR)

        pygame.draw.rect(surface, TRACTOR_COLOR, body, border_radius=2)
        pygame.draw.rect(
            surface, TRACTOR_BORDER_COLOR, body, 1, border_radius=2,
        )
        pygame.draw.rect(surface, TRACTOR_COLOR, hood, border_radius=2)
        pygame.draw.line(
            surface, TRACTOR_BORDER_COLOR,
            (hood.left + 1, hood.top + 2), (hood.right - 2, hood.top + 2), 1,
        )
        pygame.draw.rect(surface, TRACTOR_CAB_COLOR, cabin, border_radius=1)
        pygame.draw.rect(
            surface, TRACTOR_BORDER_COLOR, cabin, 1, border_radius=1,
        )
        pygame.draw.line(
            surface, TRACTOR_RIM_COLOR,
            (body.left - 1, 8), (body.right, 8), 1,
        )
        pygame.draw.line(
            surface, TRACTOR_RIM_COLOR,
            (body.left - 2, 15), (body.right + 1, 15), 1,
        )

    @classmethod
    def _draw_combine(cls, surface):
        """Kis méretben is felismerhető, felülnézetes Kombájnt rajzol."""
        rect = surface.get_rect()
        body = pygame.Rect(0, 0, 12, 14)
        body.center = (rect.centerx, rect.centery + 1)
        pygame.draw.rect(surface, COMBINE_BODY_COLOR, body, border_radius=2)
        pygame.draw.rect(
            surface, COMBINE_BODY_BORDER_COLOR, body, 1, border_radius=2,
        )

        for wheel_x in (body.left - 2, body.right + 1):
            for wheel_y in (body.top + 3, body.bottom - 4):
                cls._draw_wheel(
                    surface, (wheel_x, wheel_y), 3, COMBINE_WHEEL_COLOR,
                )

        cabin = pygame.Rect(body.left + 2, body.top + 2, body.width - 4, 5)
        pygame.draw.rect(surface, COMBINE_CAB_COLOR, cabin, border_radius=1)

        header = pygame.Rect(rect.left + 1, rect.top + 1, rect.width - 2, 4)
        pygame.draw.rect(surface, COMBINE_HEADER_COLOR, header)
        pygame.draw.line(
            surface, COMBINE_BODY_BORDER_COLOR,
            (header.left, header.bottom), (header.right, header.bottom), 1,
        )
        for x in range(header.left + 2, header.right, 4):
            pygame.draw.line(
                surface, COMBINE_BODY_BORDER_COLOR,
                (x, header.top), (x, header.bottom - 1), 1,
            )

    @classmethod
    def _draw_fruit_harvester(cls, surface):
        """Sárga, felülnézetes gyümölcsszedő gépet rajzol."""
        rect = surface.get_rect()
        body = pygame.Rect(0, 0, 10, 15)
        body.center = (rect.centerx, rect.centery + 1)

        # A négy kerék és a két oldalsó gyűjtőkar adja a jellegzetes sziluettet.
        for wheel_x in (body.left - 2, body.right + 1):
            for wheel_y in (body.top + 3, body.bottom - 4):
                cls._draw_wheel(
                    surface, (wheel_x, wheel_y), 2,
                    FRUIT_HARVESTER_RIM_COLOR,
                )

        pygame.draw.rect(
            surface, FRUIT_HARVESTER_BODY_COLOR, body, border_radius=2,
        )
        pygame.draw.rect(
            surface, FRUIT_HARVESTER_BODY_DARK, body, 1, border_radius=2,
        )
        cabin = pygame.Rect(body.left + 2, body.top + 2, body.width - 4, 5)
        pygame.draw.rect(
            surface, FRUIT_HARVESTER_CAB_COLOR, cabin, border_radius=1,
        )

        for arm_x in (body.left - 5, body.right + 1):
            arm = pygame.Rect(arm_x, body.top + 6, 4, 7)
            pygame.draw.rect(
                surface, FRUIT_HARVESTER_ARM_COLOR, arm, border_radius=1,
            )
            pygame.draw.rect(surface, FRUIT_HARVESTER_BODY_DARK, arm, 1)


class Tractor(Vehicle):
    """A meglévő mezőmunkák elvégzésére alkalmas jármű."""

    def __init__(self, vehicle_id=1):
        super().__init__(vehicle_id, VehicleType.TRACTOR)


class Combine(Vehicle):
    """A későbbi aratási feladatokra előkészített Kombájn."""

    def __init__(self, vehicle_id=1):
        super().__init__(vehicle_id, VehicleType.COMBINE)


class FruitHarvester(Vehicle):
    """A Gyümölcsös szüretelésére fenntartott önjáró jármű."""

    def __init__(self, vehicle_id=1):
        super().__init__(vehicle_id, VehicleType.FRUIT_HARVESTER)


class TowableImplement:
    """Önálló mozgás és állapotgép nélküli, általános vontatott munkagép."""

    FOLLOW_DISTANCE = 18

    def __init__(self, implement_id, implement_type):
        self.vehicle_id = implement_id
        self.vehicle_type = implement_type
        self.assigned_parking_building = None
        self.parking_slot_id = None
        self.attached_to = None
        self.row = None
        self.col = None
        self.world_x = None
        self.world_y = None
        self.facing_direction = "up"
        # A Pótkocsi első változata csak az üres rakományállapotot használja.
        # A mezők a későbbi szállítási munkafolyamatok közös kapcsolódási pontjai.
        self.cargo_type = "empty"
        self.cargo_amount = 0
        self.loading_location = None
        self.unloading_location = None
        self.assigned_task = None

    @property
    def is_attached(self):
        return self.attached_to is not None

    def attach_to(self, towing_vehicle):
        """Kétirányú kapcsolatot hoz létre egy kompatibilis vontatóval."""
        definition = VEHICLE_TYPE_DEFINITIONS[self.vehicle_type]
        if (
            towing_vehicle is None
            or towing_vehicle.vehicle_type
            not in definition.get("compatible_towing_types", ())
            or towing_vehicle.attached_implement is not None
            or self.attached_to is not None
        ):
            return False
        self.attached_to = towing_vehicle
        towing_vehicle.attached_implement = self
        self.follow_towing_vehicle()
        return True

    def detach(self):
        """Megszünteti a vontató és a munkagép közötti kapcsolatot."""
        if self.attached_to is not None:
            self.attached_to.attached_implement = None
        self.attached_to = None

    def return_to_parking(self, world):
        """Lecsatolás után visszahelyezi a munkagépet a saját Garázshelyére."""
        self.detach()
        garage = self.assigned_parking_building
        if garage is None or garage.get("type") != "garage":
            self.row = self.col = self.world_x = self.world_y = None
            return
        parking_tile = find_building_parking(world, garage)
        if parking_tile is None:
            self.row = self.col = self.world_x = self.world_y = None
            return
        self.row, self.col = parking_tile
        self.world_x, self.world_y = get_garage_parking_position(
            garage, self.parking_slot_id,
        )

    def follow_towing_vehicle(self):
        """Útvonal nélkül a vontató mögötti egyszerű követőpozíciót veszi fel."""
        towing_vehicle = self.attached_to
        if (
            towing_vehicle is None
            or towing_vehicle.world_x is None
            or towing_vehicle.world_y is None
        ):
            return
        behind = {
            "up": (0, self.FOLLOW_DISTANCE),
            "right": (-self.FOLLOW_DISTANCE, 0),
            "down": (0, -self.FOLLOW_DISTANCE),
            "left": (self.FOLLOW_DISTANCE, 0),
        }[towing_vehicle.facing_direction]
        self.world_x = towing_vehicle.world_x + behind[0]
        self.world_y = towing_vehicle.world_y + behind[1]
        self.row = towing_vehicle.row
        self.col = towing_vehicle.col
        self.facing_direction = towing_vehicle.facing_direction

    def ensure_idle_position(self, world, buildings):
        """A lecsatolt munkagépet a saját Garázshelyén tartja."""
        if self.is_attached:
            self.follow_towing_vehicle()
            return
        garage = self.assigned_parking_building
        if garage not in buildings or garage.get("type") != "garage":
            self.row = self.col = self.world_x = self.world_y = None
            return
        parking_tile = find_building_parking(world, garage)
        if parking_tile is None:
            self.row = self.col = self.world_x = self.world_y = None
            return
        self.row, self.col = parking_tile
        self.world_x, self.world_y = get_garage_parking_position(
            garage, self.parking_slot_id,
        )

    def can_save(self, world, buildings):
        """Parkoló vagy szabályosan csatolt munkagép menthető."""
        if self.is_attached:
            return self.attached_to.can_save(world, buildings)
        garage = self.assigned_parking_building
        if garage not in buildings or garage.get("type") != "garage":
            return False
        parking_tile = find_building_parking(world, garage)
        expected_position = get_garage_parking_position(
            garage, self.parking_slot_id,
        )
        return (
            parking_tile is not None
            and (self.row, self.col) == parking_tile
            and Vehicle._positions_match(
                (self.world_x, self.world_y), expected_position,
            )
        )

    def draw(self, screen):
        if self.world_x is None or self.world_y is None:
            return
        screen_x, screen_y = world_to_screen(self.world_x, self.world_y)
        center = round(screen_x), round(screen_y)
        Vehicle._draw_vehicle_shadow(screen, center, (15, 7))
        sprite = self._get_sprite()
        screen.blit(sprite, sprite.get_rect(center=center))

    def _get_sprite(self):
        """A típus és irány szerint cache-elt procedurális grafikát adja vissza."""
        cache_key = (
            self.vehicle_type, self.facing_direction,
            self.cargo_type if self.vehicle_type == VehicleType.TRAILER else None,
        )
        rotated = _VEHICLE_SPRITE_CACHE.get(cache_key)
        if rotated is not None:
            return rotated
        sprite = pygame.Surface(
            (VEHICLE_SPRITE_SIZE, VEHICLE_SPRITE_SIZE), pygame.SRCALPHA,
        )
        renderer_type = VEHICLE_TYPE_DEFINITIONS[self.vehicle_type].get(
            "renderer_type",
        )
        if renderer_type == "water_tank":
            self._draw_water_tank(sprite)
        elif renderer_type == "trailer":
            self._draw_trailer(sprite, self.cargo_type)
        rotated = pygame.transform.rotate(
            sprite, VEHICLE_ROTATION_ANGLES[self.facing_direction],
        )
        _VEHICLE_SPRITE_CACHE[cache_key] = rotated
        return rotated

    @staticmethod
    def _draw_water_tank(surface):
        """Kéttengelyes, ezüst Locsolótartályt rajzol felülnézetből."""
        center_x = surface.get_width() // 2
        pygame.draw.line(
            surface, WATER_TANK_BODY_DARK,
            (center_x, 2), (center_x, 8), 2,
        )
        tank = pygame.Rect(center_x - 5, 6, 10, 15)
        for wheel_y in (10, 17):
            Vehicle._draw_wheel(
                surface, (tank.left - 2, wheel_y), 2, WATER_TANK_RIM_COLOR,
            )
            Vehicle._draw_wheel(
                surface, (tank.right + 1, wheel_y), 2, WATER_TANK_RIM_COLOR,
            )
        pygame.draw.rect(
            surface, WATER_TANK_FENDER_COLOR,
            (tank.left - 2, tank.top + 2, tank.width + 4, tank.height - 4),
            1, border_radius=3,
        )
        pygame.draw.ellipse(surface, WATER_TANK_BODY_COLOR, tank)
        pygame.draw.ellipse(surface, WATER_TANK_BODY_DARK, tank, 1)
        pygame.draw.line(
            surface, WATER_TANK_BODY_LIGHT,
            (tank.left + 3, tank.top + 2),
            (tank.left + 3, tank.bottom - 3), 1,
        )
        for band_y in (10, 17):
            pygame.draw.line(
                surface, WATER_TANK_BODY_DARK,
                (tank.left + 1, band_y), (tank.right - 2, band_y), 1,
            )

    @staticmethod
    def _draw_trailer(surface, cargo_type="empty"):
        """Nyitott, jelenleg mindig üres Pótkocsit rajzol felülnézetből."""
        center_x = surface.get_width() // 2
        # A vonórúd a felül elhelyezkedő Traktor felé mutat.
        pygame.draw.line(
            surface, TRAILER_BORDER_COLOR,
            (center_x, 1), (center_x, 7), 2,
        )
        bed = pygame.Rect(center_x - 6, 6, 12, 16)
        for wheel_y in (11, 18):
            Vehicle._draw_wheel(
                surface, (bed.left - 2, wheel_y), 2, TRAILER_RIM_COLOR,
            )
            Vehicle._draw_wheel(
                surface, (bed.right + 1, wheel_y), 2, TRAILER_RIM_COLOR,
            )
        pygame.draw.rect(
            surface, TRAILER_BORDER_COLOR, bed, border_radius=2,
        )
        inner = bed.inflate(-2, -2)
        pygame.draw.rect(surface, TRAILER_WALL_COLOR, inner, border_radius=1)
        cargo_bed = inner.inflate(-2, -2)
        if cargo_type == "empty":
            pygame.draw.rect(surface, TRAILER_BED_COLOR, cargo_bed)
        else:
            cargo_color = (
                TRAILER_ALFALFA_COLOR
                if cargo_type == "alfalfa"
                else TRAILER_CORN_COLOR
            )
            pygame.draw.rect(surface, cargo_color, cargo_bed)
            # Néhány finom vonás kis méretben is növényi rakományt jelez.
            for y in range(cargo_bed.top + 2, cargo_bed.bottom, 3):
                pygame.draw.line(
                    surface, TRAILER_WALL_LIGHT,
                    (cargo_bed.left + 1, y), (cargo_bed.right - 2, y), 1,
                )
        pygame.draw.line(
            surface, TRAILER_WALL_LIGHT,
            (inner.left + 1, inner.top + 1),
            (inner.right - 2, inner.top + 1), 1,
        )
