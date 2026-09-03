import json
import math
import os
from datetime import datetime
from pathlib import Path

from animals import (
    ANIMAL_TYPES, find_animal_pen_group, get_pen_group_tiles,
)
from animal_troughs import (
    FOOD_STOCK_KEY, WATER_STOCK_KEY, synchronize_pen_group_stocks,
)
from bank import is_valid_loan_record
from buildings import (
    BUILDING_TYPES, FARMHOUSE_BUILDING_OFFSET, FARMHOUSE_BUILDING_SIZE,
    FARMHOUSE_LEGACY_LEVEL, FARMHOUSE_LEVELS, GARAGE_PARKING_SLOTS,
    WAREHOUSE_CAPACITY,
    get_garage_capacity,
    apply_garage_upgrades,
)
from constants import (
    BUILDING, FIELD, GRASS, ROAD, WORLD_HEIGHT_TILES, WORLD_WIDTH_TILES,
)
from crops import CROPS, get_crop_growth_weeks, get_crop_harvest_stages
from game_rules import FIELD_TYPES, UPGRADES
from game_logger import log
from inventory import get_inventory_item_ids
from financial_history import is_valid_transaction
from orchards import is_valid_tree_record, synchronize_orchard_seasons
from processing import (
    PROCESSING_RECIPES, PROCESSING_LEVELS, PROCESSING_UPGRADE_ID,
    initialize_processing_plant,
)
from restaurant import is_valid_restaurant_save_record
from time_system import TIME_FAST, TIME_NORMAL, TIME_WEEK_LENGTHS_MS
from vehicle_types import (
    VEHICLE_TYPE_DEFINITIONS, VehicleType, normalize_vehicle_type,
)


SAVE_VERSION = 4
LEGACY_SAVE_VERSIONS = {1, 2, 3}
SAVE_DIRECTORY = Path(__file__).resolve().parent.parent / "saves"
DEFAULT_SAVE_PATH = SAVE_DIRECTORY / "savegame.json"
SAVE_SLOT_COUNT = 8
MAX_SAVE_NAME_LENGTH = 32

REQUIRED_SAVE_KEYS = {
    "save_version",
    "day",
    "money",
    "world",
    "fields",
    "buildings",
}


def _atomic_write_json(path, data):
    """Azonos könyvtárbeli ideiglenes fájlból atomikusan cseréli a mentést."""
    path = Path(path)
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("w", encoding="utf-8") as save_file:
            json.dump(data, save_file, ensure_ascii=False, indent=4)
            save_file.flush()
            os.fsync(save_file.fileno())
        os.replace(temporary_path, path)
        return True
    except (OSError, TypeError, ValueError):
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _migrate_legacy_crop_data(data):
    """A régi mentések hiányzó növényadatait kompatibilis alapértékekkel pótolja."""
    if not isinstance(data, dict):
        return

    fields = data.get("fields")
    if isinstance(fields, list):
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_type = field.setdefault("field_type", "field_4x4")
            definition = FIELD_TYPES.get(field_type)
            if definition is not None:
                field.setdefault("width", definition["width"])
                field.setdefault("height", definition["height"])
            growth = field.get("growth", 0)
            valid_growth = (
                isinstance(growth, (int, float))
                and not isinstance(growth, bool)
                and math.isfinite(growth)
            )
            if "crop" not in field:
                field["crop"] = "wheat" if valid_growth and growth > 0 else None
            crop = CROPS.get(field.get("crop"))
            field.setdefault("fertilized", False)
            field.setdefault("watered", False)
            field.setdefault("sprayed", False)
            had_lifecycle_state = "harvest_count" in field
            field.setdefault("harvest_count", 0)
            field.setdefault("planted_at_week", None)
            field.setdefault("last_harvest_at_week", None)
            field.setdefault("next_maturity_at_week", None)
            # Ismeretlen régi vetési időpontból nem találunk ki lejáratot.
            field.setdefault("expires_at_week", None)
            field.setdefault("late_harvest_active", False)
            field.setdefault("late_harvest_started_at_week", None)
            field.setdefault("late_harvest_expires_at_week", None)
            field.setdefault("missed_harvest_count", 0)
            field.setdefault("annual_cycle_year", None)
            field.setdefault("annual_harvest_state", None)
            legacy_growth = field.pop("growth_days", None)
            field.pop("tractor_task_status", None)
            field.pop("tractor_queue_position", None)
            field.pop("tractor_task_type", None)
            if crop is None or not valid_growth:
                field.setdefault(
                    "growth_weeks",
                    legacy_growth if legacy_growth is not None else 0,
                )
                field.setdefault("harvestable", False)
                continue
            growth_weeks = round(growth * get_crop_growth_weeks(crop) / 100)
            if not had_lifecycle_state and len(get_crop_harvest_stages(crop)) > 1:
                # A régi, egyszeri aratású mentés százalékos előrehaladását
                # az új első szakasz hosszára vetítjük át.
                field["growth_weeks"] = growth_weeks
            else:
                field.setdefault(
                    "growth_weeks",
                    legacy_growth if legacy_growth is not None else growth_weeks,
                )
            field.setdefault("harvestable", growth >= 100)

    buildings = data.get("buildings")
    if isinstance(buildings, list):
        for building in buildings:
            if not isinstance(building, dict):
                continue
            if building.get("type") == "warehouse":
                # A Raktár kapacitása konfigurációs érték, ezért a régi mentések
                # is automatikusan a mindenkori alapkapacitást használják.
                building["capacity"] = WAREHOUSE_CAPACITY
                inventory = building.get("inventory")
                if not isinstance(inventory, dict):
                    inventory = {"wheat": building.pop("wheat", 0)}
                    building["inventory"] = inventory
                for item_id in get_inventory_item_ids():
                    inventory.setdefault(item_id, 0)
            elif building.get("type") == "animal_pen":
                building.setdefault(FOOD_STOCK_KEY, 0)
                building.setdefault(WATER_STOCK_KEY, 0)
            elif building.get("type") == "orchard":
                # A Gyümölcsös bevezetése előtti mentések üres területtel indulnak.
                building.setdefault("trees", [])
            elif building.get("type") == "processing_plant":
                initialize_processing_plant(building)

    data.setdefault("purchased_upgrades", [])
    tractors = data.setdefault("tractors", [])
    if isinstance(tractors, list):
        for tractor in tractors:
            if isinstance(tractor, dict):
                tractor.setdefault("vehicle_type", VehicleType.TRACTOR.value)
    animals = data.setdefault("animals", [])
    if isinstance(animals, list):
        for index, animal in enumerate(animals):
            if not isinstance(animal, dict):
                continue
            animal.setdefault("visual_id", index + 1)
            animal.setdefault("facing_direction", "down")
            definition = ANIMAL_TYPES.get(animal.get("type"), {})
            for production in definition.get(
                    "periodic_products", {}).values():
                legacy_counter = (
                    animal.pop("days_since_last_manure", None)
                    if production["counter_key"] == "weeks_since_last_manure"
                    else None
                )
                animal.setdefault(
                    production["counter_key"],
                    legacy_counter if legacy_counter is not None else 0,
                )
            if animal.get("slaughter_state") != "waiting_for_storage":
                animal.pop("slaughter_state", None)


