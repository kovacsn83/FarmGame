from constants import (
    ANIMAL_PEN_BUILD_COST, BUILDING, COLOR_FIELD,
    FARMHOUSE_BUILD_COST, FARMHOUSE_LEVEL_2_MAINTENANCE_BASE,
    FARMHOUSE_LEVEL_2_UPGRADE_PRICE, FARMHOUSE_LEVEL_3_MAINTENANCE_BASE,
    FARMHOUSE_LEVEL_3_UPGRADE_PRICE, GARAGE_BUILD_COST, GRASS,
    MARKET_BUILD_COST, ORCHARD_BUILD_COST, ROAD, TILE_SIZE, POND_BUILD_COST,
    PROCESSING_PLANT_BUILD_COST, WAREHOUSE_BUILD_COST,
)
from crops import CROPS
from game_rules import FIELD_TYPES, can_build_more
from inventory import (
    get_inventory_item_data, get_inventory_item_ids, get_inventory_item_name,
    get_marketable_item_ids, is_inventory_item,
)
from maintenance import format_annual_maintenance_rate
from money_format import format_money


WAREHOUSE_CAPACITY = 500
GARAGE_PARKING_SLOT_SIZE = 2

# A Farmház teljes telke és a telken belüli házgrafika helye külön
# konfigurálható, így a későbbi udvari fejlesztésekhez nem kell az
# építési footprintöt újragondolni.
FARMHOUSE_PLOT_SIZE = 8
FARMHOUSE_DEFAULT_LEVEL = 1
FARMHOUSE_LEGACY_LEVEL = 2
FARMHOUSE_LEVELS = {
    1: {
        "name": "Farmház I.",
        "size": (3, 3),
        "upgrade_price": None,
        "maintenance_base_value": FARMHOUSE_BUILD_COST,
    },
    2: {
        "name": "Farmház II.",
        "size": (4, 4),
        "upgrade_price": FARMHOUSE_LEVEL_2_UPGRADE_PRICE,
        "maintenance_base_value": FARMHOUSE_LEVEL_2_MAINTENANCE_BASE,
    },
    3: {
        "name": "Farmház III.",
        "size": (4, 4),
        "upgrade_price": FARMHOUSE_LEVEL_3_UPGRADE_PRICE,
        "maintenance_base_value": FARMHOUSE_LEVEL_3_MAINTENANCE_BASE,
    },
}
# Kompatibilitási nevek a telekmigrációhoz: a korábbi grafika a II. szint.
FARMHOUSE_BUILDING_SIZE = FARMHOUSE_LEVELS[FARMHOUSE_LEGACY_LEVEL]["size"]
FARMHOUSE_BUILDING_OFFSET = tuple(
    FARMHOUSE_PLOT_SIZE - size for size in FARMHOUSE_BUILDING_SIZE
)

# A helyek sorrendje: bal felső, jobb felső, bal alsó, jobb alsó.
GARAGE_PARKING_SLOTS = ((0, 0), (0, 2), (2, 0), (2, 2))

