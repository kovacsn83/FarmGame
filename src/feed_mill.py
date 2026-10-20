"""Level-I feed mill: shared freight, atomic flock feeding and exact tenths."""
CAPACITY = 200
ANIMAL_LIMIT = 12
INPUT_TARGET = 20
INPUT_REORDER_THRESHOLD = 10
DELIVERY_CAPACITY = 20


class StorageTooltipLines(list):
    """Ordinary tooltip text with optional storage-meter metadata."""
    def __init__(self, lines, mill):
        super().__init__(lines)
        self.storage_meter = (sum(mill.get("processing_inventory", {}).values()),
                              sum(mill.get("processing_in_transit", {}).values()), CAPACITY)


def get_feed_mill_stock_lines(mill):
    inventory = mill.get("processing_inventory", {})
    transit = mill.get("processing_in_transit", {})
    used = sum(inventory.values())
    return [f"Raktár telítettsége: {used} / {CAPACITY} ({used / CAPACITY:.0%})",
            f"Búza: {inventory.get('wheat', 0)} / {INPUT_TARGET} db célkészlet",
            f"Kukorica: {inventory.get('corn', 0)} / {INPUT_TARGET} db célkészlet",
            f"Úton: Búza {transit.get('wheat', 0)}, Kukorica {transit.get('corn', 0)} db",
            "Utánpótlás: 10 db alatt, legfeljebb 20 db / fuvar"]


def initialize_feed_mill(mill):
    mill.setdefault("processing_inventory", {"wheat": 0, "corn": 0, "chicken_feed": 0})
    for item in ("wheat", "corn", "chicken_feed"):
        mill["processing_inventory"].setdefault(item, 0)
    mill.setdefault("processing_in_transit", {})
    mill.setdefault("processing_capacity", CAPACITY)
    mill.setdefault("processing_week", -1)
    mill.setdefault("processing_status", "waiting")
    mill.setdefault("feed_mill_week", -1)
    # Old saves do not record whether their current week's batch was made.
    # Conservatively count that week as used, preventing duplicate production.
    mill.setdefault("feed_produced_week", mill["feed_mill_week"])
    mill.setdefault("fed_this_week", False)
    mill.setdefault("bonus_tenths", {"egg": 0, "chicken_meat": 0})
    return mill


def try_produce_feed(mill):
    initialize_feed_mill(mill)
    week = mill["feed_mill_week"]
    if week < 0 or mill["feed_produced_week"] == week:
        return False
    inventory = mill["processing_inventory"]
    used = sum(inventory.values()) + sum(mill["processing_in_transit"].values())
    if inventory["wheat"] < 5 or inventory["corn"] < 5 or used + 2 > CAPACITY:
        return False
    inventory["wheat"] -= 5
    inventory["corn"] -= 5
    inventory["chicken_feed"] += 12
    mill["feed_produced_week"] = week
    return True


def get_feed_mill_status_lines(mill):
    inventory = mill.get("processing_inventory", {})
    transit = mill.get("processing_in_transit", {})
    made = (mill.get("feed_mill_week", -1) >= 0 and
            mill.get("feed_produced_week") == mill.get("feed_mill_week"))
    lines = [f"E heti gyártás: {12 if made else 0} / 12 Csirketáp"]
    if made:
        lines.append("Gyártás: a heti keret elfogyott")
    elif sum(inventory.values()) + sum(transit.values()) + 2 > CAPACITY:
        lines.append("Gyártás: nincs elegendő raktárhely")
    else:
        reasons = mill.get("feed_supply_reasons", {})
        for item, name in (("wheat", "Búza"), ("corn", "Kukorica")):
            missing = max(0, 5 - inventory.get(item, 0))
            if missing:
                pending = transit.get(item, 0)
                lines.append(f"{name}: {missing} db hiányzik – " +
                             (f"{pending} db szállítás alatt" if pending else
                              reasons.get(item, "szállításra vár")))
    return lines


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
    return StorageTooltipLines(["Takarmánykeverő üzem I.",
            f"Csirkék: {len(mill_animals(mill, animals))} / {ANIMAL_LIMIT}",
            "Heti termelés: 12 Csirketáp",
            *get_feed_mill_status_lines(mill),
            f"Csirketáp: {inventory.get('chicken_feed', 0)}",
            *get_feed_mill_stock_lines(mill),
            "Sáv: zöld = készlet, sárga = úton",
            get_feed_mill_feeding_line(mill, animals),
            "Automatikus itatás | Bónusz: +10%"], mill)


def get_feed_mill_feeding_line(mill, animals):
    flock = [a for a in mill_animals(mill, animals)
             if a.get("slaughter_state") != "waiting_for_storage"]
    if not flock:
        return "Etetés: nincs etetendő csirke"
    if mill.get("fed_this_week"):
        return "Etetés: Biztosítva"
    if mill.get("processing_inventory", {}).get("chicken_feed", 0) >= len(flock):
        return "Etetés: táp rendelkezésre áll, a következő hétváltáskor"
    return "Etetés: táphiány, az állomány vár"


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
        try_produce_feed(mill)
        flock = [a for a in mill_animals(mill, animals)
                 if a.get("slaughter_state") != "waiting_for_storage"]
        if flock and inventory["chicken_feed"] >= len(flock):
            inventory["chicken_feed"] -= len(flock)
            mill["fed_this_week"] = True
        mill["processing_status"] = "ready" if mill["fed_this_week"] else "waiting"
        # Refill each ingredient to four batches once below two batches.
        # Include reserved deliveries so busy vehicles do not cause duplicate orders.
        if vehicles is not None and get_processing_available_capacity(mill) >= 2:
            for item in ("wheat", "corn"):
                available = inventory.get(item, 0) + mill["processing_in_transit"].get(item, 0)
                if available >= INPUT_REORDER_THRESHOLD:
                    continue
                _request_processing_input(world, buildings, economy, vehicles, mill,
                                          item, INPUT_TARGET, current_ticks)
                reason = "szállításra vár (jármű / útkapcsolat)"
                if mill.get("processing_status") == "no_money":
                    reason = "nincs elegendő pénz a beszerzéshez"
                elif not any(t.is_idle for t in vehicles.tractors):
                    reason = "szabad traktorra vár"
                elif not any(i.vehicle_type.value == "trailer" and
                             i.attached_to is None and i.assigned_task is None
                             for i in vehicles.implements):
                    reason = "szabad pótkocsira vár"
                mill.setdefault("feed_supply_reasons", {})[item] = reason


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
