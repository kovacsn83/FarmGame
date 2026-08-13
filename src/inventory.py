from crops import CROPS


# Az állati termékek a közös raktárkapacitást és az adatvezérelt piaci szabályt használják.
PRODUCTS = {
    "apple": {
        "name": "Alma",
        "marketable": False,
    },
    "milk": {
        "name": "Tej",
        "marketable": True,
        "price": 8.00,
    },
    "manure": {
        "name": "Trágya",
        "marketable": True,
        "price": 3.00,
    },
    "pork": {
        "name": "Sertéshús",
        "marketable": True,
        "price": 100.00,
    },
    "beef": {
        "name": "Marhahús",
        "marketable": True,
        "price": 125.00,
    },
    "egg": {
        "name": "Tojás",
        "marketable": True,
        "price": 6.00,
    },
    "chicken_meat": {
        "name": "Csirkehús",
        "marketable": True,
        "price": 50.00,
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
        }
    return PRODUCTS.get(item_id)


def get_marketable_item_ids():
    """A katalógus sorrendjében visszaadja a Piacon eladható elemeket."""
    return tuple(
        item_id
        for item_id in get_inventory_item_ids()
        if get_inventory_item_data(item_id).get("marketable", False)
    )
