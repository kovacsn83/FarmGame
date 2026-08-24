"""Adatvezérelt feldolgozóipari receptek és heti termelési ciklus."""

import math

from buildings import BUILDING_TYPES, get_total_inventory, store_item
from game_logger import log
from inventory import get_inventory_item_data, get_inventory_item_name


PROCESSING_STORAGE_CAPACITY = 200
PROCESSING_STATUS_READY = "ready"
PROCESSING_STATUS_WAITING = "waiting_input"
PROCESSING_STATUS_IN_TRANSIT = "in_transit"
PROCESSING_STATUS_NO_MONEY = "no_money"
PROCESSING_STATUS_FULL = "storage_full"
PROCESSING_STATUS_PROCESSING = "processing"
PROCESSING_STATUS_STOPPED = "stopped"

PROCESSING_RECIPES = {
    "canned_tomato": {
        "name": "Paradicsomkonzerv",
        "input_product": "tomato",
        "input_amount": 1,
        "output_product": "canned_tomato",
        "output_amount": 1,
        "weekly_capacity": 5,
    },
    "cheese": {
        "name": "Sajt",
        "input_product": "milk",
        "input_amount": 5,
        "output_product": "cheese",
        "output_amount": 5,
        "weekly_capacity": 5,
    },
    "apple_juice": {
        "name": "Almalé",
        "input_product": "apple",
        "input_amount": 5,
        "output_product": "apple_juice",
        "output_amount": 5,
        "weekly_capacity": 5,
    },
}
DEFAULT_PROCESSING_RECIPE = "canned_tomato"


def initialize_processing_plant(plant):
    """Új és korábbi mentésből érkező üzemhez biztonságos alapállapotot ad."""
    plant.setdefault("processing_inventory", {})
    inventory = plant["processing_inventory"]
    if not isinstance(inventory, dict):
        inventory = {}
        plant["processing_inventory"] = inventory
    inventory_item_ids = {
        item_id
        for recipe in PROCESSING_RECIPES.values()
        for item_id in (recipe["input_product"], recipe["output_product"])
    }
    for item_id in inventory_item_ids:
        inventory.setdefault(item_id, 0)
    plant.setdefault("processing_capacity", PROCESSING_STORAGE_CAPACITY)
    plant.setdefault("active_recipe", DEFAULT_PROCESSING_RECIPE)
    plant.setdefault("processing_status", PROCESSING_STATUS_WAITING)
    plant.setdefault("processing_in_transit", {})
    plant.setdefault("processing_week", -1)
    plant.setdefault("processed_this_week", 0)
    plant.setdefault("processing_batch", None)
    return plant


def get_processing_recipe_ids(plant):
    """Az adott üzem által választható recepteket katalógussorrendben adja."""
    initialize_processing_plant(plant)
    configured_ids = BUILDING_TYPES["processing_plant"].get(
        "recipes", tuple(PROCESSING_RECIPES),
    )
    return tuple(
        recipe_id for recipe_id in configured_ids
        if recipe_id in PROCESSING_RECIPES
    )


def get_processing_output_ids(plant):
    """Az üzem összes lehetséges késztermékét ismétlés nélkül adja vissza."""
    return tuple(dict.fromkeys(
        PROCESSING_RECIPES[recipe_id]["output_product"]
        for recipe_id in get_processing_recipe_ids(plant)
    ))


def get_processing_tooltip_lines(plant):
    """A Feldolgozó üzem rövid, később további sorokkal bővíthető nézetét adja."""
    initialize_processing_plant(plant)
    recipe = PROCESSING_RECIPES.get(plant.get("active_recipe"))
    product_name = recipe["name"] if recipe is not None else "Nincs kiválasztva"
    return [
        "Feldolgozó üzem",
        "Termék:",
        product_name,
        "Raktár:",
        f"{get_processing_inventory_used(plant)} / {plant['processing_capacity']}",
    ]


def select_processing_recipe(plant, recipe_id):
    """Kapcsolja a következő adag receptjét a futó gyártás megszakítása nélkül."""
    initialize_processing_plant(plant)
    if recipe_id not in get_processing_recipe_ids(plant):
        return False
    if plant.get("active_recipe") == recipe_id:
        plant["active_recipe"] = None
        plant["processing_status"] = PROCESSING_STATUS_STOPPED
    else:
        plant["active_recipe"] = recipe_id
        plant["processing_status"] = (
            PROCESSING_STATUS_PROCESSING
            if plant.get("processing_batch") is not None
            else PROCESSING_STATUS_WAITING
        )
    return True


