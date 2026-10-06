import sys
import unittest
from pathlib import Path
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feed_mill import initialize_feed_mill
from progress_tooltips import find_timed_object_tooltip


class FeedMillTooltipTests(unittest.TestCase):
    def setUp(self):
        self.mill = initialize_feed_mill(dict(type="feed_mill", row=8, col=10,
                                            width=12, height=8))

    def hover(self, row, col):
        return find_timed_object_tooltip(row, col, [], [], {}, buildings=[self.mill])

    def test_inside_full_plot_only(self):
        for position in ((8, 10), (15, 21), (13, 11)):
            self.assertEqual(self.hover(*position)[0], "Takarmánykeverő üzem I.")
        for position in ((7, 10), (16, 10), (8, 22)):
            self.assertIsNone(self.hover(*position))

    def test_live_stock_and_status_without_mutation(self):
        self.mill["processing_inventory"].update(wheat=5, chicken_feed=12)
        self.mill["processing_in_transit"]["corn"] = 5
        self.mill["fed_this_week"] = True
        before = deepcopy(self.mill)
        lines = self.hover(8, 10)
        self.assertIn("Raktár: 17 / 200", lines)
        self.assertIn("Csirketáp: 12", lines)
        self.assertIn("Úton lévő alapanyag: 5", lines)
        self.assertIn("Etetés: Biztosítva", lines)
        self.assertEqual(self.mill, before)
        self.mill["processing_inventory"]["chicken_feed"] = 0
        self.assertIn("Csirketáp: 0", self.hover(8, 10))


if __name__ == "__main__":
    unittest.main()
