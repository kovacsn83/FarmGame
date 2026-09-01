import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pygame

from game_rules import UPGRADES, get_upgrade_tree_columns
from screen_layout import set_screen_size
from ui import (
    InfoPanel, UPGRADE_CARD_HEIGHT, UPGRADE_INFO_HITBOX_SIZE,
)


class FarmhouseUpgradeUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.font.init()
        set_screen_size(1500, 1000)
        cls.screen = pygame.Surface((1500, 1000))
        cls.font = pygame.font.SysFont(None, 24)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        set_screen_size(1500, 1000)
        self.panel = InfoPanel()
        self.panel.open_for_building({
            "type": "farmhouse", "farmhouse_level": 1,
        })
        self.state = SimpleNamespace(purchased_upgrades=set())

    def _draw_at(self, mouse_position):
        with patch("pygame.mouse.get_pos", return_value=mouse_position):
            self.panel.draw(self.screen, self.font, self.state)

    def test_each_upgrade_has_a_compact_information_hitbox(self):
        self._draw_at((-1, -1))
        self.assertEqual(set(self.panel.upgrade_info_rects), set(UPGRADES))
        self.assertLess(UPGRADE_CARD_HEIGHT, 126)
        for upgrade_id, info_rect in self.panel.upgrade_info_rects.items():
            card_rect = self.panel.upgrade_card_rects[upgrade_id]
            self.assertEqual(
                info_rect.size,
                (UPGRADE_INFO_HITBOX_SIZE, UPGRADE_INFO_HITBOX_SIZE),
            )
            self.assertTrue(card_rect.contains(info_rect))
            self.assertGreater(info_rect.centerx, card_rect.centerx)

    def test_description_is_not_drawn_as_normal_card_text(self):
        drawn_texts = []
        self.panel.draw_text = (
            lambda screen, font, text, x, y: drawn_texts.append(text)
        )
        self._draw_at((-1, -1))
        for upgrade in UPGRADES.values():
            self.assertNotIn(upgrade["description"], drawn_texts)
            self.assertIn(upgrade["name"], drawn_texts)

    def test_hover_uses_shared_tooltip_with_catalog_description(self):
        self._draw_at((-1, -1))
        upgrade_id = next(iter(UPGRADES))
        info_rect = self.panel.upgrade_info_rects[upgrade_id]
        with (
            patch("pygame.mouse.get_pos", return_value=info_rect.center),
            patch("ui.draw_tooltip") as tooltip,
        ):
            self.panel.draw(self.screen, self.font, self.state)
        tooltip.assert_called_once_with(
            self.screen, self.font, UPGRADES[upgrade_id]["description"],
            self.panel.upgrade_info_rects[upgrade_id],
        )

    def test_leaving_information_hitbox_hides_tooltip(self):
        self._draw_at((-1, -1))
        with (
            patch("pygame.mouse.get_pos", return_value=(-1, -1)),
            patch("ui.draw_tooltip") as tooltip,
        ):
            self.panel.draw(self.screen, self.font, self.state)
        tooltip.assert_not_called()

    def test_clicking_information_hitbox_does_not_purchase_upgrade(self):
        self._draw_at((-1, -1))
        upgrade_id = next(iter(UPGRADES))
        info_rect = self.panel.upgrade_info_rects[upgrade_id]
        self.assertTrue(self.panel._handle_content_click(info_rect.center))
        self.assertIsNone(self.panel.take_upgrade_selection())

    def test_regular_card_click_still_selects_upgrade(self):
        self._draw_at((-1, -1))
        upgrade_id = next(iter(UPGRADES))
        card_rect = self.panel.upgrade_card_rects[upgrade_id]
        click_position = (card_rect.left + 10, card_rect.bottom - 10)
        self.assertTrue(self.panel._handle_content_click(click_position))
        self.assertEqual(self.panel.take_upgrade_selection(), upgrade_id)

    def test_tooltip_also_works_for_purchased_upgrade(self):
        upgrade_id = "unlock_field_6x6"
        self.state.purchased_upgrades.add(upgrade_id)
        self._draw_at((-1, -1))
        info_rect = self.panel.upgrade_info_rects[upgrade_id]
        with (
            patch("pygame.mouse.get_pos", return_value=info_rect.center),
            patch("ui.draw_tooltip") as tooltip,
        ):
            self.panel.draw(self.screen, self.font, self.state)
        tooltip.assert_called_once()

    def test_tree_has_three_columns_and_vertical_branch_order(self):
        self._draw_at((-1, -1))
        columns = get_upgrade_tree_columns()
        self.assertEqual(len(columns), 3)
        self.assertEqual(columns[0], (
            "unlock_field_6x6",
            "automated_animal_watering",
            "automated_animal_feeding",
        ))
        self.assertEqual(columns[1], (
            "unlock_field_8x8",
            "automated_field_watering",
            "automated_field_fertilizing",
            "automated_field_spraying",
        ))
        for column in columns:
            tops = [self.panel.upgrade_card_rects[item].top for item in column]
            self.assertEqual(tops, sorted(tops))
        self.assertLess(
            self.panel.upgrade_card_rects["unlock_field_6x6"].left,
            self.panel.upgrade_card_rects["unlock_field_8x8"].left,
        )
        self.assertLess(
            self.panel.upgrade_card_rects["farmhouse_level_2"].left,
            self.panel.upgrade_card_rects["farmhouse_level_3"].left,
        )

    def test_locked_node_is_visible_but_not_clickable(self):
        self._draw_at((-1, -1))
        upgrade_id = "automated_animal_watering"
        self.assertIn(upgrade_id, self.panel.upgrade_card_rects)
        self.assertNotIn(upgrade_id, self.panel.upgrade_clickable_ids)
        card = self.panel.upgrade_card_rects[upgrade_id]
        self.panel._handle_content_click((card.left + 8, card.bottom - 8))
        self.assertIsNone(self.panel.take_upgrade_selection())

        self.state.purchased_upgrades.add("unlock_field_6x6")
        self._draw_at((-1, -1))
        self.assertIn(upgrade_id, self.panel.upgrade_clickable_ids)

    def test_small_window_keeps_columns_visible_and_enables_vertical_scroll(self):
        set_screen_size(640, 480)
        self._draw_at((-1, -1))
        self.assertLessEqual(self.panel.rect.width, 640)
        self.assertLessEqual(self.panel.rect.height, 480)
        self.assertGreater(self.panel.upgrade_tree_max_scroll, 0)
        initial_scroll = self.panel.upgrade_tree_scroll
        event = pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1})
        with patch("pygame.mouse.get_pos", return_value=self.panel.rect.center):
            self.assertTrue(self.panel.handle_event(event))
        self.assertGreater(self.panel.upgrade_tree_scroll, initial_scroll)


if __name__ == "__main__":
    unittest.main()
