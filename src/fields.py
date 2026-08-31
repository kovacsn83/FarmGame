import math
import random

from calendar_utils import get_year_and_week
from buildings import (
    get_free_capacity, get_total_capacity, get_total_inventory,
    get_warehouses, remove_item, store_crop,
)
from constants import FIELD, FIELD_SIZE, GRASS, ROAD
from crops import (
    CROPS, can_harvest_crop_in_week, crop_has_annual_perennial_cycle,
    crop_has_more_harvests,
    crop_has_recurring_harvest,
    crop_resets_fertilizer_after_harvest,
    get_late_harvest_weeks_remaining, LATE_HARVEST_YIELD_MULTIPLIER,
    get_crop_lifespan_weeks, get_crop_productive_year_range,
    get_current_base_yield,
    get_current_growth_weeks, next_harvest_stage_fits_current_season,
)
from game_logger import log
from game_rules import (
    FERTILIZER_BONUS, FIELD_TYPES, PEST_PENALTY, SPRAYING_BONUS, WATER_BONUS,
    WEED_PENALTY, YIELD_RANDOM_VARIATION, get_field_fertilizer_cost,
)


def has_adjacent_road(world, row, col, width, height):
    world_rows = len(world)
    world_cols = len(world[0]) if world else 0
    if row > 0:
        for c in range(width):
            if world[row - 1][col + c] == ROAD:
                return True

    for r in range(height):
        if col > 0 and world[row + r][col - 1] == ROAD:
            return True
        if col + width < world_cols and world[row + r][col + width] == ROAD:
            return True

    if row + height < world_rows:
        for c in range(width):
            if world[row + height][col + c] == ROAD:
                return True

    return False


def can_place_field(world, row, col, width, height=None):
    height = width if height is None else height
    if row < 0 or col < 0:
        return False
    world_rows = len(world)
    world_cols = len(world[0]) if world else 0
    if row > world_rows - height or col > world_cols - width:
        return False

    for r in range(height):
        for c in range(width):
            if world[row + r][col + c] != GRASS:
                return False

    return has_adjacent_road(world, row, col, width, height)


def place_field(world, fields, row, col, field_type="field_4x4"):
    definition = FIELD_TYPES[field_type]
    width = definition["width"]
    height = definition["height"]
    for r in range(height):
        for c in range(width):
            world[row + r][col + c] = FIELD

    fields.append({
        "row": row, "col": col, "field_type": field_type,
        "width": width, "height": height, "crop": None, "growth": 0,
        "growth_weeks": 0, "harvestable": False, "fertilized": False,
        "watered": False, "sprayed": False,
        "harvest_count": 0, "planted_at_week": None,
        "last_harvest_at_week": None, "next_maturity_at_week": None,
        "expires_at_week": None,
        "late_harvest_active": False,
        "late_harvest_started_at_week": None,
        "late_harvest_expires_at_week": None,
        "missed_harvest_count": 0,
        "annual_cycle_year": None, "annual_harvest_state": None,
    })


def remove_field(world, row, col, width, height=None):
    height = width if height is None else height
    for r in range(height):
        for c in range(width):
            world[row + r][col + c] = GRASS


def remove_field_data(fields, row, col):
    for field in fields:
        if field["row"] == row and field["col"] == col:
            fields.remove(field)
            return


def is_field(world, row, col):
    return world[row][col] == FIELD


def find_field_data(fields, row, col):
    for field in fields:
        width = field.get("width", FIELD_SIZE)
        height = field.get("height", FIELD_SIZE)
        if (field["row"] <= row < field["row"] + height
                and field["col"] <= col < field["col"] + width):
            return field
    return None


