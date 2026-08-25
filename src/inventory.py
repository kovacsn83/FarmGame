from crops import CROPS
from financial_history import (
    INCOME_CROP_SALES, INCOME_LIVESTOCK_SALES, INCOME_ORCHARD_SALES,
    INCOME_PROCESSED_PRODUCT_SALES,
)


# Az állati termékek a közös raktárkapacitást és az adatvezérelt piaci szabályt használják.
PRODUCTS = {
    "mayonnaise": {
        "product_id": "mayonnaise",
        "name": "Majonéz",
        "price": 12.00,
        "product_category": "processed_products",
        "income_category": INCOME_PROCESSED_PRODUCT_SALES,
        "inventory_source": "processing_plant",
        "marketable": True,
        "restaurant_sellable": True,
    },
    "apple_juice": {
        "product_id": "apple_juice",
        "name": "Almalé",
        "price": 20.00,
        "product_category": "processed_products",
        "income_category": INCOME_PROCESSED_PRODUCT_SALES,
        "inventory_source": "processing_plant",
        "marketable": True,
        "restaurant_sellable": True,
    },
    "cheese": {
        "product_id": "cheese",
        "name": "Sajt",
        "price": 16.00,
        "product_category": "processed_products",
        "income_category": INCOME_PROCESSED_PRODUCT_SALES,
        "inventory_source": "processing_plant",
        "marketable": True,
        "restaurant_sellable": True,
    },
    "canned_tomato": {
        "product_id": "canned_tomato",
        "name": "Paradicsomkonzerv",
        "price": 32.00,
        "product_category": "processed_products",
        "income_category": INCOME_PROCESSED_PRODUCT_SALES,
        "inventory_source": "processing_plant",
        "marketable": True,
        "restaurant_sellable": True,
    },
    "apple": {
        "name": "Alma",
        "marketable": True,
        "price": 10.00,
        "income_category": INCOME_ORCHARD_SALES,
    },
    "cherry": {
        "name": "Cseresznye",
        "marketable": True,
        "price": 20.00,
        "income_category": INCOME_ORCHARD_SALES,
    },
    "milk": {
        "name": "Tej",
        "marketable": True,
        "price": 8.00,
        "income_category": INCOME_LIVESTOCK_SALES,
    },
    "manure": {
        "name": "Trágya",
        "marketable": True,
        "price": 3.00,
        "income_category": INCOME_LIVESTOCK_SALES,
    },
    "pork": {
        "name": "Sertéshús",
        "marketable": True,
        "price": 100.00,
        "income_category": INCOME_LIVESTOCK_SALES,
    },
    "beef": {
        "name": "Marhahús",
        "marketable": True,
        "price": 125.00,
        "income_category": INCOME_LIVESTOCK_SALES,
    },
    "egg": {
        "name": "Tojás",
        "marketable": True,
        "price": 6.00,
        "income_category": INCOME_LIVESTOCK_SALES,
    },
    "chicken_meat": {
        "name": "Csirkehús",
        "marketable": True,
        "price": 60.00,
        "income_category": INCOME_LIVESTOCK_SALES,
    },
}


def get_inventory_item_ids():
    """A raktárban kezelhető összes elem azonosítóit adja vissza."""
    return (*CROPS, *PRODUCTS)


def get_inventory_item_name(item_id):
    """Központilag feloldja a termények és állati termékek megjelenített nevét."""
    if item_id in CROPS:
        return CROPS[item_id]["name"]
    if item_id in PRODUCTS:
        return PRODUCTS[item_id]["name"]
    return item_id.replace("_", " ").capitalize()


def is_inventory_item(item_id):
    return item_id in CROPS or item_id in PRODUCTS


def get_inventory_item_data(item_id):
    """Egységes leírást ad növényhez és más raktári termékhez."""
    if item_id in CROPS:
        return {
            **CROPS[item_id],
            "marketable": True,
            "income_category": INCOME_CROP_SALES,
        }
    return PRODUCTS.get(item_id)


def get_marketable_item_ids():
    """A katalógus sorrendjében visszaadja a Piacon eladható elemeket."""
    return tuple(
        item_id
        for item_id in get_inventory_item_ids()
        if get_inventory_item_data(item_id).get("marketable", False)
    )
