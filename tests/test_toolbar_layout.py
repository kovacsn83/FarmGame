from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constants import TOOL_BULLDOZER
from screen_layout import set_screen_size
from ui import (
    BUTTON_SIZE, PRIMARY_TOOL_GROUPS, TOOLBAR_UTILITY_MIN_GAP,
    TOOLBAR_UTILITY_RIGHT_MARGIN, TOOLS, clicked_tool, create_buttons,
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


if __name__ == "__main__":
    unittest.main()