# Az épülettípusok központi leírása. Új épület hozzáadásához ezt kell bővíteni.
BUILDING_TYPES = {
    "farmhouse": {
        "name": "Farmház",
        "width": FARMHOUSE_PLOT_SIZE,
        "height": FARMHOUSE_PLOT_SIZE,
        "color": (181, 101, 72),
        "build_cost": FARMHOUSE_BUILD_COST,
        "draw_grass_underlay": True,
        "building_size": FARMHOUSE_BUILDING_SIZE,
        "building_offset": FARMHOUSE_BUILDING_OFFSET,
    },
    "warehouse": {
        "name": "Raktár",
        "width": 5,
        "height": 4,
        "color": (125, 115, 105),
        "build_cost": WAREHOUSE_BUILD_COST,
    },
    "market": {
        "name": "Piac",
        "width": 4,
        "height": 3,
        "color": (160, 90, 170),
        "build_cost": MARKET_BUILD_COST,
    },
    "garage": {
        "name": "Garázs",
        "width": 4,
        "height": 4,
        "color": (85, 105, 115),
        "build_cost": GARAGE_BUILD_COST,
    },
    "animal_pen": {
        "name": "Karám",
        "width": 4,
        "height": 4,
        "color": (34, 139, 34),
        "build_cost": ANIMAL_PEN_BUILD_COST,
    },
    "pond": {
        "name": "Tó",
        "width": 6,
        "height": 6,
        "color": (62, 137, 176),
        "build_cost": POND_BUILD_COST,
        "placement_rule": "road",
        "renderer_type": "pond",
        # A procedurális Tó átlátszó részei alatt a világ saját fűcsempéi látszanak.
        "draw_grass_underlay": True,
        "future_role": "irrigation_source",
        "description": (
            "A gazdaság későbbi öntözési rendszerének vízforrása."
        ),
    },
    "orchard": {
        "name": "Gyümölcsös",
        "width": 4,
        "height": 4,
        "color": (34, 139, 34),
        "build_cost": ORCHARD_BUILD_COST,
        # A füves belső terület fölé külön, összeolvadó kerítés kerül.
        "draw_grass_underlay": True,
        "future_role": "fruit_tree_area",
        "description": "Előkészített terület a későbbi gyümölcsfák számára.",
    },
    "processing_plant": {
        "name": "Feldolgozó üzem",
        "width": 6,
        "height": 5,
        "color": (171, 165, 150),
        "build_cost": PROCESSING_PLANT_BUILD_COST,
        "placement_rule": "road",
        "renderer_type": "processing_plant",
        "future_role": "processing_industry",
        "description": "Mezőgazdasági alapanyagok feldolgozása.",
        # A részletes adatok a központi processing.PROCESSING_RECIPES katalógusban vannak.
        "recipes": ("canned_tomato", "cheese"),
    },
}

# A választóablak minden építhető területe ugyanebből a katalógusból dolgozik.
# A valódi épületeknél ugyanazokra a leíró szótárakra hivatkozunk, másolat nélkül.
BUILD_OPTIONS = {
    **{
        field_type: {**field_data, "color": COLOR_FIELD}
        for field_type, field_data in FIELD_TYPES.items()
    },
    **BUILDING_TYPES,
}


def get_garage_parking_position(building, slot_index=0):
    """Visszaadja a kiválasztott 2x2-es garázshely világkoordinátás közepét."""
    if building["type"] != "garage":
        raise ValueError("Belső parkolópozíció csak Garázshoz kérhető.")
    if (not isinstance(slot_index, int) or isinstance(slot_index, bool)
            or not 0 <= slot_index < len(GARAGE_PARKING_SLOTS)):
        raise ValueError("A kért garázshely még nem létezik.")
    row_offset, col_offset = GARAGE_PARKING_SLOTS[slot_index]

    parking_col = building["col"] + col_offset
    parking_row = building["row"] + row_offset
    half_slot_size = GARAGE_PARKING_SLOT_SIZE / 2
    return (
        float((parking_col + half_slot_size) * TILE_SIZE),
        float((parking_row + half_slot_size) * TILE_SIZE),
    )


def has_adjacent_road(world, row, col, width, height):
    """Ellenőrzi, hogy az épület valamelyik oldala érintkezik-e úttal."""
    if row > 0:
        for c in range(width):
            if world[row - 1][col + c] == ROAD:
                return True

    world_rows = len(world)
    world_cols = len(world[0]) if world else 0
    if row + height < world_rows:
        for c in range(width):
            if world[row + height][col + c] == ROAD:
                return True

    for r in range(height):
        if col > 0 and world[row + r][col - 1] == ROAD:
            return True
        if col + width < world_cols and world[row + r][col + width] == ROAD:
            return True

    return False


def can_place_building(
        world, buildings, row, col, building_type, show_limit_message=False,
        animals=()):
    """Ellenőrzi a helyet, az útkapcsolatot és az építési korlátot."""
    building = BUILDING_TYPES[building_type]
    width = building["width"]
    height = building["height"]

    if row < 0 or col < 0:
        return False
    world_rows = len(world)
    world_cols = len(world[0]) if world else 0
    if row + height > world_rows or col + width > world_cols:
        return False

    for r in range(height):
        for c in range(width):
            if world[row + r][col + c] != GRASS:
                return False

    has_road_connection = has_adjacent_road(
        world, row, col, width, height,
    )
    if building_type in ("animal_pen", "orchard"):
        candidate = {
            "type": building_type, "row": row, "col": col,
            "width": width, "height": height,
        }
        connected_buildings = get_buildings_by_type(buildings, building_type)
        has_same_type_connection = any(
            buildings_are_side_adjacent(candidate, existing)
            for existing in connected_buildings
        )
        if not has_road_connection and not has_same_type_connection:
            return False
        if (building_type == "animal_pen"
                and not _candidate_pen_keeps_species_separate(
                    buildings, animals, candidate)):
            return False
    elif not has_road_connection:
        return False

    return can_build_more(buildings, building_type, show_limit_message)


