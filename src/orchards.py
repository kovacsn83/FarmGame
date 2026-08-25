import math

import pygame

from buildings import find_building_data, get_orchards, store_item
from building_renderers import (
    PROCEDURAL_LIGHT_DIRECTION, PROCEDURAL_SHADOW_OFFSET,
)
from game_logger import log
from market_procurement import purchase_automatically
from financial_history import EXPENSE_FRUIT_TREE
from inventory import get_inventory_item_name
from screen_layout import world_to_screen
from constants import AUTO_PURCHASE_DELIVERY_COST_PER_UNIT, TILE_SIZE
from calendar_utils import get_year_and_week


WEEKS_PER_TREE_YEAR = 52

# A gyümölcsfajták központi katalógusa. Új fajhoz csak új definíció szükséges.
TREE_TYPES = {
    "apple": {
        "name": "Alma",
        "tree_name": "Almafa",
        "planting_cost": 100.00,
        "first_yield_age_years": 3,
        "last_yield_age_years": 30,
        "ripening_week": 30,
        "harvest_end_week": 35,
        "annual_yield": 20,
        "product_id": "apple",
        "canopy_color": (62, 132, 58),
        "canopy_light_color": (82, 154, 72),
        "fruit_color": (176, 55, 45),
        "delivery_cost_per_unit": AUTO_PURCHASE_DELIVERY_COST_PER_UNIT,
    },
    "cherry": {
        "name": "Cseresznye",
        "tree_name": "Cseresznyefa",
        "planting_cost": 250.00,
        "first_yield_age_years": 5,
        "last_yield_age_years": 50,
        "ripening_week": 24,
        "harvest_end_week": 28,
        "annual_yield": 20,
        "product_id": "cherry",
        "canopy_color": (45, 105, 54),
        "canopy_light_color": (65, 132, 66),
        "fruit_color": (132, 31, 43),
        "canopy_lobes": ((-4, 1, 11), (4, -2, 11), (2, 5, 10)),
        "canopy_light_radius": 7,
        "fruit_offsets": ((-6, 3), (5, -3), (4, 6), (-2, -5)),
        # A specifikáció szerinti $250 a teljes telepítési levonás.
        "delivery_cost_per_unit": 0,
    },
}

# Egy 4×4-es Gyümölcsös négy rögzített, 2×2-es fahelyének bal felső eltolása.
ORCHARD_TREE_SLOT_OFFSETS = ((0, 0), (0, 2), (2, 0), (2, 2))

# A gyümölcsfák is a játék közös, bal alsó fényirányát követik.
TREE_CANOPY_LIGHT_OFFSET = (
    PROCEDURAL_LIGHT_DIRECTION[0] * 4,
    PROCEDURAL_LIGHT_DIRECTION[1] * 4,
)
TREE_GROUND_SHADOW_OFFSET = (
    PROCEDURAL_SHADOW_OFFSET[0] + 2,
    PROCEDURAL_SHADOW_OFFSET[1] - 2,
)
TREE_GROUND_SHADOW_COLOR = (55, 72, 48)


def get_tree_slot_at(buildings, row, col):
    """A kattintott Gyümölcsös 2×2-es fahelyét és annak indexét adja vissza."""
    orchard = find_building_data(buildings, row, col)
    if orchard is None or orchard.get("type") != "orchard":
        return None
    relative_row = row - orchard["row"]
    relative_col = col - orchard["col"]
    slot_row = relative_row // 2
    slot_col = relative_col // 2
    slot_index = slot_row * 2 + slot_col
    offset_row, offset_col = ORCHARD_TREE_SLOT_OFFSETS[slot_index]
    return {
        "orchard": orchard,
        "slot": slot_index,
        "row": orchard["row"] + offset_row,
        "col": orchard["col"] + offset_col,
    }


def get_tree_in_slot(orchard, slot_index):
    """Megkeresi a Gyümölcsös adott rögzített helyén álló fát."""
    return next(
        (
            tree for tree in orchard.get("trees", [])
            if tree.get("slot") == slot_index
        ),
        None,
    )


def find_tree_at(buildings, row, col):
    """A kurzor alatti 2×2-es fahely faobjektumát keresi meg."""
    slot = get_tree_slot_at(buildings, row, col)
    if slot is None:
        return None
    tree = get_tree_in_slot(slot["orchard"], slot["slot"])
    return (slot["orchard"], tree) if tree is not None else None