def print_field_info(field):
    field_type = FIELD_TYPES[field.get("field_type", "field_4x4")]
    print("=== Veteményes ===")
    print(f"Pozíció: ({field['row']}, {field['col']})")
    print(f"Típus: {field_type['name']}")
    print(f"Méret: {field.get('width', 4)}x{field.get('height', 4)}")
    crop = CROPS.get(field["crop"])
    print(f"Növény: {crop['name'] if crop else field['crop']}")
    print(f"Növekedés: {field['growth']} %")
    print(f"Hozamszorzó: {field_type['yield_multiplier'] * 100:.0f}%")
    vehicle_status = field.get("vehicle_task_status")
    task_type = field.get("vehicle_task_type")
    task_name = {
        "plant": "Ültetés",
        "fertilize": "Trágyázás",
        "harvest": "Aratás",
        "watering": "Locsolás",
        "spraying": "Permetezés",
    }.get(task_type, "Ültetés")
    if vehicle_status == "active":
        print(f"Állapot: {task_name} folyamatban")
    elif vehicle_status == "waiting":
        waiting_name = {
            "Ültetés": "Ültetésre",
            "Trágyázás": "Trágyázásra",
            "Aratás": "Aratásra",
            "Locsolás": "Locsolásra",
            "Permetezés": "Permetezésre",
        }[task_name]
        print(f"Állapot: {waiting_name} vár")
        queue_position = field.get("vehicle_queue_position")
        if queue_position is not None:
            print(f"Várólista: {queue_position}.")
    if crop:
        print(f"Eltelt idő: {field.get('growth_weeks', 0)} hét")
        print(
            f"Érési idő: "
            f"{get_current_growth_weeks(crop, field.get('harvest_count', 0))} hét"
        )
        print(f"Aratható: {'igen' if field.get('harvestable', False) else 'nem'}")
        print(
            f"Várható alaphozam: "
            f"{get_current_base_yield(crop, field.get('harvest_count', 0))} db"
        )
        print(f"Trágyázva: {'igen' if field.get('fertilized', False) else 'nem'}")
        print(f"Locsolva: {'igen' if field.get('watered', False) else 'nem'}")
        print(f"Permetezve: {'igen' if field.get('sprayed', False) else 'nem'}")
    print()


def plant_crop(field, crop, current_elapsed_week=None):
    if field["crop"] is not None:
        return False
    if crop not in CROPS:
        print(f"Ismeretlen növényazonosító: {crop}")
        return False
    field["crop"] = crop
    field["growth"] = 0
    field["growth_weeks"] = 0
    field["harvestable"] = False
    field["fertilized"] = False
    field["watered"] = False
    field["sprayed"] = False
    field["harvest_count"] = 0
    field["planted_at_week"] = current_elapsed_week
    field["last_harvest_at_week"] = None
    growth_weeks = get_current_growth_weeks(crop, 0)
    lifespan_weeks = get_crop_lifespan_weeks(crop)
    field["next_maturity_at_week"] = (
        current_elapsed_week + growth_weeks
        if current_elapsed_week is not None else None
    )
    field["expires_at_week"] = (
        current_elapsed_week + lifespan_weeks
        if current_elapsed_week is not None and lifespan_weeks is not None
        else None
    )
    _reset_late_harvest(field)
    field["missed_harvest_count"] = 0
    field["annual_cycle_year"] = None
    field["annual_harvest_state"] = None
    if crop_has_annual_perennial_cycle(crop) and current_elapsed_week is not None:
        calendar_year, _week = get_year_and_week(current_elapsed_week)
        field["annual_cycle_year"] = calendar_year
        field["annual_harvest_state"] = "ineligible"
    return True


def clear_crop(field):
    """Maradék feladat- vagy életciklusjelző nélkül kiüríti a mezőt."""
    field["crop"] = None
    field["growth"] = 0
    field["growth_weeks"] = 0
    field["harvestable"] = False
    field["fertilized"] = False
    field["watered"] = False
    field["sprayed"] = False
    field["harvest_count"] = 0
    field["planted_at_week"] = None
    field["last_harvest_at_week"] = None
    field["next_maturity_at_week"] = None
    field["expires_at_week"] = None
    _reset_late_harvest(field)
    field["missed_harvest_count"] = 0
    field["annual_cycle_year"] = None
    field["annual_harvest_state"] = None


def _reset_late_harvest(field):
    field["late_harvest_active"] = False
    field["late_harvest_started_at_week"] = None
    field["late_harvest_expires_at_week"] = None


