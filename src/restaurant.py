"""A Városi Étterem adatvezérelt, szintezett heti felvásárlása."""

from buildings import get_marketable_item_amount, remove_marketable_item
from calendar_utils import get_year_and_week
from constants import AUTO_PURCHASE_DELIVERY_COST_PER_UNIT
from financial_history import EXPENSE_SHIPPING
from game_logger import log
from inventory import get_inventory_item_data
from money_format import format_money


RESTAURANT_PRICE_MULTIPLIER = 1.20
RESTAURANT_MIN_LEVEL = 1
RESTAURANT_MAX_LEVEL = 10
RESTAURANT_PERIOD_WEEKS = 13
RESTAURANT_LEVEL_UP_RATIO = 0.75
RESTAURANT_LEVEL_DOWN_RATIO = 0.40


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


def get_restaurant_period(elapsed_week):
    """Stabil periódusazonosítót és az éven belüli 13 hetes tartományt ad."""
    year, week = get_year_and_week(elapsed_week)
    period_index = min(3, (week - 1) // RESTAURANT_PERIOD_WEEKS)
    start_week = period_index * RESTAURANT_PERIOD_WEEKS + 1
    end_week = start_week + RESTAURANT_PERIOD_WEEKS - 1
    return (year - 1) * 4 + period_index, start_week, end_week


def is_valid_restaurant_save_record(record):
    """Elfogadja az új progressziót és a korábbi lapos checkbox-sémát is."""
    if not isinstance(record, dict):
        return False
    if "auto_sell" not in record:
        return all(
            isinstance(item_id, str) and isinstance(enabled, bool)
            for item_id, enabled in record.items()
        )
    auto_sell = record.get("auto_sell")
    if not isinstance(auto_sell, dict) or not all(
            isinstance(item_id, str) and isinstance(enabled, bool)
            for item_id, enabled in auto_sell.items()):
        return False
    level = record.get("level")
    if (not isinstance(level, int) or isinstance(level, bool)
            or not RESTAURANT_MIN_LEVEL <= level <= RESTAURANT_MAX_LEVEL):
        return False
    for key in ("period_requested_units", "period_fulfilled_units"):
        value = record.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return False
    if record["period_fulfilled_units"] > record["period_requested_units"]:
        return False
    for key in (
            "current_period_id", "last_evaluated_period",
            "last_processed_week"):
        value = record.get(key)
        if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0):
            return False
    return True


