import math

import pygame

from buildings import find_building_data, get_orchards, store_item
from building_renderers import (
    PROCEDURAL_LIGHT_DIRECTION, PROCEDURAL_SHADOW_OFFSET,
)
from game_logger import log
from market_procurement import purchase_automatically
from inventory import get_inventory_item_name
from screen_layout import world_to_screen
from constants import TILE_SIZE


WEEKS_PER_TREE_YEAR = 52

# A gyümölcsfajták központi katalógusa. Új fajhoz csak új definíció szükséges.
TREE_TYPES = {
    "apple": {
        "name": "Alma",
        "tree_name": "Almafa",
        "planting_cost": 100.00,
        "first_yield_age_years": 3,
        "last_yield_age_years": 30,
        "annual_yield": 20,
        "product_id": "apple",
        "canopy_color": (62, 132, 58),
        "canopy_light_color": (82, 154, 72),
        "fruit_color": (176, 55, 45),
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
        log("Almafa csak Gyümölcsös kijelölt fahelyére ültethető.", "Orchard")
        return None
    orchard = slot["orchard"]
    if get_tree_in_slot(orchard, slot["slot"]) is not None:
        log("Ezen a fahelyen már áll egy fa.", "Orchard")
        return None
    purchase = purchase_automatically(
        economy, definition["tree_name"], definition["planting_cost"], 1,
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


def is_tree_harvestable(tree):
    """Jelzi, hogy a fa aktuális évi termése géppel leszüretelhető-e."""
    definition = TREE_TYPES.get(tree.get("type"))
    if definition is None:
        return False
    age_years = get_tree_age_years(tree)
    return (
        definition["first_yield_age_years"]
        <= age_years
        <= definition["last_yield_age_years"]
        and tree.get("last_produced_year") != age_years
    )


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
    tree["last_produced_year"] = get_tree_age_years(tree)
    log(
        f"{definition['tree_name']} leszüretelve: {amount} db "
        f"{get_inventory_item_name(definition['product_id'])} került a Raktárba.",
        "Orchard",
    )
    return True


def run_weekly_orchard_cycle(buildings):
    """Hetente öregíti a fákat; a termést a szüretelőgép gyűjti be."""
    for orchard in get_orchards(buildings):
        for tree in orchard.get("trees", []):
            definition = TREE_TYPES.get(tree.get("type"))
            if definition is None:
                continue
            tree["age_weeks"] = max(0, int(tree.get("age_weeks", 0))) + 1
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
    lines = [definition["tree_name"], "Kor:", f"{age_years} év"]
    if age_years < first:
        remaining_weeks = first * WEEKS_PER_TREE_YEAR - age_weeks
        remaining_years = max(1, math.ceil(remaining_weeks / WEEKS_PER_TREE_YEAR))
        lines.extend((
            "Állapot:", "Még nem termő",
            "Első termés:", f"{remaining_years} év múlva",
        ))
    elif age_years <= last:
        if is_tree_harvestable(tree):
            lines.extend((
                "Állapot:", "Szüretelhető",
                "Éves termés:",
                f"{definition['annual_yield']} db "
                f"{get_inventory_item_name(definition['product_id'])}",
            ))
        else:
            lines.extend((
                "Állapot:", "Ebben az évben már leszüretelve",
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
            pygame.draw.circle(
                screen, definition["canopy_color"], center, 14,
            )
            pygame.draw.circle(
                screen, definition["canopy_light_color"],
                (
                    center[0] + TREE_CANOPY_LIGHT_OFFSET[0],
                    center[1] + TREE_CANOPY_LIGHT_OFFSET[1],
                ),
                8,
            )
            if is_tree_harvestable(tree):
                for offset_x, offset_y in ((-6, 3), (5, -3), (4, 6)):
                    pygame.draw.circle(
                        screen, definition["fruit_color"],
                        (center[0] + offset_x, center[1] + offset_y), 2,
                    )
