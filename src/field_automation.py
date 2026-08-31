"""A megvásárolható, járműves veteményes-automatizálások koordinátora."""

from game_logger import log


AUTOMATED_FIELD_WATERING_UPGRADE = "automated_field_watering"
AUTOMATED_FIELD_FERTILIZING_UPGRADE = "automated_field_fertilizing"
AUTOMATED_FIELD_SPRAYING_UPGRADE = "automated_field_spraying"


def run_field_automation(
        world, buildings, economy, fields, vehicles, purchased_upgrades,
        current_ticks=None):
    """A jogosult mezőket a meglévő publikus Dispatcher-kérésekhez adja.

    A request metódusok végzik az összes készlet-, infrastruktúra-, útvonal- és
    duplikációellenőrzést; ez a réteg semmilyen mezőállapotot nem állít át.
    """
    watering_enabled = (
        AUTOMATED_FIELD_WATERING_UPGRADE in purchased_upgrades
    )
    fertilizing_enabled = (
        AUTOMATED_FIELD_FERTILIZING_UPGRADE in purchased_upgrades
    )
    spraying_enabled = (
        AUTOMATED_FIELD_SPRAYING_UPGRADE in purchased_upgrades
    )
    if not watering_enabled and not fertilizing_enabled and not spraying_enabled:
        return 0

    created = 0
    for field_number, field in enumerate(fields, start=1):
        if watering_enabled and vehicles.start_watering(
                world, buildings, economy, field,
                current_ticks=current_ticks, source="automatic"):
            created += 1
            log(
                f"Automatikus Locsolás indítva: Veteményes #{field_number}.",
                "Automation",
            )
        if fertilizing_enabled and vehicles.start_fertilizing(
                world, buildings, economy, field,
                current_ticks=current_ticks, source="automatic"):
            created += 1
            log(
                f"Automatikus Trágyázás indítva: Veteményes #{field_number}.",
                "Automation",
            )
        if spraying_enabled and vehicles.start_spraying(
                world, buildings, economy, field,
                current_ticks=current_ticks, source="automatic"):
            created += 1
            log(
                "Automatikus permetezési feladat létrehozva: "
                f"Veteményes #{field_number}.",
                "Automation",
            )
    return created