def place_building(world, buildings, row, col, building_type):
    """Elhelyezi az épületet a rácson és eltárolja a részletes adatait."""
    building = BUILDING_TYPES[building_type]
    data = {
        "type": building_type,
        "row": row,
        "col": col,
        "width": building["width"],
        "height": building["height"],
    }
    if building_type == "warehouse":
        data["capacity"] = WAREHOUSE_CAPACITY
        data["inventory"] = {
            item_id: 0 for item_id in get_inventory_item_ids()
        }
    elif building_type == "animal_pen":
        # A csoportosítás után csak a bal felső Karámelem tartja meg ezeket.
        data["trough_food_stock"] = 0
        data["trough_water_stock"] = 0
    elif building_type == "orchard":
        # A fák a saját Gyümölcsösükhöz tartoznak, így együtt mentődnek vele.
        data["trees"] = []
    elif building_type == "farmhouse":
        data["farmhouse_level"] = FARMHOUSE_DEFAULT_LEVEL
    elif building_type == "processing_plant":
        from processing import initialize_processing_plant
        initialize_processing_plant(data)

    for r in range(data["height"]):
        for c in range(data["width"]):
            world[row + r][col + c] = BUILDING

    buildings.append(data)
    return data


def get_farmhouse_level_definition(building):
    """Az aktuális, bővíthető Farmház-szintdefiníciót adja vissza."""
    level = building.get("farmhouse_level", FARMHOUSE_LEGACY_LEVEL)
    return FARMHOUSE_LEVELS.get(level, FARMHOUSE_LEVELS[FARMHOUSE_DEFAULT_LEVEL])


def get_building_maintenance_base(building):
    """Az épület aktuális állapotához tartozó fenntartási alapérték."""
    if building.get("type") == "farmhouse":
        return get_farmhouse_level_definition(building)["maintenance_base_value"]
    return BUILDING_TYPES[building["type"]]["build_cost"]


def get_warehouses(buildings):
    """Visszaadja az összes raktár típusú épületet."""
    return [building for building in buildings if building["type"] == "warehouse"]


def get_animal_pens(buildings):
    """Visszaadja az összes Karám épületet az építési sorrendben."""
    return [building for building in buildings if building["type"] == "animal_pen"]


def get_buildings_by_type(buildings, building_type):
    """Egy épülettípus példányait az építési sorrendben adja vissza."""
    return [
        building for building in buildings
        if building.get("type") == building_type
    ]


def get_orchards(buildings):
    """Visszaadja a később fákkal bővíthető Gyümölcsös-elemeket."""
    return get_buildings_by_type(buildings, "orchard")


def get_building_type_tiles(buildings, building_type):
    """Egy területszerű épülettípus teljes, összefüggésvizsgálatra kész rácsa."""
    return {
        (building["row"] + row, building["col"] + col)
        for building in get_buildings_by_type(buildings, building_type)
        for row in range(building["height"])
        for col in range(building["width"])
    }


def get_orchard_tiles(buildings):
    """A Gyümölcsösök teljes területe, későbbi faelhelyezéshez is használhatóan."""
    return get_building_type_tiles(buildings, "orchard")


def get_animal_pen_tiles(buildings):
    """A karámrendszer teljes, későbbi állatmozgáshoz is használható területe."""
    return get_building_type_tiles(buildings, "animal_pen")


def buildings_are_side_adjacent(first, second):
    """Pozitív hosszúságú közös oldallal érintkező területeket ismer fel."""
    row_overlap = min(
        first["row"] + first["height"],
        second["row"] + second["height"],
    ) - max(first["row"], second["row"])
    col_overlap = min(
        first["col"] + first["width"],
        second["col"] + second["width"],
    ) - max(first["col"], second["col"])
    touch_horizontally = row_overlap > 0 and (
        first["col"] + first["width"] == second["col"]
        or second["col"] + second["width"] == first["col"]
    )
    touch_vertically = col_overlap > 0 and (
        first["row"] + first["height"] == second["row"]
        or second["row"] + second["height"] == first["row"]
    )
    return touch_horizontally or touch_vertically


def _animal_pens_are_adjacent(first, second):
    """Kompatibilitási segéd a Karám csoportosításához."""
    return buildings_are_side_adjacent(first, second)


