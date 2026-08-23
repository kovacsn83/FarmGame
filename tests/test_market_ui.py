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

from economy import Economy
from game_state import GameState
from inventory import get_marketable_item_ids
from processing import initialize_processing_plant
from screen_layout import set_screen_size
from time_system import GameTime
from ui import InfoPanel, MarketSaleDialog


class MarketPanelLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def _state(self, item_ids):
        warehouse = {
            "type": "warehouse", "row": 1, "col": 1,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {
                item_id: 1 for item_id in item_ids
                if item_id != "canned_tomato"
            },
        }
        market = {"type": "market", "row": 8, "col": 1}
        buildings = [warehouse, market]
        if "canned_tomato" in item_ids:
            plant = initialize_processing_plant({
                "type": "processing_plant", "row": 12, "col": 1,
                "width": 6, "height": 5,
            })
            plant["processing_inventory"]["canned_tomato"] = 1
            buildings.append(plant)
        return GameState(
            [], [], buildings, Economy(), GameTime(start_ticks=0),
        ), market

    def _draw(self, width, height, item_ids):
        screen = pygame.display.set_mode((width, height))
        set_screen_size(width, height)
        state, market = self._state(item_ids)
        panel = InfoPanel()
        self.assertTrue(panel.open_for_building(market))
        panel.draw(screen, pygame.font.Font(None, 20), state)
        return panel, state, screen

    def test_cards_use_two_columns_and_odd_last_item_stays_on_the_left(self):
        items = get_marketable_item_ids()[:3]
        panel, _, _ = self._draw(1000, 800, items)
        first, second, third = (
            panel.market_card_rects[item_id] for item_id in items
        )

        self.assertEqual(2, panel.market_column_count)
        self.assertEqual(first.top, second.top)
        self.assertLess(first.left, second.left)
        self.assertEqual(first.left, third.left)
        self.assertGreater(third.top, first.top)
        self.assertEqual(first.width, second.width)

    def test_small_resolution_falls_back_to_one_column(self):
        items = get_marketable_item_ids()[:2]
        panel, _, _ = self._draw(500, 700, items)
        first, second = (
            panel.market_card_rects[item_id] for item_id in items
        )

        self.assertEqual(1, panel.market_column_count)
        self.assertEqual(first.left, second.left)
        self.assertGreater(second.top, first.top)

    def test_wheel_events_scroll_without_creating_a_sale_selection(self):
        items = get_marketable_item_ids()
        panel, _, screen = self._draw(1000, 500, items)
        font = pygame.font.Font(None, 20)
        self.assertGreater(panel.market_max_scroll, 0)

        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.MOUSEWHEEL, {"y": -1, "x": 0},
        )))
        self.assertGreater(panel.market_scroll_offset, 0)
        self.assertIsNone(panel.take_sale_selection())

        panel.draw(screen, font, self._state(items)[0])
        for hitbox in panel.market_card_rects.values():
            self.assertTrue(panel.market_list_rect.contains(hitbox))
        self.assertLess(len(panel.market_card_rects), len(items))

        panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"pos": panel.market_list_rect.center, "button": 4},
        ))
        self.assertIsNone(panel.take_sale_selection())
        panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"pos": panel.market_list_rect.center, "button": 5},
        ))
        self.assertIsNone(panel.take_sale_selection())

        for _ in range(100):
            panel.handle_event(pygame.event.Event(
                pygame.MOUSEWHEEL, {"y": -1, "x": 0},
            ))
        self.assertEqual(panel.market_max_scroll, panel.market_scroll_offset)
        for _ in range(100):
            panel.handle_event(pygame.event.Event(
                pygame.MOUSEWHEEL, {"y": 1, "x": 0},
            ))
        self.assertEqual(0, panel.market_scroll_offset)

    def test_only_left_button_opens_sale_dialog_without_immediate_sale(self):
        items = get_marketable_item_ids()[:2]
        panel, _, _ = self._draw(1000, 800, items)
        card_center = panel.market_card_rects[items[0]].center

        for button in (2, 3, 4, 5):
            panel.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"pos": card_center, "button": button},
            ))
            self.assertIsNone(panel.take_sale_selection())

        panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"pos": card_center, "button": 1},
        ))
        self.assertTrue(panel.sale_dialog.visible)
        self.assertEqual(items[0], panel.sale_dialog.item_id)
        self.assertIsNone(panel.take_sale_selection())

    def test_quantity_input_max_and_enter_create_partial_sale_request(self):
        items = get_marketable_item_ids()[:1]
        panel, state, screen = self._draw(1000, 800, items)
        item_id = items[0]
        state.buildings[0]["inventory"][item_id] = 346
        panel.draw(screen, pygame.font.Font(None, 20), state)
        panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"pos": panel.market_card_rects[item_id].center, "button": 1},
        ))

        for character in "300":
            self.assertTrue(panel.handle_event(pygame.event.Event(
                pygame.KEYDOWN,
                {"key": ord(character), "unicode": character},
            )))
        self.assertTrue(panel.sale_dialog.is_quantity_valid())
        self.assertTrue(panel.handle_event(pygame.event.Event(
            pygame.KEYDOWN,
            {"key": pygame.K_RETURN, "unicode": "\r"},
        )))
        self.assertEqual((item_id, 300), panel.take_sale_selection())
        self.assertFalse(panel.sale_dialog.visible)

        panel.sale_dialog.open_for_item(item_id, 346, 8)
        panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"pos": panel.sale_dialog.max_rect.center, "button": 1},
        ))
        self.assertEqual("346", panel.sale_dialog.quantity_text)

    def test_invalid_quantities_cannot_be_confirmed(self):
        dialog = MarketSaleDialog()
        dialog.open_for_item("milk", 346, 8)
        for quantity in ("", "0", "347", "500"):
            dialog.quantity_text = quantity
            self.assertFalse(dialog.is_quantity_valid())
            dialog.handle_event(pygame.event.Event(
                pygame.KEYDOWN,
                {"key": pygame.K_RETURN, "unicode": "\r"},
            ))
            self.assertIsNone(dialog.take_sale())
            self.assertTrue(dialog.visible)

    def test_sale_dialog_consumes_shortcuts_and_closes_without_click_through(self):
        dialog = MarketSaleDialog()
        dialog.open_for_item("milk", 10, 8)
        self.assertTrue(dialog.handle_event(pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_0, "unicode": "0"},
        )))
        self.assertEqual("0", dialog.quantity_text)
        outside = (dialog.rect.left - 1, dialog.rect.top)
        self.assertTrue(dialog.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": outside, "button": 1},
        )))
        self.assertFalse(dialog.visible)


if __name__ == "__main__":
    unittest.main()
