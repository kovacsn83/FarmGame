"""A Városi Étterem adatvezérelt, heti automatikus felvásárlása."""

from buildings import get_marketable_item_amount, remove_marketable_item
from constants import AUTO_PURCHASE_DELIVERY_COST_PER_UNIT
from financial_history import EXPENSE_SHIPPING
from game_logger import log
from inventory import get_inventory_item_data
from money_format import format_money


RESTAURANT_PRICE_MULTIPLIER = 1.20
RESTAURANT_WEEKLY_QUANTITY = 1


def get_restaurant_sellable_item_ids():
    """A katalógus sorrendjében adja vissza az éttermi termékeket."""
    from inventory import PRODUCTS
    return tuple(
        item_id for item_id, definition in PRODUCTS.items()
        if definition.get("restaurant_sellable", False)
    )


def get_restaurant_unit_price(item_id):
    """Mindig az aktuális katalógusárból számítja a 20%-os prémiumot."""
    item = get_inventory_item_data(item_id)
    if item is None or not item.get("restaurant_sellable", False):
        return None
    return float(item["price"]) * RESTAURANT_PRICE_MULTIPLIER


class RestaurantSystem:
    """Tárolja a választásokat és hetente egyszer végrehajtja az eladásokat."""

    def __init__(self):
        self.auto_sell = {
            item_id: False for item_id in get_restaurant_sellable_item_ids()
        }

    def is_enabled(self, item_id):
        return bool(self.auto_sell.get(item_id, False))

    def toggle(self, item_id):
        if item_id not in get_restaurant_sellable_item_ids():
            return False
        self.auto_sell[item_id] = not self.is_enabled(item_id)
        return True

    def run_weekly(self, buildings, economy):
        """Kijelölt termékenként legfeljebb egy darabot értékesít."""
        sales = []
        for item_id in get_restaurant_sellable_item_ids():
            if not self.is_enabled(item_id):
                continue
            if get_marketable_item_amount(buildings, item_id) < 1:
                continue
            item = get_inventory_item_data(item_id)
            price = get_restaurant_unit_price(item_id)
            if price is None or not remove_marketable_item(
                    buildings, item_id, RESTAURANT_WEEKLY_QUANTITY):
                continue
            shipping = (
                AUTO_PURCHASE_DELIVERY_COST_PER_UNIT
                * RESTAURANT_WEEKLY_QUANTITY
            )
            economy.credit_income(
                item["income_category"], price, item_id,
                f"Éttermi értékesítés: {RESTAURANT_WEEKLY_QUANTITY} db {item['name']}",
            )
            economy.charge(shipping)
            economy.record_expense(
                EXPENSE_SHIPPING, shipping, item_id,
                f"Éttermi kiszállítás: {RESTAURANT_WEEKLY_QUANTITY} db {item['name']}",
            )
            log(
                f"1 db {item['name']} értékesítve: {format_money(price)}. "
                f"Szállítás: {format_money(shipping)}.",
                "Restaurant",
            )
            sales.append(item_id)
        return tuple(sales)

    def to_save_record(self):
        return {
            item_id: self.is_enabled(item_id)
            for item_id in get_restaurant_sellable_item_ids()
        }

    def load_save_record(self, record):
        """Régi mentésnél minden automatikus értékesítés kikapcsolt."""
        record = record if isinstance(record, dict) else {}
        self.auto_sell = {
            item_id: record.get(item_id) is True
            for item_id in get_restaurant_sellable_item_ids()
        }