def get_animal_pen_groups(buildings):
    """Oldalszomszédság alapján összefüggő karámrendszerekre bont."""
    return get_connected_building_groups(buildings, "animal_pen")


def get_orchard_groups(buildings):
    """A későbbi fakészlethez összefüggő Gyümölcsös-rendszerekre bont."""
    return get_connected_building_groups(buildings, "orchard")


def get_connected_building_groups(buildings, building_type):
    """Oldalszomszédság alapján csoportosít egy területszerű épülettípust."""
    remaining = get_buildings_by_type(buildings, building_type)
    groups = []
    while remaining:
        group = [remaining.pop(0)]
        pending = list(group)
        while pending:
            current = pending.pop()
            neighbors = [
                pen for pen in remaining
                if buildings_are_side_adjacent(current, pen)
            ]
            for neighbor in neighbors:
                remaining.remove(neighbor)
                group.append(neighbor)
                pending.append(neighbor)
        groups.append(group)
    return groups


def _candidate_pen_keeps_species_separate(buildings, animals, candidate):
    """Megakadályozza eltérő fajok karámjainak utólagos összekötését."""
    if not animals:
        return True
    candidate_group = next(
        group for group in get_animal_pen_groups([*buildings, candidate])
        if candidate in group
    )
    pen_ids = {
        (pen["row"], pen["col"])
        for pen in candidate_group
        if pen is not candidate
    }
    species = {
        animal.get("type")
        for animal in animals
        if (animal.get("pen_row"), animal.get("pen_col")) in pen_ids
    }
    return len(species) <= 1


def get_total_capacity(buildings):
    """Megadja az összes raktár együttes kapacitását."""
    return sum(warehouse["capacity"] for warehouse in get_warehouses(buildings))


def get_total_inventory(buildings):
    """Terméktípusonként összesíti az összes raktár aktuális készletét."""
    inventory = {}
    for warehouse in get_warehouses(buildings):
        for item, amount in warehouse["inventory"].items():
            inventory[item] = inventory.get(item, 0) + amount
    return inventory


def get_total_crop_amount(buildings, crop="wheat"):
    """Megadja egy termény összes raktárban tárolt mennyiségét."""
    return get_total_inventory(buildings).get(crop, 0)


def get_marketable_item_amount(buildings, item_id):
    """A termék katalógusban kijelölt piaci készletforrását összesíti."""
    item_data = get_inventory_item_data(item_id)
    if item_data is None or not item_data.get("marketable", False):
        return 0
    if item_data.get("inventory_source") == "processing_plant":
        return sum(
            max(0, int(building.get("processing_inventory", {}).get(item_id, 0)))
            for building in buildings
            if building.get("type") == "processing_plant"
        )
    return get_total_inventory(buildings).get(item_id, 0)


def remove_marketable_item(buildings, item_id, amount):
    """A piaci készletet stabil építési sorrendben, negatív érték nélkül vonja le."""
    item_data = get_inventory_item_data(item_id)
    if item_data is None or not item_data.get("marketable", False):
        return False
    if (not isinstance(amount, int) or isinstance(amount, bool)
            or amount < 0
            or get_marketable_item_amount(buildings, item_id) < amount):
        return False
    if item_data.get("inventory_source") != "processing_plant":
        return remove_item(buildings, item_id, amount)

    remaining = amount
    for building in buildings:
        if building.get("type") != "processing_plant":
            continue
        inventory = building.get("processing_inventory", {})
        available = max(0, int(inventory.get(item_id, 0)))
        removed_here = min(remaining, available)
        inventory[item_id] = available - removed_here
        remaining -= removed_here
        if remaining == 0:
            return True
    return remaining == 0


def get_free_capacity(buildings):
    """Megadja az összes raktárban még felhasználható helyet."""
    stored_amount = sum(get_total_inventory(buildings).values())
    return get_total_capacity(buildings) - stored_amount


def store_crop(buildings, crop, amount):
    """A teljes terménymennyiséget sorban szétosztja a raktárak között."""
    if crop not in CROPS:
        print(f"Ismeretlen növényazonosító: {crop}")
        return False
    return store_item(buildings, crop, amount)


