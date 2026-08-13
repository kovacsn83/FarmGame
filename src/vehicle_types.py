from enum import Enum

from constants import (
    COMBINE_PURCHASE_PRICE, TRAILER_PURCHASE_PRICE,
    TRACTOR_PURCHASE_PRICE, WATER_TANK_PURCHASE_PRICE,
)


class VehicleType(str, Enum):
    """A Vehicle rendszer által támogatott járműtípusok."""

    TRACTOR = "tractor"
    COMBINE = "combine"
    WATER_TANK = "water_tank"
    TRAILER = "trailer"


VEHICLE_TYPE_DEFINITIONS = {
    VehicleType.TRACTOR: {
        "name": "Traktor",
        "purchase_price": TRACTOR_PURCHASE_PRICE,
        "accepts_field_tasks": True,
        "supported_tasks": (
            "plant", "fertilize", "watering",
            "supply_feed", "supply_water",
        ),
        "self_propelled": True,
        "towable": False,
    },
    VehicleType.COMBINE: {
        "name": "Kombájn",
        "purchase_price": COMBINE_PURCHASE_PRICE,
        "accepts_field_tasks": True,
        "supported_tasks": ("harvest",),
        "self_propelled": True,
        "towable": False,
    },
    VehicleType.WATER_TANK: {
        "name": "Locsolótartály",
        "purchase_price": WATER_TANK_PURCHASE_PRICE,
        "accepts_field_tasks": False,
        "supported_tasks": (),
        "self_propelled": False,
        "towable": True,
        "compatible_towing_types": (VehicleType.TRACTOR,),
        "category": "towable",
        "renderer_type": "water_tank",
        "parking_slots": 1,
        "cargo_states": ("empty",),
        "future_supported_tasks": (),
    },
    VehicleType.TRAILER: {
        "name": "Pótkocsi",
        "purchase_price": TRAILER_PURCHASE_PRICE,
        "accepts_field_tasks": False,
        "supported_tasks": (),
        "self_propelled": False,
        "towable": True,
        "compatible_towing_types": (VehicleType.TRACTOR,),
        "category": "towable",
        "renderer_type": "trailer",
        "parking_slots": 1,
        "cargo_states": ("empty", "alfalfa", "corn"),
        # A későbbi Dispatcher-integrációhoz csak leíró előkészítés.
        "future_supported_tasks": (
            "manure_transport", "feed_transport",
        ),
        "future_role": "Trágya és takarmány szállítására használható.",
    },
}


def normalize_vehicle_type(vehicle_type):
    """Régi vagy szöveges típusértékből biztonságos VehicleType értéket készít."""
    if isinstance(vehicle_type, VehicleType):
        return vehicle_type
    try:
        return VehicleType(vehicle_type)
    except (TypeError, ValueError):
        return None