def _advance_crop_cycle(
        field, crop, current_elapsed_week=None, missed=False):
    """Aratás vagy elveszett termés után ugyanazzal a szabállyal továbblép."""
    if crop_has_annual_perennial_cycle(crop):
        field["harvest_count"] = field.get("harvest_count", 0) + 1
        if missed:
            field["missed_harvest_count"] = (
                field.get("missed_harvest_count", 0) + 1
            )
        field["annual_harvest_state"] = "lost" if missed else "harvested"
        field["harvestable"] = False
        field["last_harvest_at_week"] = current_elapsed_week
        field["watered"] = False
        field["sprayed"] = False
        if crop_resets_fertilizer_after_harvest(crop):
            field["fertilized"] = False
        _reset_late_harvest(field)
        return True

    # Véges, többszedéses növénynél az elveszett termés nem számít
    # sikeres aratásnak, ezért nem oldhatja fel a következő szakaszt.
    if missed and not crop_has_recurring_harvest(crop):
        clear_crop(field)
        return False

    completed_harvests = field.get("harvest_count", 0) + 1
    field["harvest_count"] = completed_harvests
    if missed:
        field["missed_harvest_count"] = (
            field.get("missed_harvest_count", 0) + 1
        )
    has_more_harvests = crop_has_more_harvests(crop, completed_harvests)
    lifecycle_active = crop_lifecycle_is_active(field, current_elapsed_week)
    next_growth_weeks = get_current_growth_weeks(crop, completed_harvests)
    if (
        has_more_harvests
        and current_elapsed_week is not None
        and next_growth_weeks is not None
    ):
        _year, current_week = get_year_and_week(current_elapsed_week)
        has_more_harvests = next_harvest_stage_fits_current_season(
            crop, current_week, next_growth_weeks,
        )
    if not (has_more_harvests and lifecycle_active):
        clear_crop(field)
        return False

    field["growth"] = 0
    field["growth_weeks"] = 0
    field["harvestable"] = False
    field["last_harvest_at_week"] = current_elapsed_week
    field["next_maturity_at_week"] = (
        current_elapsed_week + next_growth_weeks
        if current_elapsed_week is not None else None
    )
    if crop_resets_fertilizer_after_harvest(crop):
        field["fertilized"] = False
    field["watered"] = False
    # A Paradicsom két aratása egyetlen termesztési ciklus: az egyszer
    # megszerzett permetezési bónusz és jelölés a második aratásig megmarad.
    # A második aratás után a clear_crop() törli az állapotot.
    if crop != "tomato":
        field["sprayed"] = False
    _reset_late_harvest(field)
    return True


def crop_lifecycle_is_active(field, current_elapsed_week):
    """Az ismeretlen régi lejáratot aktívnak, a pontos újat abszolútnak kezeli."""
    if crop_has_annual_perennial_cycle(field.get("crop")):
        if current_elapsed_week is None:
            return True
        return get_crop_age_years(field, current_elapsed_week) <= (
            get_crop_productive_year_range(field["crop"])[1]
        )
    expires_at = field.get("expires_at_week")
    return (
        expires_at is None
        or current_elapsed_week is None
        or current_elapsed_week < expires_at
    )


def get_crop_age_years(field, current_elapsed_week):
    """Az ültetés naptári évét 1. életévként kezeli."""
    planted_at = field.get("planted_at_week")
    if planted_at is None or current_elapsed_week is None:
        return 1
    planted_year, _ = get_year_and_week(planted_at)
    current_year, _ = get_year_and_week(current_elapsed_week)
    return max(1, current_year - planted_year + 1)


