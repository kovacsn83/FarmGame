from buildings import (
    BUILDING_TYPES, get_building_maintenance_base, get_total_crop_amount,
    get_warehouses, remove_item, store_crop,
)
from constants import (
    ROAD, ROAD_BUILD_COST, STARTING_MONEY, TRACTOR_PURCHASE_PRICE,
)
from crops import CROPS
from game_rules import FIELD_TYPES, UPGRADES
from game_logger import log
from inventory import get_inventory_item_data, get_inventory_item_name
from maintenance import calculate_weekly_maintenance
from money_format import format_money


class Economy:
    """A játékos pénzét és a gazdasági tranzakciókat kezeli."""

    def __init__(self, starting_money=STARTING_MONEY):
        self.money = float(starting_money)

    def can_afford(self, amount):
        return self.money >= amount

    def spend(self, amount):
        """Csak megfelelő fedezet esetén von le pénzt."""
        if not self.can_afford(amount):
            return False
        self.money -= amount
        return True

    def earn(self, amount):
        self.money += amount

    def charge(self, amount):
        """Fedezettől független kötelező terhelést hajt végre."""
        self.money -= amount
        return amount

    def can_build(self, cost):
        """Építés előtt ellenőrzi a fedezetet, és szükség esetén jelez."""
        if self.can_afford(cost):
            return True
        log(
            "Nincs elegendő pénz az építéshez. "
            f"Szükséges összeg: {format_money(cost)}", "Economy",
        )
        return False

    def acquire_seed(self, buildings, crop):
        """Raktári terményt használ, ennek hiányában közvetlenül vetőmagot vásárol."""
        return self.reserve_seed(buildings, crop) is not None

    def reserve_seed(self, buildings, crop):
        """Levonja és bizonylattal lefoglalja egy ültetési feladat vetőmagját."""
        crop_data = CROPS.get(crop)
        if crop_data is None:
            log(f"Ismeretlen növényazonosító: {crop}", "Inventory")
            return None
        crop_name = crop_data["name"]
        if get_total_crop_amount(buildings, crop) >= 1:
            for warehouse in get_warehouses(buildings):
                if warehouse["inventory"].get(crop, 0) < 1:
                    continue
                warehouse["inventory"][crop] -= 1
                log(
                    f"1 db {crop_name.lower()} felhasználva vetőmagként.",
                    "Inventory",
                )
                return {
                    "source": "inventory",
                    "amount": 1,
                    "warehouse": warehouse,
                    "buildings": buildings,
                }

        purchase_price = crop_data["price"]
        if self.spend(purchase_price):
            log(
                f"{crop_name} vetőmag vásárolva piaci áron: "
                f"{format_money(purchase_price)}",
                "Economy",
            )
            return {"source": "money", "amount": purchase_price}

        log(
            f"Nincs {crop_name.lower()} a raktárban, és nincs elegendő pénz "
            "vetőmag vásárlására.", "Inventory",
        )
        return None

    def refund_seed(self, payment, crop):
        """A feladatfelvételkor készült bizonylat alapján visszatérít."""
        if payment["source"] == "money":
            self.earn(payment["amount"])
            return True

        buildings = payment["buildings"]
        warehouse = payment["warehouse"]
        if warehouse in buildings:
            used_capacity = sum(warehouse["inventory"].values())
            if used_capacity < warehouse["capacity"]:
                warehouse["inventory"][crop] = (
                    warehouse["inventory"].get(crop, 0) + payment["amount"]
                )
                return True
        if store_crop(buildings, crop, payment["amount"]):
            return True

        # Ha időközben minden raktár megszűnt, az erőforrás értéke sem vész el.
        self.earn(CROPS[crop]["price"] * payment["amount"])
        return True

    def can_acquire_seed(self, buildings, crop):
        """Levonás nélkül ellenőrzi, rendelkezésre áll-e a kiválasztott vetőmag."""
        crop_data = CROPS.get(crop)
        if crop_data is None:
            return False
        return (
            get_total_crop_amount(buildings, crop) >= 1
            or self.can_afford(crop_data["price"])
        )

    def report_seed_unavailable(self, buildings, crop):
        """A meglévő gazdasági szabály szerint jelzi a sikertelen vetőmagbeszerzést."""
        crop_data = CROPS.get(crop)
        if crop_data is None:
            log(f"Ismeretlen növényazonosító: {crop}", "Inventory")
            return
        if get_total_crop_amount(buildings, crop) < 1:
            log(
                f"Nincs {crop_data['name'].lower()} a raktárban, és nincs "
                "elegendő pénz vetőmag vásárlására.", "Inventory",
            )

    def purchase_upgrade(self, game_state, upgrade_id):
        """Ellenőrzi és központilag végrehajtja egy fejlesztés megvásárlását."""
        if not any(
                building["type"] == "farmhouse"
                for building in game_state.buildings):
            log("A fejlesztések vásárlásához Farmház szükséges.", "Economy")
            return False
        upgrade = UPGRADES.get(upgrade_id)
        if upgrade is None:
            log(f"Ismeretlen fejlesztés: {upgrade_id}", "Economy")
            return False
        if upgrade_id in game_state.purchased_upgrades:
            log("Ezt a fejlesztést már megvásároltad.", "Economy")
            return False
        target_level = upgrade.get("target_level")
        if target_level is not None:
            farmhouse = next(
                building for building in game_state.buildings
                if building["type"] == "farmhouse"
            )
            if farmhouse.get("farmhouse_level", 1) >= target_level:
                log("Ezt a fejlesztést már megvásároltad.", "Economy")
                return False
            if not self.spend(upgrade["price"]):
                log("Nincs elegendő pénz.", "Economy")
                return False
            # A pénzlevonás után egyetlen objektummező-váltás teszi atomivá.
            farmhouse["farmhouse_level"] = target_level
            log(f"Fejlesztés megvásárolva: {upgrade['name']}", "Economy")
            return True
        required = upgrade.get("requires")
        if required and required not in game_state.purchased_upgrades:
            log("A fejlesztés előfeltétele még nem teljesült.", "Economy")
            return False
        if not self.spend(upgrade["price"]):
            log("Nincs elegendő pénz.", "Economy")
            return False
        game_state.purchased_upgrades.add(upgrade_id)
        log(f"Fejlesztés megvásárolva: {upgrade['name']}", "Economy")
        return True

    def calculate_weekly_costs(
            self, world, buildings, fields=(), vehicle_count=0,
            vehicle_weekly_cost=None):
        road_count = sum(tile == ROAD for row in world for tile in row)
        building_cost = sum(
            calculate_weekly_maintenance(
                get_building_maintenance_base(building)
            )
            for building in buildings
        )
        field_cost = sum(
            calculate_weekly_maintenance(
                FIELD_TYPES[field.get("field_type", "field_4x4")]["build_cost"]
            )
            for field in fields
        )
        if vehicle_weekly_cost is None:
            # Régi külső hívók számára a korábbi, darabszám-alapú viselkedés marad.
            vehicle_weekly_cost = vehicle_count * calculate_weekly_maintenance(
                TRACTOR_PURCHASE_PRICE
            )
        return (
            building_cost + field_cost
            + road_count * calculate_weekly_maintenance(ROAD_BUILD_COST)
            + vehicle_weekly_cost
        )

    def apply_weekly_costs(
            self, world, buildings, fields=(), vehicle_count=0,
            vehicle_weekly_cost=None):
        """A fenntartást fedezettől függetlenül levonja, így lehet negatív az egyenleg."""
        weekly_cost = self.calculate_weekly_costs(
            world, buildings, fields, vehicle_count, vehicle_weekly_cost,
        )
        self.charge(weekly_cost)
        if weekly_cost > 0:
            log(f"Heti fenntartási költség: {format_money(weekly_cost)}", "Economy")
            log(f"Aktuális egyenleg: {format_money(self.money)}", "Economy")
        return weekly_cost

    # Régi külső hívók kompatibilitási belépési pontjai.
    def calculate_daily_costs(
            self, world, buildings, fields=(), tractor_count=0):
        return self.calculate_weekly_costs(
            world, buildings, fields, vehicle_count=tractor_count,
        )

    def apply_daily_costs(
            self, world, buildings, fields=(), tractor_count=0):
        return self.apply_weekly_costs(
            world, buildings, fields, vehicle_count=tractor_count,
        )

    def sell_item(self, buildings, item_id):
        """A kiválasztott piacképes készletelem teljes mennyiségét értékesíti."""
        item_data = get_inventory_item_data(item_id)
        if item_data is None or not item_data.get("marketable", False):
            log(f"Ez a készletelem nem értékesíthető: {item_id}", "Inventory")
            return False
        if not any(building["type"] == "market" for building in buildings):
            log("Az eladáshoz legalább egy piac szükséges.", "Economy")
            return False

        amount = get_total_crop_amount(buildings, item_id)
        item_name = get_inventory_item_name(item_id)
        if amount <= 0:
            log(
                f"Nincs eladható {item_name.lower()} a raktárban.",
                "Inventory",
            )
            return False

        revenue = amount * item_data["price"]
        if not remove_item(buildings, item_id, amount):
            return False
        self.earn(revenue)
        log(
            f"Eladás sikeres: {amount} db {item_name.lower()}, "
            f"bevétel: {format_money(revenue)}", "Economy",
        )
        return True

    def sell_crop(self, buildings, crop):
        """Kompatibilis belépési pont minden piacképes készletelem eladásához."""
        return self.sell_item(buildings, crop)

    def get_sale_quote(self, buildings, item_id):
        """Visszaadja a készletet, az egységárat és a teljes eladási értéket."""
        item_data = get_inventory_item_data(item_id)
        if item_data is None or not item_data.get("marketable", False):
            return None
        amount = get_total_crop_amount(buildings, item_id)
        unit_price = item_data["price"]
        return {
            "amount": amount,
            "unit_price": unit_price,
            "total_value": amount * unit_price,
        }
