"""A megvásárolható állatellátási automatizmus heti vezérlése."""

from animal_troughs import (
    FOOD_STOCK_KEY, WATER_STOCK_KEY, get_group_animals, get_group_stock,
)
from buildings import get_animal_pen_groups
from game_logger import log


AUTOMATED_FEEDING_UPGRADE = "automated_animal_feeding"
AUTOMATED_WATERING_UPGRADE = "automated_animal_watering"
AUTOMATION_THRESHOLD_WEEKS = 2


def get_automation_threshold(animal_count):
    """Az adott karámcsoport kétheti, létszámarányos készletét adja."""
    return max(0, animal_count) * AUTOMATION_THRESHOLD_WEEKS


def run_weekly_animal_supply_automation(
        world, buildings, economy, animals, vehicles, purchased_upgrades,
        current_ticks=None):
    """A heti fogyasztás után szükség szerint valódi Dispatcher-feladatokat indít."""
    enabled_supplies = []
    if AUTOMATED_FEEDING_UPGRADE in purchased_upgrades:
        enabled_supplies.append(("food", FOOD_STOCK_KEY, "etetés"))
    if AUTOMATED_WATERING_UPGRADE in purchased_upgrades:
        enabled_supplies.append(("water", WATER_STOCK_KEY, "itatás"))
    if not enabled_supplies:
        return 0

    created_tasks = 0
    for pen_number, group in enumerate(
            get_animal_pen_groups(buildings), start=1):
        animal_count = len(get_group_animals(animals, group))
        if animal_count == 0:
            continue
        threshold = get_automation_threshold(animal_count)
        for trough_type, stock_key, action_name in enabled_supplies:
            if get_group_stock(group, stock_key) > threshold:
                continue
            trough = {
                "type": trough_type,
                "group": group,
                "manually_initiated": False,
            }
            if vehicles.start_trough_supply(
                    world, buildings, economy, animals, trough,
                    current_ticks=current_ticks):
                created_tasks += 1
                log(
                    f"Automatikus {action_name} elindítva: "
                    f"Karám #{pen_number}.",
                    "Automation",
                )
    return created_tasks
