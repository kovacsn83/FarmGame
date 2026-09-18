from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from inventory import get_grouped_warehouse_inventory


class WarehouseInventoryOrderTests(unittest.TestCase):
    def test_inventory_is_grouped_in_thematic_display_order(self):
        inventory = {
            "plum": 6,
            "milk": 4,
            "pork": 3,
            "tomato": 2,
            "wheat": 1,
            "beef": 5,
            "egg": 7,
            "apple": 8,
        }

        groups = get_grouped_warehouse_inventory(inventory)

        self.assertEqual(
            [[item_id for item_id, _ in group] for group in groups],
            [
                ["wheat", "tomato"],
                ["beef", "pork"],
                ["milk", "egg"],
                ["apple", "plum"],
            ],
        )

    def test_empty_items_are_hidden_and_unknown_items_are_kept(self):
        groups = get_grouped_warehouse_inventory({
            "wheat": 0,
            "future_product": 9,
        })

        self.assertEqual(groups, [[("future_product", 9)]])


if __name__ == "__main__":
    unittest.main()
