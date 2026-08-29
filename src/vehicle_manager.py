from collections import deque
from dataclasses import fields as dataclass_fields

import pygame

from animal_troughs import (
    get_group_anchor, trough_supply_is_needed, validate_trough_supply,
)
from buildings import (
    GARAGE_PARKING_SLOTS, get_animal_pen_groups, get_free_capacity,
    get_orchard_groups, get_total_inventory, get_warehouses, remove_item,
    store_item,
)
from constants import FIELD
from crops import (
    can_harvest_crop_in_week, can_late_harvest_crop_in_week,
    can_plant_crop_in_week,
)
from fields import (
    can_fertilize_field, can_water_field, crop_lifecycle_is_active,
    prepare_harvest, preview_harvest_yield,
    synchronize_annual_crop_cycle,
)
from game_rules import get_field_fertilizer_cost
from game_logger import log
from maintenance import calculate_weekly_maintenance
from orchards import (
    TREE_TYPES, get_tree_age_years, get_tree_in_slot, is_tree_harvestable,
)
from processing import (
    PROCESSING_STATUS_IN_TRANSIT, PROCESSING_STATUS_NO_MONEY,
    cancel_processing_delivery,
    initialize_processing_plant,
)
from quest_system import (
    QUEST_EVENT_ALFALFA_HARVESTED, QUEST_EVENT_ALFALFA_PLANTED,
    QUEST_EVENT_COMBINE_PURCHASED,
    QUEST_EVENT_CROP_HARVESTED, QUEST_EVENT_TOMATO_HARVESTED,
    QUEST_EVENT_FIELD_FERTILIZED, QUEST_EVENT_FIELD_WATERED,
    QUEST_EVENT_FOOD_TROUGH_FILLED, QUEST_EVENT_TRAILER_PURCHASED,
    QUEST_EVENT_WATER_TANK_PURCHASED, QUEST_EVENT_WATER_TROUGH_FILLED,
    QUEST_EVENT_WHEAT_HARVESTED, QUEST_EVENT_WHEAT_PLANTED,
)
from tractor import (
    FEED_LOAD_DURATION_MS, FEED_UNLOAD_DURATION_MS,
    TASK_FERTILIZING, TASK_HARVESTING, TASK_PLANTING,
    TASK_ORCHARD_HARVEST, TASK_SUPPLY_FEED, TASK_SUPPLY_WATER, TASK_WATERING,
    TASK_PROCESSING_SUPPLY,
    TRACTOR_AWAITING_ASSIGNMENT, TRACTOR_SELECTING_NEXT_TASK,
    TRACTOR_RETURNING_HOME,
    WATER_FILL_DURATION_MS, WATER_UNLOAD_DURATION_MS,
    Combine, FieldTask, FruitHarvester, TowableImplement, Tractor,
    find_building_parking, find_building_route, find_field_route,
    find_road_path,
)
from vehicle_types import (
    VEHICLE_TYPE_DEFINITIONS, VehicleType, normalize_vehicle_type,
)
from financial_history import EXPENSE_PROCESSING_INPUT, EXPENSE_VEHICLE
from inventory import get_inventory_item_data
from market_procurement import purchase_automatically
from storage_blocking import FIELD_HARVEST_STORAGE_MESSAGE


DEBUG_TRACTOR_DISPATCH = False

CROP_HARVEST_EVENTS = {
    "wheat": QUEST_EVENT_WHEAT_HARVESTED,
    "tomato": QUEST_EVENT_TOMATO_HARVESTED,
    "alfalfa": QUEST_EVENT_ALFALFA_HARVESTED,
}

CROP_PLANT_EVENTS = {
    "wheat": QUEST_EVENT_WHEAT_PLANTED,
    "alfalfa": QUEST_EVENT_ALFALFA_PLANTED,
}

# A Dispatcher később új feladattípusokkal bővíthető anélkül, hogy a
# járműválasztási logikát át kellene írni.
TASK_VEHICLE_TYPES = {
    TASK_PLANTING: VehicleType.TRACTOR,
    TASK_FERTILIZING: VehicleType.TRACTOR,
    TASK_HARVESTING: VehicleType.COMBINE,
    TASK_ORCHARD_HARVEST: VehicleType.FRUIT_HARVESTER,
    TASK_WATERING: VehicleType.TRACTOR,
    TASK_SUPPLY_FEED: VehicleType.TRACTOR,
    TASK_SUPPLY_WATER: VehicleType.TRACTOR,
    TASK_PROCESSING_SUPPLY: VehicleType.TRACTOR,
}

TASK_NAMES = {
    TASK_PLANTING: "ültetési",
    TASK_FERTILIZING: "trágyázási",
    TASK_HARVESTING: "aratási",
    TASK_ORCHARD_HARVEST: "gyümölcsszüretelési",
    TASK_WATERING: "locsolási",
    TASK_SUPPLY_FEED: "etetési ellátási",
    TASK_SUPPLY_WATER: "itatási ellátási",
    TASK_PROCESSING_SUPPLY: "feldolgozóipari alapanyag-szállítási",
}

TASK_LOG_CATEGORIES = {
    TASK_PLANTING: "Planting",
    TASK_FERTILIZING: "Fertilizing",
    TASK_HARVESTING: "Harvest",
    TASK_ORCHARD_HARVEST: "Orchard",
    TASK_WATERING: "Watering",
    TASK_SUPPLY_FEED: "Supply",
    TASK_SUPPLY_WATER: "Supply",
    TASK_PROCESSING_SUPPLY: "Processing",
}