def _migrate_save_schema(data):
    """A korábbi sémákat kompatibilis alapértékekkel emeli."""
    if not isinstance(data, dict):
        return False
    version = data.get("save_version")
    if version == SAVE_VERSION:
        data.setdefault("vehicle_runtime", None)
        data.setdefault("financial_history", [])
        data.setdefault("restaurant_auto_sell", {})
        return True
    if version in LEGACY_SAVE_VERSIONS:
        _migrate_farmhouse_footprints(data)
        _migrate_farmhouse_levels(data)
        data["save_version"] = SAVE_VERSION
        data.setdefault("vehicle_runtime", None)
        data.setdefault("financial_history", [])
        data.setdefault("restaurant_auto_sell", {})
        return True
    return False


def _migrate_farmhouse_footprints(data):
    """A régi 4×4-es házat csak teljesen szabad hely esetén bővíti telekké."""
    world = data.get("world")
    buildings = data.get("buildings")
    if not isinstance(world, list) or not world or not isinstance(buildings, list):
        return
    world_height = len(world)
    world_width = min((len(row) for row in world), default=0)
    plot_width = BUILDING_TYPES["farmhouse"]["width"]
    plot_height = BUILDING_TYPES["farmhouse"]["height"]
    house_width, house_height = FARMHOUSE_BUILDING_SIZE
    offset_row, offset_col = FARMHOUSE_BUILDING_OFFSET

    for farmhouse in buildings:
        if (not isinstance(farmhouse, dict)
                or farmhouse.get("type") != "farmhouse"):
            continue
        if (farmhouse.get("width"), farmhouse.get("height")) == (
                plot_width, plot_height):
            farmhouse.pop("legacy_footprint", None)
            continue
        if (farmhouse.get("width"), farmhouse.get("height")) != (
                house_width, house_height):
            farmhouse["legacy_footprint"] = True
            continue

        old_row, old_col = farmhouse.get("row"), farmhouse.get("col")
        if not _is_plain_int(old_row) or not _is_plain_int(old_col):
            farmhouse["legacy_footprint"] = True
            continue
        plot_row = old_row - offset_row
        plot_col = old_col - offset_col
        inside_world = (
            plot_row >= 0 and plot_col >= 0
            and plot_row + plot_height <= world_height
            and plot_col + plot_width <= world_width
        )
        old_tiles = set(_area_tiles(
            old_row, old_col, house_width, house_height,
        ))
        plot_tiles = set(_area_tiles(
            plot_row, plot_col, plot_width, plot_height,
        )) if inside_world else set()
        can_expand = inside_world and all(
            world[row][col] == (BUILDING if (row, col) in old_tiles else GRASS)
            for row, col in plot_tiles
        )
        if not can_expand:
            # Nem mozgatunk vagy bontunk le játékos-objektumot a migráció kedvéért.
            farmhouse["legacy_footprint"] = True
            continue

        farmhouse.update({
            "row": plot_row, "col": plot_col,
            "width": plot_width, "height": plot_height,
        })
        farmhouse.pop("legacy_footprint", None)
        for row, col in plot_tiles:
            world[row][col] = BUILDING
        for vehicle in data.get("tractors", []):
            if (
                isinstance(vehicle, dict)
                and vehicle.get("parking_type") == "farmhouse"
                and vehicle.get("parking_row") == old_row
                and vehicle.get("parking_col") == old_col
            ):
                vehicle["parking_row"] = plot_row
                vehicle["parking_col"] = plot_col


