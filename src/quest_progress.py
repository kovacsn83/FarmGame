"""A tartós világállapotból levezethető Quest-feltételek központi leképezése."""

from animals import get_animals_in_pen_group
from buildings import get_animal_pen_groups
from quest_system import (
    QUEST_EVENT_CHERRY_TREE_COUNT_CHANGED,
    QUEST_EVENT_ORCHARD_COUNT_CHANGED,
    QUEST_EVENT_SEPARATE_CHICKEN_PEN_READY,
)


def get_world_quest_progress(buildings, animals):
    """Visszaadja az új Questek mentés után is rekonstruálható értékeit."""
    pen_groups = get_animal_pen_groups(buildings)
    separate_chicken_pen_ready = len(pen_groups) >= 2 and any(
        sum(
            animal.get("type") == "chicken"
            for animal in get_animals_in_pen_group(animals, group)
        ) >= 2
        for group in pen_groups
    )
    orchards = [
        building for building in buildings
        if building.get("type") == "orchard"
    ]
    return {
        QUEST_EVENT_SEPARATE_CHICKEN_PEN_READY: int(
            separate_chicken_pen_ready
        ),
        QUEST_EVENT_ORCHARD_COUNT_CHANGED: len(orchards),
        QUEST_EVENT_CHERRY_TREE_COUNT_CHANGED: sum(
            tree.get("type") == "cherry"
            for orchard in orchards
            for tree in orchard.get("trees", [])
        ),
    }