def get_processing_plants(buildings):
    return [
        initialize_processing_plant(building)
        for building in buildings
        if building.get("type") == "processing_plant"
    ]


def get_processing_inventory_used(plant):
    initialize_processing_plant(plant)
    return sum(max(0, int(amount)) for amount in plant["processing_inventory"].values())


def get_processing_free_capacity(plant):
    initialize_processing_plant(plant)
    return max(0, plant["processing_capacity"] - get_processing_inventory_used(plant))


def get_processing_in_transit(plant, item_id):
    initialize_processing_plant(plant)
    return max(0, int(plant["processing_in_transit"].get(item_id, 0)))


def receive_processing_delivery(plant, item_id, amount):
    """A fizikailag célba ért rakományt az üzemi készletbe helyezi."""
    initialize_processing_plant(plant)
    amount = min(max(0, int(amount)), get_processing_free_capacity(plant))
    if amount <= 0:
        return 0
    inventory = plant["processing_inventory"]
    inventory[item_id] = inventory.get(item_id, 0) + amount
    pending = get_processing_in_transit(plant, item_id)
    plant["processing_in_transit"][item_id] = max(0, pending - amount)
    plant["processing_status"] = PROCESSING_STATUS_READY
    start_processing_batch(plant)
    return amount


def cancel_processing_delivery(plant, item_id, amount):
    """Megszünteti egy meghiúsult fuvar úton lévő nyilvántartását."""
    initialize_processing_plant(plant)
    pending = get_processing_in_transit(plant, item_id)
    plant["processing_in_transit"][item_id] = max(0, pending - max(0, int(amount)))


def refund_processing_delivery(buildings, plant, item_id, amount):
    """Meghiúsult saját fuvar foglalását visszaadja a központi Raktárnak."""
    amount = max(0, int(amount))
    cancel_processing_delivery(plant, item_id, amount)
    return amount == 0 or store_item(buildings, item_id, amount)


def _recipe_unit_amounts(recipe):
    """A recept arányát legkisebb egész gyártási egységre egyszerűsíti."""
    divisor = math.gcd(recipe["input_amount"], recipe["output_amount"])
    return (
        recipe["input_amount"] // divisor,
        recipe["output_amount"] // divisor,
    )


def _max_units_for_storage(plant, recipe, requested_units):
    input_amount, output_amount = _recipe_unit_amounts(recipe)
    occupied = get_processing_inventory_used(plant)
    capacity = plant["processing_capacity"]
    reserved_in_transit = sum(
        max(0, int(amount))
        for amount in plant["processing_in_transit"].values()
    )
    pending_output = sum(
        max(0, int(amount))
        for amount in (plant.get("processing_batch") or {}).get("outputs", {}).values()
    )
    units = max(0, int(requested_units))
    while units > 0:
        resulting_occupied = occupied - units * input_amount + units * output_amount
        if resulting_occupied + reserved_in_transit + pending_output <= capacity:
            return units
        units -= 1
    return 0


def start_processing_batch(plant, elapsed_week=None):
    """A rendelkezésre álló inputot lefoglalja egy következő heti adaghoz."""
    initialize_processing_plant(plant)
    if elapsed_week is not None:
        plant["processing_week"] = elapsed_week
    if plant.get("processing_batch") is not None:
        plant["processing_status"] = (
            PROCESSING_STATUS_STOPPED
            if plant.get("active_recipe") is None
            else PROCESSING_STATUS_PROCESSING
        )
        return 0
    if plant.get("active_recipe") is None:
        plant["processing_status"] = PROCESSING_STATUS_STOPPED
        return 0
    recipe = PROCESSING_RECIPES[plant["active_recipe"]]
    unit_input, unit_output = _recipe_unit_amounts(recipe)
    units = recipe["weekly_capacity"] // unit_output
    inventory = plant["processing_inventory"]
    units = min(
        units,
        inventory.get(recipe["input_product"], 0) // unit_input,
    )
    units = _max_units_for_storage(plant, recipe, units)
    if units <= 0:
        if get_processing_free_capacity(plant) <= 0:
            plant["processing_status"] = PROCESSING_STATUS_FULL
        return 0
    input_used = units * unit_input
    output_scheduled = units * unit_output
    inventory[recipe["input_product"]] -= input_used
    plant["processing_batch"] = {
        "recipe_id": plant["active_recipe"],
        "started_week": plant["processing_week"],
        "inputs": {recipe["input_product"]: input_used},
        "outputs": {recipe["output_product"]: output_scheduled},
    }
    plant["processing_status"] = PROCESSING_STATUS_PROCESSING
    log(
        f"{output_scheduled} db {get_inventory_item_name(recipe['output_product'])} "
        "gyártása elindult.", "Processing",
    )
    return output_scheduled