def _migrate_farmhouse_levels(data):
    """A korábbi 4×4-es grafikájú Farmházakat II. szintként őrzi meg."""
    buildings = data.get("buildings")
    if not isinstance(buildings, list):
        return
    for building in buildings:
        if isinstance(building, dict) and building.get("type") == "farmhouse":
            building.setdefault("farmhouse_level", FARMHOUSE_LEGACY_LEVEL)


def _prepare_world_data(data):
    """Ellenőrzi, majd jobbra és lefelé adatvesztés nélkül kibővíti a világot."""
    if not isinstance(data, dict):
        return False
    world = data.get("world")
    if not isinstance(world, list) or not world:
        return False
    if not all(isinstance(row, list) for row in world):
        return False
    if not all(
        isinstance(tile, int) and not isinstance(tile, bool)
        for row in world for tile in row
    ):
        return False

    actual_width = max((len(row) for row in world), default=0)
    actual_height = len(world)
    if actual_width <= 0 or actual_height <= 0:
        return False

    saved_width = data.get("world_width_tiles", actual_width)
    saved_height = data.get("world_height_tiles", actual_height)
    if (not isinstance(saved_width, int) or isinstance(saved_width, bool)
            or not isinstance(saved_height, int) or isinstance(saved_height, bool)
            or saved_width <= 0 or saved_height <= 0):
        return False

    target_width = max(actual_width, saved_width, WORLD_WIDTH_TILES)
    target_height = max(actual_height, saved_height, WORLD_HEIGHT_TILES)
    for row in world:
        row.extend(GRASS for _ in range(target_width - len(row)))
    for _ in range(target_height - len(world)):
        world.append([GRASS for _ in range(target_width)])

    data["world_width_tiles"] = target_width
    data["world_height_tiles"] = target_height
    return True


def _create_save_data(game_state):
    """Csak a nem újraszámolható, JSON-kompatibilis játékállapotot gyűjti össze."""
    game_state.synchronize_processing_upgrades()
    vehicles = getattr(game_state, "vehicles", None)
    bank_system = getattr(game_state, "bank_system", None)
    quest_manager = getattr(game_state, "quest_manager", None)
    restaurant_system = getattr(game_state, "restaurant_system", None)
    return {
        "save_version": SAVE_VERSION,
        "day": game_state.game_time.day,
        "time_speed": game_state.game_time.current_time_speed,
        "week_progress": game_state.game_time.week_progress,
        "money": game_state.economy.money,
        "financial_history": game_state.economy.financial_history_save_record(),
        "world": game_state.world,
        "world_width_tiles": len(game_state.world[0]) if game_state.world else 0,
        "world_height_tiles": len(game_state.world),
        "fields": game_state.fields,
        "buildings": [{k: v for k, v in b.items() if k != "_garage_level"}
                      for b in game_state.buildings],
        "purchased_upgrades": sorted(game_state.purchased_upgrades),
        "tractors": vehicles.save_records() if vehicles is not None else [],
        "vehicle_runtime": (
            vehicles.runtime_save_record(game_state.fields, game_state.buildings)
            if vehicles is not None else None
        ),
        "animals": getattr(game_state, "animals", []),
        "bank": bank_system.to_save_record() if bank_system is not None else None,
        "quest": (
            quest_manager.to_save_record() if quest_manager is not None else None
        ),
        "restaurant_auto_sell": (
            restaurant_system.to_save_record()
            if restaurant_system is not None else {}
        ),
    }