def synchronize_annual_crop_cycle(field, current_elapsed_week):
    """Az éves évelő állapotát menthető, adatvezérelt naptári ciklushoz igazítja."""
    crop_id = field.get("crop")
    productive_range = get_crop_productive_year_range(crop_id)
    if productive_range is None or current_elapsed_week is None:
        return
    calendar_year, current_week = get_year_and_week(current_elapsed_week)
    age = get_crop_age_years(field, current_elapsed_week)
    first_year, last_year = productive_range
    if age > last_year:
        return

    if field.get("annual_cycle_year") != calendar_year:
        previous_state = field.get("annual_harvest_state")
        field["annual_cycle_year"] = calendar_year
        field["annual_harvest_state"] = (
            "growing" if first_year <= age <= last_year else "ineligible"
        )
        field["harvestable"] = False
        # A telepítés évében elvégzett gondozás az első, második évi
        # termést készíti elő. A későbbi ciklusok aratáskor vagy elveszett
        # terméskor már külön lenullázzák ezeket a bónuszokat.
        entering_first_productive_year = (
            previous_state == "ineligible" and age == first_year
        )
        if not entering_first_productive_year:
            field["watered"] = False
            field["fertilized"] = False
            field["sprayed"] = False
        _reset_late_harvest(field)
        if age >= first_year:
            field["growth"] = 100
            field["growth_weeks"] = get_current_growth_weeks(crop_id, 0)

    state = field.get("annual_harvest_state")
    if not first_year <= age <= last_year or state in ("harvested", "lost"):
        field["harvestable"] = False
        return
    normal_window = can_harvest_crop_in_week(crop_id, current_week)
    if normal_window and field.get("growth", 0) >= 100:
        field["annual_harvest_state"] = "ripe"
        field["harvestable"] = True


def can_fertilize_field(
        field, include_task_status=True, allow_mature=False):
    """Megadja, hogy a mező aktuális növekedési ciklusa trágyázható-e."""
    if field is None:
        return False
    if include_task_status and field.get("vehicle_task_status") is not None:
        return False
    return (
        field.get("crop") in CROPS
        and (
            allow_mature
            or (
                crop_has_annual_perennial_cycle(field.get("crop"))
                and field.get("annual_harvest_state") in ("growing", "ripe")
            )
            or (
                field.get("growth", 0) < 100
                and not field.get("harvestable", False)
            )
        )
        and not field.get("fertilized", False)
    )


def fertilize_crop(field, buildings, allow_mature=False):
    """A munka végén a teljes termőföld méretköltségét felhasználja."""
    if not can_fertilize_field(
            field, include_task_status=False, allow_mature=allow_mature):
        return False
    fertilizer_cost = get_field_fertilizer_cost(field)
    if fertilizer_cost is None:
        return False
    if not remove_item(buildings, "manure", fertilizer_cost):
        return False
    field["fertilized"] = True
    return True


def can_water_field(field, include_task_status=True):
    """Jelzi, hogy a teljes Veteményes megkaphatja-e a következő hozambónuszt."""
    if field is None:
        return False
    if include_task_status and field.get("vehicle_task_status") is not None:
        return False
    if (
        crop_has_annual_perennial_cycle(field.get("crop"))
        and field.get("annual_harvest_state") in ("harvested", "lost")
    ):
        return False
    return field.get("crop") in CROPS and not field.get("watered", False)


def water_crop(field):
    """A Traktor munkájának végén egyszer locsolttá teszi a Veteményest."""
    if not can_water_field(field, include_task_status=False):
        return False
    field["watered"] = True
    return True


def can_spray_field(field, include_task_status=True, allow_mature=False):
    """Jelzi, hogy az aktuális termési ciklus még permetezhető-e."""
    if field is None:
        return False
    if include_task_status and field.get("vehicle_task_status") is not None:
        return False
    if (
        crop_has_annual_perennial_cycle(field.get("crop"))
        and field.get("annual_harvest_state") in ("harvested", "lost")
    ):
        return False
    return (
        field.get("crop") in CROPS
        and (
            allow_mature
            or crop_has_annual_perennial_cycle(field.get("crop"))
            or (
                field.get("growth", 0) < 100
                and not field.get("harvestable", False)
            )
        )
        and not field.get("sprayed", False)
    )


def spray_crop(field, allow_mature=False):
    """A Traktor munkájának végén aktiválja a permetezési hozambónuszt."""
    if not can_spray_field(
            field, include_task_status=False, allow_mature=allow_mature):
        return False
    field["sprayed"] = True
    return True


