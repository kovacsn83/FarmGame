from pathlib import Path
import os
import sys
import unittest


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pygame

from screen_layout import set_screen_size
from ui import (
    TOOLTIP_MAX_WIDTH, TOOLTIP_PADDING_X, draw_tooltip,
    wrap_tooltip_lines,
)


class TooltipLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.font.init()
        cls.font = pygame.font.SysFont(None, 24)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_important_lines_are_not_truncated(self):
        lines = wrap_tooltip_lines(
            self.font,
            ["Aratások száma: 4 / 8", "Még 3 hét az érésig"],
            TOOLTIP_MAX_WIDTH,
        )
        self.assertIn("Aratások száma: 4 / 8", lines)
        self.assertIn("Még 3 hét az érésig", lines)
        self.assertFalse(any("..." in line for line in lines))

    def test_width_follows_longest_line_with_horizontal_padding(self):
        set_screen_size(800, 600)
        screen = pygame.Surface((800, 600))
        anchor = pygame.Rect(390, 300, 20, 20)
        text = ["Rövid", "Aratások száma: 4 / 8"]
        rect = draw_tooltip(screen, self.font, text, anchor)
        expected = self.font.size(text[1])[0] + TOOLTIP_PADDING_X * 2
        self.assertEqual(rect.width, expected)

    def test_very_long_text_wraps_without_losing_words(self):
        text = (
            "A lucerna érett, de a raktár nem rendelkezik elegendő "
            "szabad kapacitással."
        )
        lines = wrap_tooltip_lines(self.font, text, 220)
        self.assertGreater(len(lines), 1)
        self.assertEqual(" ".join(lines), text)
        self.assertTrue(all(self.font.size(line)[0] <= 220 for line in lines))

    def test_tooltip_is_clamped_to_screen_edges(self):
        set_screen_size(320, 180)
        screen = pygame.Surface((320, 180))
        for anchor in (
            pygame.Rect(0, 0, 20, 20),
            pygame.Rect(300, 160, 20, 20),
        ):
            rect = draw_tooltip(
                screen, self.font,
                "Hosszabb tooltip szöveg, amely a képernyőn marad.",
                anchor,
            )
            self.assertGreaterEqual(rect.left, 0)
            self.assertGreaterEqual(rect.top, 0)
            self.assertLessEqual(rect.right, 320)
            self.assertLessEqual(rect.bottom, 180)


if __name__ == "__main__":
    unittest.main()