def _is_valid_save_data(data):
    """A kisebb validátorokból felépíti a teljes mentésellenőrzést."""
    if not isinstance(data, dict) or not REQUIRED_SAVE_KEYS.issubset(data):
        return False
    if not isinstance(data["day"], int) or isinstance(data["day"], bool):
        return False
    if data["day"] < 1:
        return False
    if "time_speed" in data:
        time_speed = data["time_speed"]
        if isinstance(time_speed, bool) or time_speed not in TIME_WEEK_LENGTHS_MS:
            return False
    if "week_progress" in data:
        progress = data["week_progress"]
        if (not isinstance(progress, (int, float))
                or isinstance(progress, bool)
                or not math.isfinite(progress)
                or not 0 <= progress < 1):
            return False
    if not isinstance(data["money"], (int, float)) or isinstance(data["money"], bool):
        return False
    if not math.isfinite(data["money"]):
        return False
    history = data.get("financial_history", [])
    if not isinstance(history, list) or not all(
            is_valid_transaction(item) for item in history):
        return False
    restaurant_auto_sell = data.get("restaurant_auto_sell", {})
    if not is_valid_restaurant_save_record(restaurant_auto_sell):
        return False
    if not _validate_tiles(data):
        return False
    if not _validate_buildings(data):
        return False
    if not _validate_fields(data):
        return False
    if not _validate_vehicles(data):
        return False
    runtime = data.get("vehicle_runtime")
    if runtime is not None and not (
        isinstance(runtime, dict)
        and isinstance(runtime.get("tasks"), list)
        and isinstance(runtime.get("queue"), list)
        and isinstance(runtime.get("assets"), list)
        and isinstance(runtime.get("next_task_order"), int)
        and not isinstance(runtime.get("next_task_order"), bool)
    ):
        return False
    if not _validate_animals(data):
        return False
    if not is_valid_loan_record(data.get("bank")):
        return False
    if data.get("quest") is not None and not isinstance(data.get("quest"), dict):
        return False
    purchased_upgrades = data.get("purchased_upgrades")
    if not isinstance(purchased_upgrades, list):
        return False
    if (len(purchased_upgrades) != len(set(purchased_upgrades))
            or not all(item in UPGRADES for item in purchased_upgrades)):
        return False
    return True


def _is_plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_tiles(data):
    world = data.get("world")
    width = data.get("world_width_tiles")
    height = data.get("world_height_tiles")
    known_tiles = {GRASS, ROAD, FIELD, BUILDING}
    return (
        isinstance(world, list)
        and bool(world)
        and _is_plain_int(width) and width > 0
        and _is_plain_int(height) and height > 0
        and len(world) == height
        and all(
            isinstance(row, list)
            and len(row) == width
            and all(_is_plain_int(tile) and tile in known_tiles for tile in row)
            for row in world
        )
    )


def _area_tiles(row, col, width, height):
    return {
        (row + row_offset, col + col_offset)
        for row_offset in range(height)
        for col_offset in range(width)
    }


def _area_is_inside(row, col, width, height, world_width, world_height):
    return (
        row >= 0 and col >= 0 and width > 0 and height > 0
        and row + height <= world_height
        and col + width <= world_width
    )


def _validate_processing_line(line):
    if not isinstance(line, dict):
        return False
    batch = line.get("processing_batch")
    return (
        (line.get("active_recipe") is None or line.get("active_recipe") in PROCESSING_RECIPES)
        and _is_plain_int(line.get("processing_week"))
        and _is_plain_int(line.get("processed_this_week"))
        and line["processed_this_week"] >= 0
        and (batch is None or (
            isinstance(batch, dict)
            and batch.get("recipe_id") in PROCESSING_RECIPES
            and _is_plain_int(batch.get("started_week"))
            and all(isinstance(items, dict) and all(
                item_id in get_inventory_item_ids()
                and _is_plain_int(amount) and amount >= 0
                for item_id, amount in items.items()
            ) for items in (batch.get("inputs"), batch.get("outputs")))
        ))
    )


def _validate_inventory(building):
    if building["type"] == "processing_plant":
        inventory = building.get("processing_inventory")
        in_transit = building.get("processing_in_transit")
        additional_lines = building.get("additional_processing_lines", [])
        if not isinstance(additional_lines, list):
            return False
        definition = next((level for level in PROCESSING_LEVELS.values()
                           if level["lines"] == len(additional_lines) + 1), None)
        return (
            definition is not None
            and building.get("processing_capacity") == definition["storage"]
            and all(_validate_processing_line(line)
                    for line in [building, *additional_lines])
            and isinstance(inventory, dict)
            and all(
                item_id in get_inventory_item_ids()
                and _is_plain_int(amount) and amount >= 0
                for item_id, amount in inventory.items()
            )
            and sum(inventory.values()) <= building["processing_capacity"]
            and isinstance(in_transit, dict)
            and all(
                item_id in get_inventory_item_ids()
                and _is_plain_int(amount) and amount >= 0
                for item_id, amount in in_transit.items()
            )
        )
    if building["type"] != "warehouse":
        return True
    capacity = building.get("capacity")
    inventory = building.get("inventory")
    known_items = set(get_inventory_item_ids())
    return (
        _is_plain_int(capacity) and capacity >= 0
        and isinstance(inventory, dict)
        and set(inventory).issubset(known_items)
        and all(_is_plain_int(amount) and amount >= 0
                for amount in inventory.values())
        and sum(inventory.values()) <= capacity
    )


