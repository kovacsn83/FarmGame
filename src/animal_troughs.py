import pygame

from buildings import get_animal_pen_groups
from constants import TILE_SIZE
from game_logger import log
from screen_layout import world_to_screen


FOOD_STOCK_KEY = "trough_food_stock"
WATER_STOCK_KEY = "trough_water_stock"
TROUGH_WEEKS = 8
FOOD_PER_ANIMAL_PER_WEEK = 1
WATER_PER_ANIMAL_PER_WEEK = 1

TROUGH_WIDTH = 14
TROUGH_HEIGHT = 7
TROUGH_GAP = 4
TROUGH_OFFSET = 4
TROUGH_FRAME_COLOR = (91, 72, 52)
TROUGH_BORDER_COLOR = (55, 48, 40)
TROUGH_EMPTY_COLOR = (63, 58, 50)
TROUGH_FEED_COLOR = (157, 139, 72)
TROUGH_WATER_COLOR = (67, 119, 145)
TROUGH_WATER_HIGHLIGHT_COLOR = (132, 168, 181)
TROUGH_MOVEMENT_SAFETY_MARGIN = 3


def _pen_key(pen):
    return pen["row"], pen["col"]


def _canonical_pen(group):
    return min(group, key=_pen_key) if group else None


def get_group_anchor(group):
    """Stabil célpontot ad a Közös Dispatcher ellátási feladataihoz."""
    return _canonical_pen(group)


def get_group_animals(animals, group):
    """A Karámcsoporthoz rendelt állatokat adja vissza."""
    pen_keys = {_pen_key(pen) for pen in group}
    return [
        animal for animal in animals
        if (animal.get("pen_row"), animal.get("pen_col")) in pen_keys
    ]


def get_group_stock(group, stock_key):
    """Az átmenetileg több elemen tárolt készletet is biztonságosan összegzi."""
    return sum(
        max(0, pen.get(stock_key, 0))
        for pen in group
        if isinstance(pen.get(stock_key, 0), int)
        and not isinstance(pen.get(stock_key, 0), bool)
    )


def synchronize_pen_group_stocks(buildings, animals=(), cap_merged=False):
    """Csoportonként egyetlen, bal felső Karámelemre rendezi a készleteket."""
    for group in get_animal_pen_groups(buildings):
        canonical = _canonical_pen(group)
        animal_count = len(get_group_animals(animals, group))
        maximum = animal_count * TROUGH_WEEKS
        for stock_key in (FOOD_STOCK_KEY, WATER_STOCK_KEY):
            stock = get_group_stock(group, stock_key)
            if cap_merged:
                stock = min(stock, maximum)
            canonical[stock_key] = stock
            for pen in group:
                if pen is not canonical:
                    pen.pop(stock_key, None)


def get_group_supply(group):
    canonical = _canonical_pen(group)
    if canonical is None:
        return 0, 0
    return (
        max(0, canonical.get(FOOD_STOCK_KEY, 0)),
        max(0, canonical.get(WATER_STOCK_KEY, 0)),
    )


def get_trough_capacity(animals, group):
    return len(get_group_animals(animals, group)) * TROUGH_WEEKS


def _group_trough_world_rects(group):
    """A csoport bal felső részén két, tile-t nem foglaló világ-hitboxot képez."""
    canonical = _canonical_pen(group)
    if canonical is None:
        return {}
    left = canonical["col"] * TILE_SIZE + TROUGH_OFFSET
    top = canonical["row"] * TILE_SIZE + TROUGH_OFFSET
    food_rect = pygame.Rect(left, top, TROUGH_WIDTH, TROUGH_HEIGHT)
    water_rect = pygame.Rect(
        food_rect.right + TROUGH_GAP, top, TROUGH_WIDTH, TROUGH_HEIGHT,
    )
    return {"food": food_rect, "water": water_rect}


def get_forbidden_movement_rects(group):
    """A Karámcsoport állatai elől elzárt, világkoordinátás területeket adja."""
    margin = TROUGH_MOVEMENT_SAFETY_MARGIN
    return [
        rect.inflate(margin * 2, margin * 2)
        for rect in _group_trough_world_rects(group).values()
    ]


def _to_screen_rect(world_rect):
    left, top = world_to_screen(world_rect.left, world_rect.top)
    return pygame.Rect(left, top, world_rect.width, world_rect.height)


def iter_troughs(buildings, animals):
    synchronize_pen_group_stocks(buildings, animals)
    for group in get_animal_pen_groups(buildings):
        food_stock, water_stock = get_group_supply(group)
        capacity = get_trough_capacity(animals, group)
        stocks = {"food": food_stock, "water": water_stock}
        for trough_type, world_rect in _group_trough_world_rects(group).items():
            yield {
                "type": trough_type,
                "group": group,
                "rect": _to_screen_rect(world_rect),
                "stock": stocks[trough_type],
                "capacity": capacity,
            }


def find_trough_at(position, buildings, animals):
    return next(
        (
            trough for trough in iter_troughs(buildings, animals)
            if trough["rect"].collidepoint(position)
        ),
        None,
    )


def fill_trough_at(position, buildings, animals):
    """A kattintott vályút az aktuális állatlétszám nyolchetes maximumára tölti."""
    trough = find_trough_at(position, buildings, animals)
    if trough is None:
        return False
    return fill_group_trough(trough["group"], animals, trough["type"])


