import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from animal_troughs import FOOD_STOCK_KEY
from economy import Economy
from feed_supply import (
    deliver_feed_cargo, get_feed_requirement, prepare_feed_supply,
)
from game_logger import get_logger


class FeedSupplyTransactionTests(unittest.TestCase):
    def setUp(self):
        self.pen = {
            "type": "animal_pen", "row": 10, "col": 10,
            "width": 4, "height": 4,
        }
        self.cattle = [
            {"type": "cattle", "pen_row": 10, "pen_col": 10},
            {"type": "cattle", "pen_row": 10, "pen_col": 10},
        ]
        self.warehouse = {
            "type": "warehouse", "row": 1, "col": 1,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {"alfalfa": 0, "corn": 0},
        }
        self.market = {
            "type": "market", "row": 1, "col": 10,
            "width": 4, "height": 3,
        }

    def test_requirement_uses_only_missing_eight_week_amount(self):
        self.pen[FOOD_STOCK_KEY] = 3
        feed_type, amount = get_feed_requirement([self.pen], self.cattle)
        self.assertEqual(feed_type, "alfalfa")
        self.assertEqual(amount, 13)

    def test_partial_inventory_buys_only_missing_alfalfa(self):
        self.pen[FOOD_STOCK_KEY] = 2
        self.warehouse["inventory"]["alfalfa"] = 3
        economy = Economy(starting_money=200)
        get_logger().reset()
        result = prepare_feed_supply(
            [self.warehouse, self.market], economy,
            [self.pen], self.cattle,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.feed_type, "alfalfa")
        self.assertEqual(result.required_amount, 14)
        self.assertEqual(result.warehouse_amount, 3)
        self.assertEqual(result.purchased_amount, 11)
        self.assertEqual(result.goods_cost, 77.0)
        self.assertEqual(result.delivery_cost, 55.0)
        self.assertEqual(result.purchase_cost, 132.0)
        self.assertEqual(self.warehouse["inventory"]["alfalfa"], 0)
        self.assertEqual(economy.money, 68.0)
        self.assertTrue(any(
            entry.category == "Market"
            and "11 db Lucerna vásárolva" in entry.message
            and "Ár: $77" in entry.message
            and "Szállítás: $55" in entry.message
            and "Összesen: $132" in entry.message
            for entry in get_logger().entries
        ))

    def test_pig_feed_uses_corn_catalog_price(self):
        pigs = [{"type": "pig", "pen_row": 10, "pen_col": 10}]
        economy = Economy(starting_money=200)
        result = prepare_feed_supply(
            [self.warehouse, self.market], economy,
            [self.pen], pigs,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.feed_type, "corn")
        self.assertEqual(result.required_amount, 8)
        self.assertEqual(result.goods_cost, 96.0)
        self.assertEqual(result.delivery_cost, 40.0)
        self.assertEqual(result.purchase_cost, 136.0)
        self.assertEqual(economy.money, 64.0)

    def test_sufficient_inventory_works_without_market(self):
        self.warehouse["inventory"]["alfalfa"] = 16
        economy = Economy(starting_money=20)
        result = prepare_feed_supply(
            [self.warehouse], economy, [self.pen], self.cattle,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.purchased_amount, 0)
        self.assertEqual(self.warehouse["inventory"]["alfalfa"], 0)
        self.assertEqual(economy.money, 20.0)

    def test_missing_market_keeps_inventory_and_money_unchanged(self):
        self.warehouse["inventory"]["alfalfa"] = 3
        economy = Economy(starting_money=100)
        result = prepare_feed_supply(
            [self.warehouse], economy, [self.pen], self.cattle,
        )
        self.assertFalse(result.success)
        self.assertEqual(self.warehouse["inventory"]["alfalfa"], 3)
        self.assertEqual(economy.money, 100.0)

    def test_insufficient_money_is_transactional(self):
        self.warehouse["inventory"]["alfalfa"] = 3
        economy = Economy(starting_money=10)
        result = prepare_feed_supply(
            [self.warehouse, self.market], economy,
            [self.pen], self.cattle,
        )
        self.assertFalse(result.success)
        self.assertEqual(self.warehouse["inventory"]["alfalfa"], 3)
        self.assertEqual(economy.money, 10.0)

    def test_delivery_never_exceeds_current_target(self):
        self.pen[FOOD_STOCK_KEY] = 14
        trailer = SimpleNamespace(cargo_type="alfalfa", cargo_amount=5)
        delivered = deliver_feed_cargo(
            [self.pen], self.cattle, trailer,
        )
        self.assertEqual(delivered, 2)
        self.assertEqual(self.pen[FOOD_STOCK_KEY], 16)
        self.assertEqual(trailer.cargo_type, "alfalfa")
        self.assertEqual(trailer.cargo_amount, 3)

    def test_sequential_transactions_cannot_spend_same_inventory_twice(self):
        second_pen = {
            "type": "animal_pen", "row": 20, "col": 20,
            "width": 4, "height": 4,
        }
        second_cattle = [
            {"type": "cattle", "pen_row": 20, "pen_col": 20},
            {"type": "cattle", "pen_row": 20, "pen_col": 20},
        ]
        self.warehouse["inventory"]["alfalfa"] = 16
        economy = Economy(starting_money=0)
        first = prepare_feed_supply(
            [self.warehouse], economy, [self.pen], self.cattle,
        )
        second = prepare_feed_supply(
            [self.warehouse], economy, [second_pen], second_cattle,
        )
        self.assertTrue(first.success)
        self.assertFalse(second.success)
        self.assertEqual(self.warehouse["inventory"]["alfalfa"], 0)
        self.assertEqual(economy.money, 0.0)


if __name__ == "__main__":
    unittest.main()
