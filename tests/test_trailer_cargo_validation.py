import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from processing import PROCESSING_RECIPES
from save_system import _validate_vehicles
from vehicle_types import VEHICLE_TYPE_DEFINITIONS, VehicleType


class TrailerCargoValidationTests(unittest.TestCase):
    def document(self, cargo, amount=6):
        return {"buildings": [{"type": "garage", "row": 0, "col": 0,
                                "width": 4, "height": 4}],
                "tractors": [{"id": 1, "vehicle_type": "tractor",
                               "parking_type": "garage", "parking_row": 0,
                               "parking_col": 0, "slot_id": 0},
                              {"id": 2, "vehicle_type": "trailer",
                               "parking_type": "garage", "parking_row": 0,
                               "parking_col": 0, "slot_id": 1, "attached_to_id": 1,
                               "cargo_type": cargo, "cargo_amount": amount}]}

    def test_all_current_processing_inputs_are_valid_trailer_cargo(self):
        supported = VEHICLE_TYPE_DEFINITIONS[VehicleType.TRAILER]["cargo_states"]
        for recipe in PROCESSING_RECIPES.values():
            with self.subTest(recipe=recipe["input_product"]):
                self.assertIn(recipe["input_product"], supported)

    def test_plum_and_goat_milk_pass_saved_vehicle_validation(self):
        for cargo in ("plum", "goat_milk", "wheat", "corn"):
            with self.subTest(cargo=cargo):
                self.assertTrue(_validate_vehicles(self.document(cargo)))

    def test_invalid_cargo_and_amount_are_still_rejected(self):
        for cargo, amount in (("unknown", 6), ("plum", -1),
                              ("plum", 1.5), ("empty", 6)):
            with self.subTest(cargo=cargo, amount=amount):
                self.assertFalse(_validate_vehicles(self.document(cargo, amount)))


if __name__ == "__main__":
    unittest.main()
