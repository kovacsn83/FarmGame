import random

import pygame

from buildings import (
    find_building_data, get_animal_pen_groups, store_items,
)
from animal_troughs import (
    get_forbidden_movement_rects, supply_animals_from_troughs,
)
from constants import TILE_SIZE
from game_logger import log
from money_format import format_money
from inventory import PRODUCTS
from animal_renderer import draw_animal


ANIMAL_TILES_PER_CAPACITY = 4
ANIMAL_MOVE_INTERVAL_MIN_MS = 6000
ANIMAL_MOVE_INTERVAL_MAX_MS = 9000
# Kompatibilitási alias régebbi külső kiegészítések számára.
ANIMAL_MOVE_INTERVAL_MS = ANIMAL_MOVE_INTERVAL_MAX_MS
ANIMAL_MOVE_DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))
ANIMAL_MOVE_TARGET_RETRIES = 4
ANIMAL_MOVEMENT_HITBOX_SIZE = 12
ANIMAL_DIRECTION_BY_OFFSET = {
    (-1, 0): "up",
    (1, 0): "down",
    (0, -1): "left",
    (0, 1): "right",
}
CATTLE_MILK_PER_WEEK = 1
CATTLE_MANURE_PER_WEEK = 1
CATTLE_LIFESPAN_WEEKS = 104
CATTLE_BEEF_PER_CYCLE = 10
PIG_MANURE_PER_WEEK = 1
PIG_FATTENING_WEEKS = 52
PIG_PORK_PER_CYCLE = 10
CHICKEN_EGGS_PER_WEEK = 1
CHICKEN_FATTENING_WEEKS = 26
CHICKEN_MEAT_PER_CYCLE = 5

# Az állattípusok központi katalógusa később további állatokkal bővíthető.
ANIMAL_TYPES = {
    "cattle": {
        "name": "Szarvasmarha",
        "purchase_price": 200.00,
        "width": 1,
        "height": 1,
        "color": (145, 92, 55),
        "weekly_products": {
            "milk": CATTLE_MILK_PER_WEEK,
            "manure": CATTLE_MANURE_PER_WEEK,
        },
        "periodic_products": {
            "beef": {
                "amount": CATTLE_BEEF_PER_CYCLE,
                "interval_weeks": CATTLE_LIFESPAN_WEEKS,
                "counter_key": "age_weeks",
                "progress_label": "Életkor",
                "remove_animal_after_production": True,
            },
        },
        "weekly_feed": {
            "item": "alfalfa",
            "amount": 1,
        },
    },
    "pig": {
        "name": "Sertés",
        "purchase_price": 150.00,
        "width": 1,
        "height": 1,
        "color": (218, 137, 145),
        "weekly_products": {
            "manure": PIG_MANURE_PER_WEEK,
        },
        "periodic_products": {
            "pork": {
                "amount": PIG_PORK_PER_CYCLE,
                "interval_weeks": PIG_FATTENING_WEEKS,
                "counter_key": "fattening_weeks",
                "progress_label": "Hízás",
                # A hízási ciklus végén ez a termék lezárja az állat életciklusát.
                "remove_animal_after_production": True,
            },
        },
        "weekly_feed": {
            "item": "corn",
            "amount": 1,
        },
    },
    "chicken": {
        "name": "Csirke",
        "purchase_price": 100.00,
        "width": 1,
        "height": 1,
        "color": (236, 224, 184),
        "weekly_products": {
            "egg": CHICKEN_EGGS_PER_WEEK,
        },
        "weekly_product_tooltips": {
            "egg": "Heti tojástermelés",
        },
        "periodic_products": {
            "chicken_meat": {
                "amount": CHICKEN_MEAT_PER_CYCLE,
                "interval_weeks": CHICKEN_FATTENING_WEEKS,
                "counter_key": "age_weeks",
                "progress_label": "Kor",
                "remove_animal_after_production": True,
            },
        },
        "weekly_feed": {
            "item": "corn",
            "amount": 1,
        },
    },
}


def _pen_identity(pen):
    return pen["row"], pen["col"]


