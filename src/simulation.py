"""Fej nélküli, determinisztikus hosszú távú gazdasági szimuláció."""

from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import nullcontext, redirect_stdout
from dataclasses import asdict, dataclass
import io
import json
import math
from pathlib import Path
import random
import time

from animal_troughs import get_group_supply
from animal_automation import (
    AUTOMATED_FEEDING_UPGRADE, AUTOMATED_WATERING_UPGRADE,
    run_weekly_animal_supply_automation,
)
from bank import BankSystem, LOAN_INTEREST_PERCENT
from animals import (
    get_animal_placement_error, get_animals_in_pen_group, get_pen_group_tiles,
    purchase_and_place_animal, run_weekly_animal_cycle,
)
from buildings import (
    BUILDING_TYPES, can_place_building, get_animal_pen_groups,
    get_building_maintenance_base,
    get_free_capacity, get_total_capacity, get_total_inventory,
    place_building, remove_building,
)
from constants import BUILDING, FIELD, GRASS, ROAD, ROAD_BUILD_COST
from crops import (
    CROPS, can_harvest_crop_in_week, can_late_harvest_crop_in_week,
    can_plant_crop_in_week,
)
from economy import Economy
from financial_history import EXPENSE_CONSTRUCTION
from fields import (
    can_place_field, grow_crops, place_field, remove_field, remove_field_data,
)
from game_rules import FIELD_TYPES, UPGRADES
from game_state import GameState
from inventory import PRODUCTS, get_marketable_item_ids
from market_procurement import get_automatic_purchase_unit_cost
from maintenance import calculate_weekly_maintenance
from money_format import format_money
from simulation_report import write_simulation_reports
from time_system import GameTime, TIME_SLOW, WEEKS_PER_YEAR
from tractor import TRACTOR_IDLE
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType
from world import create_world


DEFAULT_SIMULATION_SEED = 12345
DEFAULT_SIMULATION_YEARS = 5
VIRTUAL_TICK_MS = 500
MAX_TASK_TICKS = 20_000

INCOME_CATEGORIES = (
    "crop_sales", "milk_sales", "pork_sales",
    "other_animal_sales", "other_income",
)
EXPENSE_CATEGORIES = (
    "building_maintenance", "field_maintenance", "road_maintenance",
    "vehicle_maintenance", "animal_purchase", "vehicle_purchase",
    "building_construction", "field_construction", "road_construction",
    "feed_purchase", "seed_purchase", "bank_repayment", "other_expense",
)


class SimulationInvariantError(AssertionError):
    """A reprodukálható hét és állapot adataival jelzi a sérült szabályt."""

    def __init__(self, message, diagnostic):
        super().__init__(message)
        self.diagnostic = diagnostic


@dataclass
class YearSnapshot:
    year: int
    money: float
    income: float
    expenses: float
    net_profit: float
    income_breakdown: dict
    expense_breakdown: dict
    investments: dict
    maintenance_expense_ratio: float
    feed_expense_ratio: float
    investment_expense_ratio: float
    largest_income_source: dict
    largest_expense_category: dict
    buildings: dict
    vehicles: dict
    animals: dict
    fields: dict
    inventory: dict
    warehouse_capacity: int
    warehouse_used: int
    warehouse_utilization: float
    sold_products: dict
    purchased_feed: dict
    purchased_feed_cost: float
    completed_tasks: int
    failed_tasks: int
    loans_taken: int
    loan_principal_received: float
    bank_repayments: float
    bank_interest_paid: float
    outstanding_loan_balance: float
    loan_remaining_weeks: int


