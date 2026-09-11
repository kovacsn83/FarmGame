import os
from pathlib import Path
import sys
import unittest


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pygame

from screen_layout import set_screen_size
from ui import BUILDING_SELECTION_ORDER, BuildingSelectionPanel


class BuildingSelectionOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_default_cards_follow_thematic_pair_order(self):
        panel = BuildingSelectionPanel()
        self.assertEqual(
            BUILDING_SELECTION_ORDER,
            tuple(panel._available_options()),
        )

    def test_thematic_pairs_share_rows_in_two_column_layout(self):
        set_screen_size(1000, 800)
        panel = BuildingSelectionPanel()
        panel.open()
        panel._update_layout()

        for left, right in zip(
                BUILDING_SELECTION_ORDER[::2],
                BUILDING_SELECTION_ORDER[1::2]):
            self.assertEqual(
                panel.card_rects[left].top,
                panel.card_rects[right].top,
            )
            self.assertLess(
                panel.card_rects[left].left,
                panel.card_rects[right].left,
            )


if __name__ == "__main__":
    unittest.main()
