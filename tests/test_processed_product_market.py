import os
from pathlib import Path
import sys
import unittest


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pygame

from buildings import get_marketable_item_amount, remove_marketable_item
from economy import Economy
from financial_history import INCOME_PROCESSED_PRODUCT_SALES
from game_logger import get_logger
from game_state import GameState
from inventory import get_inventory_item_data, get_marketable_item_ids
from processing import initialize_processing_plant
from screen_layout import set_screen_size
from time_system import GameTime
from ui import FinancialSummaryPanel, InfoPanel


def _processing_plant(canned_tomato):
    plant = initialize_processing_plant({
        "type": "processing_plant", "row": 4, "col": 4,
        "width": 6, "height": 5,
    })
    plant["processing_inventory"]["canned_tomato"] = canned_tomato
    return plant


class ProcessedProductMarketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_catalog_and_market_quote_use_thirty_two_dollar_price(self):
        product = get_inventory_item_data("canned_tomato")
        self.assertEqual("canned_tomato", product["product_id"])
        self.assertEqual("processed_products", product["product_category"])
        self.assertEqual(32.00, product["price"])
        self.assertTrue(product["marketable"])
        self.assertIn("canned_tomato", get_marketable_item_ids())

        plant = _processing_plant(5)
        market = {"type": "market"}
        quote = Economy().get_sale_quote([plant, market], "canned_tomato")
        self.assertEqual(5, quote["amount"])
        self.assertEqual(32.00, quote["unit_price"])
        self.assertEqual(160.00, quote["total_value"])

    def test_sale_aggregates_plants_and_records_processed_product_income(self):
        first = _processing_plant(20)
        second = _processing_plant(30)
        market = {"type": "market"}
        buildings = [first, second, market]
        economy = Economy(starting_money=0)
        get_logger().reset()

        self.assertEqual(
            50, get_marketable_item_amount(buildings, "canned_tomato"),
        )
        self.assertTrue(economy.sell_item(buildings, "canned_tomato"))
        self.assertEqual(1600.00, economy.money)
        self.assertEqual(0, first["processing_inventory"]["canned_tomato"])
        self.assertEqual(0, second["processing_inventory"]["canned_tomato"])
        self.assertEqual(
            INCOME_PROCESSED_PRODUCT_SALES,
            economy.financial_history[-1]["category"],
        )
        self.assertEqual(
            "canned_tomato", economy.financial_history[-1]["subcategory"],
        )
        self.assertTrue(any(
            entry.category == "Market"
            and "50 db paradicsomkonzerv" in entry.message.lower()
            and "$1 600" in entry.message
            for entry in get_logger().entries
        ))

    def test_partial_removal_is_fifo_and_never_makes_inventory_negative(self):
        first = _processing_plant(20)
        second = _processing_plant(30)
        buildings = [first, second]

        self.assertTrue(remove_marketable_item(
            buildings, "canned_tomato", 25,
        ))
        self.assertEqual(0, first["processing_inventory"]["canned_tomato"])
        self.assertEqual(25, second["processing_inventory"]["canned_tomato"])
        self.assertFalse(remove_marketable_item(
            buildings, "canned_tomato", 26,
        ))
        self.assertEqual(25, second["processing_inventory"]["canned_tomato"])

    def test_market_panel_and_financial_summary_include_processed_product(self):
        set_screen_size(1000, 800)
        screen = pygame.display.set_mode((1000, 800))
        font = pygame.font.Font(None, 20)
        plant = _processing_plant(20)
        market = {"type": "market"}
        economy = Economy(starting_money=0)
        state = GameState(
            [], [], [plant, market], economy, GameTime(start_ticks=0),
        )

        market_panel = InfoPanel()
        self.assertTrue(market_panel.open_for_building(market))
        market_panel.draw(screen, font, state)
        self.assertIn("canned_tomato", market_panel.market_card_rects)

        self.assertTrue(economy.sell_item(
            state.buildings, "canned_tomato",
        ))
        summary = economy.get_financial_summary(52)
        financial_panel = FinancialSummaryPanel()
        rows = financial_panel._column_rows(summary, "income")
        self.assertIn((
            "income", "Feldolgozott termékek értékesítése", 640.00,
        ), rows)
        self.assertIn(("detail", "  Paradicsomkonzerv", 640.00), rows)


if __name__ == "__main__":
    unittest.main()
