from pathlib import Path
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constants import (
    TOOL_ANIMAL_HUSBANDRY, TOOL_BULLDOZER, TOOL_CITY, TOOL_ORCHARD,
)
from screen_layout import set_screen_size
from ui import (
    BUTTON_SIZE, CITY_TOOL_GROUPS, PRIMARY_TOOL_GROUPS, TOOLBAR_CITY_LEFT_MARGIN,
    TOOLBAR_CITY_MIN_GAP, TOOLBAR_GROUP_SPACING,
    TOOLBAR_UTILITY_MIN_GAP, TOOLBAR_UTILITY_RIGHT_MARGIN, TOOLS,
    clicked_tool, create_buttons, create_toolbar_icons,
)


PRIMARY_TOOLS = [
    tool["tool"] for group in PRIMARY_TOOL_GROUPS for tool in group
]


class ToolbarLayoutTests(unittest.TestCase):
    def _assert_layout(self, width, height=800):
        set_screen_size(width, height)
        buttons = create_buttons()
        primary_left = min(buttons[tool].left for tool in PRIMARY_TOOLS)
        primary_right = max(buttons[tool].right for tool in PRIMARY_TOOLS)
        primary_center = (primary_left + primary_right) / 2
        bulldozer = buttons[TOOL_BULLDOZER]

        self.assertEqual(
            bulldozer.right, width - TOOLBAR_UTILITY_RIGHT_MARGIN,
        )
        self.assertEqual(bulldozer.width, BUTTON_SIZE)
        self.assertTrue(all(
            buttons[tool].centery == bulldozer.centery
            for tool in PRIMARY_TOOLS
        ))
        self.assertGreaterEqual(
            bulldozer.left - primary_right, TOOLBAR_UTILITY_MIN_GAP,
        )
        return buttons, primary_center

    def test_primary_tools_are_centered_and_bulldozer_is_right_aligned(self):
        buttons, primary_center = self._assert_layout(1500, 1000)
        self.assertEqual(primary_center, 750)
        self.assertEqual(
            clicked_tool(
                buttons, buttons[TOOL_BULLDOZER].center,
            ),
            TOOL_BULLDOZER,
        )

    def test_layout_recalculates_for_multiple_window_sizes(self):
        for width in (600, 900, 1200, 1800):
            with self.subTest(width=width):
                _buttons, primary_center = self._assert_layout(width)
                self.assertEqual(primary_center, width / 2)

    def test_existing_tool_order_and_bulldozer_tooltip_data_are_preserved(self):
        bulldozer_definition = next(
            tool for tool in TOOLS if tool["tool"] == TOOL_BULLDOZER
        )
        self.assertEqual(bulldozer_definition["name"], "Buldózer")
        self.assertEqual(TOOLS[-1]["tool"], TOOL_BULLDOZER)

    def test_city_is_left_aligned_without_moving_primary_tools(self):
        set_screen_size(1500, 1000)
        buttons = create_buttons()
        city = buttons[TOOL_CITY]
        primary_left = min(buttons[tool].left for tool in PRIMARY_TOOLS)
        primary_right = max(buttons[tool].right for tool in PRIMARY_TOOLS)

        self.assertEqual(TOOLBAR_CITY_LEFT_MARGIN, city.left)
        self.assertEqual(750, (primary_left + primary_right) / 2)
        self.assertGreaterEqual(
            primary_left - city.right, TOOLBAR_CITY_MIN_GAP,
        )
        self.assertEqual(
            [TOOL_CITY],
            [tool["tool"] for group in CITY_TOOL_GROUPS for tool in group],
        )
        city_definition = next(
            tool for tool in TOOLS if tool["tool"] == TOOL_CITY
        )
        self.assertEqual("Város", city_definition["name"])
        self.assertEqual("city_24.png", city_definition["icon_path"].name)
        self.assertEqual(TOOL_CITY, clicked_tool(buttons, city.center))

    def test_orchard_is_a_separate_group_after_animal_husbandry(self):
        orchard_definition = next(
            tool for tool in TOOLS if tool["tool"] == TOOL_ORCHARD
        )
        self.assertEqual("Gyümölcsös", orchard_definition["name"])
        self.assertEqual(
            "fruit_tree_24.png", orchard_definition["icon_path"].name,
        )
        self.assertEqual(
            [TOOL_ORCHARD],
            [tool["tool"] for tool in PRIMARY_TOOL_GROUPS[-1]],
        )
        self.assertEqual(
            TOOL_ANIMAL_HUSBANDRY,
            PRIMARY_TOOL_GROUPS[-2][-1]["tool"],
        )

        set_screen_size(1500, 1000)
        buttons = create_buttons()
        self.assertEqual(
            TOOLBAR_GROUP_SPACING,
            buttons[TOOL_ORCHARD].left
            - buttons[TOOL_ANIMAL_HUSBANDRY].right,
        )
        self.assertEqual(
            TOOL_ORCHARD,
            clicked_tool(buttons, buttons[TOOL_ORCHARD].center),
        )

    def test_orchard_icon_loads_at_toolbar_size(self):
        pygame.display.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        orchard_icon = create_toolbar_icons()[TOOL_ORCHARD]
        self.assertIsNotNone(orchard_icon)
        self.assertEqual((24, 24), orchard_icon.get_size())

    def test_city_icon_loads_at_toolbar_size(self):
        pygame.display.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        city_icon = create_toolbar_icons()[TOOL_CITY]
        self.assertIsNotNone(city_icon)
        self.assertEqual((24, 24), city_icon.get_size())


if __name__ == "__main__":
    unittest.main()
