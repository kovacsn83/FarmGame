from buildings import (
    BUILDING_TYPES, get_building_maintenance_base, get_building_asset_value, get_total_crop_amount,
    get_marketable_item_amount, get_total_inventory, get_warehouses,
    remove_marketable_item, store_crop,
    GARAGE_UPGRADE_LEVELS, WAREHOUSE_UPGRADE_LEVELS,
)
from constants import (
    ROAD, ROAD_BUILD_COST, STARTING_MONEY, TRACTOR_PURCHASE_PRICE,
)
from crops import CROPS
from game_rules import FIELD_TYPES, UPGRADES
from game_logger import log
from inventory import get_inventory_item_data, get_inventory_item_name
from maintenance import calculate_weekly_maintenance
from market_procurement import (
    get_automatic_purchase_quote, purchase_automatically,
)
from money_format import format_money
from financial_history import (
    EXPENSE, INCOME, EXPENSE_CONSTRUCTION, EXPENSE_MAINTENANCE,
    EXPENSE_PLANTING, EXPENSE_SHIPPING, EXPENSE_UPGRADE,
    FINANCIAL_HISTORY_RETENTION_WEEKS,
    FINANCIAL_SUMMARY_WEEKS, is_valid_transaction,
)


class Economy:
    """A játékos pénzét és a gazdasági tranzakciókat kezeli."""

    def __init__(self, starting_money=STARTING_MONEY):
        self.money = float(starting_money)
        self.financial_history = []
        self._next_transaction_id = 1
        self._game_time = None
        self._seed_purchase_transactions = {}
        self._storage_capacity_changed_handler = None

    def bind_game_time(self, game_time):
        self._game_time = game_time

    def bind_storage_capacity_changed(self, handler):
        """Eseményalapú újrapróbálást köt a készletcsökkenésekhez."""
        self._storage_capacity_changed_handler = handler

    def notify_storage_capacity_changed(self):
        if self._storage_capacity_changed_handler is not None:
            self._storage_capacity_changed_handler()

    def get_farm_value_breakdown(self, game_state=None):
        """Az aktuális farm állományértékét központi katalógusokból számolja.

        A Farmház szintfejlesztéseit az aktuális szint értékalapja már
        tartalmazza, ezért azok nem szerepelnek még egyszer a fejlesztések
        között. Ismeretlen piaci árú készletelemhez nem talál ki értéket.
        """
        breakdown = {
            "built_objects": 0.0,
            "upgrades": 0.0,
            "animals": 0.0,
            "fruit_trees": 0.0,
            "warehouse_inventory": 0.0,
            "processing_inventory": 0.0,
            "vehicles": 0.0,
            "money": float(self.money),
            "loan_balance": 0.0,
        }
        if game_state is None:
            breakdown["total"] = breakdown["money"]
            return breakdown

        from animals import ANIMAL_TYPES
        from orchards import TREE_TYPES
        from vehicle_types import (
            VEHICLE_TYPE_DEFINITIONS, normalize_vehicle_type,
        )

        road_count = sum(
            tile == ROAD for row in game_state.world for tile in row
        )
        built_objects = road_count * ROAD_BUILD_COST
        for building in game_state.buildings:
            definition = BUILDING_TYPES.get(building.get("type"))
            if definition is None:
                continue
            built_objects += get_building_asset_value(building)
        for field in game_state.fields:
            definition = FIELD_TYPES.get(
                field.get("field_type", "field_4x4")
            )
            if definition is not None:
                built_objects += definition["build_cost"]
        breakdown["built_objects"] = built_objects

        breakdown["upgrades"] = sum(
            UPGRADES[upgrade_id]["price"]
            for upgrade_id in game_state.purchased_upgrades
            if (
                upgrade_id in UPGRADES
                and UPGRADES[upgrade_id].get("target_building_type")
                != "farmhouse"
            )
        )
        breakdown["animals"] = sum(
            ANIMAL_TYPES.get(animal.get("type"), {}).get(
                "purchase_price", 0.0,
            )
            for animal in game_state.animals
        )
        breakdown["fruit_trees"] = sum(
            TREE_TYPES.get(tree.get("type"), {}).get("planting_cost", 0.0)
            for building in game_state.buildings
            if building.get("type") == "orchard"
            for tree in building.get("trees", ())
        )

        def inventory_value(inventory):
            value = 0.0
            for item_id, amount in inventory.items():
                definition = get_inventory_item_data(item_id)
                if definition is None or "price" not in definition:
                    continue
                try:
                    safe_amount = max(0, int(amount))
                    price = max(0.0, float(definition["price"]))
                except (TypeError, ValueError, OverflowError):
                    continue
                value += safe_amount * price
            return value

        breakdown["warehouse_inventory"] = inventory_value(
            get_total_inventory(game_state.buildings)
        )
        breakdown["processing_inventory"] = sum(
            inventory_value(building.get("processing_inventory", {}))
            for building in game_state.buildings
            if building.get("type") == "processing_plant"
        )

        vehicle_manager = game_state.vehicles or game_state.tractor
        if vehicle_manager is not None:
            assets = getattr(vehicle_manager, "managed_assets", ())
            breakdown["vehicles"] = sum(
                VEHICLE_TYPE_DEFINITIONS.get(
                    normalize_vehicle_type(asset.vehicle_type), {}
                ).get("purchase_price", 0.0)
                for asset in assets
            )

        bank_system = game_state.bank_system
        loan = getattr(bank_system, "loan", None)
        breakdown["loan_balance"] = max(
            0, int(getattr(loan, "remaining_balance_cents", 0))
        ) / 100
        breakdown["total"] = (
            sum(
                breakdown[key] for key in (
                    "built_objects", "upgrades", "animals", "fruit_trees",
                    "warehouse_inventory", "processing_inventory",
                    "vehicles", "money",
                )
            )
            - breakdown["loan_balance"]
        )
        return breakdown

    def calculate_net_farm_value(self, game_state=None):
        """Visszaadja a farm mindig újraszámolt aktuális nettó értékét."""
        return self.get_farm_value_breakdown(game_state)["total"]

    def _current_week(self):
        return max(0, int(getattr(self._game_time, "elapsed_weeks", 0)))

    def record_transaction(
            self, transaction_type, category, amount,
            subcategory=None, description=None, week=None):
        amount = float(amount)
        if amount <= 0:
            return None
        record = {
            "id": self._next_transaction_id,
            "week": self._current_week() if week is None else max(0, int(week)),
            "type": transaction_type,
            "category": category,
            "subcategory": subcategory,
            "amount": amount,
            "description": description,
        }
        self._next_transaction_id += 1
        self.financial_history.append(record)
        self._prune_financial_history(record["week"])
        return record["id"]

    def record_income(self, category, amount, subcategory=None, description=None):
        return self.record_transaction(
            INCOME, category, amount, subcategory, description,
        )

    def record_expense(self, category, amount, subcategory=None, description=None):
        return self.record_transaction(
            EXPENSE, category, amount, subcategory, description,
        )

    def remove_transactions(self, transaction_ids):
        transaction_ids = {item for item in transaction_ids if item is not None}
        self.financial_history[:] = [
            item for item in self.financial_history
            if item.get("id") not in transaction_ids
        ]

    def _remove_latest_seed_purchase(self, crop):
        """Betöltés után is visszavonja egy megszakított vetés két tételét."""
        planting_record = None
        for record in reversed(self.financial_history):
            if (record.get("subcategory") == crop
                    and record.get("category") == EXPENSE_PLANTING):
                planting_record = record
                break
        if planting_record is None:
            return
        removable = [planting_record.get("id")]
        shipping_id = planting_record.get("id", 0) + 1
        if any(
                record.get("id") == shipping_id
                and record.get("category") == EXPENSE_SHIPPING
                and record.get("subcategory") == crop
                for record in self.financial_history):
            removable.append(shipping_id)
        self.remove_transactions(removable)

    def _prune_financial_history(self, current_week=None):
        current_week = self._current_week() if current_week is None else current_week
        oldest_week = max(0, current_week - FINANCIAL_HISTORY_RETENTION_WEEKS + 1)
        self.financial_history[:] = [
            item for item in self.financial_history
            if item["week"] >= oldest_week
        ]

    def get_financial_summary(self, weeks=FINANCIAL_SUMMARY_WEEKS):
        current_week = self._current_week()
        oldest_week = max(0, current_week - max(1, int(weeks)) + 1)
        summary = {INCOME: {}, EXPENSE: {}, "income_total": 0.0,
                   "expense_total": 0.0, "net": 0.0,
                   "start_week": oldest_week, "end_week": current_week}
        for item in self.financial_history:
            if not oldest_week <= item["week"] <= current_week:
                continue
            bucket = summary[item["type"]]
            category = bucket.setdefault(item["category"], {"total": 0.0, "items": {}})
            category["total"] += item["amount"]
            if item.get("subcategory"):
                category["items"][item["subcategory"]] = (
                    category["items"].get(item["subcategory"], 0.0)
                    + item["amount"]
                )
            summary[f"{item['type']}_total"] += item["amount"]
        summary["net"] = summary["income_total"] - summary["expense_total"]
        return summary

    def financial_history_save_record(self):
        self._prune_financial_history()
        return [dict(item) for item in self.financial_history]

    def load_financial_history(self, records):
        self.financial_history = [
            dict(item) for item in (records or ()) if is_valid_transaction(item)
        ]
        self._next_transaction_id = max(
            ((item.get("id") or 0) for item in self.financial_history), default=0,
        ) + 1
        self._prune_financial_history()

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

    def credit_income(
            self, category, amount, subcategory=None, description=None):
        """Egy lépésben jóváír és rögzít egy bevételi tranzakciót."""
        amount = float(amount)
        if amount <= 0:
            return False
        self.earn(amount)
        self.record_income(category, amount, subcategory, description)
        return True

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

        receipt = purchase_automatically(
            self, crop_name, crop_data["price"], 1,
            EXPENSE_PLANTING, crop,
        )
        if receipt is not None:
            self._seed_purchase_transactions.setdefault(crop, []).append(
                getattr(receipt, "transaction_ids", ()),
            )
            return {"source": "money", "amount": receipt.total_cost}

        log(
            f"Nincs {crop_name.lower()} a raktárban, és nincs elegendő pénz "
            "vetőmag vásárlására.", "Inventory",
        )
        return None

    def refund_seed(self, payment, crop):
        """A feladatfelvételkor készült bizonylat alapján visszatérít."""
        if payment["source"] == "money":
            self.earn(payment["amount"])
            pending = self._seed_purchase_transactions.get(crop, [])
            if pending:
                self.remove_transactions(pending.pop(0))
            else:
                self._remove_latest_seed_purchase(crop)
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
            or self.can_afford(
                get_automatic_purchase_quote(crop_data["price"], 1).total_cost
            )
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
            required_level = upgrade.get("required_level")
            if (
                required_level is not None
                and farmhouse.get("farmhouse_level", 1) < required_level
            ):
                log("A fejlesztés előfeltétele még nem teljesült.", "Economy")
                return False
            if not self.spend(upgrade["price"]):
                log("Nincs elegendő pénz.", "Economy")
                return False
            # A pénzlevonás után egyetlen objektummező-váltás teszi atomivá.
            farmhouse["farmhouse_level"] = target_level
            self.record_expense(EXPENSE_UPGRADE, upgrade["price"], upgrade_id)
            log(f"Fejlesztés megvásárolva: {upgrade['name']}", "Economy")
            return True
        required = upgrade.get("requires")
        required_level = upgrade.get("required_farmhouse_level")
        if required_level is not None:
            farmhouse = next(
                building for building in game_state.buildings
                if building["type"] == "farmhouse"
            )
            if farmhouse.get("farmhouse_level", 1) < required_level:
                log("A szükséges Farmház-szint még nincs kifejlesztve.", "Economy")
                return False
        if required and required not in game_state.purchased_upgrades:
            log("A fejlesztés előfeltétele még nem teljesült.", "Economy")
            return False
        if not self.spend(upgrade["price"]):
            log("Nincs elegendő pénz.", "Economy")
            return False
        game_state.purchased_upgrades.add(upgrade_id)
        if upgrade_id == "processing_plant_level_2":
            game_state.synchronize_processing_upgrades()
        if upgrade_id in GARAGE_UPGRADE_LEVELS:
            game_state.synchronize_garage_upgrades()
            if game_state.vehicles is not None:
                game_state.vehicles.compact_garage_assignments(game_state.world, game_state.buildings)
        if upgrade_id in WAREHOUSE_UPGRADE_LEVELS:
            game_state.synchronize_warehouse_upgrades()
        self.record_expense(EXPENSE_UPGRADE, upgrade["price"], upgrade_id)
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
        self.record_expense(EXPENSE_MAINTENANCE, weekly_cost)
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

    def sell_item(self, buildings, item_id, amount=None):
        """A piacképes készletelemből a kért, pozitív egész mennyiséget eladja.

        Az ``amount=None`` megtartja a korábbi, teljes készletet értékesítő
        programozott hívások működését (például az automatikus szimulációban).
        """
        item_data = get_inventory_item_data(item_id)
        if item_data is None or not item_data.get("marketable", False):
            log(f"Ez a készletelem nem értékesíthető: {item_id}", "Inventory")
            return False
        if not any(building["type"] == "market" for building in buildings):
            log("Az eladáshoz legalább egy piac szükséges.", "Economy")
            return False

        available_amount = get_marketable_item_amount(buildings, item_id)
        item_name = get_inventory_item_name(item_id)
        if available_amount <= 0:
            log(
                f"Nincs eladható {item_name.lower()} a raktárban.",
                "Inventory",
            )
            return False

        if amount is None:
            amount = available_amount
        if (
            not isinstance(amount, int)
            or isinstance(amount, bool)
            or amount <= 0
            or amount > available_amount
        ):
            log(
                f"Érvénytelen eladási mennyiség: {amount!r} "
                f"(elérhető: {available_amount} db).",
                "Market",
            )
            return False

        revenue = amount * item_data["price"]
        if not remove_marketable_item(buildings, item_id, amount):
            return False
        self.earn(revenue)
        self.record_income(
            item_data["income_category"], revenue, item_id,
            f"{amount} db {item_name}",
        )
        log(
            f"Eladva: {amount} db {item_name}. "
            f"Bevétel: {format_money(revenue)}.", "Market",
        )
        self.notify_storage_capacity_changed()
        return True

    def sell_crop(self, buildings, crop):
        """Kompatibilis belépési pont minden piacképes készletelem eladásához."""
        return self.sell_item(buildings, crop)

    def get_sale_quote(self, buildings, item_id):
        """Visszaadja a készletet, az egységárat és a teljes eladási értéket."""
        item_data = get_inventory_item_data(item_id)
        if item_data is None or not item_data.get("marketable", False):
            return None
        amount = get_marketable_item_amount(buildings, item_id)
        unit_price = item_data["price"]
        return {
            "amount": amount,
            "unit_price": unit_price,
            "total_value": amount * unit_price,
        }