def _validate_buildings(data):
    buildings = data.get("buildings")
    if not isinstance(buildings, list):
        return False
    world = data["world"]
    world_width = data["world_width_tiles"]
    world_height = data["world_height_tiles"]
    occupied = set()
    for building in buildings:
        if not isinstance(building, dict):
            return False
        building_type = building.get("type")
        definition = BUILDING_TYPES.get(building_type)
        if definition is None:
            return False
        row, col = building.get("row"), building.get("col")
        width, height = building.get("width"), building.get("height")
        if not all(_is_plain_int(value) for value in (row, col, width, height)):
            return False
        legacy_farmhouse = (
            building_type == "farmhouse"
            and building.get("legacy_footprint") is True
            and (width, height) == FARMHOUSE_BUILDING_SIZE
        )
        if (width != definition["width"] or height != definition["height"]):
            if not legacy_farmhouse:
                return False
        if not _area_is_inside(
                row, col, width, height, world_width, world_height):
            return False
        tiles = _area_tiles(row, col, width, height)
        if occupied.intersection(tiles):
            return False
        occupied.update(tiles)
        if not _validate_inventory(building):
            return False
        if (building_type == "processing_plant"
                and building.get("additional_processing_lines")
                and PROCESSING_UPGRADE_ID not in data.get("purchased_upgrades", [])):
            return False
        if (
            building_type == "farmhouse"
            and building.get("farmhouse_level") not in FARMHOUSE_LEVELS
        ):
            return False
        if building_type == "animal_pen" and any(
            not _is_plain_int(building.get(stock_key, 0))
            or building.get(stock_key, 0) < 0
            for stock_key in (FOOD_STOCK_KEY, WATER_STOCK_KEY)
        ):
            return False
        if building_type == "orchard":
            trees = building.get("trees")
            if (
                not isinstance(trees, list)
                or len(trees) > 4
                or not all(isinstance(tree, dict) for tree in trees)
                or len({tree.get("slot") for tree in trees}) != len(trees)
                or not all(is_valid_tree_record(tree, building) for tree in trees)
            ):
                return False
    world_tiles = {
        (row, col)
        for row, world_row in enumerate(world)
        for col, tile in enumerate(world_row)
        if tile == BUILDING
    }
    return occupied == world_tiles


def _validate_fields(data):
    fields = data.get("fields")
    if not isinstance(fields, list):
        return False
    world = data["world"]
    world_width = data["world_width_tiles"]
    world_height = data["world_height_tiles"]
    occupied = set()
    required_keys = {"row", "col", "crop", "growth"}
    for field in fields:
        if not isinstance(field, dict) or not required_keys.issubset(field):
            return False
        field_type = field.get("field_type")
        definition = FIELD_TYPES.get(field_type)
        if definition is None:
            return False
        row, col = field["row"], field["col"]
        width, height = field.get("width"), field.get("height")
        if not all(_is_plain_int(value) for value in (row, col, width, height)):
            return False
        if width != definition["width"] or height != definition["height"]:
            return False
        if not _area_is_inside(
                row, col, width, height, world_width, world_height):
            return False
        tiles = _area_tiles(row, col, width, height)
        if occupied.intersection(tiles):
            return False
        occupied.update(tiles)
        growth = field["growth"]
        harvest_count = field.get("harvest_count", 0)
        lifecycle_weeks = (
            field.get("planted_at_week"),
            field.get("last_harvest_at_week"),
            field.get("next_maturity_at_week"),
            field.get("expires_at_week"),
            field.get("late_harvest_started_at_week"),
            field.get("late_harvest_expires_at_week"),
            field.get("annual_cycle_year"),
        )
        if (field["crop"] not in (None, *CROPS)
                or not isinstance(growth, (int, float))
                or isinstance(growth, bool) or not math.isfinite(growth)
                or not 0 <= growth <= 100
                or not _is_plain_int(field.get("growth_weeks", 0))
                or field.get("growth_weeks", 0) < 0
                or not isinstance(field.get("harvestable", False), bool)
                or not isinstance(field.get("fertilized", False), bool)
                or not isinstance(field.get("watered", False), bool)
                or not isinstance(field.get("sprayed", False), bool)
                or not isinstance(field.get("late_harvest_active", False), bool)
                or field.get("annual_harvest_state") not in (
                    None, "ineligible", "growing", "ripe", "harvested", "lost",
                )
                or not _is_plain_int(harvest_count) or harvest_count < 0
                or not _is_plain_int(field.get("missed_harvest_count", 0))
                or not 0 <= field.get("missed_harvest_count", 0) <= harvest_count
                or any(
                    value is not None
                    and (not _is_plain_int(value) or value < 0)
                    for value in lifecycle_weeks
                )):
            return False
    world_tiles = {
        (row, col)
        for row, world_row in enumerate(world)
        for col, tile in enumerate(world_row)
        if tile == FIELD
    }
    return occupied == world_tiles