def can_plant_tree(buildings, row, col, tree_type):
    """Ellenőrzi a fafajt, a Gyümölcsöst és a rögzített hely foglaltságát."""
    if tree_type not in TREE_TYPES:
        return False
    slot = get_tree_slot_at(buildings, row, col)
    return (
        slot is not None
        and get_tree_in_slot(slot["orchard"], slot["slot"]) is None
    )


def plant_tree(buildings, economy, row, col, tree_type):
    """Egy üres fahelyre telepít, és csak siker esetén vonja le az árát."""
    definition = TREE_TYPES.get(tree_type)
    slot = get_tree_slot_at(buildings, row, col)
    if definition is None or slot is None:
        log(
            "Gyümölcsfa csak Gyümölcsös kijelölt fahelyére ültethető.",
            "Orchard",
        )
        return None
    orchard = slot["orchard"]
    if get_tree_in_slot(orchard, slot["slot"]) is not None:
        log("Ezen a fahelyen már áll egy fa.", "Orchard")
        return None
    purchase = purchase_automatically(
        economy, definition["tree_name"], definition["planting_cost"], 1,
        EXPENSE_FRUIT_TREE, tree_type,
        delivery_cost_per_unit=definition.get(
            "delivery_cost_per_unit", AUTO_PURCHASE_DELIVERY_COST_PER_UNIT,
        ),
    )
    if purchase is None:
        log("Nincs elegendő pénz a gyümölcsfa ültetéséhez.", "Economy")
        return None

    tree = {
        "type": tree_type,
        "slot": slot["slot"],
        "row": slot["row"],
        "col": slot["col"],
        "age_weeks": 0,
        "last_produced_year": None,
        "last_harvested_calendar_year": None,
        "annual_state_year": None,
        "annual_harvest_state": "waiting",
        "annual_productive": False,
        "current_calendar_year": None,
        "current_calendar_week": None,
    }
    orchard.setdefault("trees", []).append(tree)
    log(
        f"{definition['tree_name']} elültetve: "
        f"({slot['row']}, {slot['col']}).",
        "Orchard",
    )
    return tree


def get_tree_age_years(tree):
    """A belső heti életkort a felhasználói egész életévekre alakítja."""
    return max(0, int(tree.get("age_weeks", 0))) // WEEKS_PER_TREE_YEAR


def _was_productive_at_ripening(tree, definition, current_week):
    """Megmondja, hogy a fa az adott év érési hetében termőkorú volt-e."""
    ripening_week = definition["ripening_week"]
    weeks_since_ripening = max(0, current_week - ripening_week)
    age_at_ripening = max(0, int(tree.get("age_weeks", 0))) - weeks_since_ripening
    return (
        definition["first_yield_age_years"] * WEEKS_PER_TREE_YEAR
        <= age_at_ripening
        < (definition["last_yield_age_years"] + 1) * WEEKS_PER_TREE_YEAR
    )


def synchronize_tree_season(tree, current_year, current_week, legacy=False):
    """A fa menthető éves állapotát a központi naptárhoz igazítja."""
    definition = TREE_TYPES.get(tree.get("type"))
    if definition is None:
        return None
    if tree.get("annual_state_year") != current_year:
        tree["annual_state_year"] = current_year
        tree["annual_harvest_state"] = "waiting"
        tree["annual_productive"] = False

    tree["current_calendar_year"] = current_year
    tree["current_calendar_week"] = current_week
    ripening_week = definition["ripening_week"]
    harvest_end_week = definition["harvest_end_week"]
    productive = _was_productive_at_ripening(
        tree, definition, max(current_week, ripening_week),
    )
    tree["annual_productive"] = productive

    if (
        legacy
        and current_week >= ripening_week
        and tree.get("last_harvested_calendar_year") is None
    ):
        legacy_year = tree.get("last_produced_year")
        if legacy_year is not None and legacy_year == get_tree_age_years(tree):
            tree["last_harvested_calendar_year"] = current_year

    if tree.get("last_harvested_calendar_year") == current_year:
        state = "harvested"
    elif current_week < ripening_week:
        state = "waiting"
    elif not productive:
        state = "ineligible"
    elif current_week <= harvest_end_week:
        state = "ripe"
    else:
        state = "lost"
    tree["annual_harvest_state"] = state
    return state