class VehicleManager:
    """Központilag kezeli a járműveket és a lefoglalt parkolóhelyeket."""

    def __init__(self, storage_block_manager=None):
        self.vehicles = []
        self.implements = []
        self.next_vehicle_id = 1
        self.task_queue = deque()
        self.next_task_order = 1
        self.quest_event_handler = None
        self.field_automation_handler = None
        self.storage_block_manager = storage_block_manager

    @staticmethod
    def _field_harvest_storage_event_id(field):
        """Egy Veteményes fennálló kapacitásblokkjának stabil kulcsa."""
        return (
            f"storage:field_harvest:{field.get('row')}:{field.get('col')}:"
            f"{field.get('crop')}"
        )

    @property
    def tractors(self):
        """Kompatibilis nézet a mezőmunkára alkalmas járművekről."""
        return [
            vehicle for vehicle in self.vehicles
            if vehicle.vehicle_type == VehicleType.TRACTOR
        ]

    @property
    def managed_assets(self):
        """Az önjáró járművek és a vontatott munkagépek közös, olvasható nézete."""
        return [*self.vehicles, *self.implements]

    @property
    def weekly_cost(self):
        """A központi járműkatalógus alapján összesíti a heti fenntartást."""
        return sum(
            calculate_weekly_maintenance(
                VEHICLE_TYPE_DEFINITIONS[asset.vehicle_type]["purchase_price"]
            )
            for asset in self.managed_assets
        )

    @property
    def reserved_fertilizer(self):
        """A váró és aktív trágyázási feladatok által lefoglalt készlet."""
        queued = sum(
            task.resource_amount
            for task in self.task_queue
            if task.task_type == TASK_FERTILIZING and task.resource_reserved
        )
        active = sum(
            tractor.current_task.resource_amount
            for tractor in self.tractors
            if (
                tractor.current_task is not None
                and tractor.current_task.task_type == TASK_FERTILIZING
                and tractor.current_task.resource_reserved
            )
        )
        return queued + active

    @property
    def reserved_harvest_capacity(self):
        """A váró és aktív aratások számára lefoglalt raktárkapacitás."""
        tasks = list(self.task_queue) + [
            vehicle.current_task for vehicle in self.vehicles
            if vehicle.current_task is not None
        ]
        return sum(
            task.resource_amount for task in tasks
            if task.task_type in (TASK_HARVESTING, TASK_ORCHARD_HARVEST)
            and task.resource_reserved
        )

    @property
    def primary_tractor(self):
        """Az eredeti ingyenes traktort adja vissza parkolási kompatibilitáshoz."""
        return self.tractors[0] if self.tractors else None

    def _create_tractor(self, parking_building=None, slot_id=None):
        return self._create_vehicle(
            VehicleType.TRACTOR, parking_building, slot_id,
        )

    def _create_vehicle(
            self, vehicle_type, parking_building=None, slot_id=None):
        normalized_type = normalize_vehicle_type(vehicle_type)
        if normalized_type == VehicleType.TRACTOR:
            vehicle = Tractor(self.next_vehicle_id)
        elif normalized_type == VehicleType.COMBINE:
            vehicle = Combine(self.next_vehicle_id)
        elif normalized_type == VehicleType.FRUIT_HARVESTER:
            vehicle = FruitHarvester(self.next_vehicle_id)
        else:
            return None
        self.next_vehicle_id += 1
        vehicle.assigned_parking_building = parking_building
        vehicle.parking_slot_id = slot_id
        self.vehicles.append(vehicle)
        return vehicle

    def _create_implement(
            self, implement_type, parking_building=None, slot_id=None):
        normalized_type = normalize_vehicle_type(implement_type)
        definition = VEHICLE_TYPE_DEFINITIONS.get(normalized_type, {})
        if not definition.get("towable"):
            return None
        implement = TowableImplement(self.next_vehicle_id, normalized_type)
        self.next_vehicle_id += 1
        implement.assigned_parking_building = parking_building
        implement.parking_slot_id = slot_id
        self.implements.append(implement)
        return implement

    def _create_managed_asset(
            self, asset_type, parking_building=None, slot_id=None):
        definition = VEHICLE_TYPE_DEFINITIONS.get(
            normalize_vehicle_type(asset_type), {},
        )
        if definition.get("towable"):
            return self._create_implement(
                asset_type, parking_building, slot_id,
            )
        return self._create_vehicle(asset_type, parking_building, slot_id)

    def on_farmhouse_built(self, world, buildings, farmhouse):
        """Az első Farmház pontosan egy ingyenes traktort ad."""
        if self.tractors:
            return self.primary_tractor
        garage = next(
            (building for building in buildings if building["type"] == "garage"),
            None,
        )
        garage_slot = self.first_free_slot(garage) if garage is not None else None
        tractor = self._create_tractor(
            garage if garage_slot is not None else farmhouse,
            garage_slot,
        )
        tractor.ensure_idle_position(world, buildings)
        return tractor

    def occupied_slot_ids(self, garage):
        return {
            asset.parking_slot_id
            for asset in self.managed_assets
            if asset.assigned_parking_building is garage
            and asset.parking_slot_id is not None
        }

    def garage_status(self, garage):
        occupied = len(self.occupied_slot_ids(garage))
        capacity = len(GARAGE_PARKING_SLOTS)
        return {
            "occupied": occupied,
            "capacity": capacity,
            "free": capacity - occupied,
        }

    def count_by_type(self, vehicle_type):
        normalized_type = normalize_vehicle_type(vehicle_type)
        return sum(
            asset.vehicle_type == normalized_type
            for asset in self.managed_assets
        )

    def assets_in_garage(self, garage):
        """Az adott Garázshoz rendelt eszközöket azonosító szerint rendezi."""
        return sorted(
            (
                asset for asset in self.managed_assets
                if asset.assigned_parking_building is garage
            ),
            key=lambda asset: asset.vehicle_id,
        )

    def vehicles_for_task(self, task_type):
        required_type = TASK_VEHICLE_TYPES.get(task_type)
        if required_type is None:
            return []
        return [
            vehicle for vehicle in self.vehicles
            if vehicle.vehicle_type == required_type
        ]

    def first_free_slot(self, garage):
        occupied = self.occupied_slot_ids(garage)
        return next(
            (slot_id for slot_id in range(len(GARAGE_PARKING_SLOTS))
             if slot_id not in occupied),
            None,
        )

    def on_garage_built(self, world, buildings, garage):
        """A Farmháznál álló első traktort az új Garázs első helyére költözteti."""
        tractor = self.primary_tractor
        if tractor is None or tractor.parking_building_type == "garage":
            return False
        return tractor.request_parking_relocation(
            world, buildings, parking_building=garage, parking_slot_id=0,
        )

    def purchase_vehicle(
            self, world, buildings, economy, garage, vehicle_type):
        """Az első szabad Garázshelyre megvásárol egy kiválasztott járművet."""
        normalized_type = normalize_vehicle_type(vehicle_type)
        definition = VEHICLE_TYPE_DEFINITIONS.get(normalized_type)
        if definition is None:
            return False
        slot_id = self.first_free_slot(garage)
        if slot_id is None:
            log("Nincs szabad parkolóhely. Építs új Garázst.", "Vehicle")
            return False
        if not economy.can_afford(definition["purchase_price"]):
            log(
                f"Nincs elegendő pénz új {definition['name'].lower()} "
                "vásárlásához.", "Vehicle",
            )
            return False
        economy.spend(definition["purchase_price"])
        economy.record_expense(
            EXPENSE_VEHICLE, definition["purchase_price"],
            normalized_type.value, definition["name"],
        )
        vehicle = self._create_managed_asset(normalized_type, garage, slot_id)
        vehicle.ensure_idle_position(world, buildings)
        log(
            f"Új {definition['name'].lower()} vásárolva: #{vehicle.vehicle_id}, "
            f"parkolóhely: {slot_id}.", "Vehicle",
        )
        vehicle_purchase_events = {
            VehicleType.COMBINE: QUEST_EVENT_COMBINE_PURCHASED,
            VehicleType.WATER_TANK: QUEST_EVENT_WATER_TANK_PURCHASED,
            VehicleType.TRAILER: QUEST_EVENT_TRAILER_PURCHASED,
        }
        purchase_event = vehicle_purchase_events.get(normalized_type)
        if purchase_event is not None and self.quest_event_handler is not None:
            self.quest_event_handler(purchase_event)
        self._dispatch_tasks(world, buildings, economy)
        return True

    def purchase_tractor(self, world, buildings, economy, garage):
        """Kompatibilis belépési pont a Traktor vásárlásához."""
        return self.purchase_vehicle(
            world, buildings, economy, garage, VehicleType.TRACTOR,
        )

    def purchase_combine(self, world, buildings, economy, garage):
        """Új Kombájnt vásárol a közös Garázs-kapacitás terhére."""
        return self.purchase_vehicle(
            world, buildings, economy, garage, VehicleType.COMBINE,
        )

    def purchase_fruit_harvester(self, world, buildings, economy, garage):
        """Gyümölcs szüretelőgépet vásárol a közös Garázskapacitásba."""
        return self.purchase_vehicle(
            world, buildings, economy, garage,
            VehicleType.FRUIT_HARVESTER,
        )

    def purchase_water_tank(self, world, buildings, economy, garage):
        """Kompatibilis belépési pont a Locsolótartály vásárlásához."""
        return self.purchase_vehicle(
            world, buildings, economy, garage, VehicleType.WATER_TANK,
        )

    def purchase_trailer(self, world, buildings, economy, garage):
        """A közös vontatmányrendszeren keresztül Pótkocsit vásárol."""
        return self.purchase_vehicle(
            world, buildings, economy, garage, VehicleType.TRAILER,
        )

    def attach_implement(self, tractor, implement):
        """Általános csatolási pont a későbbi vontatott munkafolyamatokhoz."""
        if tractor not in self.vehicles or implement not in self.implements:
            return False
        return implement.attach_to(tractor)

    def detach_implement(self, implement):
        if implement not in self.implements:
            return False
        implement.detach()
        return True

    def start_planting(
            self, world, buildings, economy, field, crop,
            current_ticks=None, current_week=None):
        """Lefoglalja az erőforrást, majd a közös FIFO sorba teszi a munkát."""
        if field.get("crop") is not None or crop is None:
            return False
        if (current_week is not None
                and not can_plant_crop_in_week(crop, current_week)):
            log("Most nincs vetési időszaka.", "Planting")
            return False
        task_vehicles = self.vehicles_for_task(TASK_PLANTING)
        if not task_vehicles:
            log("Az ültetéshez traktor szükséges.", "Planting")
            return False
        if field.get("vehicle_task_status") is not None:
            log("Ez a veteményes már traktorfeladatra vár.", "Planting")
            return False
        has_road_connection = False
        has_reachable_tractor = False
        for tractor in task_vehicles:
            _, parking_tile = tractor.get_parking(world, buildings)
            if parking_tile is None:
                continue
            route, _, connected = find_field_route(world, parking_tile, field)
            has_road_connection = has_road_connection or connected
            if (route is not None
                    and find_road_path(world, route[-1], parking_tile) is not None):
                has_reachable_tractor = True
                break
        if not has_road_connection:
            log("A veteményes nem érhető el útról.", "Planting")
            return False
        if not has_reachable_tractor:
            log(
                "Egyik traktor sem talál útvonalat a veteményeshez.",
                "Planting",
            )
            return False
        if not economy.can_acquire_seed(buildings, crop):
            economy.report_seed_unavailable(buildings, crop)
            return False
        payment = economy.reserve_seed(buildings, crop)
        if payment is None:
            return False
        self.task_queue.append(
            FieldTask(
                field=field, crop=crop, payment=payment,
                task_type=TASK_PLANTING, buildings=buildings,
                creation_order=self._take_task_order(),
            )
        )
        self._set_waiting_statuses()
        self._dispatch_tasks(
            world, buildings, economy, current_ticks=current_ticks,
        )
        if field.get("vehicle_task_status") == "active":
            log("Ültetési feladat elindítva.", "Planting")
        else:
            log(
                "Ültetési feladat hozzáadva a közös várólistához.",
                "Planting",
            )
        return True

    def start_fertilizing(
            self, world, buildings, economy, field, current_ticks=None,
            source="manual"):
        """Egy Trágyát lefoglal, majd a közös FIFO sorba teszi a mezőmunkát."""
        report = source == "manual"
        task_vehicles = self.vehicles_for_task(TASK_FERTILIZING)
        if not task_vehicles:
            if report:
                log("A trágyázáshoz traktor szükséges.", "Fertilizing")
            return False
        if self.has_pending_field_task(field, TASK_FERTILIZING):
            if report:
                log(
                    "A trágyázás már folyamatban van vagy várakozik.",
                    "Fertilizing",
                )
            return False
        if not can_fertilize_field(field, include_task_status=False):
            if report:
                log(
                    "Nincs trágyázható növény a kijelölt területen.",
                    "Fertilizing",
                )
            return False

        fertilizer_cost = get_field_fertilizer_cost(field)
        if fertilizer_cost is None:
            if report:
                log(
                    "A termőföld Trágya-igénye nincs beállítva.",
                    "Fertilizing",
                )
            return False
        manure_amount = get_total_inventory(buildings).get("manure", 0)
        if manure_amount - self.reserved_fertilizer < fertilizer_cost:
            if report:
                log("Nincs elegendő trágya a raktárban.", "Fertilizing")
            return False

        has_road_connection = False
        has_reachable_tractor = False
        for tractor in task_vehicles:
            _, parking_tile = tractor.get_parking(world, buildings)
            if parking_tile is None:
                continue
            route, _, connected = find_field_route(
                world, parking_tile, field,
            )
            has_road_connection = has_road_connection or connected
            if (route is not None
                    and find_road_path(
                        world, route[-1], parking_tile,
                    ) is not None):
                has_reachable_tractor = True
                break
        if not has_road_connection:
            if report:
                log("A veteményes nem érhető el útról.", "Fertilizing")
            return False
        if not has_reachable_tractor:
            if report:
                log(
                    "Egyik traktor sem talál útvonalat a veteményeshez.",
                    "Fertilizing",
                )
            return False

        self.task_queue.append(FieldTask(
            field=field,
            task_type=TASK_FERTILIZING,
            buildings=buildings,
            resource_reserved=True,
            resource_amount=fertilizer_cost,
            creation_order=self._take_task_order(),
            manually_initiated=report,
        ))
        self._set_waiting_statuses()
        self._dispatch_tasks(
            world, buildings, economy, current_ticks=current_ticks,
        )
        if report and field.get("vehicle_task_status") == "active":
            log("Trágyázási feladat elindítva.", "Fertilizing")
        elif report:
            log(
                "Trágyázási feladat hozzáadva a közös várólistához.",
                "Fertilizing",
            )
        return True

    def start_watering(
            self, world, buildings, economy, field, current_ticks=None,
            source="manual"):
        """Ellenőrzi és a közös Dispatcherhez adja a teljes locsolási munkát."""
        report = source == "manual"
        if field is None:
            if report:
                log("A kijelölt helyen nincs Veteményes.", "Watering")
            return False
        if field.get("crop") is None:
            if report:
                log("Az üres Veteményes nem locsolható.", "Watering")
            return False
        if field.get("watered", False):
            if report:
                log("Ez a Veteményes már meg van locsolva.", "Watering")
            return False
        if self.has_pending_field_task(field, TASK_WATERING):
            if report:
                log(
                    "A locsolás már folyamatban van vagy várakozik.",
                    "Watering",
                )
            return False
        if not can_water_field(field, include_task_status=False):
            if report:
                log("Ez a Veteményes jelenleg nem locsolható.", "Watering")
            return False

        ponds = [
            building for building in buildings
            if building.get("type") == "pond"
        ]
        if not ponds:
            if report:
                log("A locsoláshoz megépített Tó szükséges.", "Watering")
            return False
        water_tanks = [
            implement for implement in self.implements
            if implement.vehicle_type == VehicleType.WATER_TANK
        ]
        if not water_tanks:
            if report:
                log("A locsoláshoz Locsolótartály szükséges.", "Watering")
            return False
        if not self.tractors:
            if report:
                log("A locsoláshoz Traktor szükséges.", "Watering")
            return False

        assignment = self._find_watering_assignment(
            world, buildings, field, self.tractors, water_tanks, ponds,
            use_parking_start=True,
        )
        if assignment is None:
            if report:
                log(
                    "Nem található összefüggő útvonal a Garázs, a Tó és a "
                    "Veteményes között.", "Watering",
                )
            return False
        task = FieldTask(
            field=field,
            task_type=TASK_WATERING,
            buildings=buildings,
            required_implement_type=VehicleType.WATER_TANK,
            source_type="pond",
            creation_order=self._take_task_order(),
            manually_initiated=report,
        )
        self.task_queue.append(task)
        self._set_waiting_statuses()
        self._dispatch_tasks(
            world, buildings, economy, current_ticks=current_ticks,
        )
        if report and field.get("vehicle_task_status") == "active":
            log("Locsolási feladat létrehozva.", "Watering")
        elif report:
            log("Locsolási feladat várólistára helyezve.", "Dispatcher")
        return True

    @staticmethod
    def _find_watering_assignment(
            world, buildings, field, tractors, implements, ponds,
            use_parking_start=False):
        """Az első alkalmas Traktorhoz a legközelebbi elérhető Tavat választja."""
        for tractor in tractors:
            parking_building, parking_tile = tractor.get_parking(
                world, buildings,
            )
            if parking_tile is None or parking_building is None:
                continue
            start_tile = parking_tile if use_parking_start else (tractor.row, tractor.col)
            candidates = []
            for implement in implements:
                implement_road = find_building_parking(
                    world, implement.assigned_parking_building,
                )
                if implement_road is None:
                    continue
                route_to_implement = find_road_path(
                    world, start_tile, implement_road,
                )
                if route_to_implement is None:
                    continue
                for pond in ponds:
                    route_to_pond, pond_road = find_building_route(
                        world, implement_road, pond,
                    )
                    if route_to_pond is None:
                        continue
                    route_to_field, field_entry, connected = find_field_route(
                        world, pond_road, field,
                    )
                    if not connected or route_to_field is None:
                        continue
                    return_route = find_road_path(
                        world, route_to_field[-1], implement_road,
                    )
                    implement_to_home = find_road_path(
                        world, implement_road, parking_tile,
                    )
                    if return_route is None or implement_to_home is None:
                        continue
                    total_distance = (
                        len(route_to_implement) + len(route_to_pond)
                        + len(route_to_field) + len(return_route)
                        + len(implement_to_home)
                    )
                    candidates.append((
                        total_distance, implement, pond, {
                            "to_implement": route_to_implement,
                            "to_pond": route_to_pond,
                            "pond_to_field": route_to_field,
                            "return": return_route,
                            "implement_to_home": implement_to_home,
                            "implement_road": implement_road,
                            "pond_road": pond_road,
                            "field_entry": field_entry,
                            "field_road": route_to_field[-1],
                        },
                    ))
            if candidates:
                _, implement, pond, routes = min(
                    candidates, key=lambda item: item[0],
                )
                return tractor, implement, pond, routes
        return None

    def start_harvesting(
            self, world, buildings, economy, field, current_ticks=None,
            current_week=None, current_elapsed_week=None):
        """A teljes aratást a Kombájn számára a közös FIFO sorba teszi."""
        block_reason = self.get_harvest_block_reason(
            world, buildings, field,
            current_week=current_week,
            current_elapsed_week=current_elapsed_week,
        )
        if block_reason is not None:
            log(self.get_harvest_block_message(block_reason), "Harvest")
            if block_reason == "no_capacity" and self.storage_block_manager:
                self.storage_block_manager.report(
                    self._field_harvest_storage_event_id(field),
                    FIELD_HARVEST_STORAGE_MESSAGE,
                    (
                        "Aratás blokkolva: nincs elegendő hely a teljes "
                        f"terméshez ({field.get('row')}, {field.get('col')})."
                    ),
                )
            return False

        if self.storage_block_manager is not None:
            self.storage_block_manager.resolve(
                self._field_harvest_storage_event_id(field),
                "A Veteményes aratási kapacitásblokkja feloldva.",
            )

        original_watered = field.get("watered", False)
        original_fertilized = field.get("fertilized", False)
        late_harvest = bool(
            field.get("late_harvest_active", False)
            or (
                current_week is not None
                and can_late_harvest_crop_in_week(field.get("crop"), current_week)
            )
        )
        if self.has_pending_field_task(field, TASK_WATERING):
            field["watered"] = True
        if self.has_pending_field_task(field, TASK_FERTILIZING):
            field["fertilized"] = True
        try:
            harvest = prepare_harvest(
                field, buildings, self.reserved_harvest_capacity,
                include_task_status=False,
                late_harvest=late_harvest,
            )
        finally:
            field["watered"] = original_watered
            field["fertilized"] = original_fertilized
        if harvest is None:
            return False

        self.task_queue.append(FieldTask(
            field=field,
            crop=harvest["crop"],
            task_type=TASK_HARVESTING,
            buildings=buildings,
            resource_reserved=True,
            resource_amount=harvest["amount"],
            creation_order=self._take_task_order(),
        ))
        self._set_waiting_statuses()
        self._dispatch_tasks(
            world, buildings, economy, current_ticks=current_ticks,
        )
        if field.get("vehicle_task_status") == "active":
            log("Aratási feladat elindítva.", "Harvest")
        else:
            log(
                "Aratási feladat hozzáadva a közös várólistához.",
                "Harvest",
            )
        return True

    def start_orchard_harvest(
            self, world, buildings, economy, orchard, tree,
            current_ticks=None):
        """Egy konkrét gyümölcsfa szüretét a közös FIFO sorba teszi."""
        reason = self.get_orchard_harvest_block_reason(
            world, buildings, orchard, tree,
        )
        if reason is not None:
            log(self.get_orchard_harvest_block_message(reason), "Orchard")
            return False
        definition = TREE_TYPES[tree["type"]]
        self.task_queue.append(FieldTask(
            field=orchard,
            crop=definition["product_id"],
            task_type=TASK_ORCHARD_HARVEST,
            buildings=buildings,
            resource_reserved=True,
            resource_amount=definition["annual_yield"],
            tree_slot=tree["slot"],
            tree_type=tree["type"],
            creation_order=self._take_task_order(),
        ))
        self._set_waiting_statuses()
        self._dispatch_tasks(
            world, buildings, economy, current_ticks=current_ticks,
        )
        tree_name = definition["tree_name"]
        if orchard.get("vehicle_task_status") == "active":
            log(f"{tree_name} szüretelési feladat elindítva.", "Orchard")
        else:
            log(
                f"{tree_name} szüretelési feladat várólistára került.",
                "Orchard",
            )
        return True

    def get_orchard_harvest_block_reason(
            self, world, buildings, orchard, tree):
        """Mellékhatás nélkül ellenőrzi a konkrét fa szüretelhetőségét."""
        if orchard not in buildings or orchard.get("type") != "orchard":
            return "missing_tree"
        stored_tree = get_tree_in_slot(orchard, tree.get("slot")) if tree else None
        if stored_tree is not tree:
            return "missing_tree"
        definition = TREE_TYPES.get(tree.get("type"))
        if definition is None:
            return "missing_tree"
        age_years = get_tree_age_years(tree)
        if age_years < definition["first_yield_age_years"]:
            return "immature"
        if age_years > definition["last_yield_age_years"]:
            return "expired"
        if tree.get("annual_harvest_state") == "harvested":
            return "already_harvested"
        if not is_tree_harvestable(tree):
            return "outside_harvest_season"
        if any(
            task.task_type == TASK_ORCHARD_HARVEST
            and task.field is orchard
            and task.tree_slot == tree["slot"]
            for task in self._all_tasks()
        ):
            return "duplicate"
        vehicles = [
            vehicle
            for vehicle in self.vehicles_for_task(TASK_ORCHARD_HARVEST)
            if tree["type"] in VEHICLE_TYPE_DEFINITIONS[
                vehicle.vehicle_type
            ].get("supported_tree_types", ())
        ]
        if not vehicles:
            return "no_fruit_harvester"
        has_connection = False
        for vehicle in vehicles:
            _, parking_tile = vehicle.get_parking(world, buildings)
            if parking_tile is None:
                continue
            route, connected = self._find_orchard_group_route(
                world, buildings, parking_tile, orchard,
            )
            has_connection = has_connection or connected
            if route is not None:
                break
        else:
            return "no_route" if has_connection else "no_road"
        if not get_warehouses(buildings):
            return "no_warehouse"
        if (
            get_free_capacity(buildings) - self.reserved_harvest_capacity
            < definition["annual_yield"]
        ):
            return "no_capacity"
        return None

    @staticmethod
    def _find_orchard_group_route(world, buildings, start, target_orchard):
        """A célfa összefüggő Gyümölcsösének legjobb közúti útját adja."""
        group = next(
            (items for items in get_orchard_groups(buildings)
             if target_orchard in items),
            None,
        )
        if group is None:
            return None, False
        routes = []
        connected = False
        for orchard in group:
            route, _ = find_building_route(world, start, orchard)
            if route is not None:
                routes.append(route)
                connected = True
            else:
                connected = connected or (
                    find_building_parking(world, orchard) is not None
                )
        return (min(routes, key=len), True) if routes else (None, connected)

    @staticmethod
    def get_orchard_harvest_block_message(reason):
        return {
            "missing_tree": "A kijelölt gyümölcsfa nem található.",
            "immature": "A gyümölcsfa még nem érett.",
            "expired": "Ez a gyümölcsfa már nem szüretelhető.",
            "already_harvested": "Ez a gyümölcsfa ebben az évben már le lett szüretelve.",
            "outside_harvest_season": "Most nincs szüreti időszaka.",
            "duplicate": "Ehhez a fához már tartozik szüretelési feladat.",
            "no_fruit_harvester": "A szürethez Gyümölcs szüretelőgép szükséges.",
            "no_road": "A Gyümölcsös-rendszer nem érhető el útról.",
            "no_route": "A Gyümölcs szüretelőgép nem talál útvonalat.",
            "no_warehouse": "A szürethez legalább egy Raktár szükséges.",
            "no_capacity": "Nincs elegendő hely a Raktárban.",
        }.get(reason, "A gyümölcsszüret jelenleg nem indítható.")

    def get_harvest_block_reason(
            self, world, buildings, field, current_week=None,
            current_elapsed_week=None):
        """Mellékhatás nélkül megadja az Aratás legfontosabb kizáró okát."""
        if field is None or field.get("crop") is None:
            return "empty"
        crop = field.get("crop")
        synchronize_annual_crop_cycle(field, current_elapsed_week)
        if not crop_lifecycle_is_active(field, current_elapsed_week):
            return "lifecycle_ended"
        annual_state = field.get("annual_harvest_state")
        if annual_state == "ineligible":
            return "not_productive_yet"
        if annual_state == "harvested":
            return "already_harvested"
        if annual_state == "lost":
            return "annual_yield_lost"
        if field.get("growth", 0) < 100:
            return "immature"
        if (
            current_week is not None
            and not can_harvest_crop_in_week(crop, current_week)
            and not can_late_harvest_crop_in_week(crop, current_week)
        ):
            return "outside_harvest_window"

        harvest_status = self.get_field_task_status(field, TASK_HARVESTING)
        if harvest_status == "active":
            return "harvest_active"
        if harvest_status == "waiting":
            return "harvest_waiting"

        task_vehicles = self.vehicles_for_task(TASK_HARVESTING)
        if not task_vehicles:
            return "no_combine"
        has_road_connection = False
        for vehicle in task_vehicles:
            _, parking_tile = vehicle.get_parking(world, buildings)
            if parking_tile is None:
                continue
            route, _, connected = find_field_route(world, parking_tile, field)
            has_road_connection = has_road_connection or connected
            if (
                route is not None
                and find_road_path(world, route[-1], parking_tile) is not None
            ):
                break
        else:
            return "no_route" if has_road_connection else "no_road"

        if not get_warehouses(buildings):
            return "no_warehouse"
        late_harvest = bool(
            field.get("late_harvest_active", False)
            or (
                current_week is not None
                and can_late_harvest_crop_in_week(crop, current_week)
            )
        )
        required_capacity = preview_harvest_yield(field, late_harvest)
        if (
            required_capacity is None
            or get_free_capacity(buildings) - self.reserved_harvest_capacity
            < required_capacity
        ):
            return "no_capacity"
        return None

    @staticmethod
    def get_harvest_block_message(reason):
        """Az állapotkódot a művelet és a tooltip közös rövid üzenetére fordítja."""
        return {
            "empty": "Ezen a veteményesen nincs elültetett növény.",
            "lifecycle_ended": "A növény életciklusa lejárt.",
            "not_productive_yet": "Az évelő növény még nem termőkorú.",
            "already_harvested": "Ez az évelő növény idén már le lett aratva.",
            "annual_yield_lost": "Az idei termés elveszett.",
            "immature": "A növény még nem érett.",
            "outside_harvest_window": "Most nincs aratási időszaka.",
            "harvest_active": "Aratás folyamatban.",
            "harvest_waiting": "Aratás várakozik.",
            "field_busy": "A veteményesen más járműfeladat van folyamatban.",
            "no_combine": "Az aratáshoz kombájn szükséges.",
            "no_road": "A veteményes nem érhető el útról.",
            "no_route": "Egyik kombájn sem talál útvonalat a veteményeshez.",
            "no_warehouse": "Az aratáshoz legalább egy raktár szükséges.",
            "no_capacity": "Nincs elegendő hely a raktárban.",
        }.get(reason, "Az aratás jelenleg nem indítható.")

    def start_trough_supply(
            self, world, buildings, economy, animals, trough,
            current_ticks=None):
        """Járműves feladatot indít a kattintott etető- vagy itatóvályúhoz."""
        if not validate_trough_supply(trough, animals):
            return False
        group = trough["group"]
        anchor = get_group_anchor(group)
        if anchor is None:
            return False

        is_feed = trough["type"] == "food"
        task_type = TASK_SUPPLY_FEED if is_feed else TASK_SUPPLY_WATER
        if self._has_equivalent_task(task_type, anchor):
            log("Ez a feladat már folyamatban van vagy várakozik.", "Supply")
            return False
        implement_type = VehicleType.TRAILER if is_feed else VehicleType.WATER_TANK
        source_type = "warehouse" if is_feed else "pond"
        sources = [
            building for building in buildings
            if building.get("type") == source_type
        ]
        if not sources:
            required_name = "Raktár" if is_feed else "Tó"
            log(f"Az ellátáshoz megépített {required_name} szükséges.", "Supply")
            return False

        matching_implements = [
            implement for implement in self.implements
            if implement.vehicle_type == implement_type
        ]
        implement_name = VEHICLE_TYPE_DEFINITIONS[implement_type]["name"]
        if not matching_implements:
            log(f"Az ellátáshoz {implement_name} szükséges.", "Supply")
            return False
        if not self.tractors:
            log("Az ellátáshoz Traktor szükséges.", "Supply")
            return False

        assignment = self._find_supply_assignment(
            world, buildings, group, self.tractors, matching_implements, sources,
            use_parking_start=True,
        )
        if assignment is None:
            source_name = "Raktár" if is_feed else "Tó"
            log(
                f"Nem található összefüggő útvonal a Garázs, a {source_name} "
                "és a Karám között.", "Supply",
            )
            return False
        task = FieldTask(
            field=anchor,
            task_type=task_type,
            buildings=buildings,
            target_group=group,
            animals=animals,
            trough_type=trough["type"],
            required_implement_type=implement_type,
            source_type=source_type,
            manually_initiated=trough.get("manually_initiated", True),
            creation_order=self._take_task_order(),
            loading_duration_ms=(
                FEED_LOAD_DURATION_MS if is_feed else WATER_FILL_DURATION_MS
            ),
            unloading_duration_ms=(
                FEED_UNLOAD_DURATION_MS if is_feed else WATER_UNLOAD_DURATION_MS
            ),
        )
        self.task_queue.append(task)
        self._set_waiting_statuses()
        self._dispatch_tasks(
            world, buildings, economy, current_ticks=current_ticks,
        )
        task_name = "Etetési" if is_feed else "Itatási"
        if anchor.get("vehicle_task_status") == "active":
            log(f"{task_name} feladat létrehozva.", "Supply")
        else:
            log(f"{task_name} feladat várólistára helyezve.", "Dispatcher")
        return True

    def start_processing_supply(
            self, world, buildings, plant, item_id, amount,
            current_ticks=None):
        """Saját Raktárból Traktor + Pótkocsi fuvart foglal egy üzemhez."""
        initialize_processing_plant(plant)
        amount = max(0, int(amount))
        if amount <= 0 or plant not in buildings:
            return 0
        if self._has_equivalent_task(TASK_PROCESSING_SUPPLY, plant):
            return 0
        trailers = [
            implement for implement in self.implements
            if implement.vehicle_type == VehicleType.TRAILER
        ]
        warehouses = get_warehouses(buildings)
        if not self.tractors or not trailers or not warehouses:
            return 0
        assignment = self._find_supply_assignment(
            world, buildings, [plant], self.tractors, trailers, warehouses,
            use_parking_start=True,
        )
        if assignment is None or not remove_item(buildings, item_id, amount):
            return 0
        task = FieldTask(
            field=plant,
            task_type=TASK_PROCESSING_SUPPLY,
            buildings=buildings,
            target_group=[plant],
            required_implement_type=VehicleType.TRAILER,
            source_type="warehouse",
            manually_initiated=False,
            creation_order=self._take_task_order(),
            loading_duration_ms=FEED_LOAD_DURATION_MS,
            unloading_duration_ms=FEED_UNLOAD_DURATION_MS,
            resource_reserved=True,
            resource_amount=amount,
            cargo_type=item_id,
        )
        plant["processing_in_transit"][item_id] = (
            plant["processing_in_transit"].get(item_id, 0) + amount
        )
        plant["processing_status"] = PROCESSING_STATUS_IN_TRANSIT
        self.task_queue.append(task)
        self._set_waiting_statuses()
        self._dispatch_tasks(
            world, buildings, None, current_ticks=current_ticks,
        )
        log(
            f"{amount} db alapanyag szállítása elindult a Raktárból.",
            "Processing",
        )
        return amount

    def start_processing_market_supply(
            self, world, buildings, plant, item_id, amount, economy,
            current_ticks=None):
        """Piacról vásárol, majd Traktor + Pótkocsi fuvart indít az üzemhez."""
        initialize_processing_plant(plant)
        amount = max(0, int(amount))
        if amount <= 0 or plant not in buildings:
            return 0
        if self._has_equivalent_task(TASK_PROCESSING_SUPPLY, plant):
            return 0
        trailers = [
            implement for implement in self.implements
            if implement.vehicle_type == VehicleType.TRAILER
        ]
        markets = [
            building for building in buildings
            if building.get("type") == "market"
        ]
        if not self.tractors or not trailers or not markets:
            return 0
        assignment = self._find_supply_assignment(
            world, buildings, [plant], self.tractors, trailers, markets,
            use_parking_start=True,
        )
        if assignment is None:
            return 0
        item_data = get_inventory_item_data(item_id)
        if item_data is None:
            return 0
        quote = purchase_automatically(
            economy, item_data["name"], item_data["price"], amount,
            EXPENSE_PROCESSING_INPUT, item_id,
        )
        if quote is None:
            plant["processing_status"] = PROCESSING_STATUS_NO_MONEY
            return 0
        task = FieldTask(
            field=plant,
            task_type=TASK_PROCESSING_SUPPLY,
            buildings=buildings,
            target_group=[plant],
            required_implement_type=VehicleType.TRAILER,
            source_type="market",
            manually_initiated=False,
            creation_order=self._take_task_order(),
            loading_duration_ms=FEED_LOAD_DURATION_MS,
            unloading_duration_ms=FEED_UNLOAD_DURATION_MS,
            resource_reserved=True,
            resource_amount=quote.quantity,
            cargo_type=item_id,
        )
        plant["processing_in_transit"][item_id] = (
            plant["processing_in_transit"].get(item_id, 0) + quote.quantity
        )
        plant["processing_status"] = PROCESSING_STATUS_IN_TRANSIT
        self.task_queue.append(task)
        self._set_waiting_statuses()
        self._dispatch_tasks(
            world, buildings, economy, current_ticks=current_ticks,
        )
        log(
            f"{quote.quantity} db {item_data['name']} automatikusan "
            "megvásárolva a Piacról.", "Processing",
        )
        log(f"Szállítási költség: ${quote.delivery_cost:.0f}.", "Processing")
        log(
            f"{quote.quantity} db alapanyag szállítása elindult a Piacról.",
            "Processing",
        )
        return quote.quantity

    @staticmethod
    def _find_supply_assignment(
            world, buildings, group, tractors, implements, sources,
            use_parking_start=False):
        """A legrövidebb teljes, forrást és Karámot összekötő útvonalat adja."""
        for tractor in tractors:
            parking_building, parking_tile = tractor.get_parking(world, buildings)
            if parking_building is None or parking_tile is None:
                continue
            start_tile = parking_tile if use_parking_start else (tractor.row, tractor.col)
            candidates = []
            for implement in implements:
                implement_road = find_building_parking(
                    world, implement.assigned_parking_building,
                )
                if implement_road is None:
                    continue
                route_to_implement = find_road_path(
                    world, start_tile, implement_road,
                )
                if route_to_implement is None:
                    continue
                for source in sources:
                    route_to_source, source_road = find_building_route(
                        world, implement_road, source,
                    )
                    if route_to_source is None:
                        continue
                    target_routes = []
                    for pen in group:
                        route_to_target, target_road = find_building_route(
                            world, source_road, pen,
                        )
                        if route_to_target is not None:
                            target_routes.append((
                                len(route_to_target), route_to_target, target_road,
                            ))
                    if not target_routes:
                        continue
                    _, route_to_target, target_road = min(target_routes)
                    return_route = find_road_path(
                        world, target_road, implement_road,
                    )
                    implement_to_home = find_road_path(
                        world, implement_road, parking_tile,
                    )
                    if return_route is None or implement_to_home is None:
                        continue
                    total_distance = sum(map(len, (
                        route_to_implement, route_to_source, route_to_target,
                        return_route, implement_to_home,
                    )))
                    candidates.append((
                        total_distance, implement, source, {
                            "to_implement": route_to_implement,
                            "to_source": route_to_source,
                            "source_to_target": route_to_target,
                            "return": return_route,
                            "implement_to_home": implement_to_home,
                            "implement_road": implement_road,
                        },
                    ))
            if candidates:
                _, implement, source, routes = min(
                    candidates, key=lambda item: item[0],
                )
                return tractor, implement, source, routes
        return None

    def _take_task_order(self):
        order = self.next_task_order
        self.next_task_order += 1
        return order

    def _all_tasks(self):
        return [*self.task_queue, *(
            vehicle.current_task for vehicle in self.vehicles
            if vehicle.current_task is not None
        )]

    def _has_equivalent_task(self, task_type, target):
        return any(
            task.task_type == task_type and task.field is target
            for task in self._all_tasks()
        )

    def get_field_task_status(self, field, task_type):
        """Egy konkrét Veteményes-művelet központi logikai állapotát adja."""
        task = next((
            item for item in self._all_tasks()
            if item.field is field and item.task_type == task_type
        ), None)
        return task.status if task is not None else None

    def has_pending_field_task(self, field, task_type):
        return self.get_field_task_status(field, task_type) in (
            "waiting", "active",
        )

    def _has_earlier_field_task(self, task):
        """Azonos Veteményesen a korábban kiadott feladatot engedi előre."""
        return any(
            other is not task
            and other.field is task.field
            and not (
                task.task_type == TASK_ORCHARD_HARVEST
                and other.task_type == TASK_ORCHARD_HARVEST
                and other.tree_slot != task.tree_slot
            )
            and other.creation_order < task.creation_order
            and other.status in ("waiting", "active")
            for other in self._all_tasks()
        )

    def _free_implements(self, implement_type):
        reserved = {
            vehicle.current_task.implement
            for vehicle in self.vehicles
            if vehicle.current_task is not None
            and vehicle.current_task.implement is not None
        }
        return [
            implement for implement in self.implements
            if implement.vehicle_type == implement_type
            and not implement.is_attached
            and implement not in reserved
        ]

    @staticmethod
    def _field_still_exists(world, field):
        row, col = field.get("row"), field.get("col")
        height, width = field.get("height"), field.get("width")
        if not all(isinstance(value, int) for value in (row, col, height, width)):
            return False
        return all(
            0 <= tile_row < len(world)
            and 0 <= tile_col < len(world[tile_row])
            and world[tile_row][tile_col] == FIELD
            for tile_row in range(row, row + height)
            for tile_col in range(col, col + width)
        )

    def _refresh_supply_group(self, task, buildings):
        if task.field not in buildings or task.field.get("type") != "animal_pen":
            return False
        group = next(
            (group for group in get_animal_pen_groups(buildings)
             if task.field in group),
            None,
        )
        if group is None:
            return False
        task.target_group = group
        return trough_supply_is_needed(group, task.animals, task.trough_type)

    def _task_is_valid(self, task, world, buildings):
        if task.task_type == TASK_ORCHARD_HARVEST:
            tree = get_tree_in_slot(task.field, task.tree_slot)
            return (
                task.field in buildings
                and task.field.get("type") == "orchard"
                and tree is not None
                and tree.get("type") == task.tree_type
                and is_tree_harvestable(tree)
            )
        if task.task_type == TASK_WATERING:
            return (
                any(b.get("type") == "pond" for b in buildings)
                and any(i.vehicle_type == VehicleType.WATER_TANK for i in self.implements)
                and bool(self.tractors)
                and self._field_still_exists(world, task.field)
                and task.field.get("crop") is not None
                and not task.field.get("watered", False)
                and can_water_field(task.field, include_task_status=False)
            )
        if task.task_type == TASK_FERTILIZING:
            return (
                self._field_still_exists(world, task.field)
                and can_fertilize_field(
                    task.field, include_task_status=False,
                    allow_mature=True,
                )
                and get_total_inventory(buildings).get("manure", 0)
                >= task.resource_amount
            )
        if task.task_type in (
                TASK_SUPPLY_FEED, TASK_SUPPLY_WATER, TASK_PROCESSING_SUPPLY):
            if task.task_type == TASK_PROCESSING_SUPPLY:
                return (
                    task.field in buildings
                    and task.field.get("type") == "processing_plant"
                    and any(b.get("type") == task.source_type for b in buildings)
                    and any(i.vehicle_type == VehicleType.TRAILER for i in self.implements)
                    and bool(self.tractors)
                    and task.resource_amount > 0
                )
            return (
                any(b.get("type") == task.source_type for b in buildings)
                and any(
                    i.vehicle_type == task.required_implement_type
                    for i in self.implements
                )
                and bool(self.tractors)
                and self._refresh_supply_group(task, buildings)
            )
        return True

    @staticmethod
    def _clear_task_marker(task):
        task.status = "cancelled"
        task.field.pop("vehicle_task_status", None)
        task.field.pop("vehicle_queue_position", None)
        task.field.pop("vehicle_task_type", None)

    def _discard_invalid_tasks(self, world, buildings):
        for task in tuple(self.task_queue):
            if task.task_type not in (
                    TASK_WATERING, TASK_FERTILIZING,
                    TASK_SUPPLY_FEED, TASK_SUPPLY_WATER,
                    TASK_ORCHARD_HARVEST, TASK_PROCESSING_SUPPLY):
                continue
            if self._task_is_valid(task, world, buildings):
                continue
            self.task_queue.remove(task)
            if task.task_type == TASK_PROCESSING_SUPPLY:
                cancel_processing_delivery(
                    task.field, task.cargo_type, task.resource_amount,
                )
                store_item(buildings, task.cargo_type, task.resource_amount)
            self._clear_task_marker(task)
            log("Egy időközben érvénytelenné vált feladat törölve.", "Dispatcher")

    @staticmethod
    def _apply_watering_assignment(task, assignment):
        tractor, implement, pond, routes = assignment
        task.pond = pond
        task.source_building = pond
        task.implement = implement
        task.required_vehicle_id = tractor.vehicle_id
        task.route_to_implement = routes["to_implement"]
        task.route_to_pond = routes["to_pond"]
        task.route_pond_to_field = routes["pond_to_field"]
        task.return_route = routes["return"]
        task.route_implement_to_home = routes["implement_to_home"]
        task.implement_connection_road = routes["implement_road"]
        task.pond_connection_road = routes["pond_road"]
        task.entry_tile = routes["field_entry"]
        task.connection_road = routes["field_road"]

    @staticmethod
    def _apply_supply_assignment(task, assignment):
        tractor, implement, source, routes = assignment
        task.source_building = source
        task.implement = implement
        task.required_vehicle_id = tractor.vehicle_id
        task.route_to_implement = routes["to_implement"]
        task.route_to_source = routes["to_source"]
        task.route_source_to_target = routes["source_to_target"]
        task.return_route = routes["return"]
        task.route_implement_to_home = routes["implement_to_home"]
        task.implement_connection_road = routes["implement_road"]

    def _prepare_initial_implement_task(
            self, task, vehicle, world, buildings):
        implements = self._free_implements(task.required_implement_type)
        if not implements or not vehicle.is_idle:
            return False
        if task.task_type == TASK_WATERING:
            ponds = [b for b in buildings if b.get("type") == "pond"]
            assignment = self._find_watering_assignment(
                world, buildings, task.field, [vehicle], implements, ponds,
            )
            if assignment is None:
                return False
            self._apply_watering_assignment(task, assignment)
            return True
        sources = [
            b for b in buildings if b.get("type") == task.source_type
        ]
        assignment = self._find_supply_assignment(
            world, buildings, task.target_group, [vehicle], implements, sources,
        )
        if assignment is None:
            return False
        self._apply_supply_assignment(task, assignment)
        return True

    def _dispatch_tasks(
            self, world, buildings, economy, current_ticks=None):
        """FIFO szerint az első alkalmas, megfelelő típusú járműnek ad munkát."""
        self._discard_invalid_tasks(world, buildings)
        implement_tasks = {
            TASK_WATERING, TASK_SUPPLY_FEED, TASK_SUPPLY_WATER,
            TASK_PROCESSING_SUPPLY,
        }
        while True:
            assignment = None
            for task in tuple(self.task_queue):
                if self._has_earlier_field_task(task):
                    continue
                for vehicle in self.vehicles_for_task(task.task_type):
                    if (
                        task.required_vehicle_id is not None
                        and vehicle.vehicle_id != task.required_vehicle_id
                    ):
                        continue
                    if not vehicle.can_accept_task:
                        continue
                    if (
                        task.task_type in implement_tasks
                        and not self._prepare_initial_implement_task(
                            task, vehicle, world, buildings,
                        )
                    ):
                        continue
                    if vehicle.accept_task(
                            world, buildings, task,
                            current_ticks=current_ticks):
                        assignment = (task, vehicle)
                        break
                if assignment is not None:
                    break
            if assignment is None:
                break
            task, assigned_vehicle = assignment
            self.task_queue.remove(task)
            self._set_waiting_statuses()
            task_name = TASK_NAMES.get(task.task_type, "mezőmunka")
            vehicle_name = VEHICLE_TYPE_DEFINITIONS[
                assigned_vehicle.vehicle_type
            ]["name"].lower()
            log(
                f"A(z) #{assigned_vehicle.vehicle_id} {vehicle_name} felvette "
                f"a következő {task_name} feladatot.", "Dispatcher",
            )

    def _handle_task_completion(
            self, vehicle, world, buildings, economy, current_ticks=None):
        """Ha a Dispatcher nem adott új kompatibilis munkát, hazaküldi a járművet."""
        if DEBUG_TRACTOR_DISPATCH:
            log(
                f"[Vehicle #{vehicle.vehicle_id}] "
                "awaiting_assignment -> returning_to_parking "
                f"queue={len(self.task_queue)} "
                "decision=no_available_task", "Dispatcher",
            )
        vehicle.begin_return_home(
            world, buildings, current_ticks=current_ticks,
        )
        return False

    def _set_waiting_statuses(self):
        for position, task in enumerate(self.task_queue, start=1):
            task.status = "waiting"
            task.field["vehicle_task_status"] = "waiting"
            task.field["vehicle_queue_position"] = position
            task.field["vehicle_task_type"] = task.task_type

    def update(
            self, world, buildings, economy, game_time,
            current_ticks=None):
        field_became_treatable = False
        for vehicle in self.vehicles:
            active_task = vehicle.current_task
            completed = vehicle.update(
                world, buildings, economy, game_time,
                current_ticks=current_ticks,
            )
            if (
                completed
                and active_task is not None
                and active_task.status == "completed"
                and active_task.task_type in (TASK_PLANTING, TASK_HARVESTING)
            ):
                field_became_treatable = True
            if (
                completed
                and active_task is not None
                and active_task.task_type == TASK_PLANTING
                and self.quest_event_handler is not None
            ):
                crop_event = CROP_PLANT_EVENTS.get(active_task.crop)
                if crop_event is not None:
                    self.quest_event_handler(
                        crop_event,
                        unique_key=(active_task.field["row"], active_task.field["col"]),
                    )
            if (
                completed
                and active_task is not None
                and active_task.status == "completed"
                and active_task.task_type in (TASK_WATERING, TASK_FERTILIZING)
                and active_task.manually_initiated
                and self.quest_event_handler is not None
            ):
                field_event = (
                    QUEST_EVENT_FIELD_WATERED
                    if active_task.task_type == TASK_WATERING
                    else QUEST_EVENT_FIELD_FERTILIZED
                )
                self.quest_event_handler(
                    field_event,
                    unique_key=(active_task.field["row"], active_task.field["col"]),
                )
            if (
                completed
                and active_task is not None
                and active_task.status == "completed"
                and active_task.task_type in (TASK_SUPPLY_FEED, TASK_SUPPLY_WATER)
                and active_task.manually_initiated
                and self.quest_event_handler is not None
            ):
                supply_event = (
                    QUEST_EVENT_FOOD_TROUGH_FILLED
                    if active_task.task_type == TASK_SUPPLY_FEED
                    else QUEST_EVENT_WATER_TROUGH_FILLED
                )
                self.quest_event_handler(supply_event)
            if (
                completed
                and active_task is not None
                and active_task.task_type == TASK_HARVESTING
                and self.quest_event_handler is not None
            ):
                self.quest_event_handler(QUEST_EVENT_CROP_HARVESTED)
                crop_event = CROP_HARVEST_EVENTS.get(active_task.crop)
                if crop_event is not None:
                    self.quest_event_handler(
                        crop_event,
                        unique_key=(active_task.field["row"], active_task.field["col"]),
                    )
        for implement in self.implements:
            implement.follow_towing_vehicle()
        for vehicle in self.vehicles:
            if vehicle.state == TRACTOR_SELECTING_NEXT_TASK:
                self._continue_implement_session(
                    vehicle, world, buildings,
                )
        self._dispatch_tasks(
            world, buildings, economy, current_ticks=current_ticks,
        )
        if field_became_treatable and self.field_automation_handler is not None:
            self.field_automation_handler(current_ticks)
        for vehicle in self.vehicles:
            if vehicle.state == TRACTOR_AWAITING_ASSIGNMENT:
                self._handle_task_completion(
                    vehicle, world, buildings, economy,
                    current_ticks=current_ticks,
                )

    def _prepare_chained_task(
            self, vehicle, task, world, buildings, reload_source=False):
        """Az aktuális célútról tervezi újra a felcsatolt szerelvény útját."""
        if not self._task_is_valid(task, world, buildings):
            return None
        start = (vehicle.row, vehicle.col)
        implement = vehicle.attached_implement
        implement_road = find_building_parking(
            world, implement.assigned_parking_building,
        )
        _, tractor_home = vehicle.get_parking(world, buildings)
        if implement_road is None or tractor_home is None:
            return None

        if reload_source:
            sources = [
                b for b in buildings if b.get("type") == task.source_type
            ]
            candidates = []
            for source in sources:
                route_to_source, source_road = find_building_route(
                    world, start, source,
                )
                if route_to_source is None:
                    continue
                if task.task_type == TASK_WATERING:
                    route_to_target, entry, connected = find_field_route(
                        world, source_road, task.field,
                    )
                    if not connected or route_to_target is None:
                        continue
                    target_road = route_to_target[-1]
                else:
                    target_options = []
                    for pen in task.target_group:
                        route, road = find_building_route(world, source_road, pen)
                        if route is not None:
                            target_options.append((len(route), route, road))
                    if not target_options:
                        continue
                    _, route_to_target, target_road = min(target_options)
                    entry = None
                return_route = find_road_path(world, target_road, implement_road)
                home_route = find_road_path(world, implement_road, tractor_home)
                if return_route is None or home_route is None:
                    continue
                candidates.append((len(route_to_source) + len(route_to_target), (
                    source, route_to_source, source_road, route_to_target,
                    target_road, entry, return_route, home_route,
                )))
            if not candidates:
                return None
            _, data = min(candidates, key=lambda item: item[0])
            (source, route_to_source, source_road, route_to_target,
             target_road, entry, return_route, home_route) = data
            task.source_building = source
            task.route_to_source = route_to_source
            if task.task_type == TASK_WATERING:
                task.pond = source
                task.route_to_pond = route_to_source
                task.pond_connection_road = source_road
                task.route_pond_to_field = route_to_target
                task.entry_tile = entry
                task.connection_road = target_road
            else:
                task.route_source_to_target = route_to_target
        elif task.task_type == TASK_WATERING:
            route_to_target, entry, connected = find_field_route(
                world, start, task.field,
            )
            if not connected or route_to_target is None:
                return None
            target_road = route_to_target[-1]
            task.route_pond_to_field = route_to_target
            task.entry_tile = entry
            task.connection_road = target_road
        else:
            target_options = []
            for pen in task.target_group:
                route, road = find_building_route(world, start, pen)
                if route is not None:
                    target_options.append((len(route), route, road))
            if not target_options:
                return None
            _, route_to_target, target_road = min(target_options)
            task.route_source_to_target = route_to_target

        if not reload_source:
            return_route = find_road_path(world, target_road, implement_road)
            home_route = find_road_path(world, implement_road, tractor_home)
            if return_route is None or home_route is None:
                return None
        task.implement = implement
        task.required_vehicle_id = vehicle.vehicle_id
        task.return_route = return_route
        task.route_implement_to_home = home_route
        task.implement_connection_road = implement_road
        return (
            task.route_to_pond if reload_source and task.task_type == TASK_WATERING
            else task.route_to_source if reload_source
            else task.route_pond_to_field if task.task_type == TASK_WATERING
            else task.route_source_to_target
        )

    def _continue_implement_session(self, vehicle, world, buildings):
        """Az első elérhető kompatibilis feladatot ugyanazzal a párossal folytatja."""
        current_type = vehicle.current_task.task_type
        candidate_types = [current_type]
        if current_type == TASK_WATERING:
            candidate_types.append(TASK_SUPPLY_WATER)
        elif current_type == TASK_SUPPLY_WATER:
            candidate_types.append(TASK_WATERING)

        for candidate_type in candidate_types:
            reload_source = (
                candidate_type != current_type
                or candidate_type in (TASK_SUPPLY_FEED, TASK_PROCESSING_SUPPLY)
            )
            for task in tuple(self.task_queue):
                if task.task_type != candidate_type:
                    continue
                if not self._task_is_valid(task, world, buildings):
                    self.task_queue.remove(task)
                    self._clear_task_marker(task)
                    continue
                route = self._prepare_chained_task(
                    vehicle, task, world, buildings,
                    reload_source=reload_source,
                )
                if route is None:
                    continue
                self.task_queue.remove(task)
                self._set_waiting_statuses()
                if vehicle.accept_chained_task(
                        task, route, reload_source=reload_source):
                    name = TASK_NAMES[task.task_type]
                    category = TASK_LOG_CATEGORIES[task.task_type]
                    log(f"A Traktor a következő {name} célhoz indul.", category)
                    remaining = sum(
                        queued.task_type == task.task_type
                        for queued in self.task_queue
                    )
                    if remaining:
                        log(f"Még {remaining} {name} feladat várakozik.", category)
                    return True

        category = TASK_LOG_CATEGORIES.get(current_type, "Vehicle")
        log("Nincs több kompatibilis feladat, visszatérés a Garázsba.", category)
        vehicle.finish_implement_session()
        return False

    def ensure_idle_positions(self, world, buildings):
        for vehicle in self.vehicles:
            vehicle.ensure_idle_position(world, buildings)
        for implement in self.implements:
            implement.ensure_idle_position(world, buildings)

    def draw(self, screen):
        # A vontatmány előbb rajzolódik, így a Traktor természetesen elé kerül.
        for implement in self.implements:
            implement.draw(screen)
        for vehicle in self.vehicles:
            vehicle.draw(screen)

    def synchronize_time(self, current_ticks=None):
        """Menüszünet alatt megakadályozza a mozgásidő felhalmozódását."""
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks
        for vehicle in self.vehicles:
            vehicle.last_update_ticks = now

    def demolition_block_reason(self, row, col, building=None, field=None):
        if building is not None and any(
                vehicle.assigned_parking_building is building
                for vehicle in self.managed_assets):
            if building.get("type") == "garage":
                return "A Garázs nem bontható, amíg jármű parkolóhelyet foglal benne."
        for vehicle in self.vehicles:
            reason = vehicle.demolition_block_reason(row, col, building, field)
            if reason:
                return reason
        for task in self.task_queue:
            if field is not None and task.field is field:
                return "A Veteményes várakozó járműfeladat közben nem bontható."
            if building is not None:
                if task.task_type in (TASK_SUPPLY_FEED, TASK_SUPPLY_WATER):
                    if building in (task.target_group or ()):
                        return "A Karám várakozó ellátási feladat közben nem bontható."
                    if building.get("type") == task.source_type:
                        return "Az ellátási forrás várakozó feladat közben nem bontható."
                if (task.task_type == TASK_WATERING
                        and building.get("type") == "pond"):
                    return "A Tó várakozó locsolási feladat közben nem bontható."
                if (task.task_type == TASK_PROCESSING_SUPPLY
                        and (building is task.field
                             or building.get("type") == task.source_type)):
                    return "Az épület alapanyag-szállítás közben nem bontható."
        return None

    def can_save(self, world, buildings):
        return (
            not self.task_queue
            and all(
                vehicle.can_save(world, buildings) for vehicle in self.vehicles
            )
            and all(
                implement.can_save(world, buildings)
                for implement in self.implements
            )
        )

    @staticmethod
    def _target_reference(target, fields, buildings):
        for index, field in enumerate(fields):
            if target is field:
                return {"kind": "field", "index": index}
        for index, building in enumerate(buildings):
            if target is building:
                return {"kind": "building", "index": index}
        return None

    @staticmethod
    def _resolve_target_reference(reference, fields, buildings):
        if not isinstance(reference, dict):
            return None
        collection = fields if reference.get("kind") == "field" else buildings
        index = reference.get("index")
        if not isinstance(index, int) or isinstance(index, bool):
            return None
        return collection[index] if 0 <= index < len(collection) else None

    def runtime_save_record(self, fields, buildings):
        """JSON-kompatibilis pillanatképet készít a Dispatcherről és járművekről."""
        tasks = []
        known_task_ids = set()
        for task in self._all_tasks():
            if id(task) not in known_task_ids:
                tasks.append(task)
                known_task_ids.add(id(task))
        task_ids = {id(task): index + 1 for index, task in enumerate(tasks)}
        task_records = []
        reference_fields = {
            "field", "pond", "source_building",
        }
        route_fields = {
            "route_to_implement", "route_to_source", "route_to_pond",
            "route_pond_to_field", "return_route", "route_implement_to_home",
            "route_source_to_target", "orchard_internal_path",
        }
        tuple_fields = {
            "entry_tile", "connection_road", "implement_connection_road",
            "pond_connection_road", "orchard_entry_tile",
            "harvest_approach_position",
        }
        for task in tasks:
            record = {"task_id": task_ids[id(task)]}
            for definition in dataclass_fields(FieldTask):
                name = definition.name
                value = getattr(task, name)
                if name in reference_fields:
                    value = self._target_reference(value, fields, buildings)
                elif name == "target_group":
                    value = [
                        self._target_reference(item, fields, buildings)
                        for item in (value or [])
                    ]
                elif name == "implement":
                    value = value.vehicle_id if value is not None else None
                elif name == "required_implement_type":
                    value = value.value if value is not None else None
                elif name in ("buildings", "animals"):
                    continue
                elif name in route_fields:
                    value = [list(point) for point in (value or [])]
                elif name in tuple_fields:
                    value = list(value) if value is not None else None
                record[name] = value
            task_records.append(record)

        asset_records = []
        for asset in self.managed_assets:
            record = {
                "id": asset.vehicle_id,
                "row": asset.row,
                "col": asset.col,
                "world_x": asset.world_x,
                "world_y": asset.world_y,
                "facing_direction": asset.facing_direction,
            }
            if isinstance(asset, TowableImplement):
                record.update({
                    "attached_to_id": (
                        asset.attached_to.vehicle_id
                        if asset.attached_to is not None else None
                    ),
                    "assigned_task_id": (
                        task_ids.get(id(asset.assigned_task))
                        if asset.assigned_task is not None else None
                    ),
                    "loading_location": asset.loading_location,
                    "unloading_location": asset.unloading_location,
                })
            else:
                record.update({
                    "state": asset.state,
                    "path": [list(point) for point in asset.path],
                    "next_path_index": asset.next_path_index,
                    "movement_accumulator_ms": asset.movement_accumulator_ms,
                    "current_task_id": (
                        task_ids.get(id(asset.current_task))
                        if asset.current_task is not None else None
                    ),
                    "parking_tile": (
                        list(asset.parking_tile)
                        if asset.parking_tile is not None else None
                    ),
                    "parking_building_type": asset.parking_building_type,
                    "parking_world_position": asset.parking_world_position,
                    "state_after_parking_exit": asset._state_after_parking_exit,
                    "parking_arrival_reason": asset._parking_arrival_reason,
                    "unreachable_parking_building": self._target_reference(
                        asset._unreachable_parking_building, fields, buildings,
                    ),
                    "protected_road_tiles": [
                        list(point) for point in sorted(asset.protected_road_tiles)
                    ],
                    "orchard_exit_path": [
                        list(point) for point in (asset._orchard_exit_path or [])
                    ],
                    "orchard_exit_road": (
                        list(asset._orchard_exit_road)
                        if asset._orchard_exit_road is not None else None
                    ),
                    "attached_implement_id": (
                        asset.attached_implement.vehicle_id
                        if asset.attached_implement is not None else None
                    ),
                })
            asset_records.append(record)
        return {
            "tasks": task_records,
            "queue": [task_ids[id(task)] for task in self.task_queue],
            "assets": asset_records,
            "next_task_order": self.next_task_order,
        }

    def reset_for_loaded_game(
            self, world, fields, buildings, tractor_records=None,
            animals=None, runtime_record=None):
        """Betöltéskor típushelyesen helyreállítja a parkoló járműveket."""
        self.vehicles.clear()
        self.implements.clear()
        self.task_queue.clear()
        self.next_vehicle_id = 1
        self.next_task_order = 1
        for target in [*fields, *buildings]:
            target.pop("vehicle_task_status", None)
            target.pop("vehicle_queue_position", None)
            target.pop("vehicle_task_type", None)
        records = tractor_records or []
        for record in records:
            parking = next((building for building in buildings if (
                building["type"] == record.get("parking_type")
                and building["row"] == record.get("parking_row")
                and building["col"] == record.get("parking_col")
            )), None)
            vehicle_type = record.get("vehicle_type", VehicleType.TRACTOR.value)
            vehicle = self._create_managed_asset(
                vehicle_type, parking, record.get("slot_id"),
            )
            if vehicle is None:
                continue
            vehicle.vehicle_id = record.get("id", vehicle.vehicle_id)
            if isinstance(vehicle, TowableImplement):
                definition = VEHICLE_TYPE_DEFINITIONS[vehicle.vehicle_type]
                cargo_type = record.get("cargo_type", "empty")
                vehicle.cargo_type = (
                    cargo_type
                    if cargo_type in definition.get("cargo_states", ("empty",))
                    else "empty"
                )
                vehicle.cargo_amount = max(0, record.get("cargo_amount", 0))
                if (
                    runtime_record is None
                    and
                    vehicle.vehicle_type == VehicleType.TRAILER
                    and vehicle.cargo_type != "empty"
                    and vehicle.cargo_amount > 0
                    and store_item(
                        buildings, vehicle.cargo_type, vehicle.cargo_amount,
                    )
                ):
                    vehicle.cargo_type = "empty"
                    vehicle.cargo_amount = 0
                    log(
                        "A betöltött árva Pótkocsi-rakomány visszakerült "
                        "a Raktárba.", "Load",
                    )
            self.next_vehicle_id = max(self.next_vehicle_id, vehicle.vehicle_id + 1)

        if runtime_record is not None and self._restore_runtime_record(
                runtime_record, world, fields, buildings, animals or []):
            return

        if not self.tractors:
            farmhouse = next(
                (building for building in buildings if building["type"] == "farmhouse"),
                None,
            )
            if farmhouse is not None:
                self._create_tractor(farmhouse)

        for vehicle in self.vehicles:
            vehicle.reset(fields)
            vehicle.ensure_idle_position(world, buildings)
        for implement in self.implements:
            implement.ensure_idle_position(world, buildings)

        assets_by_id = {
            asset.vehicle_id: asset for asset in self.managed_assets
        }
        for record in records:
            implement = assets_by_id.get(record.get("id"))
            towing_vehicle = assets_by_id.get(record.get("attached_to_id"))
            if (
                implement in self.implements
                and towing_vehicle in self.vehicles
            ):
                implement.attach_to(towing_vehicle)

    def _restore_runtime_record(
            self, runtime, world, fields, buildings, animals):
        """Az azonosító-alapú snapshotból visszaköti a runtime referenciákat."""
        if not isinstance(runtime, dict):
            return False
        assets = {asset.vehicle_id: asset for asset in self.managed_assets}
        task_map = {}
        route_names = {
            "route_to_implement", "route_to_source", "route_to_pond",
            "route_pond_to_field", "return_route", "route_implement_to_home",
            "route_source_to_target", "orchard_internal_path",
        }
        tuple_names = {
            "entry_tile", "connection_road", "implement_connection_road",
            "pond_connection_road", "orchard_entry_tile",
            "harvest_approach_position",
        }
        reference_names = {"field", "pond", "source_building"}
        for record in runtime.get("tasks", []):
            if not isinstance(record, dict):
                continue
            target = self._resolve_target_reference(
                record.get("field"), fields, buildings,
            )
            task_id = record.get("task_id")
            if target is None or not isinstance(task_id, int):
                continue
            task = FieldTask(field=target)
            for definition in dataclass_fields(FieldTask):
                name = definition.name
                if name not in record or name == "field":
                    continue
                value = record[name]
                if name in reference_names:
                    value = self._resolve_target_reference(value, fields, buildings)
                elif name == "target_group":
                    value = [
                        item for item in (
                            self._resolve_target_reference(ref, fields, buildings)
                            for ref in (value or [])
                        ) if item is not None
                    ]
                elif name == "implement":
                    value = assets.get(value)
                elif name == "required_implement_type":
                    try:
                        value = normalize_vehicle_type(value) if value else None
                    except (TypeError, ValueError):
                        value = None
                elif name in route_names:
                    value = [tuple(point) for point in (value or [])]
                elif name in tuple_names:
                    value = tuple(value) if value is not None else None
                setattr(task, name, value)
            task.buildings = buildings
            task.animals = animals
            task_map[task_id] = task

        runtime_assets = {
            record.get("id"): record
            for record in runtime.get("assets", [])
            if isinstance(record, dict)
        }
        for asset_id, asset in assets.items():
            record = runtime_assets.get(asset_id)
            if record is None:
                continue
            asset.row = record.get("row")
            asset.col = record.get("col")
            asset.world_x = record.get("world_x")
            asset.world_y = record.get("world_y")
            asset.facing_direction = record.get("facing_direction", "up")
            if isinstance(asset, TowableImplement):
                asset.assigned_task = task_map.get(record.get("assigned_task_id"))
                asset.loading_location = record.get("loading_location")
                asset.unloading_location = record.get("unloading_location")
                continue
            asset.state = record.get("state", "idle")
            asset.path = [tuple(point) for point in record.get("path", [])]
            asset.next_path_index = max(0, record.get("next_path_index", 0))
            asset.movement_accumulator_ms = max(
                0.0, record.get("movement_accumulator_ms", 0.0),
            )
            asset.current_task = task_map.get(record.get("current_task_id"))
            asset.parking_tile = (
                tuple(record["parking_tile"])
                if record.get("parking_tile") is not None else None
            )
            asset.parking_building_type = record.get("parking_building_type")
            asset.parking_world_position = record.get("parking_world_position")
            asset._state_after_parking_exit = record.get("state_after_parking_exit")
            asset._parking_arrival_reason = record.get("parking_arrival_reason")
            asset._unreachable_parking_building = self._resolve_target_reference(
                record.get("unreachable_parking_building"), fields, buildings,
            )
            asset.protected_road_tiles = {
                tuple(point) for point in record.get("protected_road_tiles", [])
            }
            asset._orchard_exit_path = [
                tuple(point) for point in record.get("orchard_exit_path", [])
            ] or None
            asset._orchard_exit_road = (
                tuple(record["orchard_exit_road"])
                if record.get("orchard_exit_road") is not None else None
            )
            asset.last_update_ticks = None
            asset._last_time_speed = None
            if (
                asset.state != "idle"
                and asset.current_task is None
                and asset.state != TRACTOR_RETURNING_HOME
            ):
                asset.reset(fields)
                asset.ensure_idle_position(world, buildings)

        for asset in self.managed_assets:
            if isinstance(asset, TowableImplement):
                asset.attached_to = None
            else:
                asset.attached_implement = None
        for asset_id, asset in assets.items():
            record = runtime_assets.get(asset_id, {})
            if isinstance(asset, TowableImplement):
                towing = assets.get(record.get("attached_to_id"))
                if towing in self.vehicles:
                    asset.attached_to = towing
                    towing.attached_implement = asset

        self.task_queue = deque(
            task_map[task_id]
            for task_id in runtime.get("queue", [])
            if task_id in task_map
        )
        self.next_task_order = max(
            runtime.get("next_task_order", 1),
            max((task.creation_order for task in task_map.values()), default=0) + 1,
        )
        active_count = sum(
            vehicle.current_task is not None for vehicle in self.vehicles
        )
        log(
            f"{active_count} aktív és {len(self.task_queue)} várakozó "
            "járműfeladat visszaállítva.",
            "Load",
        )
        return True

    def save_records(self):
        records = []
        for vehicle in self.managed_assets:
            building = vehicle.assigned_parking_building
            records.append({
                "id": vehicle.vehicle_id,
                "vehicle_type": vehicle.vehicle_type.value,
                "parking_type": building["type"] if building else None,
                "parking_row": building["row"] if building else None,
                "parking_col": building["col"] if building else None,
                "slot_id": vehicle.parking_slot_id,
                "attached_to_id": (
                    vehicle.attached_to.vehicle_id
                    if isinstance(vehicle, TowableImplement)
                    and vehicle.attached_to is not None
                    else None
                ),
                "cargo_type": (
                    vehicle.cargo_type
                    if isinstance(vehicle, TowableImplement)
                    else None
                ),
                "cargo_amount": (
                    vehicle.cargo_amount
                    if isinstance(vehicle, TowableImplement)
                    else 0
                ),
            })
        return records