def _validate_vehicles(data):
    apply_garage_upgrades(data["buildings"], data.get("purchased_upgrades", []))
    vehicles = data.get("tractors", [])
    if not isinstance(vehicles, list):
        return False
    garage_capacity = sum(get_garage_capacity(b) for b in data["buildings"])
    # The original starter tractor may live at the Farmhouse before a garage exists.
    if garage_capacity and len(vehicles) > garage_capacity:
        return False
    vehicle_ids = set()
    vehicle_types_by_id = {}
    attachments = []
    occupied_slots = set()
    parking_buildings = {
        (building["type"], building["row"], building["col"])
        for building in data["buildings"]
        if building["type"] in ("garage", "farmhouse")
    }
    for vehicle in vehicles:
        if not isinstance(vehicle, dict):
            return False
        vehicle_id = vehicle.get("id")
        if (not _is_plain_int(vehicle_id) or vehicle_id <= 0
                or vehicle_id in vehicle_ids):
            return False
        vehicle_ids.add(vehicle_id)
        vehicle_type = normalize_vehicle_type(
            vehicle.get("vehicle_type", VehicleType.TRACTOR.value),
        )
        if vehicle_type is None:
            return False
        vehicle_types_by_id[vehicle_id] = vehicle_type
        parking = (
            vehicle.get("parking_type"), vehicle.get("parking_row"),
            vehicle.get("parking_col"),
        )
        if parking not in parking_buildings:
            return False
        definition = VEHICLE_TYPE_DEFINITIONS[vehicle_type]
        if definition.get("towable") and parking[0] != "garage":
            return False
        if definition.get("towable"):
            cargo_type = vehicle.get("cargo_type", "empty")
            cargo_amount = vehicle.get("cargo_amount", 0)
            if (
                cargo_type not in definition.get("cargo_states", ("empty",))
                or not _is_plain_int(cargo_amount)
                or cargo_amount < 0
                or (cargo_type == "empty" and cargo_amount != 0)
            ):
                return False
        slot_id = vehicle.get("slot_id")
        if parking[0] == "garage":
            home = next(b for b in data["buildings"]
                        if (b["type"], b["row"], b["col"]) == parking)
            if (not _is_plain_int(slot_id)
                    or not 0 <= slot_id < get_garage_capacity(home)):
                return False
            occupancy = (parking[1], parking[2], slot_id)
            if occupancy in occupied_slots:
                return False
            occupied_slots.add(occupancy)
        elif slot_id is not None:
            return False
        attached_to_id = vehicle.get("attached_to_id")
        if attached_to_id is not None:
            if not _is_plain_int(attached_to_id) or attached_to_id <= 0:
                return False
            attachments.append((vehicle_id, attached_to_id))
    attached_tractors = set()
    for implement_id, towing_vehicle_id in attachments:
        implement_type = vehicle_types_by_id.get(implement_id)
        towing_type = vehicle_types_by_id.get(towing_vehicle_id)
        definition = VEHICLE_TYPE_DEFINITIONS.get(implement_type, {})
        if (
            not definition.get("towable")
            or towing_type not in definition.get("compatible_towing_types", ())
            or towing_vehicle_id in attached_tractors
        ):
            return False
        attached_tractors.add(towing_vehicle_id)
    return True


def _validate_animals(data):
    animals = data.get("animals", [])
    if not isinstance(animals, list):
        return False
    animal_keys = {"type", "row", "col", "pen_row", "pen_col"}
    if not all(
            isinstance(animal, dict)
            and animal_keys.issubset(animal)
            and animal["type"] in ANIMAL_TYPES
            and all(
                isinstance(animal[key], int)
                and not isinstance(animal[key], bool)
                and animal[key] >= 0
                for key in ("row", "col", "pen_row", "pen_col")
            )
            for animal in animals):
        return False
    for animal in animals:
        definition = ANIMAL_TYPES[animal["type"]]
        if (
            not _is_plain_int(animal.get("visual_id", 0))
            or animal.get("visual_id", 0) <= 0
            or animal.get("facing_direction", "down")
            not in ("up", "right", "down", "left")
        ):
            return False
        for production in definition.get("periodic_products", {}).values():
            counter = animal.get(production["counter_key"], 0)
            if (
                not isinstance(counter, int)
                or isinstance(counter, bool)
                or not 0 <= counter <= production["interval_weeks"]
            ):
                return False
        if animal.get("slaughter_state") not in (None, "waiting_for_storage"):
            return False
    if len({(animal["row"], animal["col"]) for animal in animals}) != len(animals):
        return False
    if len({animal.get("visual_id") for animal in animals}) != len(animals):
        return False
    checked_pen_groups = set()
    for animal in animals:
        pen = next(
            (
                building for building in data["buildings"]
                if building.get("type") == "animal_pen"
                and building.get("row") == animal["pen_row"]
                and building.get("col") == animal["pen_col"]
            ),
            None,
        )
        group = find_animal_pen_group(data["buildings"], pen)
        if (
            pen is None
            or (animal["row"], animal["col"]) not in get_pen_group_tiles(group)
        ):
            return False
        group_key = frozenset(
            (group_pen["row"], group_pen["col"])
            for group_pen in group
        )
        if group_key not in checked_pen_groups:
            checked_pen_groups.add(group_key)
            group_species = {
                candidate.get("type")
                for candidate in animals
                if (candidate.get("pen_row"), candidate.get("pen_col"))
                in group_key
            }
            if len(group_species) > 1:
                return False
    return True


