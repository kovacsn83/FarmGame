import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constants import TOOL_CITY, TOOL_INSPECT
from asset_loader import load_toolbar_icons
from screen_layout import set_screen_size
from ui import (
    BUTTON_GAP, BUTTON_SIZE, CITY_TOOLBAR_SERVICES,
    TOOL_CITY_BANK, TOOL_CITY_MARKET, TOOL_CITY_RESTAURANT,
    TOOLS, clicked_tool, create_buttons, create_toolbar_icons, draw_ui,
    get_visible_toolbar_tools,
)


class CityToolbarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1500, 1000))
        set_screen_size(1500, 1000)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_service_catalog_is_ordered_and_extensible(self):
        self.assertEqual(
            ["bank", "market", "restaurant"],
            [service["id"] for service in CITY_TOOLBAR_SERVICES],
        )
        self.assertEqual(
            [TOOL_CITY_BANK, TOOL_CITY_MARKET, TOOL_CITY_RESTAURANT],
            [service["tool"] for service in CITY_TOOLBAR_SERVICES],
        )

    def test_collapsed_layout_has_no_service_buttons_or_hitboxes(self):
        buttons = create_buttons(False)
        self.assertIn(TOOL_CITY, buttons)
        for service in CITY_TOOLBAR_SERVICES:
            self.assertNotIn(service["tool"], buttons)
        service_tools = {
            item["tool"] for item in get_visible_toolbar_tools(False)
        }
        self.assertTrue(all(
            service["tool"] not in service_tools
            for service in CITY_TOOLBAR_SERVICES
        ))

    def test_expanded_layout_places_services_after_city(self):
        buttons = create_buttons(True)
        ordered_tools = [
            TOOL_CITY, TOOL_CITY_BANK, TOOL_CITY_MARKET,
            TOOL_CITY_RESTAURANT,
        ]
        for left_tool, right_tool in zip(ordered_tools, ordered_tools[1:]):
            self.assertEqual(
                buttons[left_tool].right + BUTTON_GAP,
                buttons[right_tool].left,
            )
            self.assertEqual((BUTTON_SIZE, BUTTON_SIZE), buttons[right_tool].size)
            self.assertEqual(
                right_tool,
                clicked_tool(buttons, buttons[right_tool].center),
            )

    def test_expanded_layout_has_no_overlaps_after_resize(self):
        for width in (600, 640, 800, 1200, 1800):
            with self.subTest(width=width):
                set_screen_size(width, 800)
                buttons = create_buttons(True)
                ordered = sorted(buttons.values(), key=lambda rect: rect.left)
                self.assertTrue(all(
                    left.right <= right.left
                    for left, right in zip(ordered, ordered[1:])
                ))
                self.assertLessEqual(max(rect.right for rect in ordered), width)
        set_screen_size(1500, 1000)

    def test_only_visible_left_click_targets_are_actionable(self):
        collapsed = create_buttons(False)
        expanded = create_buttons(True)
        for service in CITY_TOOLBAR_SERVICES:
            position = expanded[service["tool"]].center
            self.assertNotEqual(service["tool"], clicked_tool(collapsed, position))
            self.assertEqual(service["tool"], clicked_tool(expanded, position))
        # A main event router csak MOUSEBUTTONDOWN + button 1 esetén hívja ezt.
        wheel = pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1})
        self.assertNotEqual(pygame.MOUSEBUTTONDOWN, wheel.type)

    def test_city_selected_style_tracks_expanded_state(self):
        screen = pygame.display.get_surface()
        font = pygame.font.SysFont(None, 24)
        buttons = create_buttons(True)
        with patch("ui.draw_button") as draw_button:
            draw_ui(
                screen, font, buttons, TOOL_INSPECT,
                city_toolbar_expanded=True,
            )
        city_calls = [
            call for call in draw_button.call_args_list
            if call.args and call.args[1] == buttons[TOOL_CITY]
        ]
        self.assertEqual(1, len(city_calls))
        self.assertTrue(city_calls[0].args[3])

    def test_service_icons_load_at_all_supplied_sizes(self):
        self.assertTrue(create_toolbar_icons())
        for size in (20, 24, 64):
            icons = load_toolbar_icons(TOOLS, size)
            for service in CITY_TOOLBAR_SERVICES:
                icon = icons[service["tool"]]
                self.assertIsNotNone(icon)
                self.assertEqual((size, size), icon.get_size())


if __name__ == "__main__":
    unittest.main()