def find_animal_pen_group(buildings, pen):
    """Megkeresi a konkrét Karámot tartalmazó összefüggő karámrendszert."""
    if pen is None or pen.get("type") != "animal_pen":
        return None
    return next(
        (
            group for group in get_animal_pen_groups(buildings)
            if pen in group
        ),
        None,
    )


def get_pen_group_capacity(group):
    """Négy karámmezőnként egy állat férőhelyét biztosítja."""
    if not group:
        return 0
    tile_count = sum(
        pen["width"] * pen["height"]
        for pen in group
    )
    return tile_count // ANIMAL_TILES_PER_CAPACITY


def get_animals_in_pen_group(animals, group):
    if not group:
        return []
    pen_ids = {_pen_identity(pen) for pen in group}
    return [
        animal for animal in animals
        if (animal.get("pen_row"), animal.get("pen_col")) in pen_ids
    ]


def get_pen_group_tiles(group):
    """Egyetlen összefüggő karámrendszer minden bejárható tile-ját adja vissza."""
    if not group:
        return set()
    return {
        (pen["row"] + row, pen["col"] + col)
        for pen in group
        for row in range(pen["height"])
        for col in range(pen["width"])
    }


def _find_assigned_pen(buildings, animal):
    return next(
        (
            building for building in buildings
            if building.get("type") == "animal_pen"
            and building.get("row") == animal.get("pen_row")
            and building.get("col") == animal.get("pen_col")
        ),
        None,
    )