def complete_processing_batch(plant, elapsed_week):
    """A korábbi héten elindított adagot egyszer írja jóvá késztermékként."""
    initialize_processing_plant(plant)
    batch = plant.get("processing_batch")
    if not batch or batch.get("started_week", elapsed_week) >= elapsed_week:
        return 0
    outputs = batch.get("outputs", {})
    output_total = sum(max(0, int(amount)) for amount in outputs.values())
    if output_total > get_processing_free_capacity(plant):
        plant["processing_status"] = PROCESSING_STATUS_FULL
        return 0
    for item_id, amount in outputs.items():
        plant["processing_inventory"][item_id] = (
            plant["processing_inventory"].get(item_id, 0) + amount
        )
    plant["processing_batch"] = None
    plant["processed_this_week"] = output_total
    plant["processing_status"] = PROCESSING_STATUS_READY
    if output_total:
        output_names = ", ".join(
            f"{amount} db {get_inventory_item_name(item_id)}"
            for item_id, amount in outputs.items()
        )
        log(f"{output_names} elkészült.", "Processing")
    return output_total


def _required_input_for_capacity(recipe):
    unit_input, unit_output = _recipe_unit_amounts(recipe)
    units = recipe["weekly_capacity"] // unit_output
    return units * unit_input


def run_weekly_processing_cycle(
        world, buildings, economy, vehicle_manager, elapsed_week,
        current_ticks=None):
    """Minden üzemet egyszer futtat, majd csak a heti hiányt szerzi be."""
    for plant in get_processing_plants(buildings):
        plant["processing_week"] = elapsed_week
        plant["processed_this_week"] = 0
        complete_processing_batch(plant, elapsed_week)
        recipe = PROCESSING_RECIPES.get(plant.get("active_recipe"))
        if recipe is None:
            plant["processing_status"] = PROCESSING_STATUS_STOPPED
            continue
        start_processing_batch(plant, elapsed_week)
        if plant.get("processing_batch") is not None:
            continue
        required = _required_input_for_capacity(recipe)
        input_id = recipe["input_product"]
        local = plant["processing_inventory"].get(input_id, 0)
        in_transit = get_processing_in_transit(plant, input_id)
        missing = max(0, required - local - in_transit)
        reserved_space = sum(
            max(0, int(amount))
            for amount in plant["processing_in_transit"].values()
        )
        available_space = max(0, get_processing_free_capacity(plant) - reserved_space)
        missing = min(missing, available_space)
        if missing <= 0:
            plant["processing_status"] = (
                PROCESSING_STATUS_IN_TRANSIT if in_transit
                else PROCESSING_STATUS_FULL if required > local
                else PROCESSING_STATUS_READY
            )
            continue

        log(
            f"{missing} db {get_inventory_item_name(input_id)} igény a "
            "Feldolgozó üzemben.", "Processing",
        )
        warehouse_available = get_total_inventory(buildings).get(input_id, 0)
        warehouse_request = min(missing, warehouse_available)
        transported = 0
        if warehouse_request > 0:
            transported = vehicle_manager.start_processing_supply(
                world, buildings, plant, input_id, warehouse_request,
                current_ticks=current_ticks,
            )
            missing -= transported

        # A saját raktárban lévő, de útvonal/jármű hiányában el nem indítható
        # mennyiséget nem kerüljük meg felesleges piaci vásárlással.
        market_missing = max(0, missing - max(0, warehouse_request - transported))
        market_missing = min(market_missing, get_processing_free_capacity(plant))
        if market_missing > 0:
            item_data = get_inventory_item_data(input_id)
            if item_data is None:
                plant["processing_status"] = PROCESSING_STATUS_WAITING
                continue
            transported = vehicle_manager.start_processing_market_supply(
                world, buildings, plant, input_id, market_missing, economy,
                current_ticks=current_ticks,
            )
            if transported > 0:
                plant["processing_status"] = PROCESSING_STATUS_IN_TRANSIT
            elif plant.get("processing_status") != PROCESSING_STATUS_NO_MONEY:
                plant["processing_status"] = PROCESSING_STATUS_WAITING
        elif transported:
            plant["processing_status"] = PROCESSING_STATUS_IN_TRANSIT
        elif missing:
            plant["processing_status"] = PROCESSING_STATUS_WAITING
