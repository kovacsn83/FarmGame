from dataclasses import dataclass

from constants import AUTO_PURCHASE_DELIVERY_COST_PER_UNIT
from game_logger import log
from money_format import format_money


@dataclass(frozen=True)
class AutomaticPurchaseQuote:
    """Egy automatikus piaci beszerzés központilag számított költségei."""

    quantity: int
    unit_price: float
    goods_cost: float
    delivery_cost: float
    total_cost: float


def get_automatic_purchase_quote(unit_price, quantity):
    """Áruértéket, szállítást és végösszeget számol egyetlen szabályból."""
    quantity = max(0, int(quantity))
    unit_price = float(unit_price)
    goods_cost = unit_price * quantity
    delivery_cost = AUTO_PURCHASE_DELIVERY_COST_PER_UNIT * quantity
    return AutomaticPurchaseQuote(
        quantity=quantity,
        unit_price=unit_price,
        goods_cost=goods_cost,
        delivery_cost=delivery_cost,
        total_cost=goods_cost + delivery_cost,
    )


def get_automatic_purchase_unit_cost(unit_price):
    """A szimuláció és a jövőbeli beszerzések közös darabköltsége."""
    return get_automatic_purchase_quote(unit_price, 1).total_cost


def purchase_automatically(economy, item_name, unit_price, quantity):
    """Egységesen levonja és naplózza az automatikus piaci beszerzést."""
    quote = get_automatic_purchase_quote(unit_price, quantity)
    if quote.quantity <= 0 or not economy.spend(quote.total_cost):
        return None
    log(
        f"{quote.quantity} db {item_name} vásárolva. "
        f"Ár: {format_money(quote.goods_cost)}. "
        f"Szállítás: {format_money(quote.delivery_cost)}. "
        f"Összesen: {format_money(quote.total_cost)}.",
        "Market",
    )
    return quote