def synchronize_orchard_seasons(buildings, elapsed_weeks, legacy=False):
    """Betöltéskor és heti lépéskor minden fa naptári állapotát frissíti."""
    year, week = get_year_and_week(elapsed_weeks)
    for orchard in get_orchards(buildings):
        for tree in orchard.get("trees", []):
            synchronize_tree_season(tree, year, week, legacy=legacy)


def is_tree_harvestable(tree, current_year=None, current_week=None):
    """Jelzi, hogy a fa aktuális évi termése géppel leszüretelhető-e."""
    definition = TREE_TYPES.get(tree.get("type"))
    if definition is None:
        return False
    if current_year is not None and current_week is not None:
        synchronize_tree_season(tree, current_year, current_week)
    return tree.get("annual_harvest_state") == "ripe"


def complete_tree_harvest(buildings, orchard, tree_slot):
    """A konkrét fa esedékes termését veszteség nélkül betárolja."""
    if orchard not in get_orchards(buildings):
        return False
    tree = get_tree_in_slot(orchard, tree_slot)
    if tree is None or not is_tree_harvestable(tree):
        return False
    definition = TREE_TYPES[tree["type"]]
    amount = definition["annual_yield"]
    if not store_item(buildings, definition["product_id"], amount):
        log(
            f"Nincs elegendő hely a Raktárban a(z) "
            f"{definition['tree_name']} terméséhez.",
            "Orchard",
        )
        return False
    current_year = tree.get("current_calendar_year")
    tree["last_harvested_calendar_year"] = current_year
    tree["last_produced_year"] = get_tree_age_years(tree)
    tree["annual_harvest_state"] = "harvested"
    log(
        f"{definition['tree_name']} leszüretelve: {amount} db "
        f"{get_inventory_item_name(definition['product_id'])} került a Raktárba.",
        "Orchard",
    )
    return True


def run_weekly_orchard_cycle(buildings, elapsed_weeks):
    """Hetente öregíti a fákat; a termést a szüretelőgép gyűjti be."""
    ripened = {}
    lost = {}
    year, week = get_year_and_week(elapsed_weeks)
    for orchard in get_orchards(buildings):
        for tree in orchard.get("trees", []):
            definition = TREE_TYPES.get(tree.get("type"))
            if definition is None:
                continue
            tree["age_weeks"] = max(0, int(tree.get("age_weeks", 0))) + 1
            previous_state = tree.get("annual_harvest_state")
            state = synchronize_tree_season(tree, year, week)
            if state == "ripe" and previous_state != "ripe":
                ripened[tree["type"]] = ripened.get(tree["type"], 0) + 1
            elif state == "lost" and previous_state != "lost":
                lost[tree["type"]] = lost.get(tree["type"], 0) + 1
    for tree_type, count in ripened.items():
        definition = TREE_TYPES[tree_type]
        log(
            f"A(z) {definition['name']} érési időszaka megkezdődött "
            f"({count} fa).",
            "Orchard",
        )
    for tree_type, count in lost.items():
        definition = TREE_TYPES[tree_type]
        log(
            f"{count} {definition['tree_name']} idei termése nem került "
            "leszüretelésre és elveszett.", "Orchard",
        )
    return {}