def get_animal_movement_rect(row, col):
    """Az állat testét közelítő, mezőközépre igazított világ-hitboxot adja."""
    center_x = col * TILE_SIZE + TILE_SIZE // 2
    center_y = row * TILE_SIZE + TILE_SIZE // 2
    size = ANIMAL_MOVEMENT_HITBOX_SIZE
    return pygame.Rect(center_x - size // 2, center_y - size // 2, size, size)


def animal_position_is_forbidden(row, col, forbidden_rects):
    """Jelzi, ha az állat teste bármely karámberendezésre rálógna."""
    animal_rect = get_animal_movement_rect(row, col)
    return any(animal_rect.colliderect(rect) for rect in forbidden_rects)


def animal_move_crosses_forbidden(origin, target, forbidden_rects):
    """A teljes következő lépést vizsgálja, nem csak annak végpontját."""
    origin_rect = get_animal_movement_rect(*origin)
    target_rect = get_animal_movement_rect(*target)
    movement_rect = origin_rect.union(target_rect)
    return any(movement_rect.colliderect(rect) for rect in forbidden_rects)


class AnimalMovementSystem:
    """Önálló, időzített és útkeresés nélküli véletlen állatmozgást kezel."""

    def __init__(self, direction_choice=None, wait_time_generator=None):
        self.direction_choice = direction_choice or random.choice
        self.wait_time_generator = wait_time_generator or random.uniform
        self.movement_accumulators = {}
        self.movement_wait_times = {}
        self.obstacle_validated_animals = set()
        self.pen_layout_signature = None
        self.last_update_ticks = None

    def reset(self, current_ticks=None):
        """Új játék és betöltés után teljes mozgási periódust indít."""
        self.movement_accumulators.clear()
        self.movement_wait_times.clear()
        self.obstacle_validated_animals.clear()
        self.pen_layout_signature = None
        self.last_update_ticks = (
            pygame.time.get_ticks() if current_ticks is None else current_ticks
        )

    def synchronize(self, current_ticks=None):
        """Menüszünet alatt eldobja a valós időt, az addigi részidőt megtartja."""
        self.last_update_ticks = (
            pygame.time.get_ticks() if current_ticks is None else current_ticks
        )

    def _get_movement_context(self, animal, buildings):
        pen = _find_assigned_pen(buildings, animal)
        group = find_animal_pen_group(buildings, pen)
        return (
            get_pen_group_tiles(group),
            get_forbidden_movement_rects(group),
        )

    def _relocate_from_forbidden_area(
            self, animal, buildings, occupied_tiles):
        """Régi mentésből származó állatot a legközelebbi szabad mezőre tesz."""
        allowed_tiles, forbidden_rects = self._get_movement_context(
            animal, buildings,
        )
        if not allowed_tiles:
            return False

        origin = animal["row"], animal["col"]
        if not animal_position_is_forbidden(*origin, forbidden_rects):
            return False

        candidates = sorted(
            allowed_tiles,
            key=lambda tile: (
                abs(tile[0] - origin[0]) + abs(tile[1] - origin[1]),
                tile[0], tile[1],
            ),
        )
        for target in candidates:
            if target in occupied_tiles:
                continue
            if animal_position_is_forbidden(*target, forbidden_rects):
                continue
            occupied_tiles.discard(origin)
            animal["row"], animal["col"] = target
            occupied_tiles.add(target)
            return True
        return False

    def _try_move(self, animal, buildings, occupied_tiles):
        allowed_tiles, forbidden_rects = self._get_movement_context(
            animal, buildings,
        )
        if not allowed_tiles:
            return False

        origin = animal["row"], animal["col"]
        for _ in range(ANIMAL_MOVE_TARGET_RETRIES):
            row_offset, col_offset = self.direction_choice(
                ANIMAL_MOVE_DIRECTIONS,
            )
            target = (
                animal["row"] + row_offset,
                animal["col"] + col_offset,
            )
            if target not in allowed_tiles or target in occupied_tiles:
                continue
            if animal_position_is_forbidden(*target, forbidden_rects):
                continue
            if animal_move_crosses_forbidden(origin, target, forbidden_rects):
                continue
            break
        else:
            return False

        occupied_tiles.remove(origin)
        animal["row"], animal["col"] = target
        animal["facing_direction"] = ANIMAL_DIRECTION_BY_OFFSET[
            row_offset, col_offset
        ]
        occupied_tiles.add(target)
        return True

    def update(self, animals, buildings, game_time, current_ticks=None):
        """Az eltelt, sebességkorrigált idő alapján állatonként lépést próbál."""
        now = (
            pygame.time.get_ticks()
            if current_ticks is None else current_ticks
        )
        elapsed_ms = (
            0 if self.last_update_ticks is None
            else max(0, now - self.last_update_ticks)
        )
        self.last_update_ticks = now
        active_keys = {id(animal) for animal in animals}
        self.movement_accumulators = {
            key: value
            for key, value in self.movement_accumulators.items()
            if key in active_keys
        }
        self.movement_wait_times = {
            key: value
            for key, value in self.movement_wait_times.items()
            if key in active_keys
        }
        self.obstacle_validated_animals.intersection_update(active_keys)
        pen_layout_signature = tuple(sorted(
            (
                building["row"], building["col"],
                building["width"], building["height"],
            )
            for building in buildings
            if building.get("type") == "animal_pen"
        ))
        if pen_layout_signature != self.pen_layout_signature:
            self.obstacle_validated_animals.clear()
            self.pen_layout_signature = pen_layout_signature
        occupied_tiles = {
            (animal["row"], animal["col"])
            for animal in animals
        }
        # Betöltés után szüneteltetett időnél is azonnal felszabadítjuk a vályút.
        for animal in animals:
            key = id(animal)
            if key not in self.obstacle_validated_animals:
                self._relocate_from_forbidden_area(
                    animal, buildings, occupied_tiles,
                )
                self.obstacle_validated_animals.add(key)

        speed_multiplier = game_time.time_speed_multiplier
        if speed_multiplier <= 0:
            return 0

        moved_count = 0
        for animal in animals:
            key = id(animal)
            accumulated = self.movement_accumulators.get(key, 0.0)
            accumulated += elapsed_ms * speed_multiplier
            wait_time = self.movement_wait_times.get(key)
            if wait_time is None:
                wait_time = self._new_wait_time()
            while accumulated >= wait_time:
                if self._try_move(animal, buildings, occupied_tiles):
                    moved_count += 1
                accumulated -= wait_time
                # Sikeres és sikertelen próbálkozás után is új ritmus indul.
                wait_time = self._new_wait_time()
            self.movement_accumulators[key] = accumulated
            self.movement_wait_times[key] = wait_time
        return moved_count

    def _new_wait_time(self):
        """Új, 1× sebességen 6–9 másodperces mozgási várakozást ad."""
        return float(self.wait_time_generator(
            ANIMAL_MOVE_INTERVAL_MIN_MS,
            ANIMAL_MOVE_INTERVAL_MAX_MS,
        ))


def get_animal_placement_error(
        animals, buildings, row, col, animal_type):
    """Visszaadja az állat elhelyezését akadályozó első szabályt."""
    definition = ANIMAL_TYPES.get(animal_type)
    if definition is None:
        return "Ismeretlen állattípus."
    pen = find_building_data(buildings, row, col)
    if pen is None or pen.get("type") != "animal_pen":
        return f"A {definition['name'].lower()} csak Karámba helyezhető."
    if any(
            animal["row"] == row and animal["col"] == col
            for animal in animals):
        return "A kiválasztott Karámmező már foglalt."

    group = find_animal_pen_group(buildings, pen)
    if animal_position_is_forbidden(
            row, col, get_forbidden_movement_rects(group)):
        return "Az állat nem helyezhető az Etető- vagy Itatóvályúra."
    group_animals = get_animals_in_pen_group(animals, group)
    if any(animal.get("type") != animal_type for animal in group_animals):
        return "Különböző állatfajok nem tarthatók ugyanabban a Karámban."
    if len(group_animals) >= get_pen_group_capacity(group):
        return "Nincs szabad férőhely a kiválasztott Karámban."
    return None


def can_place_animal(animals, buildings, row, col, animal_type):
    """Ellenőrzi a helyet, a férőhelyet és a karám állatfaját."""
    return get_animal_placement_error(
        animals, buildings, row, col, animal_type,
    ) is None


def purchase_and_place_animal(
        animals, buildings, economy, row, col, animal_type):
    """Érvényes karámhelyre megvásárol és eltárol egy új állatot."""
    animal_definition = ANIMAL_TYPES.get(animal_type)
    if animal_definition is None:
        return False
    placement_error = get_animal_placement_error(
        animals, buildings, row, col, animal_type,
    )
    if placement_error is not None:
        log(placement_error, "Animals")
        return False
    price = animal_definition["purchase_price"]
    if not economy.can_afford(price):
        log(
            f"Nincs elegendő pénz a {animal_definition['name'].lower()} "
            "megvásárlásához.", "Animals",
        )
        return False

    pen = find_building_data(buildings, row, col)
    economy.spend(price)
    animal = {
        "type": animal_type,
        "row": row,
        "col": col,
        "pen_row": pen["row"],
        "pen_col": pen["col"],
        "facing_direction": "down",
        "visual_id": max(
            (
                existing.get("visual_id", index + 1)
                if isinstance(existing.get("visual_id", index + 1), int)
                and not isinstance(existing.get("visual_id", index + 1), bool)
                else index + 1
                for index, existing in enumerate(animals)
            ),
            default=0,
        ) + 1,
    }
    for periodic_product in animal_definition.get(
            "periodic_products", {}).values():
        animal[periodic_product["counter_key"]] = 0
    animals.append(animal)
    log(
        f"{animal_definition['name']} megvásárolva: {format_money(price)}",
        "Animals",
    )
    return True


def produce_weekly_animal_products(
        animals, buildings, animal_registry=None, notification_manager=None):
    """A heti és az önálló időközű állati termékeket raktárba helyezi."""
    animal_registry = animals if animal_registry is None else animal_registry
    produced_animals = 0
    produced_totals = {}
    storage_failed = False
    animals_to_remove = []
    for animal in list(animals):
        definition = ANIMAL_TYPES.get(animal.get("type"))
        if definition is None:
            continue

        animal_produced = False
        weekly_products = definition.get("weekly_products", {})
        if weekly_products:
            if store_items(buildings, weekly_products):
                animal_produced = True
                for item_id, amount in weekly_products.items():
                    produced_totals[item_id] = (
                        produced_totals.get(item_id, 0) + amount
                    )
            else:
                storage_failed = True

        for item_id, production in definition.get(
                "periodic_products", {}).items():
            counter_key = production["counter_key"]
            elapsed_weeks = animal.get(counter_key, 0) + 1
            if elapsed_weeks < production["interval_weeks"]:
                animal[counter_key] = elapsed_weeks
                continue

            # Az esedékes ciklus tárolási eredménytől függetlenül lezárul,
            # ezért telt raktár után sem halmozódik későbbi túltermelés.
            animal[counter_key] = 0
            amount = production["amount"]
            if store_items(buildings, {item_id: amount}):
                animal_produced = True
                produced_totals[item_id] = (
                    produced_totals.get(item_id, 0) + amount
                )
                if production.get("remove_animal_after_production"):
                    animals_to_remove.append((animal, item_id, amount))
            else:
                storage_failed = True

        if animal_produced:
            produced_animals += 1

    removed_animal_counts = {}
    removed_product_totals = {}
    # Csak a sikeresen eltárolt végtermék után szűnik meg az állat minden állapota.
    for animal, item_id, amount in animals_to_remove:
        if animal in animal_registry:
            animal_registry.remove(animal)
            animal_type = animal.get("type")
            removed_animal_counts[animal_type] = (
                removed_animal_counts.get(animal_type, 0) + 1
            )
            animal_products = removed_product_totals.setdefault(
                animal_type, {},
            )
            animal_products[item_id] = (
                animal_products.get(item_id, 0) + amount
            )

    for animal_type, slaughtered_count in removed_animal_counts.items():
        definition = ANIMAL_TYPES.get(animal_type, {})
        animal_name = definition.get("name", animal_type).lower()
        subject = (
            f"Egy {animal_name}" if slaughtered_count == 1
            else f"{slaughtered_count} {animal_name}"
        )
        product_parts = [
            f"{amount} db {PRODUCTS[item_id]['name'].lower()}"
            for item_id, amount in removed_product_totals.get(
                animal_type, {},
            ).items()
        ]
        products_text = ", ".join(product_parts)
        public_message = (
            f"{subject} levágásra került. {products_text} került a raktárba."
        )
        log(
            f"{subject} levágásra került, {products_text} került a Raktárba.",
            "Animals",
        )
        if notification_manager is not None:
            notification_manager.enqueue(public_message)

    if produced_animals:
        product_names = ", ".join(
            f"{amount} {PRODUCTS[item_id]['name'].lower()}"
            for item_id, amount in produced_totals.items()
        )
        log(
            f"Állati termelés: {product_names} került a raktárba.",
            "Animals",
        )
    if storage_failed:
        log(
            "Nincs elegendő raktárkapacitás az összes állati termékhez.",
            "Inventory",
        )
    return produced_animals


def feed_animals(animals, buildings, economy):
    """A Karámcsoport közös Etető- és Itatóvályújából biztosít ellátást."""
    return supply_animals_from_troughs(animals, buildings), 0.0


def run_weekly_animal_cycle(
        animals, buildings, economy, notification_manager=None):
    """Az etetést és az arra épülő termelést egyetlen heti ciklusba fogja."""
    fed_animals, purchase_cost = feed_animals(
        animals, buildings, economy,
    )
    produced_animals = produce_weekly_animal_products(
        fed_animals, buildings, animal_registry=animals,
        notification_manager=notification_manager,
    )
    return {
        "fed_animals": len(fed_animals),
        "produced_animals": produced_animals,
        "feed_purchase_cost": purchase_cost,
    }


# A mentésekhez vagy külső kiegészítésekhez használt régi függvénynevek.
produce_daily_animal_products = produce_weekly_animal_products
run_daily_animal_cycle = run_weekly_animal_cycle


def animal_pen_demolition_block_reason(building, buildings, animals):
    """Megakadályozza egy állatokat tartalmazó karámrendszer megbontását."""
    if building is None or building.get("type") != "animal_pen":
        return None
    group = find_animal_pen_group(buildings, building)
    if get_animals_in_pen_group(animals, group):
        return "A Karám nem bontható le, amíg állat van benne."
    return None


def draw_animals(screen, animals):
    """Az állattípusok külön procedurális renderelőit hívja meg."""
    for index, animal in enumerate(animals):
        definition = ANIMAL_TYPES.get(animal.get("type"))
        if definition is None:
            continue
        draw_animal(screen, animal, index)
