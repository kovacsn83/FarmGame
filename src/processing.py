"""Adatvezérelt feldolgozóipari receptek és heti termelési ciklus."""

from buildings import get_total_inventory, store_item
from crops import CROPS
from financial_history import EXPENSE_PROCESSING_INPUT
from game_logger import log
from inventory import get_inventory_item_name
from market_procurement import purchase_automatically


PROCESSING_STORAGE_CAPACITY = 200
PROCESSING_STATUS_READY = "ready"
PROCESSING_STATUS_WAITING = "waiting_input"
PROCESSING_STATUS_IN_TRANSIT = "in_transit"
PROCESSING_STATUS_NO_MONEY = "no_money"
PROCESSING_STATUS_FULL = "storage_full"

PROCESSING_RECIPES = {
    "canned_tomato": {
        "name": "Paradicsomkonzerv",
        "input_product": "tomato",
        "input_amount": 1,
        "output_product": "canned_tomato",
        "output_amount": 1,
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
    for item_id in ("tomato", "canned_tomato"):
        inventory.setdefault(item_id, 0)
    plant.setdefault("processing_capacity", PROCESSING_STORAGE_CAPACITY)
    plant.setdefault("active_recipe", DEFAULT_PROCESSING_RECIPE)
    plant.setdefault("processing_status", PROCESSING_STATUS_WAITING)
    plant.setdefault("processing_in_transit", {})
    plant.setdefault("processing_week", -1)
    plant.setdefault("processed_this_week", 0)
    return plant


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


def _max_batches_for_storage(plant, recipe, requested_batches):
    input_amount = recipe["input_amount"]
    output_amount = recipe["output_amount"]
    occupied = get_processing_inventory_used(plant)
    capacity = plant["processing_capacity"]
    reserved_in_transit = sum(
        max(0, int(amount))
        for amount in plant["processing_in_transit"].values()
    )
    batches = max(0, int(requested_batches))
    while batches > 0:
        resulting_occupied = occupied - batches * input_amount + batches * output_amount
        if resulting_occupied + reserved_in_transit <= capacity:
            return batches
        batches -= 1
    return 0


def produce_available(plant, elapsed_week):
    """Csak a fizikailag az üzemben lévő inputból termel a heti keretig."""
    initialize_processing_plant(plant)
    recipe = PROCESSING_RECIPES[plant["active_recipe"]]
    if plant["processing_week"] != elapsed_week:
        plant["processing_week"] = elapsed_week
        plant["processed_this_week"] = 0
    remaining_output = max(
        0, recipe["weekly_capacity"] - plant["processed_this_week"],
    )
    batches = remaining_output // recipe["output_amount"]
    inventory = plant["processing_inventory"]
    batches = min(batches, inventory.get(recipe["input_product"], 0) // recipe["input_amount"])
    batches = _max_batches_for_storage(plant, recipe, batches)
    if batches <= 0:
        if get_processing_free_capacity(plant) <= 0:
            plant["processing_status"] = PROCESSING_STATUS_FULL
        return 0
    input_used = batches * recipe["input_amount"]
    output_created = batches * recipe["output_amount"]
    inventory[recipe["input_product"]] -= input_used
    inventory[recipe["output_product"]] = (
        inventory.get(recipe["output_product"], 0) + output_created
    )
    plant["processed_this_week"] += output_created
    plant["processing_status"] = PROCESSING_STATUS_READY
    log(
        f"{output_created} db {get_inventory_item_name(recipe['output_product'])} "
        "elkészült.", "Processing",
    )
    return output_created


def _required_input_for_remaining_capacity(plant, recipe):
    remaining_output = max(0, recipe["weekly_capacity"] - plant["processed_this_week"])
    batches = remaining_output // recipe["output_amount"]
    return batches * recipe["input_amount"]


def run_weekly_processing_cycle(
        world, buildings, economy, vehicle_manager, elapsed_week,
        current_ticks=None):
    """Minden üzemet egyszer futtat, majd csak a heti hiányt szerzi be."""
    for plant in get_processing_plants(buildings):
        recipe = PROCESSING_RECIPES.get(plant.get("active_recipe"))
        if recipe is None:
            continue
        produce_available(plant, elapsed_week)
        required = _required_input_for_remaining_capacity(plant, recipe)
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
            item_data = CROPS[input_id]
            quote = purchase_automatically(
                economy, item_data["name"], item_data["price"], market_missing,
                EXPENSE_PROCESSING_INPUT, input_id,
            )
            if quote is None:
                plant["processing_status"] = PROCESSING_STATUS_NO_MONEY
            else:
                plant["processing_inventory"][input_id] = local + quote.quantity
                log(
                    f"{quote.quantity} db {item_data['name']} automatikusan "
                    "megvásárolva a Piacról.", "Processing",
                )
                log(f"Szállítási költség: ${quote.delivery_cost:.0f}.", "Processing")
                produce_available(plant, elapsed_week)
                if get_processing_in_transit(plant, input_id):
                    plant["processing_status"] = PROCESSING_STATUS_IN_TRANSIT
        elif transported:
            plant["processing_status"] = PROCESSING_STATUS_IN_TRANSIT
        elif missing:
            plant["processing_status"] = PROCESSING_STATUS_WAITING
