"""Időalapú játékállapotok egységes, UI-tól független tooltip-szövegei."""

from animal_troughs import get_group_animals, get_group_supply
from buildings import get_animal_pen_groups
from crops import (
    CROPS, can_harvest_crop_in_week, format_crop_week_intervals,
    get_crop_lifespan_weeks, get_current_growth_weeks,
    LATE_HARVEST_DURATION_WEEKS, LATE_HARVEST_YIELD_MULTIPLIER,
)
from orchards import find_tree_at, get_tree_tooltip_lines


def format_progress(
        label, current, required, completed=False, completed_text="Kész"):
    """Egységesen formáz egyszeri és ismétlődő időalapú folyamatot."""
    required = max(0, int(required or 0))
    current = max(0, min(int(current or 0), required))
    lines = [f"{label}:", f"{current} / {required} hét"]
    if completed:
        lines.append(completed_text)
    return lines


def get_field_progress_lines(
        field, current_elapsed_week=None, current_week=None,
        harvest_block_reason=None):
    """A Veteményes aktuális érési vagy újratermési ciklusát írja le."""
    crop_id = field.get("crop")
    crop = CROPS.get(crop_id)
    if crop is None:
        return None

    harvest_count = max(0, int(field.get("harvest_count", 0) or 0))
    required = get_current_growth_weeks(crop, harvest_count)
    if required is None:
        return None

    lines = [crop["name"]]
    lifespan = get_crop_lifespan_weeks(crop)
    expires_at = field.get("expires_at_week")
    if (
        lifespan is not None
        and expires_at is not None
        and current_elapsed_week is not None
        and current_elapsed_week >= expires_at
    ):
        lines.append("Élettartama véget ért")
        return lines

    recurring = crop.get("recurring_harvest") is not None
    if recurring and harvest_count:
        # A Lucernának nincs rögzített aratásszám-korlátja: a központilag
        # beállított élettartam és a tényleges aratások határozzák meg.
        successful_harvests = max(
            0, harvest_count - field.get("missed_harvest_count", 0),
        )
        lines.append(f"Aratások száma: {successful_harvests}")

    label = "Újratermés" if harvest_count else "Érés"
    completed = bool(
        field.get("harvestable", False)
        or field.get("growth", 0) >= 100
        or field.get("growth_weeks", 0) >= required
    )
    lines.extend(format_progress(
        label,
        field.get("growth_weeks", 0),
        required,
        completed=False,
    ))
    if not completed:
        lines.append(f"Még {max(0, required - field.get('growth_weeks', 0))} hét az érésig")
        return lines

    if field.get("late_harvest_active", False):
        expires_at = field.get("late_harvest_expires_at_week")
        remaining = (
            max(0, expires_at - current_elapsed_week)
            if expires_at is not None and current_elapsed_week is not None
            else LATE_HARVEST_DURATION_WEEKS
        )
        lines.extend((
            "Pótaratás",
            f"{LATE_HARVEST_YIELD_MULTIPLIER * 100:.0f}% hozam",
            f"Még {remaining} hét",
        ))
        return lines

    # Önálló használatkor is ugyanaz a növénykatalógus-szabály érvényesül;
    # a játékból érkező részletes ok ezen felül az infrastruktúrát is lefedi.
    if (
        harvest_block_reason is None
        and current_week is not None
        and not can_harvest_crop_in_week(crop_id, current_week)
    ):
        harvest_block_reason = "outside_harvest_window"

    status_text = {
        "lifecycle_ended": "Élettartama véget ért",
        "harvest_active": "Aratás folyamatban",
        "harvest_waiting": "Aratás várakozik",
        "field_busy": "Érett – más járműfeladat van folyamatban",
        "no_combine": "Érett – nincs elérhető Kombájn",
        "no_road": "Érett – nincs útkapcsolat",
        "no_route": "Érett – nincs érvényes útvonal",
        "no_warehouse": "Érett – nincs Raktár",
        "no_capacity": "Érett – nincs elegendő Raktárkapacitás",
    }.get(harvest_block_reason)
    if harvest_block_reason == "outside_harvest_window":
        intervals = format_crop_week_intervals(crop_id, "harvest_weeks")
        status_text = (
            f"Érett – aratás csak a {intervals}"
            if intervals else "Érett – jelenleg nincs aratási időszak"
        )
    lines.append(status_text or "Aratható")
    return lines


def get_animal_progress_lines(animal, animal_types):
    """Adatvezérelten megjeleníti az állat időszakos termelési ciklusát."""
    definition = animal_types.get(animal.get("type"))
    if definition is None:
        return None
    production = next(
        (
            item
            for item_id, item in definition.get(
                "periodic_products", {},
            ).items()
            if item.get("remove_animal_after_production")
            or item_id in ("pork", "beef")
        ),
        None,
    )
    if production is None:
        return None

    required = production.get("interval_weeks")
    counter_key = production.get("counter_key")
    if not required or not counter_key:
        return None
    current = animal.get(counter_key, 0)
    completed = current >= required
    progress = format_progress(
        production.get("progress_label", "Életkor"), current, required,
        completed=completed,
        completed_text="Vágásra kész",
    )
    if not completed:
        progress.append(f"Még {max(0, required - current)} hét a levágásig")

    weekly_lines = []
    for item_id, label in definition.get(
            "weekly_product_tooltips", {}).items():
        amount = definition.get("weekly_products", {}).get(item_id, 0)
        weekly_lines.extend((f"{label}:", f"{amount} db"))
    if weekly_lines and not completed:
        progress[-1:-1] = weekly_lines
    else:
        progress.extend(weekly_lines)
    return [definition["name"], *progress]


def get_animal_supply_status_lines(animal, animals, buildings):
    """A kijelölt állat karámjának következő heti ellátási hiányát jelzi."""
    if not buildings:
        return []
    pen_key = animal.get("pen_row"), animal.get("pen_col")
    group = next(
        (
            group for group in get_animal_pen_groups(buildings)
            if any((pen.get("row"), pen.get("col")) == pen_key for pen in group)
        ),
        None,
    )
    if group is None:
        return []
    group_animals = get_group_animals(animals, group)
    food_stock, water_stock = get_group_supply(group)
    required = len(group_animals)
    lines = []
    if food_stock < required:
        lines.append("Nincs elegendő eledel")
    if water_stock < required:
        lines.append("Nincs elegendő ivóvíz")
    return lines


def find_timed_object_tooltip(
        row, col, fields, animals, animal_types, current_elapsed_week=None,
        current_week=None, harvest_availability=None, buildings=None):
    """A kurzor alatti időalapú objektum friss tooltip-sorait adja vissza."""
    animal = next(
        (
            item for item in reversed(animals)
            if item.get("row") == row and item.get("col") == col
        ),
        None,
    )
    if animal is not None:
        lines = get_animal_progress_lines(animal, animal_types)
        if lines is not None:
            return [
                *lines,
                *get_animal_supply_status_lines(animal, animals, buildings),
            ]

    if buildings:
        orchard_tree = find_tree_at(buildings, row, col)
        if orchard_tree is not None:
            _orchard, tree = orchard_tree
            return get_tree_tooltip_lines(tree)

    field = next(
        (
            item for item in fields
            if item.get("row", 0) <= row
            < item.get("row", 0) + item.get("height", 4)
            and item.get("col", 0) <= col
            < item.get("col", 0) + item.get("width", 4)
        ),
        None,
    )
    if field is not None:
        block_reason = (
            harvest_availability(field)
            if harvest_availability is not None else None
        )
        return get_field_progress_lines(
            field, current_elapsed_week, current_week, block_reason,
        )
    return None