class SimulationBot:
    """Dokumentált prioritásokkal vezérelt, a publikus játékműveleteket használó bot."""

    CROP_PLAN = (
        "alfalfa", "alfalfa", "alfalfa", "corn",
        "corn", "tomato", "tomato", "wheat",
    )

    def __init__(self, seed=DEFAULT_SIMULATION_SEED, accept_first_bank_offer=True):
        self.seed = int(seed)
        random.seed(self.seed)
        self.world = create_world()
        self.fields = []
        self.buildings = []
        self.animals = []
        self.economy = Economy()
        self.bank_system = BankSystem(self.economy)
        self.game_time = GameTime(current_time_speed=TIME_SLOW, start_ticks=0)
        self.vehicles = VehicleManager()
        self.state = GameState(
            self.world, self.fields, self.buildings, self.economy,
            self.game_time, tractor=self.vehicles, vehicles=self.vehicles,
            animals=self.animals, bank_system=self.bank_system,
        )
        self.virtual_ticks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.completed_tasks_by_year = defaultdict(int)
        self.failed_tasks_by_year = defaultdict(int)
        self.income = defaultdict(float)
        self.expenses = defaultdict(float)
        self.income_breakdown = defaultdict(lambda: defaultdict(float))
        self.expense_breakdown = defaultdict(lambda: defaultdict(float))
        self.investments = defaultdict(lambda: defaultdict(int))
        self.sold = defaultdict(lambda: defaultdict(int))
        self.feed_bought = defaultdict(lambda: defaultdict(int))
        self.feed_cost = defaultdict(float)
        self.decisions = []
        self.snapshots = []
        self.accept_first_bank_offer = bool(accept_first_bank_offer)
        self.loan_count_by_year = defaultdict(int)
        self.loan_principal_by_year = defaultdict(float)
        self.bank_repayments_by_year = defaultdict(float)
        self.bank_interest_by_year = defaultdict(float)

    @property
    def year(self):
        return self.game_time.year

    @property
    def week(self):
        return self.game_time.week

    def _record_money_change(self, year, before, category):
        change = self.economy.money - before
        if change > 0:
            self.income[year] += change
            self.income_breakdown[year][category] += change
        elif change < 0:
            self.expenses[year] -= change
            self.expense_breakdown[year][category] -= change
        return change

    def _record_expense(self, year, category, amount):
        """Pénzmozgás nélküli részletezéshez rögzít egy már levont kiadást."""
        if amount > 0:
            self.expense_breakdown[year][category] += amount

    @staticmethod
    def _sale_income_category(item_id):
        if item_id in CROPS:
            return "crop_sales"
        if item_id == "apple":
            return "fruit_sales"
        if item_id == "milk":
            return "milk_sales"
        if item_id == "pork":
            return "pork_sales"
        if item_id in PRODUCTS:
            return "other_animal_sales"
        return "other_income"

    def build_road(self, row, col):
        if self.world[row][col] != GRASS or not self.economy.can_build(ROAD_BUILD_COST):
            return False
        before = self.economy.money
        if not self.economy.spend(ROAD_BUILD_COST):
            return False
        self.economy.record_expense(
            EXPENSE_CONSTRUCTION, ROAD_BUILD_COST, "road", "1 út csempe",
        )
        self.world[row][col] = ROAD
        self._record_money_change(self.year, before, "road_construction")
        self.investments[self.year]["road"] += 1
        return True

    def build_building(self, building_type, row, col):
        definition = BUILDING_TYPES[building_type]
        if not can_place_building(
                self.world, self.buildings, row, col, building_type,
                animals=self.animals):
            return None
        before = self.economy.money
        if not self.economy.spend(definition["build_cost"]):
            return None
        self.economy.record_expense(
            EXPENSE_CONSTRUCTION, definition["build_cost"], building_type,
            definition["name"],
        )
        building = place_building(
            self.world, self.buildings, row, col, building_type,
        )
        self._record_money_change(self.year, before, "building_construction")
        self.investments[self.year][building_type] += 1
        if building_type == "farmhouse":
            self.vehicles.on_farmhouse_built(
                self.world, self.buildings, building,
            )
        elif building_type == "garage":
            self.vehicles.on_garage_built(self.world, self.buildings, building)
        return building

    def build_field(self, row, col, field_type="field_4x4"):
        definition = FIELD_TYPES[field_type]
        if not can_place_field(
                self.world, row, col,
                definition["width"], definition["height"]):
            return None
        before = self.economy.money
        if not self.economy.spend(definition["build_cost"]):
            return None
        self.economy.record_expense(
            EXPENSE_CONSTRUCTION, definition["build_cost"], field_type,
            definition["name"],
        )
        place_field(self.world, self.fields, row, col, field_type)
        self._record_money_change(self.year, before, "field_construction")
        self.investments[self.year][field_type] += 1
        return self.fields[-1]

    def demolish_field(self, field):
        if self.vehicles.demolition_block_reason(
                field["row"], field["col"], field=field):
            return False
        remove_field(
            self.world, field["row"], field["col"],
            field["width"], field["height"],
        )
        remove_field_data(self.fields, field["row"], field["col"])
        return True

    def demolish_building(self, building):
        """A normál bontási tiltásokat alkalmazva távolít el egy épületet."""
        if self.vehicles.demolition_block_reason(
                building["row"], building["col"], building=building):
            return False
        return remove_building(self.world, self.buildings, building)

    def purchase_vehicle(self, vehicle_type):
        garage = next(
            (item for item in self.buildings if item["type"] == "garage"), None,
        )
        if garage is None:
            return False
        before = self.economy.money
        result = self.vehicles.purchase_vehicle(
            self.world, self.buildings, self.economy, garage, vehicle_type,
        )
        if result:
            self._record_money_change(self.year, before, "vehicle_purchase")
            normalized_type = getattr(vehicle_type, "value", vehicle_type)
            self.investments[self.year][f"vehicle:{normalized_type}"] += 1
        return result

    def purchase_animal(self, animal_type, pen):
        tile = next(
            (
                tile for tile in sorted(get_pen_group_tiles([pen]))
                if get_animal_placement_error(
                    self.animals, self.buildings,
                    tile[0], tile[1], animal_type,
                ) is None
            ),
            None,
        )
        if tile is None:
            return False
        before = self.economy.money
        result = purchase_and_place_animal(
            self.animals, self.buildings, self.economy,
            tile[0], tile[1], animal_type,
        )
        if result:
            self._record_money_change(self.year, before, "animal_purchase")
            self.investments[self.year][f"animal:{animal_type}"] += 1
        return result

    def purchase_upgrade(self, upgrade_id):
        """A bot is a játék valódi fejlesztésvásárlási útvonalát használja."""
        before = self.economy.money
        if not self.economy.purchase_upgrade(self.state, upgrade_id):
            return False
        self._record_money_change(self.year, before, "other_expense")
        self.investments[self.year][f"upgrade:{upgrade_id}"] += 1
        return True

    def _purchase_animal_automation(self):
        """Megfelelő tartalék esetén fokozatosan automatizálja az ellátást."""
        reserve = 5000.00
        for upgrade_id in (
                AUTOMATED_FEEDING_UPGRADE, AUTOMATED_WATERING_UPGRADE):
            if upgrade_id in self.state.purchased_upgrades:
                continue
            if self.economy.money >= UPGRADES[upgrade_id]["price"] + reserve:
                self.purchase_upgrade(upgrade_id)

    def _has_pending_vehicle_work(self):
        return bool(self.vehicles.task_queue) or any(
            vehicle.state != TRACTOR_IDLE or vehicle.current_task is not None
            for vehicle in self.vehicles.vehicles
        )

    def drain_vehicle_tasks(self):
        """Gyorsított tickekkel, de a valódi Dispatcher/állapotgépek útján futtat."""
        if not self._has_pending_vehicle_work():
            return
        initial_tasks = len(self.vehicles.task_queue) + sum(
            vehicle.current_task is not None for vehicle in self.vehicles.vehicles
        )
        for _ in range(MAX_TASK_TICKS):
            self.virtual_ticks += VIRTUAL_TICK_MS
            self.vehicles.update(
                self.world, self.buildings, self.economy, self.game_time,
                current_ticks=self.virtual_ticks,
            )
            if not self._has_pending_vehicle_work():
                self.completed_tasks += initial_tasks
                self.completed_tasks_by_year[self.year] += initial_tasks
                return
        self.failed_tasks += max(1, initial_tasks)
        self.failed_tasks_by_year[self.year] += max(1, initial_tasks)
        self._fail("Beragadt járműfeladat vagy Dispatcher-várólista.")

    def bootstrap(self):
        """Új játék szabályos, takarékos és minden alrendszert elérő alapfarmja."""
        for col in range(1, 77):
            if not self.build_road(20, col):
                self._fail("Az induló úthálózat nem építhető meg.")

        layout = (
            ("farmhouse", 12, 2), ("warehouse", 16, 11),
            ("market", 17, 17), ("garage", 16, 22),
            ("pond", 14, 29), ("animal_pen", 21, 38),
            ("animal_pen", 21, 43), ("animal_pen", 21, 72),
        )
        created = {}
        for kind, row, col in layout:
            created.setdefault(kind, []).append(
                self.build_building(kind, row, col),
            )
        if any(item is None for values in created.values() for item in values):
            self._fail("Az induló épületelrendezés valamelyik eleme érvénytelen.")

        field_cols = (2, 7, 12, 17, 22, 49, 54, 59)
        for col in field_cols:
            if self.build_field(21, col) is None:
                self._fail("Az induló Veteményes nem építhető meg.")

        for vehicle_type in (
                VehicleType.COMBINE, VehicleType.WATER_TANK, VehicleType.TRAILER):
            if not self.purchase_vehicle(vehicle_type):
                self._fail(f"Nem vásárolható meg az induló {vehicle_type.value}.")

        pens = created["animal_pen"]
        if not self.purchase_animal("cattle", pens[0]):
            self._fail("Nem vásárolható meg az induló szarvasmarha.")
        if not self.purchase_animal("pig", pens[1]):
            self._fail("Nem vásárolható meg az induló sertés.")
        if not self.purchase_animal("chicken", pens[2]):
            self._fail("Nem vásárolható meg az induló csirke.")
        self.decisions.append(
            "1. év: minimális teljes termelési lánc épült (8 Veteményes, "
            "külön fajonkénti Karám, egyetlen négyhelyes Garázs)."
        )
        self.drain_vehicle_tasks()

    def _supply_animals(self):
        """Első prioritás: a következő heti fogyasztás előtt tölti a vályúkat."""
        for group in get_animal_pen_groups(self.buildings):
            if not get_animals_in_pen_group(self.animals, group):
                continue
            food, water = get_group_supply(group)
            for trough_type, stock in (("food", food), ("water", water)):
                upgrade_id = (
                    AUTOMATED_FEEDING_UPGRADE
                    if trough_type == "food"
                    else AUTOMATED_WATERING_UPGRADE
                )
                if upgrade_id in self.state.purchased_upgrades:
                    continue
                if stock > 0:
                    continue
                before_money = self.economy.money
                trough = {"type": trough_type, "group": group}
                if self.vehicles.start_trough_supply(
                        self.world, self.buildings, self.economy,
                        self.animals, trough, current_ticks=self.virtual_ticks):
                    self.drain_vehicle_tasks()
                    if trough_type == "food":
                        animal_type = get_animals_in_pen_group(
                            self.animals, group,
                        )[0]["type"]
                        feed = "alfalfa" if animal_type == "cattle" else "corn"
                        cost = max(0.0, before_money - self.economy.money)
                        bought = round(
                            cost / get_automatic_purchase_unit_cost(
                                CROPS[feed]["price"],
                            )
                        )
                        self.feed_bought[self.year][feed] += bought
                        self.feed_cost[self.year] += cost
                        self._record_money_change(
                            self.year, before_money, "feed_purchase",
                        )

    def _plant_and_tend(self):
        for field, crop in zip(self.fields, self.CROP_PLAN):
            if (field.get("crop") is None
                    and can_plant_crop_in_week(crop, self.week)):
                before = self.economy.money
                if self.vehicles.start_planting(
                        self.world, self.buildings, self.economy, field, crop,
                        current_ticks=self.virtual_ticks, current_week=self.week):
                    self._record_money_change(self.year, before, "seed_purchase")
                    self.drain_vehicle_tasks()
            if field.get("crop") is not None and field.get("growth", 0) < 100:
                if not field.get("watered", False):
                    if self.vehicles.start_watering(
                            self.world, self.buildings, self.economy, field,
                            current_ticks=self.virtual_ticks):
                        self.drain_vehicle_tasks()
                if (not field.get("fertilized", False)
                        and get_total_inventory(self.buildings).get("manure", 0) > 0):
                    if self.vehicles.start_fertilizing(
                            self.world, self.buildings, self.economy, field,
                            current_ticks=self.virtual_ticks):
                        self.drain_vehicle_tasks()

    def _harvest(self):
        for field in self.fields:
            crop = field.get("crop")
            if (
                crop and field.get("growth", 0) >= 100
                and (
                    can_harvest_crop_in_week(crop, self.week)
                    or can_late_harvest_crop_in_week(crop, self.week)
                )
            ):
                if self.vehicles.start_harvesting(
                        self.world, self.buildings, self.economy, field,
                        current_ticks=self.virtual_ticks,
                        current_week=self.week,
                        current_elapsed_week=self.game_time.elapsed_weeks):
                    self.drain_vehicle_tasks()

    def _sell_market_surplus(self):
        """A takarmányt megtartja; eladással előbb kapacitást, majd pénzt biztosít."""
        inventory = get_total_inventory(self.buildings)
        utilization = (
            sum(inventory.values()) / get_total_capacity(self.buildings)
            if get_total_capacity(self.buildings) else 0
        )
        sale_week = self.week in (13, 26, 39, 52)
        if not sale_week and utilization < 0.80:
            return
        for item_id in get_marketable_item_ids():
            amount = get_total_inventory(self.buildings).get(item_id, 0)
            if amount <= 0:
                continue
            before = self.economy.money
            if self.economy.sell_item(self.buildings, item_id):
                self.sold[self.year][item_id] += amount
                self._record_money_change(
                    self.year, before, self._sale_income_category(item_id),
                )

    def run_week(self):
        """A prioritási sorrend: ellátás, aratás/vetés, gondozás, eladás, heti ciklus."""
        self._purchase_animal_automation()
        self._supply_animals()
        self._harvest()
        self._plant_and_tend()
        self._sell_market_surplus()

        year = self.year
        road_count = sum(tile == ROAD for row in self.world for tile in row)
        maintenance_breakdown = {
            "building_maintenance": sum(
                calculate_weekly_maintenance(
                    get_building_maintenance_base(item)
                )
                for item in self.buildings
            ),
            "field_maintenance": sum(
                calculate_weekly_maintenance(
                    FIELD_TYPES[item.get("field_type", "field_4x4")]["build_cost"]
                )
                for item in self.fields
            ),
            "road_maintenance": (
                road_count * calculate_weekly_maintenance(ROAD_BUILD_COST)
            ),
            "vehicle_maintenance": self.vehicles.weekly_cost,
        }
        before = self.economy.money
        self.economy.apply_weekly_costs(
            self.world, self.buildings, self.fields,
            vehicle_weekly_cost=self.vehicles.weekly_cost,
        )
        maintenance_change = self._record_money_change(
            year, before, "maintenance_total",
        )
        # Az összesítő technikai kategória helyett a részletes tételek maradnak.
        self.expense_breakdown[year].pop("maintenance_total", None)
        for category, amount in maintenance_breakdown.items():
            self._record_expense(year, category, amount)
        maintenance_total = sum(maintenance_breakdown.values())
        if not math.isclose(-maintenance_change, maintenance_total, abs_tol=0.01):
            self._fail("A fenntartási költség részletezése eltér a tényleges levonástól.")
        before = self.economy.money
        repayment = self.bank_system.apply_weekly_repayment()
        if repayment:
            self._record_money_change(year, before, "bank_repayment")
            self.bank_repayments_by_year[year] += repayment
            self.bank_interest_by_year[year] += (
                repayment * LOAN_INTEREST_PERCENT
                / (100 + LOAN_INTEREST_PERCENT)
            )
        grow_crops(self.fields, self.game_time.elapsed_weeks + 1)
        run_weekly_animal_cycle(self.animals, self.buildings, self.economy)
        if run_weekly_animal_supply_automation(
                self.world, self.buildings, self.economy, self.animals,
                self.vehicles, self.state.purchased_upgrades,
                current_ticks=self.virtual_ticks):
            self.drain_vehicle_tasks()
        self.game_time.elapsed_weeks += 1
        if self.bank_system.observe_balance():
            if self.accept_first_bank_offer and self.bank_system.loan.loans_taken == 0:
                if self.bank_system.accept_offer():
                    self.loan_count_by_year[year] += 1
                    principal = self.bank_system.loan.principal_cents / 100
                    self.loan_principal_by_year[year] += principal
                    self.decisions.append(
                        f"{year}. év: az első negatív egyenlegnél a bot "
                        f"elfogadta a {format_money(principal)} bankhitelt."
                    )
            else:
                self.bank_system.decline_offer()
        self.assert_invariants()

    def _counts(self):
        return (
            Counter(item["type"] for item in self.buildings),
            Counter(asset.vehicle_type.value for asset in self.vehicles.managed_assets),
            Counter(item["type"] for item in self.animals),
            Counter(item.get("field_type", "field_4x4") for item in self.fields),
        )

    def take_snapshot(self, year):
        buildings, vehicles, animals, fields = self._counts()
        inventory = get_total_inventory(self.buildings)
        capacity = get_total_capacity(self.buildings)
        used = sum(inventory.values())
        income_breakdown = {
            key: round(self.income_breakdown[year].get(key, 0.0), 2)
            for key in INCOME_CATEGORIES
        }
        expense_breakdown = {
            key: round(self.expense_breakdown[year].get(key, 0.0), 2)
            for key in EXPENSE_CATEGORIES
        }
        expenses = self.expenses[year]
        maintenance_expense = sum(
            value for key, value in self.expense_breakdown[year].items()
            if key.endswith("_maintenance")
        )
        investment_expense = sum(
            value for key, value in self.expense_breakdown[year].items()
            if key.endswith("_construction") or key.endswith("_purchase")
            and key != "feed_purchase"
        )

        def largest_entry(values):
            if not values:
                return {"category": None, "amount": 0.0}
            category, amount = max(values.items(), key=lambda item: item[1])
            return {"category": category, "amount": round(amount, 2)}

        snapshot = YearSnapshot(
            year=year, money=round(self.economy.money, 2),
            income=round(self.income[year], 2),
            expenses=round(expenses, 2),
            net_profit=round(self.income[year] - expenses, 2),
            income_breakdown=income_breakdown,
            expense_breakdown=expense_breakdown,
            investments=dict(sorted(self.investments[year].items())),
            maintenance_expense_ratio=round(
                maintenance_expense / expenses, 4,
            ) if expenses else 0.0,
            feed_expense_ratio=round(
                self.expense_breakdown[year].get("feed_purchase", 0.0) / expenses,
                4,
            ) if expenses else 0.0,
            investment_expense_ratio=round(
                investment_expense / expenses, 4,
            ) if expenses else 0.0,
            largest_income_source=largest_entry(self.income_breakdown[year]),
            largest_expense_category=largest_entry(self.expense_breakdown[year]),
            buildings=dict(sorted(buildings.items())),
            vehicles=dict(sorted(vehicles.items())),
            animals=dict(sorted(animals.items())),
            fields=dict(sorted(fields.items())), inventory=dict(sorted(inventory.items())),
            warehouse_capacity=capacity, warehouse_used=used,
            warehouse_utilization=round(used / capacity, 4) if capacity else 0.0,
            sold_products=dict(sorted(self.sold[year].items())),
            purchased_feed=dict(sorted(self.feed_bought[year].items())),
            purchased_feed_cost=round(self.feed_cost[year], 2),
            completed_tasks=self.completed_tasks_by_year[year],
            failed_tasks=self.failed_tasks_by_year[year],
            loans_taken=self.loan_count_by_year[year],
            loan_principal_received=round(self.loan_principal_by_year[year], 2),
            bank_repayments=round(self.bank_repayments_by_year[year], 2),
            bank_interest_paid=round(self.bank_interest_by_year[year], 2),
            outstanding_loan_balance=round(
                self.bank_system.loan.remaining_balance_cents / 100, 2,
            ),
            loan_remaining_weeks=self.bank_system.loan.remaining_weeks,
        )
        self.snapshots.append(snapshot)
        return snapshot

    def diagnostic(self):
        return {
            "seed": self.seed, "elapsed_weeks": self.game_time.elapsed_weeks,
            "year": self.year, "week": self.week,
            "money": self.economy.money,
            "inventory": get_total_inventory(self.buildings),
            "queue_length": len(self.vehicles.task_queue),
            "vehicle_states": {
                str(v.vehicle_id): v.state for v in self.vehicles.vehicles
            },
        }

    def _fail(self, message):
        raise SimulationInvariantError(message, self.diagnostic())

    def assert_invariants(self):
        if not math.isfinite(self.economy.money):
            self._fail("A pénzegyenleg nem véges szám.")
        loan = self.bank_system.loan
        if loan.active_loan and (
                loan.remaining_balance_cents <= 0 or loan.remaining_weeks <= 0):
            self._fail("Az aktív bankhitel állapota ellentmondásos.")
        if not loan.active_loan and (
                loan.remaining_balance_cents != 0 or loan.remaining_weeks != 0):
            self._fail("A lezárt bankhitelnek fennmaradó tartozása van.")
        inventory = get_total_inventory(self.buildings)
        if any(not isinstance(value, int) or value < 0 for value in inventory.values()):
            self._fail("Negatív vagy nem egész raktárkészlet.")
        if sum(inventory.values()) > get_total_capacity(self.buildings):
            self._fail("A raktárkészlet túllépte a kapacitást.")
        ids = [asset.vehicle_id for asset in self.vehicles.managed_assets]
        if len(ids) != len(set(ids)):
            self._fail("Nem egyediek a járműazonosítók.")
        occupied_slots = [
            (id(asset.assigned_parking_building), asset.parking_slot_id)
            for asset in self.vehicles.managed_assets
            if asset.parking_slot_id is not None
        ]
        if len(occupied_slots) != len(set(occupied_slots)):
            self._fail("Két jármű ugyanazt a garázshelyet foglalja.")
        if any(implement.is_attached and (
                implement.attached_to not in self.vehicles.vehicles
                or implement.attached_to.attached_implement is not implement)
               for implement in self.vehicles.implements):
            self._fail("Árva vontatmány található.")
        for group in get_animal_pen_groups(self.buildings):
            species = {
                animal["type"] for animal in get_animals_in_pen_group(
                    self.animals, group,
                )
            }
            if len(species) > 1:
                self._fail("Eltérő állatfajok kerültek közös Karámba.")
        pen_tiles = {
            tile for group in get_animal_pen_groups(self.buildings)
            for tile in get_pen_group_tiles(group)
        }
        if any((animal["row"], animal["col"]) not in pen_tiles
               for animal in self.animals):
            self._fail("Állat érvényes Karámon kívül található.")
        targets = [
            (task.task_type, id(task.field)) for task in self.vehicles.task_queue
        ] + [
            (vehicle.current_task.task_type, id(vehicle.current_task.field))
            for vehicle in self.vehicles.vehicles if vehicle.current_task is not None
        ]
        if len(targets) != len(set(targets)):
            self._fail("Duplikált célfeladat található.")
        for building in self.buildings:
            if any(
                    self.world[building["row"] + row][building["col"] + col]
                    != BUILDING
                    for row in range(building["height"])
                    for col in range(building["width"])):
                self._fail("Az épületlista és a világrács eltér.")
        for field in self.fields:
            if any(
                    self.world[field["row"] + row][field["col"] + col] != FIELD
                    for row in range(field["height"])
                    for col in range(field["width"])):
                self._fail("A Veteményes-lista és a világrács eltér.")


