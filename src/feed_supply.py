from dataclasses import dataclass

from animal_troughs import (
    FOOD_STOCK_KEY, TROUGH_WEEKS, get_group_anchor, get_group_animals,
)
from animals import ANIMAL_TYPES
from buildings import (
    get_total_inventory, remove_item, store_item,
)
from crops import CROPS
from game_logger import log
from inventory import get_inventory_item_name
from market_procurement import (
    get_automatic_purchase_quote, purchase_automatically,
)
from financial_history import EXPENSE_ANIMAL_FEED


@dataclass(frozen=True)
class FeedSupplyTransaction:
    """Egy sikeres, teljes takarmányrakodás visszaellenőrizhető bizonylata."""

    success: bool
    feed_type: str | None = None
    required_amount: int = 0
    warehouse_amount: int = 0
    purchased_amount: int = 0
    goods_cost: float = 0.0
    delivery_cost: float = 0.0
    purchase_cost: float = 0.0
    error_message: str | None = None


def get_feed_requirement(group, animals):
    """Meghatározza a Karámcsoport takarmányát és a nyolchetes hiányt."""
    group_animals = get_group_animals(animals, group)
    if not group_animals:
        return None, 0
    feed_types = {
        ANIMAL_TYPES.get(animal.get("type"), {})
        .get("weekly_feed", {})
        .get("item")
        for animal in group_animals
    }
    feed_types.discard(None)
    if len(feed_types) != 1:
        return None, 0
    feed_type = next(iter(feed_types))
    anchor = get_group_anchor(group)
    current_stock = max(0, anchor.get(FOOD_STOCK_KEY, 0))
    target_stock = len(group_animals) * TROUGH_WEEKS
    return feed_type, max(0, target_stock - current_stock)


def prepare_feed_supply(buildings, economy, group, animals):
    """A teljes rakományt atomikusan biztosítja készletből és piaci vételből."""
    feed_type, required = get_feed_requirement(group, animals)
    if feed_type not in CROPS or required <= 0:
        return FeedSupplyTransaction(
            False, feed_type=feed_type,
            error_message="Az Etetővályúhoz jelenleg nincs szükség takarmányra.",
        )

    available = get_total_inventory(buildings).get(feed_type, 0)
    warehouse_amount = min(required, available)
    purchased_amount = required - warehouse_amount
    purchase_quote = get_automatic_purchase_quote(
        CROPS[feed_type]["price"], purchased_amount,
    )
    purchase_cost = purchase_quote.total_cost
    feed_name = get_inventory_item_name(feed_type)
    log(
        f"Az etetéshez szükséges takarmány: {required} {feed_name}.",
        "Supply",
    )

    if purchased_amount:
        if not any(b.get("type") == "market" for b in buildings):
            message = (
                "Nincs elegendő takarmány a Raktárban, és nincs Piac az "
                "automatikus vásárláshoz."
            )
            log(message, "Supply")
            return FeedSupplyTransaction(False, error_message=message)
        if not economy.can_afford(purchase_cost):
            message = (
                "Nincs elegendő takarmány a Raktárban, és nincs elég pénz "
                "a hiányzó mennyiség megvásárlására."
            )
            log(message, "Supply")
            return FeedSupplyTransaction(False, error_message=message)

    # Minden ellenőrzés megelőzi a két módosítást; így résztranzakció nem marad.
    if warehouse_amount and not remove_item(
            buildings, feed_type, warehouse_amount):
        message = "A Raktár takarmánykészlete időközben megváltozott."
        log(message, "Inventory")
        return FeedSupplyTransaction(False, error_message=message)
    receipt = None
    if purchased_amount:
        receipt = purchase_automatically(
            economy, feed_name, CROPS[feed_type]["price"], purchased_amount,
            EXPENSE_ANIMAL_FEED, feed_type,
        )
    if purchased_amount and receipt is None:
        if warehouse_amount:
            store_item(buildings, feed_type, warehouse_amount)
        message = "A takarmányvásárlás a pénzegyenleg változása miatt meghiúsult."
        log(message, "Market")
        return FeedSupplyTransaction(False, error_message=message)

    if warehouse_amount:
        log(
            f"{warehouse_amount} {feed_name} levonva a Raktárból.",
            "Inventory",
        )
    return FeedSupplyTransaction(
        True, feed_type, required, warehouse_amount,
        purchased_amount, purchase_quote.goods_cost,
        purchase_quote.delivery_cost, purchase_cost,
    )


def deliver_feed_cargo(group, animals, trailer):
    """A rakományból csak az aktuális vályúhiányt adja át, többletet nem veszít."""
    if trailer is None or trailer.cargo_type not in CROPS:
        return 0
    expected_type, missing = get_feed_requirement(group, animals)
    if expected_type != trailer.cargo_type or missing <= 0:
        return 0
    delivered = min(missing, trailer.cargo_amount)
    anchor = get_group_anchor(group)
    anchor[FOOD_STOCK_KEY] = anchor.get(FOOD_STOCK_KEY, 0) + delivered
    trailer.cargo_amount -= delivered
    if trailer.cargo_amount == 0:
        trailer.cargo_type = "empty"
    log(
        f"Etetővályú feltöltve: +{delivered} "
        f"{get_inventory_item_name(expected_type)}.", "Supply",
    )
    return delivered


def return_feed_cargo(buildings, trailer):
    """Megszakított szállítás rakományát egyszer, veszteség nélkül visszateszi."""
    if trailer is None or trailer.cargo_type == "empty" or trailer.cargo_amount <= 0:
        return True
    if not store_item(buildings, trailer.cargo_type, trailer.cargo_amount):
        log(
            "A Pótkocsi rakománya a szabad kapacitás hiánya miatt a "
            "Pótkocsiban maradt.", "Inventory",
        )
        return False
    trailer.cargo_type = "empty"
    trailer.cargo_amount = 0
    log("A Pótkocsi rakománya visszakerült a Raktárba.", "Supply")
    return True