def store_item(buildings, item_id, amount):
    """Egy általános készletelemet sorban szétoszt a raktárak között."""
    if not is_inventory_item(item_id):
        print(f"Ismeretlen készletelem: {item_id}")
        return False
    if (not isinstance(amount, int) or isinstance(amount, bool)
            or amount < 0 or get_free_capacity(buildings) < amount):
        return False

    remaining = amount
    for warehouse in get_warehouses(buildings):
        used_capacity = sum(warehouse["inventory"].values())
        available_capacity = warehouse["capacity"] - used_capacity
        stored_here = min(remaining, available_capacity)
        warehouse["inventory"][item_id] = (
            warehouse["inventory"].get(item_id, 0) + stored_here
        )
        remaining -= stored_here
        if remaining == 0:
            return True

    return remaining == 0


def store_items(buildings, amounts):
    """Egy teljes termékcsomagot csak elegendő összkapacitás esetén tárol el."""
    if not isinstance(amounts, dict) or not all(
            is_inventory_item(item_id)
            and isinstance(amount, int)
            and not isinstance(amount, bool)
            and amount >= 0
            for item_id, amount in amounts.items()):
        return False
    if get_free_capacity(buildings) < sum(amounts.values()):
        return False
    return all(
        store_item(buildings, item_id, amount)
        for item_id, amount in amounts.items()
    )


def remove_crop(buildings, crop, amount):
    """A megadott terményt sorban levonja a raktárak készletéből."""
    if crop not in CROPS:
        print(f"Ismeretlen növényazonosító: {crop}")
        return False
    return remove_item(buildings, crop, amount)


def remove_item(buildings, item_id, amount):
    """Egy általános készletelemet FIFO raktársorrendben levon."""
    if not is_inventory_item(item_id):
        print(f"Ismeretlen készletelem: {item_id}")
        return False
    if (not isinstance(amount, int) or isinstance(amount, bool)
            or amount < 0
            or get_total_inventory(buildings).get(item_id, 0) < amount):
        return False

    remaining = amount
    for warehouse in get_warehouses(buildings):
        available = warehouse["inventory"].get(item_id, 0)
        removed_here = min(remaining, available)
        warehouse["inventory"][item_id] = available - removed_here
        remaining -= removed_here
        if remaining == 0:
            return True

    return remaining == 0


def find_building_data(buildings, row, col):
    """Megkeresi azt az épületet, amely a megadott mezőt lefedi."""
    for building in buildings:
        if (building["row"] <= row < building["row"] + building["height"]
                and building["col"] <= col < building["col"] + building["width"]):
            return building
    return None


def remove_building(world, buildings, building):
    """Az épület összes mezőjét és a hozzá tartozó adatot is törli."""
    if (building["type"] == "warehouse"
            and sum(building["inventory"].values()) > 0):
        print("A raktár nem bontható le, amíg termény van benne.")
        return False
    for r in range(building["height"]):
        for c in range(building["width"]):
            world[building["row"] + r][building["col"] + c] = GRASS
    buildings.remove(building)
    return True


def print_building_info(building):
    building_type = BUILDING_TYPES[building["type"]]
    if building["type"] == "warehouse":
        free_capacity = building["capacity"] - sum(building["inventory"].values())
        print("=== Raktár ===")
        print(f"Pozíció: ({building['row']}, {building['col']})")
        print(f"Méret: {building['width']}x{building['height']}")
        for item_id in get_inventory_item_ids():
            amount = building["inventory"].get(item_id, 0)
            if amount > 0:
                print(f"{get_inventory_item_name(item_id)}: {amount}")
        print(f"Szabad hely: {free_capacity}")
        print(f"Építési ár: {format_money(building_type['build_cost'])}")
        print(f"Éves költség: {format_annual_maintenance_rate()}")
        print()
        return

    print("=== Épület ===")
    display_name = building_type["name"]
    if building["type"] == "farmhouse":
        display_name = get_farmhouse_level_definition(building)["name"]
    print(f"Típus: {display_name}")
    print(f"Pozíció: ({building['row']}, {building['col']})")
    print(f"Méret: {building['width']}x{building['height']}")
    print(f"Építési ár: {format_money(building_type['build_cost'])}")
    print(f"Éves költség: {format_annual_maintenance_rate()}")
    if building["type"] == "market":
        for item_id in get_marketable_item_ids():
            item_data = get_inventory_item_data(item_id)
            print(
                f"{get_inventory_item_name(item_id)} eladási ára: "
                f"{format_money(item_data['price'])}/db"
            )
    description = building_type.get("description")
    if description:
        print(f"Funkció: {description}")
    print()
