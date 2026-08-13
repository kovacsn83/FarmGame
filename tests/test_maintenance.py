from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buildings import BUILDING_TYPES, get_building_maintenance_base
from constants import ROAD, ROAD_BUILD_COST
from economy import Economy
from game_rules import FIELD_TYPES
from maintenance import (
    ANNUAL_MAINTENANCE_RATE, MAINTENANCE_WEEKS_PER_YEAR,
    calculate_annual_maintenance, calculate_weekly_maintenance,
    format_annual_maintenance_rate,
)
from vehicle_manager import VehicleManager
from vehicle_types import VEHICLE_TYPE_DEFINITIONS, VehicleType


class MaintenanceSystemTests(unittest.TestCase):
    def test_central_formula_uses_ten_percent_over_fifty_two_weeks(self):
        self.assertEqual(ANNUAL_MAINTENANCE_RATE, 0.10)
        self.assertEqual(MAINTENANCE_WEEKS_PER_YEAR, 52)
        self.assertEqual(calculate_annual_maintenance(1000), 100.0)
        self.assertAlmostEqual(
            calculate_weekly_maintenance(1000), 100.0 / 52,
        )
        self.assertEqual(format_annual_maintenance_rate(), "10%")

    def test_catalogs_do_not_store_manual_weekly_costs(self):
        for definition in (
                *BUILDING_TYPES.values(), *FIELD_TYPES.values(),
                *VEHICLE_TYPE_DEFINITIONS.values()):
            self.assertNotIn("weekly_cost", definition)

    def test_every_building_and_field_uses_its_purchase_price(self):
        buildings = [
            {
                "type": item_id,
                **({"farmhouse_level": 1} if item_id == "farmhouse" else {}),
            }
            for item_id in BUILDING_TYPES
        ]
        fields = [{"field_type": item_id} for item_id in FIELD_TYPES]
        expected = sum(
            calculate_weekly_maintenance(get_building_maintenance_base(item))
            for item in buildings
        ) + sum(
            calculate_weekly_maintenance(item["build_cost"])
            for item in FIELD_TYPES.values()
        )
        actual = Economy(0).calculate_weekly_costs(
            [[0]], buildings, fields, vehicle_weekly_cost=0,
        )
        self.assertAlmostEqual(actual, expected)
        self.assertGreater(
            calculate_weekly_maintenance(FIELD_TYPES["field_4x4"]["build_cost"]),
            0,
        )

    def test_every_vehicle_uses_its_purchase_price(self):
        manager = VehicleManager()
        manager.vehicles = [
            SimpleNamespace(vehicle_type=VehicleType.TRACTOR),
            SimpleNamespace(vehicle_type=VehicleType.COMBINE),
            SimpleNamespace(vehicle_type=VehicleType.FRUIT_HARVESTER),
        ]
        manager.implements = [
            SimpleNamespace(vehicle_type=VehicleType.WATER_TANK),
            SimpleNamespace(vehicle_type=VehicleType.TRAILER),
        ]
        expected = sum(
            calculate_weekly_maintenance(
                VEHICLE_TYPE_DEFINITIONS[vehicle_type]["purchase_price"]
            )
            for vehicle_type in VehicleType
        )
        self.assertAlmostEqual(manager.weekly_cost, expected)

    def test_road_cost_and_weekly_charge_use_the_same_rule(self):
        economy = Economy(100)
        expected = calculate_weekly_maintenance(ROAD_BUILD_COST)
        charged = economy.apply_weekly_costs(
            [[ROAD]], [], vehicle_weekly_cost=0,
        )
        self.assertAlmostEqual(charged, expected)
        self.assertAlmostEqual(economy.money, 100 - expected)


if __name__ == "__main__":
    unittest.main()