def run_simulation(years=DEFAULT_SIMULATION_YEARS, seed=DEFAULT_SIMULATION_SEED,
                   report_dir="reports", verbose=False):
    if years <= 0:
        raise ValueError("Az évek számának pozitívnak kell lennie.")
    started = time.perf_counter()
    bot = SimulationBot(seed)
    invariant_errors = []
    output_context = nullcontext() if verbose else redirect_stdout(io.StringIO())
    with output_context:
        try:
            bot.bootstrap()
            for elapsed_week in range(1, years * WEEKS_PER_YEAR + 1):
                bot.run_week()
                if elapsed_week % WEEKS_PER_YEAR == 0:
                    bot.take_snapshot(elapsed_week // WEEKS_PER_YEAR)
        except SimulationInvariantError as error:
            invariant_errors.append({
                "message": str(error), "diagnostic": error.diagnostic,
            })
            failure_dir = Path(report_dir)
            failure_dir.mkdir(parents=True, exist_ok=True)
            failure_path = failure_dir / f"five_year_simulation_seed_{seed}_failure.json"
            failure_path.write_text(
                json.dumps(invariant_errors[-1], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            raise
    runtime = time.perf_counter() - started
    result = {
        "seed": bot.seed, "years": years,
        "weeks_processed": bot.game_time.elapsed_weeks,
        "runtime_seconds": round(runtime, 6),
        "final_money": round(bot.economy.money, 2),
        "loans_taken": bot.bank_system.loan.loans_taken,
        "total_bank_repaid": round(
            bot.bank_system.loan.total_repaid_cents / 100, 2,
        ),
        "active_loan": bot.bank_system.loan.active_loan,
        "outstanding_loan_balance": round(
            bot.bank_system.loan.remaining_balance_cents / 100, 2,
        ),
        "snapshots": [asdict(item) for item in bot.snapshots],
        "decisions": bot.decisions,
        "invariant_errors": invariant_errors,
    }
    md_path, json_path = write_simulation_reports(result, report_dir)
    result["report_paths"] = {
        "markdown": str(md_path), "json": str(json_path),
    }
    return result