def grow_crops(fields, current_elapsed_week=None, notification_manager=None):
    late_entries = []
    for field in fields:
        crop = CROPS.get(field.get("crop"))
        if field.get("crop") is not None and crop is None:
            print(f"Ismeretlen növényazonosító: {field['crop']}")
            continue
        if crop_has_annual_perennial_cycle(field.get("crop")):
            synchronize_annual_crop_cycle(field, current_elapsed_week)
        if (
            crop is not None
            and not crop_lifecycle_is_active(field, current_elapsed_week)
        ):
            # Egy korábban elfogadott járműfeladat biztonságosan befejeződhet.
            if field.get("vehicle_task_status") is None:
                clear_crop(field)
            continue
        if crop is not None and field.get("growth", 0) < 100:
            growth_time = get_current_growth_weeks(
                crop, field.get("harvest_count", 0),
            )
            if growth_time is None:
                continue
            # A sorosított kulcs neve a régi mentések kompatibilitása miatt marad.
            elapsed_weeks = field.get("growth_weeks")
            if elapsed_weeks is None:
                elapsed_weeks = round(
                    field.get("growth", 0) * growth_time / 100,
                )
            field["growth_weeks"] = min(growth_time, elapsed_weeks + 1)
            field["growth"] = min(
                100, round(field["growth_weeks"] * 100 / growth_time)
            )
            field["harvestable"] = field["growth_weeks"] >= growth_time

        if (
            crop is not None
            and crop_has_annual_perennial_cycle(field.get("crop"))
            and field.get("annual_harvest_state") in (
                "ineligible", "harvested", "lost",
            )
        ):
            continue

        if (
            crop is None
            or current_elapsed_week is None
            or field.get("growth", 0) < 100
        ):
            continue

        late_expires = field.get("late_harvest_expires_at_week")
        if field.get("late_harvest_active", False):
            if (
                late_expires is not None
                and current_elapsed_week >= late_expires
                and field.get("vehicle_task_status") is None
            ):
                crop_id = field["crop"]
                crop_name = crop["name"].lower()
                harvest_count = field.get("harvest_count", 0)
                if crop_id == "tomato":
                    stage_name = "első" if harvest_count == 0 else "második"
                    loss_message = (
                        f"A {crop_name} {stage_name} termése elveszett."
                    )
                else:
                    loss_message = f"A {crop_name} termése elveszett."
                log(loss_message, "Harvest")
                _advance_crop_cycle(
                    field, crop_id, current_elapsed_week, missed=True,
                )
            continue

        _year, current_week = get_year_and_week(current_elapsed_week)
        remaining = get_late_harvest_weeks_remaining(
            field["crop"], current_week,
        )
        if remaining:
            field["late_harvest_active"] = True
            field["late_harvest_started_at_week"] = current_elapsed_week
            field["late_harvest_expires_at_week"] = (
                current_elapsed_week + remaining
            )
            late_entries.append(field)
            log(
                f"A {crop['name'].lower()} pótaratási időszakba lépett.",
                "Harvest",
            )

    if notification_manager is not None and late_entries:
        if len(late_entries) == 1:
            crop_name = CROPS[late_entries[0]["crop"]]["name"].lower()
            message = f"A {crop_name} pótaratási időszaka megkezdődött."
        else:
            message = (
                f"{len(late_entries)} Veteményes belépett a "
                "pótaratási időszakba."
            )
        notification_manager.enqueue(
            message,
            event_id=("late_harvest", current_elapsed_week),
        )