def save_game(game_state, save_path=DEFAULT_SAVE_PATH):
    """A teljes központi játékállapotot UTF-8 JSON-fájlba menti."""
    if not _atomic_write_json(
            Path(save_path), _create_save_data(game_state)):
        log("A játék mentése nem sikerült.", "Save")
        return False

    log("Játék sikeresen elmentve.", "Save")
    return True


def get_slot_path(slot_id):
    """Ellenőrzött slotazonosítóból fix, biztonságos fájlnevet képez."""
    if (not isinstance(slot_id, int) or isinstance(slot_id, bool)
            or not 1 <= slot_id <= SAVE_SLOT_COUNT):
        raise ValueError("Érvénytelen mentésihely-azonosító.")
    return SAVE_DIRECTORY / f"save_slot_{slot_id}.json"


def _read_json(path):
    try:
        with Path(path).open("r", encoding="utf-8") as save_file:
            return json.load(save_file)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _validate_slot_document(document, expected_slot_id):
    if not isinstance(document, dict):
        return None
    metadata = document.get("metadata")
    game_data = document.get("game_state")
    if not isinstance(metadata, dict) or not isinstance(game_data, dict):
        return None
    save_name = metadata.get("save_name")
    saved_at = metadata.get("saved_at")
    if (not isinstance(save_name, str) or not save_name.strip()
            or len(save_name) > MAX_SAVE_NAME_LENGTH
            or metadata.get("slot_id") != expected_slot_id
            or metadata.get("save_version") not in ({SAVE_VERSION} | LEGACY_SAVE_VERSIONS)
            or not isinstance(saved_at, str) or not saved_at
            or not isinstance(metadata.get("game_day"), int)
            or isinstance(metadata.get("game_day"), bool)):
        return None
    if not _migrate_save_schema(game_data):
        return None
    metadata["save_version"] = SAVE_VERSION
    _migrate_legacy_crop_data(game_data)
    if not _prepare_world_data(game_data):
        return None
    if (not _is_valid_save_data(game_data)
            or metadata["game_day"] != game_data["day"]):
        return None
    return metadata, game_data


