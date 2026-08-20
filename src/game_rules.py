# =====================
# Növénytermesztés
# =====================

# Termés
YIELD_RANDOM_VARIATION = 0.10

# Bónuszok
WATER_BONUS = 0.10
FERTILIZER_BONUS = 0.10

# Büntetések
PEST_PENALTY = 0.10
WEED_PENALTY = 0.10

from constants import (
    FARMHOUSE_LEVEL_2_UPGRADE_PRICE, FARMHOUSE_LEVEL_3_UPGRADE_PRICE,
)


# A veteményesek központi, minden rendszer által használt definíciói.
FIELD_TYPES = {
    "field_4x4": {
        "name": "4x4-es veteményes",
        "width": 4,
        "height": 4,
        "fertilizer_cost": 1,
        "build_cost": 50.00,
        "yield_multiplier": 1.0,
        "required_upgrade": None,
    },
    "field_6x6": {
        "name": "6x6-os veteményes",
        "width": 6,
        "height": 6,
        "fertilizer_cost": 2,
        "build_cost": 250.00,
        "yield_multiplier": 2.5,
        "required_upgrade": "unlock_field_6x6",
    },
    "field_8x8": {
        "name": "8x8-as veteményes",
        "width": 8,
        "height": 8,
        "fertilizer_cost": 3,
        "build_cost": 1000.00,
        "yield_multiplier": 5.0,
        "required_upgrade": "unlock_field_8x8",
    },
}


def get_field_fertilizer_cost(field):
    """A teljes termőföld központilag konfigurált Trágya-igényét adja."""
    field_type = field.get("field_type", "field_4x4")
    definition = FIELD_TYPES.get(field_type)
    if definition is None:
        return None
    return definition["fertilizer_cost"]


# A fejlesztések azonosítóalapú katalógusa későbbi előfeltételeket is támogat.
UPGRADES = {
    "farmhouse_level_2": {
        "name": "Farmház II.",
        "description": "A Farmház nagyobb, fejlettebb épületté bővül.",
        "price": FARMHOUSE_LEVEL_2_UPGRADE_PRICE,
        "unlocks": None,
        "state_key": "farmhouse_level_2",
        "requires": None,
        "target_building_type": "farmhouse",
        "target_level": 2,
    },
    "farmhouse_level_3": {
        "name": "Farmház III.",
        "description": (
            "Vizuálisan továbbfejleszti a Farmház telkét garázzsal, "
            "térköves autóbeállóval és medencével."
        ),
        "price": FARMHOUSE_LEVEL_3_UPGRADE_PRICE,
        "unlocks": None,
        "state_key": "farmhouse_level_3",
        "requires": None,
        "required_level": 2,
        "target_building_type": "farmhouse",
        "target_level": 3,
    },
    "unlock_field_6x6": {
        "name": "6x6-os veteményes",
        "description": "Feloldja a 6x6-os veteményes építését.",
        "price": 2000.00,
        "unlocks": "field_6x6",
        "state_key": "unlock_field_6x6",
        "requires": None,
    },
    "unlock_field_8x8": {
        "name": "8x8-as veteményes",
        "description": "Feloldja a 8x8-as veteményes építését.",
        "price": 5000.00,
        "unlocks": "field_8x8",
        "state_key": "unlock_field_8x8",
        "requires": None,
    },
    "automated_animal_feeding": {
        "name": "Automatizált állat etetés",
        "description": "Legfeljebb 2 heti eledelnél automatikusan ellátási feladat indul.",
        "price": 20000.00,
        "unlocks": "automated_animal_feeding",
        "state_key": "automated_animal_feeding",
        "requires": None,
    },
    "automated_animal_watering": {
        "name": "Automatizált állat itatás",
        "description": "Legfeljebb 2 heti ivóvíznél automatikusan ellátási feladat indul.",
        "price": 20000.00,
        "unlocks": "automated_animal_watering",
        "state_key": "automated_animal_watering",
        "requires": None,
    },
    "automated_field_watering": {
        "name": "Automatizált veteményes locsolás",
        "description": (
            "Amikor egy Veteményes locsolhatóvá válik, automatikusan "
            "Locsolási feladat indul."
        ),
        "price": 20000.00,
        "unlocks": "automated_field_watering",
        "state_key": "automated_field_watering",
        "requires": None,
    },
    "automated_field_fertilizing": {
        "name": "Automatizált veteményes trágyázás",
        "description": (
            "Amikor egy Veteményes trágyázhatóvá válik, automatikusan "
            "Trágyázási feladat indul."
        ),
        "price": 20000.00,
        "unlocks": "automated_field_fertilizing",
        "state_key": "automated_field_fertilizing",
        "requires": None,
    },
}


def is_build_option_unlocked(option, purchased_upgrades):
    """Megadja, hogy egy építhető elemhez teljesült-e a szükséges fejlesztés."""
    required_upgrade = option.get("required_upgrade")
    return required_upgrade is None or required_upgrade in purchased_upgrades


def get_upgrade_status(upgrade_id, purchased_upgrades, farmhouse_level=None):
    """A fejlesztés adatvezérelt, felhasználói állapotát adja vissza."""
    upgrade = UPGRADES[upgrade_id]
    target_level = upgrade.get("target_level")
    if target_level is not None:
        if farmhouse_level is not None and farmhouse_level >= target_level:
            return "Kifejlesztve"
        required_level = upgrade.get("required_level")
        if required_level is not None and (
                farmhouse_level is None or farmhouse_level < required_level):
            return "Előfeltétel szükséges"
        return "Nincs kifejlesztve"
    if upgrade_id in purchased_upgrades:
        return "Kifejlesztve"
    required = upgrade.get("requires")
    if required and required not in purchased_upgrades:
        return "Előfeltétel szükséges"
    return "Fejleszthető"


# Az itt nem szereplő épülettípusok korlátlan számban építhetők.
BUILDING_LIMITS = {
    "farmhouse": 1,
    "market": 1,
}

BUILDING_LIMIT_MESSAGES = {
    "farmhouse": "Már van farmházad.",
    "market": "Már van piacod.",
}


def can_build_more(buildings, building_type, show_message=False):
    """Az aktuális épületlista alapján ellenőrzi a darabszámkorlátot."""
    limit = BUILDING_LIMITS.get(building_type)
    if limit is None:
        return True

    current_count = sum(
        building["type"] == building_type for building in buildings
    )
    if current_count < limit:
        return True

    if show_message:
        print(BUILDING_LIMIT_MESSAGES.get(
            building_type,
            "Elérted az épülettípus építési korlátját.",
        ))
    return False