def calculate_harvest_yield(field, late_harvest=None):
    """Kiszámítja a hozamot a meglévő szabályok alapján, egész értékre kerekítve."""
    crop = CROPS.get(field.get("crop"))
    if crop is None:
        print(f"Ismeretlen növényazonosító: {field.get('crop')}")
        return None
    field_definition = FIELD_TYPES[field.get("field_type", "field_4x4")]
    stage_yield = get_current_base_yield(
        crop, field.get("harvest_count", 0),
    )
    if stage_yield is None:
        return None
    base_yield = stage_yield * field_definition["yield_multiplier"]
    variation = random.uniform(
        1 - YIELD_RANDOM_VARIATION,
        1 + YIELD_RANDOM_VARIATION,
    )
    modifier = 1.0

    # Ezek a módosítók csak akkor lépnek életbe, ha a mező később ilyen adatokat kap.
    if field.get("watered", False):
        modifier += WATER_BONUS
    if field.get("fertilized", False):
        modifier += FERTILIZER_BONUS
    if field.get("sprayed", False):
        modifier += SPRAYING_BONUS
    if field.get("pests", False):
        modifier -= PEST_PENALTY
    if field.get("weeds", False):
        modifier -= WEED_PENALTY

    final_yield = max(0, base_yield * variation * modifier)
    if field.get("watered", False):
        rounded_yield = math.ceil(final_yield)
    else:
        rounded_yield = int(final_yield + 0.5)
    if late_harvest is None:
        late_harvest = field.get("late_harvest_active", False)
    if late_harvest:
        return int(rounded_yield * LATE_HARVEST_YIELD_MULTIPLIER + 0.5)
    return rounded_yield


def preview_harvest_yield(field, late_harvest=None):
    """Mellékhatás nélkül előre jelzi a következő aratás tényleges hozamát."""
    random_state = random.getstate()
    try:
        return calculate_harvest_yield(field, late_harvest)
    finally:
        random.setstate(random_state)


def prepare_harvest(
        field, buildings, reserved_capacity=0, include_task_status=True,
        late_harvest=None):
    """Ellenőrzi és rögzíti a később végrehajtandó aratás hozamát."""
    if include_task_status and field.get("vehicle_task_status") is not None:
        print("A veteményesen traktorfeladat van folyamatban.")
        return None
    if field["crop"] is None:
        print("Ezen a veteményesen nincs elültetett növény.")
        return None
    if field.get("annual_harvest_state") in (
        "ineligible", "harvested", "lost",
    ):
        return None
    if field["growth"] < 100:
        print("A növény még nem érett.")
        return None
    if not get_warehouses(buildings):
        print("Az aratáshoz legalább egy raktár szükséges.")
        return None

    crop = field["crop"]
    harvested_amount = calculate_harvest_yield(field, late_harvest)
    if harvested_amount is None:
        return None
    if get_free_capacity(buildings) - reserved_capacity < harvested_amount:
        print("Nincs elegendő hely a raktárban.")
        return None

    return {"crop": crop, "amount": harvested_amount}


def complete_harvest(
        field, buildings, crop, harvested_amount, current_elapsed_week=None):
    """A kombájn munkájának végén betárolja és továbblépteti a ciklust."""
    if (field.get("crop") != crop or field.get("growth", 0) < 100
            or harvested_amount is None):
        return False
    if field.get("annual_harvest_state") in (
        "ineligible", "harvested", "lost",
    ):
        return False
    if not get_warehouses(buildings):
        return False
    if get_free_capacity(buildings) < harvested_amount:
        print("Nincs elegendő hely a raktárban.")
        return False

    if not store_crop(buildings, crop, harvested_amount):
        print("Nincs elegendő hely a raktárban.")
        return False

    # A locsolás mindig pontosan a következő sikeres aratásra érvényes.
    field["watered"] = False

    _advance_crop_cycle(field, crop, current_elapsed_week)

    crop_name = CROPS[crop]["name"].lower()
    stored_amount = sum(get_total_inventory(buildings).values())
    total_capacity = get_total_capacity(buildings)
    print(
        f"Aratás sikeres: {harvested_amount} egység {crop_name} "
        "került a raktárba."
    )
    print(f"Raktárkészlet: {stored_amount} / {total_capacity}")
    return True


def harvest_crop(field, buildings):
    """Kompatibilis azonnali aratás a régebbi hívók számára."""
    harvest = prepare_harvest(field, buildings)
    if harvest is None:
        return False
    return complete_harvest(
        field, buildings, harvest["crop"], harvest["amount"],
    )


def draw_crop(screen, field):
    """Kompatibilis belépési pont az új, teljes Veteményes-renderelőhöz."""
    from field_renderer import draw_field
    draw_field(screen, field)