def _migrate_legacy_save():
    """A régi savegame.json fájlt adatvesztés nélkül az üres első slotba másolja."""
    first_slot = get_slot_path(1)
    if first_slot.exists() or not DEFAULT_SAVE_PATH.exists():
        return
    game_data = _read_json(DEFAULT_SAVE_PATH)
    if not isinstance(game_data, dict):
        return
    if not _migrate_save_schema(game_data):
        return
    _migrate_legacy_crop_data(game_data)
    if not _prepare_world_data(game_data):
        return
    if not _is_valid_save_data(game_data):
        return
    document = {
        "metadata": {
            "save_name": "Korábbi mentés",
            "slot_id": 1,
            "save_version": SAVE_VERSION,
            "saved_at": datetime.fromtimestamp(
                DEFAULT_SAVE_PATH.stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M"),
            "game_day": game_data["day"],
        },
        "game_state": game_data,
    }
    if not _atomic_write_json(first_slot, document):
        # A régi fájl érintetlen marad; a többi slot ettől még használható.
        return


def get_slot_metadata(slot_id):
    """Üres, sérült vagy érvényes állapotként ír le egyetlen mentési helyet."""
    path = get_slot_path(slot_id)
    if not path.exists():
        return {"slot_id": slot_id, "status": "empty", "path": path}
    validated = _validate_slot_document(_read_json(path), slot_id)
    if validated is None:
        return {"slot_id": slot_id, "status": "corrupt", "path": path}
    metadata, _ = validated
    return {
        "slot_id": slot_id,
        "status": "valid",
        "path": path,
        "save_name": metadata["save_name"],
        "saved_at": metadata["saved_at"],
        "game_day": metadata["game_day"],
        "save_version": metadata["save_version"],
    }


def get_save_slots():
    """Mindig pontosan nyolc, sorszám szerint rendezett slotleírást ad vissza."""
    _migrate_legacy_save()
    return [
        get_slot_metadata(slot_id)
        for slot_id in range(1, SAVE_SLOT_COUNT + 1)
    ]


def slot_exists(slot_id):
    return get_slot_metadata(slot_id)["status"] == "valid"


def save_game_to_slot(game_state, slot_id, save_name, saved_at=None):
    """Metaadatokkal együtt, fix nevű slotfájlba menti a játékállapotot."""
    try:
        path = get_slot_path(slot_id)
    except ValueError:
        return False
    if not isinstance(save_name, str):
        return False
    normalized_name = save_name.strip()
    if not normalized_name or len(normalized_name) > MAX_SAVE_NAME_LENGTH:
        return False
    document = {
        "metadata": {
            "save_name": normalized_name,
            "slot_id": slot_id,
            "save_version": SAVE_VERSION,
            "saved_at": saved_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
            "game_day": game_state.game_time.day,
        },
        "game_state": _create_save_data(game_state),
    }
    if not _atomic_write_json(path, document):
        log("A játék mentése nem sikerült.", "Save")
        return False
    log("Játék sikeresen elmentve.", "Save")
    return True


def _apply_game_data(game_state, data):
    """Az ellenőrzött adatokat a meglévő objektumreferenciák megtartásával tölti be."""
    game_state.world[:] = data["world"]
    game_state.fields[:] = data["fields"]
    game_state.buildings[:] = data["buildings"]
    if hasattr(game_state, "animals"):
        game_state.animals[:] = data.get("animals", [])
        synchronize_pen_group_stocks(
            game_state.buildings, game_state.animals,
        )
    game_state.economy.money = float(data["money"])
    game_state.economy.load_financial_history(data.get("financial_history", []))
    bank_system = getattr(game_state, "bank_system", None)
    if bank_system is not None:
        bank_system.load_save_record(data.get("bank"))
    # A régi `day` mező 1-től induló értékét a GameTime kompatibilitási
    # tulajdonsága alakítja át a belső, 0-tól induló eltelt hetekre.
    game_state.game_time.day = data["day"]
    saved_time_speed = data.get("time_speed", TIME_NORMAL)
    # A korábbi 3× mentések betölthetők maradnak, de a már nem
    # választható fokozat helyett a jelenlegi leggyorsabb, 2× mód indul.
    if saved_time_speed == TIME_FAST:
        saved_time_speed = TIME_NORMAL
    game_state.game_time.set_time_speed(saved_time_speed)
    # A mező opcionális: a korábbi mentések biztonságosan a hét elejéről
    # folytatódnak, az új mentések pedig pontosan a mentett részprogresszről.
    game_state.game_time.restore_week_progress(data.get("week_progress", 0.0))
    synchronize_orchard_seasons(
        game_state.buildings, game_state.game_time.elapsed_weeks, legacy=True,
    )
    game_state.purchased_upgrades.clear()
    game_state.purchased_upgrades.update(data.get("purchased_upgrades", []))
    game_state.synchronize_processing_upgrades()
    quest_manager = getattr(game_state, "quest_manager", None)
    if quest_manager is not None:
        quest_manager.load_save_record(data.get("quest"))
    restaurant_system = getattr(game_state, "restaurant_system", None)
    if restaurant_system is not None:
        restaurant_system.load_save_record(data.get("restaurant_auto_sell"))
    vehicles = getattr(game_state, "vehicles", None)
    if vehicles is not None:
        vehicles.reset_for_loaded_game(
            game_state.world, game_state.fields, game_state.buildings,
            data.get("tractors"), animals=getattr(game_state, "animals", []),
            runtime_record=data.get("vehicle_runtime"),
        )
    else:
        tractor = getattr(game_state, "tractor", None)
        if tractor is not None:
            tractor.reset(game_state.fields)
            tractor.ensure_idle_position(game_state.world, game_state.buildings)


def load_game_from_slot(game_state, slot_id):
    """Csak érvényes, foglalt slotot tölt be; üres vagy sérült fájlt nem."""
    try:
        path = get_slot_path(slot_id)
    except ValueError:
        return False
    validated = _validate_slot_document(_read_json(path), slot_id)
    if validated is None:
        log(
            "A kiválasztott mentés hiányzik, sérült vagy nem kompatibilis.",
            "Load",
        )
        return False
    _, game_data = validated
    _apply_game_data(game_state, game_data)
    log("Játék sikeresen betöltve.", "Load")
    return True


def load_game(game_state, save_path=DEFAULT_SAVE_PATH):
    """A mentett adatokat a meglévő GameState objektumaiba tölti vissza."""
    path = Path(save_path)
    if not path.exists():
        log("Nem található mentés.", "Load")
        return False

    try:
        with path.open("r", encoding="utf-8") as save_file:
            data = json.load(save_file)
    except (OSError, UnicodeError, json.JSONDecodeError):
        log("A mentés sérült vagy nem olvasható.", "Load")
        return False

    if not _migrate_save_schema(data):
        log("A mentés verziója nem kompatibilis.", "Load")
        return False
    _migrate_legacy_crop_data(data)

    if not _prepare_world_data(data):
        log("A mentés sérült vagy nem olvasható.", "Load")
        return False

    if not isinstance(data, dict) or "save_version" not in data:
        log("A mentés sérült vagy nem olvasható.", "Load")
        return False
    if not _is_valid_save_data(data):
        log("A mentés sérült vagy nem olvasható.", "Load")
        return False

    _apply_game_data(game_state, data)

    log("Játék sikeresen betöltve.", "Load")
    return True
