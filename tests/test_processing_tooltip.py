import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from processing import (
    get_processing_tooltip_lines, initialize_processing_plant,
    select_processing_recipe,
)
from progress_tooltips import find_timed_object_tooltip


class ProcessingTooltipTests(unittest.TestCase):
    def _plant(self, row=4, col=6):
        return initialize_processing_plant({
            "type": "processing_plant",
            "row": row,
            "col": col,
            "width": 6,
            "height": 5,
        })

    def _find(self, row, col, buildings):
        return find_timed_object_tooltip(
            row, col, [], [], {}, buildings=buildings,
        )

    def test_hover_lines_show_selected_product_and_shared_storage_usage(self):
        plant = self._plant()
        plant["processing_inventory"]["tomato"] = 10
        plant["processing_inventory"]["canned_tomato"] = 20
        plant["processing_inventory"]["cheese"] = 5
        self.assertTrue(select_processing_recipe(plant, "cheese"))

        self.assertEqual(self._find(6, 8, [plant]), [
            "Feldolgozó üzem",
            "Termék:",
            "Sajt",
            "Raktár:",
            "35 / 200",
        ])

    def test_no_selected_recipe_has_explicit_text(self):
        plant = self._plant()
        self.assertTrue(select_processing_recipe(plant, "canned_tomato"))
        self.assertIsNone(plant["active_recipe"])
        self.assertIn("Nincs kiválasztva", get_processing_tooltip_lines(plant))

    def test_each_processing_plant_reports_its_own_data(self):
        first = self._plant(2, 2)
        first["processing_inventory"]["canned_tomato"] = 7
        second = self._plant(12, 20)
        self.assertTrue(select_processing_recipe(second, "cheese"))
        second["processing_inventory"]["milk"] = 13

        self.assertEqual(self._find(3, 3, [first, second])[-1], "7 / 200")
        second_lines = self._find(13, 21, [first, second])
        self.assertIn("Sajt", second_lines)
        self.assertEqual(second_lines[-1], "13 / 200")

    def test_tooltip_disappears_outside_processing_plant(self):
        self.assertIsNone(self._find(0, 0, [self._plant()]))


if __name__ == "__main__":
    unittest.main()