class RestaurantSystem:
    """Tárolja a választásokat és a 13 hetes keresleti progressziót."""

    def __init__(self):
        self.auto_sell = {
            item_id: False for item_id in get_restaurant_sellable_item_ids()
        }
        self.level = RESTAURANT_MIN_LEVEL
        self.period_requested_units = 0
        self.period_fulfilled_units = 0
        self.current_period_id = None
        self.last_evaluated_period = None
        self.last_processed_week = None

    @property
    def weekly_quantity_per_product(self):
        return self.level

    @property
    def period_ratio(self):
        if self.period_requested_units <= 0:
            return 0.0
        return self.period_fulfilled_units / self.period_requested_units

    def is_enabled(self, item_id):
        return bool(self.auto_sell.get(item_id, False))

    def toggle(self, item_id):
        if item_id not in get_restaurant_sellable_item_ids():
            return False
        self.auto_sell[item_id] = not self.is_enabled(item_id)
        return True

    def _sell_product(self, buildings, economy, item_id, requested_quantity):
        if not self.is_enabled(item_id):
            return 0
        quantity = min(
            requested_quantity,
            get_marketable_item_amount(buildings, item_id),
        )
        if quantity <= 0:
            return 0
        item = get_inventory_item_data(item_id)
        unit_price = get_restaurant_unit_price(item_id)
        if unit_price is None or not remove_marketable_item(
                buildings, item_id, quantity):
            return 0
        income = unit_price * quantity
        shipping = AUTO_PURCHASE_DELIVERY_COST_PER_UNIT * quantity
        economy.credit_income(
            item["income_category"], income, item_id,
            f"Éttermi értékesítés: {quantity} db {item['name']}",
        )
        economy.charge(shipping)
        economy.record_expense(
            EXPENSE_SHIPPING, shipping, item_id,
            f"Éttermi kiszállítás: {quantity} db {item['name']}",
        )
        log(
            f"{quantity} db {item['name']} értékesítve: "
            f"{format_money(income)}. Szállítás: {format_money(shipping)}.",
            "Restaurant",
        )
        return quantity

    def _evaluate_period(self, period_id, notification_manager=None):
        if self.last_evaluated_period == period_id:
            return None
        previous_level = self.level
        ratio = self.period_ratio
        if ratio >= RESTAURANT_LEVEL_UP_RATIO:
            self.level = min(RESTAURANT_MAX_LEVEL, self.level + 1)
        elif ratio < RESTAURANT_LEVEL_DOWN_RATIO:
            self.level = max(RESTAURANT_MIN_LEVEL, self.level - 1)
        self.last_evaluated_period = period_id
        log(
            "Időszak lezárva: "
            f"{self.period_fulfilled_units}/{self.period_requested_units} db "
            f"({ratio * 100:.2f}%). Szint {previous_level} -> {self.level}.",
            "Restaurant",
        )
        if notification_manager is not None and self.level != previous_level:
            if self.level > previous_level:
                message = (
                    f"Az Étterem {self.level}. szintre fejlődött!\n"
                    f"Teljesítés: {ratio * 100:.2f}%"
                )
            else:
                message = (
                    f"Az Étterem {self.level}. szintre csökkent.\n"
                    f"Teljesítés: {ratio * 100:.2f}%"
                )
            notification_manager.enqueue(
                message, event_id=("restaurant_period", period_id),
            )
        result = {
            "period_id": period_id,
            "requested": self.period_requested_units,
            "fulfilled": self.period_fulfilled_units,
            "ratio": ratio,
            "previous_level": previous_level,
            "level": self.level,
        }
        self.period_requested_units = 0
        self.period_fulfilled_units = 0
        return result

    def run_weekly(
            self, buildings, economy, elapsed_week,
            notification_manager=None):
        """Egy játékhetet legfeljebb egyszer könyvel és szükség esetén értékel."""
        elapsed_week = max(0, int(elapsed_week))
        if self.last_processed_week == elapsed_week:
            return ()
        # A heti esemény az éppen lezárult hetet adja; a HUD ekkor már a
        # következő hetet mutatja, ezért az értékelési naptárhoz eggyel
        # korábbi belső index tartozik.
        completed_week_index = max(0, elapsed_week - 1)
        period_id, _start_week, end_week = get_restaurant_period(
            completed_week_index,
        )
        if self.current_period_id != period_id:
            self.current_period_id = period_id
            self.period_requested_units = 0
            self.period_fulfilled_units = 0

        item_ids = get_restaurant_sellable_item_ids()
        requested_per_product = self.weekly_quantity_per_product
        self.period_requested_units += requested_per_product * len(item_ids)
        sales = []
        for item_id in item_ids:
            fulfilled = self._sell_product(
                buildings, economy, item_id, requested_per_product,
            )
            self.period_fulfilled_units += fulfilled
            if fulfilled:
                sales.append(item_id)
        self.last_processed_week = elapsed_week

        _year, week = get_year_and_week(completed_week_index)
        if week == end_week:
            self._evaluate_period(period_id, notification_manager)
        return tuple(sales)

    def to_save_record(self):
        return {
            "auto_sell": {
                item_id: self.is_enabled(item_id)
                for item_id in get_restaurant_sellable_item_ids()
            },
            "level": self.level,
            "period_requested_units": self.period_requested_units,
            "period_fulfilled_units": self.period_fulfilled_units,
            "current_period_id": self.current_period_id,
            "last_evaluated_period": self.last_evaluated_period,
            "last_processed_week": self.last_processed_week,
        }

    def load_save_record(self, record):
        """A korábbi, lapos checkbox-rekordot is kompatibilisen betölti."""
        record = record if isinstance(record, dict) else {}
        auto_sell = record.get("auto_sell")
        if not isinstance(auto_sell, dict):
            auto_sell = record
        self.auto_sell = {
            item_id: auto_sell.get(item_id) is True
            for item_id in get_restaurant_sellable_item_ids()
        }
        level = record.get("level", RESTAURANT_MIN_LEVEL)
        self.level = (
            max(RESTAURANT_MIN_LEVEL, min(RESTAURANT_MAX_LEVEL, level))
            if isinstance(level, int) and not isinstance(level, bool)
            else RESTAURANT_MIN_LEVEL
        )
        self.period_requested_units = _safe_counter(
            record.get("period_requested_units"),
        )
        self.period_fulfilled_units = min(
            self.period_requested_units,
            _safe_counter(record.get("period_fulfilled_units")),
        )
        self.current_period_id = _safe_optional_counter(
            record.get("current_period_id"),
        )
        self.last_evaluated_period = _safe_optional_counter(
            record.get("last_evaluated_period"),
        )
        self.last_processed_week = _safe_optional_counter(
            record.get("last_processed_week"),
        )


def _safe_counter(value):
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else 0
    )


def _safe_optional_counter(value):
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else None
    )