def validate_trough_supply(trough, animals):
    """Feladatindítás előtt ellenőrzi az állatlétszámot és a töltöttséget."""
    group = trough["group"]
    group_animals = get_group_animals(animals, group)
    if not group_animals:
        log("A Karámban nincs állat.", "Animals")
        return False

    capacity = len(group_animals) * TROUGH_WEEKS
    canonical = _canonical_pen(group)
    stock_key = (
        FOOD_STOCK_KEY if trough["type"] == "food" else WATER_STOCK_KEY
    )
    current_stock = canonical.get(stock_key, 0)
    trough_name = "Etetővályú" if trough["type"] == "food" else "Itatóvályú"
    if current_stock >= capacity:
        log(f"Az {trough_name} már tele van.", "Animals")
        return False
    return True


def trough_supply_is_needed(group, animals, trough_type):
    """Naplózás nélkül jelzi, hogy egy létező vályúcél még kiszolgálandó-e."""
    group_animals = get_group_animals(animals, group)
    canonical = _canonical_pen(group)
    if canonical is None or not group_animals:
        return False
    stock_key = FOOD_STOCK_KEY if trough_type == "food" else WATER_STOCK_KEY
    return canonical.get(stock_key, 0) < len(group_animals) * TROUGH_WEEKS


def fill_group_trough(group, animals, trough_type):
    """Sikeres járműves ürítéskor a nyolchetes maximumra tölt."""
    group_animals = get_group_animals(animals, group)
    if not group_animals:
        log("A Karámban nincs állat.", "Animals")
        return False
    capacity = len(group_animals) * TROUGH_WEEKS
    canonical = _canonical_pen(group)
    stock_key = FOOD_STOCK_KEY if trough_type == "food" else WATER_STOCK_KEY
    current_stock = canonical.get(stock_key, 0)
    trough_name = "Etetővályú" if trough_type == "food" else "Itatóvályú"
    if current_stock >= capacity:
        log(f"Az {trough_name} már tele van.", "Animals")
        return False

    canonical[stock_key] = capacity
    unit_name = "eledel" if trough_type == "food" else "víz"
    log(
        f"{trough_name} feltöltve: {capacity} {unit_name}, "
        f"{TROUGH_WEEKS} heti készlet.",
        "Animals",
    )
    return True


def get_trough_tooltip(position, buildings, animals):
    trough = find_trough_at(position, buildings, animals)
    if trough is None:
        return None
    name = "Etetővályú" if trough["type"] == "food" else "Itatóvályú"
    animal_count = len(get_group_animals(animals, trough["group"]))
    remaining_weeks = (
        min(TROUGH_WEEKS, trough["stock"] // animal_count)
        if animal_count > 0 else 0
    )
    suffix = ""
    anchor = _canonical_pen(trough["group"])
    if (
        trough["type"] == "food"
        and anchor is not None
        and anchor.get("vehicle_task_type") == "supply_feed"
    ):
        suffix = " – feltöltés folyamatban"
    return (
        f"{name}: {remaining_weeks} / {TROUGH_WEEKS} hét{suffix}",
        trough["rect"],
    )


def _draw_trough(screen, rect, fill_color, stock, capacity, water=False):
    pygame.draw.rect(screen, TROUGH_BORDER_COLOR, rect, border_radius=2)
    frame = rect.inflate(-2, -2)
    pygame.draw.rect(screen, TROUGH_FRAME_COLOR, frame, border_radius=1)
    interior = frame.inflate(-2, -2)
    pygame.draw.rect(screen, TROUGH_EMPTY_COLOR, interior)
    ratio = min(1.0, stock / capacity) if capacity > 0 else 0.0
    fill_width = round(interior.width * ratio)
    if fill_width > 0:
        fill_rect = pygame.Rect(
            interior.left, interior.top, fill_width, interior.height,
        )
        pygame.draw.rect(screen, fill_color, fill_rect)
        if water and fill_rect.width >= 4:
            pygame.draw.line(
                screen, TROUGH_WATER_HIGHLIGHT_COLOR,
                (fill_rect.left + 1, fill_rect.top),
                (fill_rect.right - 2, fill_rect.top),
            )


def draw_pen_troughs(screen, buildings, animals):
    """Karámcsoportonként pontosan egy etető- és itatóvályút rajzol."""
    troughs = list(iter_troughs(buildings, animals))
    for trough in troughs:
        is_water = trough["type"] == "water"
        _draw_trough(
            screen,
            trough["rect"],
            TROUGH_WATER_COLOR if is_water else TROUGH_FEED_COLOR,
            trough["stock"],
            trough["capacity"],
            water=is_water,
        )


def supply_animals_from_troughs(animals, buildings):
    """Teljes Karámcsoportonként, részleges fogyasztás nélkül biztosít ellátást."""
    synchronize_pen_group_stocks(buildings, animals)
    supplied_animals = []
    for group in get_animal_pen_groups(buildings):
        group_animals = get_group_animals(animals, group)
        if not group_animals:
            continue
        required_food = len(group_animals) * FOOD_PER_ANIMAL_PER_WEEK
        required_water = len(group_animals) * WATER_PER_ANIMAL_PER_WEEK
        food_stock, water_stock = get_group_supply(group)
        food_missing = food_stock < required_food
        water_missing = water_stock < required_water
        if food_missing:
            log(
                "A Karám állatai nem kaptak elegendő eledelt.",
                "Animals",
            )
        if water_missing:
            log(
                "A Karám állatai nem kaptak elegendő ivóvizet.",
                "Animals",
            )
        if food_missing or water_missing:
            continue

        canonical = _canonical_pen(group)
        canonical[FOOD_STOCK_KEY] = food_stock - required_food
        canonical[WATER_STOCK_KEY] = water_stock - required_water
        supplied_animals.extend(group_animals)
    return supplied_animals
