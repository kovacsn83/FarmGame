"""Level-I feed mill: shared freight, atomic flock feeding and exact tenths."""
CAPACITY = 200
ANIMAL_LIMIT = 12


def initialize_feed_mill(mill):
    mill.setdefault("processing_inventory", {"wheat": 0, "corn": 0, "chicken_feed": 0})
    for item in ("wheat", "corn", "chicken_feed"):
        mill["processing_inventory"].setdefault(item, 0)
    mill.setdefault("processing_in_transit", {})
    mill.setdefault("processing_capacity", CAPACITY)
    mill.setdefault("processing_week", -1)
    mill.setdefault("processing_status", "waiting")
    mill.setdefault("feed_mill_week", -1)
    mill.setdefault("fed_this_week", False)
    mill.setdefault("bonus_tenths", {"egg": 0, "chicken_meat": 0})
    return mill


def yard_tiles(mill):
    if (mill["width"], mill["height"]) != (12, 8):
        return set()
    return {(mill["row"] + r, mill["col"] + c)
            for r in range(8) for c in range(12)
            if not (r >= 4 and c < 4) and not (r == 0 and c in (0, 1))}


def assigned_mill(animal, buildings):
    return next((b for b in buildings if b.get("type") == "feed_mill"
                 and (b["row"], b["col"]) ==
                 (animal.get("pen_row"), animal.get("pen_col"))), None)


def mill_animals(mill, animals):
    return [a for a in animals if (a.get("pen_row"), a.get("pen_col")) ==
            (mill["row"], mill["col"])]


def get_feed_mill_tooltip_lines(mill, animals):
    """Read-only live overview for the existing black hover tooltip."""
    inventory = mill.get("processing_inventory", {})
    transit = mill.get("processing_in_transit", {})
    return ["Takarmánykeverő üzem I.",
            f"Csirkék: {len(mill_animals(mill, animals))} / {ANIMAL_LIMIT}",
            "Heti termelés: 12 Csirketáp",
            f"Raktár: {sum(inventory.values())} / {CAPACITY}",
            f"Csirketáp: {inventory.get('chicken_feed', 0)}",
            f"Úton lévő alapanyag: {sum(transit.values())}",
            "Etetés: " + ("Biztosítva" if mill.get("fed_this_week") else "Táphiány / nincs állat"),
            "Automatikus itatás | Bónusz: +10%"]


def run_weekly_feed_mills(world, buildings, animals, economy, vehicles, week,
                         current_ticks=None):
    from processing import _request_processing_input, get_processing_available_capacity
    reconcile = getattr(vehicles, "reconcile_processing_deliveries", None)
    if reconcile is not None:
        reconcile(buildings)
    for mill in buildings:
        if mill.get("type") != "feed_mill":
            continue
        initialize_feed_mill(mill)
        if mill["feed_mill_week"] == week:
            continue
        mill["feed_mill_week"] = week
        inventory = mill["processing_inventory"]
        mill["fed_this_week"] = False
        if inventory["wheat"] >= 5 and inventory["corn"] >= 5:
            # 10 inputs become 12 output: reserve space for the extra two units.
            used = sum(inventory.values()) + sum(mill["processing_in_transit"].values())
            if used + 2 <= CAPACITY:
                inventory["wheat"] -= 5
                inventory["corn"] -= 5
                inventory["chicken_feed"] += 12
        flock = [a for a in mill_animals(mill, animals)
                 if a.get("slaughter_state") != "waiting_for_storage"]
        if flock and inventory["chicken_feed"] >= len(flock):
            inventory["chicken_feed"] -= len(flock)
            mill["fed_this_week"] = True
        mill["processing_status"] = "ready" if mill["fed_this_week"] else "waiting"
        # Keep one batch supplied; in-transit reservations prevent duplicate purchases.
        if vehicles is not None and get_processing_available_capacity(mill) >= 2:
            for item in ("wheat", "corn"):
                _request_processing_input(world, buildings, economy, vehicles, mill,
                                          item, 5, current_ticks)


def feed_mill_fed_animals(animals, buildings):
    return [a for a in animals if (mill := assigned_mill(a, buildings)) is not None
            and mill.get("fed_this_week")
            and a.get("slaughter_state") != "waiting_for_storage"]


def bonus_output(animal, buildings, item, amount):
    mill = assigned_mill(animal, buildings)
    if mill is None or item not in ("egg", "chicken_meat"):
        return amount, None
    initialize_feed_mill(mill)
    tenths = mill["bonus_tenths"].get(item, 0) + amount * 11
    return tenths // 10, (mill, item, tenths % 10)


def commit_bonus(pending):
    if pending is not None:
        mill, item, remainder = pending
        mill["bonus_tenths"][item] = remainder