def get_tree_tooltip_lines(tree):
    """A fafajtából és heti életkorból állítja elő az általános tooltipet."""
    definition = TREE_TYPES.get(tree.get("type"))
    if definition is None:
        return None
    age_weeks = max(0, int(tree.get("age_weeks", 0)))
    age_years = age_weeks // WEEKS_PER_TREE_YEAR
    first = definition["first_yield_age_years"]
    last = definition["last_yield_age_years"]
    ripening_week = definition["ripening_week"]
    harvest_end_week = definition["harvest_end_week"]
    lines = [definition["tree_name"], "Kor:", f"{age_years} év"]
    if age_years < first:
        remaining_weeks = first * WEEKS_PER_TREE_YEAR - age_weeks
        remaining_years = max(1, math.ceil(remaining_weeks / WEEKS_PER_TREE_YEAR))
        lines.extend((
            "Állapot:", "Még nem termő",
            "Első termés:", f"{remaining_years} év múlva",
        ))
    elif age_years <= last:
        state = tree.get("annual_harvest_state", "waiting")
        if state == "ripe":
            lines.extend((
                "Állapot:", "Szüretelhető",
                "Szüreti időszak:", f"{ripening_week}–{harvest_end_week}. hét",
                "Éves termés:",
                f"{definition['annual_yield']} db "
                f"{get_inventory_item_name(definition['product_id'])}",
            ))
        elif state == "harvested":
            lines.extend((
                "Állapot:", "Ebben az évben már leszüretelve",
            ))
        elif state == "lost":
            lines.extend((
                "Állapot:", "Az idei termés elveszett",
                "Következő érés:", f"következő év {ripening_week}. hét",
            ))
        else:
            lines.extend((
                "Állapot:", "Érés alatt",
                "Szüret:", f"{ripening_week}–{harvest_end_week}. hét",
            ))
    else:
        lines.extend(("Állapot:", "Már nem termő"))
    return lines


def is_valid_tree_record(tree, orchard):
    """A mentésből érkező fa minimális, adatvezérelt szerkezetét ellenőrzi."""
    if not isinstance(tree, dict) or tree.get("type") not in TREE_TYPES:
        return False
    slot = tree.get("slot")
    age_weeks = tree.get("age_weeks")
    last_produced_year = tree.get("last_produced_year")
    last_harvested_calendar_year = tree.get("last_harvested_calendar_year")
    if (
        not isinstance(slot, int) or isinstance(slot, bool)
        or not 0 <= slot < len(ORCHARD_TREE_SLOT_OFFSETS)
        or not isinstance(age_weeks, int) or isinstance(age_weeks, bool)
        or age_weeks < 0
        or (
            last_produced_year is not None
            and (
                not isinstance(last_produced_year, int)
                or isinstance(last_produced_year, bool)
                or last_produced_year < 0
            )
        )
        or (
            last_harvested_calendar_year is not None
            and (
                not isinstance(last_harvested_calendar_year, int)
                or isinstance(last_harvested_calendar_year, bool)
                or last_harvested_calendar_year < 1
            )
        )
    ):
        return False
    offset_row, offset_col = ORCHARD_TREE_SLOT_OFFSETS[slot]
    return (
        tree.get("row") == orchard["row"] + offset_row
        and tree.get("col") == orchard["col"] + offset_col
    )


def draw_orchard_trees(screen, buildings):
    """Kis méretben is felismerhető, egyszerű felülnézetes fákat rajzol."""
    for orchard in get_orchards(buildings):
        for tree in orchard.get("trees", []):
            definition = TREE_TYPES.get(tree.get("type"))
            if definition is None:
                continue
            center_x, center_y = world_to_screen(
                (tree["col"] + 1) * TILE_SIZE,
                (tree["row"] + 1) * TILE_SIZE,
            )
            center = round(center_x), round(center_y)
            shadow_center = (
                center[0] + TREE_GROUND_SHADOW_OFFSET[0],
                center[1] + TREE_GROUND_SHADOW_OFFSET[1],
            )
            pygame.draw.ellipse(
                screen, TREE_GROUND_SHADOW_COLOR,
                (shadow_center[0] - 14, shadow_center[1] - 4, 28, 9),
            )
            pygame.draw.circle(screen, (105, 72, 40), center, 5)
            for offset_x, offset_y, radius in definition.get(
                    "canopy_lobes", ((0, 0, 14),)):
                pygame.draw.circle(
                    screen, definition["canopy_color"],
                    (center[0] + offset_x, center[1] + offset_y), radius,
                )
            pygame.draw.circle(
                screen, definition["canopy_light_color"],
                (
                    center[0] + TREE_CANOPY_LIGHT_OFFSET[0],
                    center[1] + TREE_CANOPY_LIGHT_OFFSET[1],
                ),
                definition.get("canopy_light_radius", 8),
            )
            if is_tree_harvestable(tree):
                for offset_x, offset_y in definition.get(
                        "fruit_offsets", ((-6, 3), (5, -3), (4, 6))):
                    pygame.draw.circle(
                        screen, definition["fruit_color"],
                        (center[0] + offset_x, center[1] + offset_y), 2,
                    )
