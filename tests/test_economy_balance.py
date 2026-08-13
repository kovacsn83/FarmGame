from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buildings import place_building
from constants import GRASS, STARTING_MONEY
from economy import Economy
from game_logger import get_logger
from inventory import get_inventory_item_data, get_marketable_item_ids


class EconomyBalanceTests(unittest.TestCase):
    def test_new_game_uses_ten_thousand_starting_money(self):
        self.assertEqual(STARTING_MONEY, 10000.00)
        self.assertEqual(Economy().money, 10000.00)

    def test_milk_sale_uses_eight_dollar_catalog_price(self):
        self.assertEqual(get_inventory_item_data("milk")["price"], 8.00)
        world = [[GRASS for _ in range(20)] for _ in range(20)]
        buildings = []
        warehouse = place_building(world, buildings, 1, 1, "warehouse")
        place_building(world, buildings, 8, 1, "market")
        warehouse["inventory"]["milk"] = 3
        economy = Economy(starting_money=0)
        self.assertTrue(economy.sell_item(buildings, "milk"))
        self.assertEqual(economy.money, 24.00)
        self.assertEqual(warehouse["inventory"]["milk"], 0)

    def test_pork_sale_uses_hundred_dollar_catalog_price(self):
        pork_data = get_inventory_item_data("pork")
        self.assertTrue(pork_data["marketable"])
        self.assertEqual(pork_data["price"], 100.00)
        self.assertIn("pork", get_marketable_item_ids())

        world = [[GRASS for _ in range(20)] for _ in range(20)]
        buildings = []
        warehouse = place_building(world, buildings, 1, 1, "warehouse")
        place_building(world, buildings, 8, 1, "market")
        warehouse["inventory"]["pork"] = 10
        economy = Economy(starting_money=0)
        get_logger().reset()

        self.assertTrue(economy.sell_item(buildings, "pork"))
        self.assertEqual(economy.money, 1000.00)
        self.assertEqual(warehouse["inventory"]["pork"], 0)
        self.assertTrue(any(
            entry.category == "Economy"
            and "10 db sertéshús" in entry.message
            and "$1 000" in entry.message
            for entry in get_logger().entries
        ))

    def test_beef_sale_uses_hundred_twenty_five_dollar_catalog_price(self):
        beef_data = get_inventory_item_data("beef")
        self.assertTrue(beef_data["marketable"])
        self.assertEqual(beef_data["price"], 125.00)
        self.assertIn("beef", get_marketable_item_ids())

        world = [[GRASS for _ in range(20)] for _ in range(20)]
        buildings = []
        warehouse = place_building(world, buildings, 1, 1, "warehouse")
        place_building(world, buildings, 8, 1, "market")
        warehouse["inventory"]["beef"] = 10
        economy = Economy(starting_money=0)

        self.assertTrue(economy.sell_item(buildings, "beef"))
        self.assertEqual(economy.money, 1250.00)
        self.assertEqual(warehouse["inventory"]["beef"], 0)

    def test_manure_sale_uses_three_dollar_catalog_price(self):
        manure_data = get_inventory_item_data("manure")
        self.assertTrue(manure_data["marketable"])
        self.assertEqual(manure_data["price"], 3.00)
        self.assertIn("manure", get_marketable_item_ids())

        world = [[GRASS for _ in range(20)] for _ in range(20)]
        buildings = []
        warehouse = place_building(world, buildings, 1, 1, "warehouse")
        place_building(world, buildings, 8, 1, "market")
        warehouse["inventory"]["manure"] = 15
        economy = Economy(starting_money=0)
        get_logger().reset()

        self.assertTrue(economy.sell_item(buildings, "manure"))
        self.assertEqual(economy.money, 45.00)
        self.assertEqual(warehouse["inventory"]["manure"], 0)
        self.assertTrue(any(
            entry.category == "Economy"
            and "15 db trágya" in entry.message
            and "$45" in entry.message
            for entry in get_logger().entries
        ))


if __name__ == "__main__":
    unittest.main()
