import os
import sys
import unittest
from pathlib import Path
from copy import deepcopy

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feed_mill import initialize_feed_mill, try_produce_feed, get_feed_mill_status_lines
from processing import receive_processing_delivery
from save_system import _validate_inventory


class FeedMillArrivalTests(unittest.TestCase):
    def mill(self):
        mill = initialize_feed_mill(dict(type="feed_mill"))
        mill["feed_mill_week"] = 10
        return mill

    def test_second_ingredient_delivery_produces_immediately(self):
        mill = self.mill()
        receive_processing_delivery(mill, "wheat", 5)
        self.assertEqual(mill["processing_inventory"]["chicken_feed"], 0)
        receive_processing_delivery(mill, "corn", 5)
        self.assertEqual(mill["processing_inventory"]["chicken_feed"], 12)
        self.assertEqual(mill["feed_produced_week"], 10)
        self.assertFalse(mill["fed_this_week"])

    def test_extra_deliveries_cannot_exceed_weekly_limit(self):
        mill = self.mill()
        for _ in range(2):
            receive_processing_delivery(mill, "wheat", 5)
            receive_processing_delivery(mill, "corn", 5)
        self.assertEqual(mill["processing_inventory"]["chicken_feed"], 12)
        self.assertFalse(try_produce_feed(mill))
        mill["feed_mill_week"] = 11
        self.assertTrue(try_produce_feed(mill))
        self.assertEqual(mill["processing_inventory"]["chicken_feed"], 24)

    def test_persisted_counter_and_old_save_safe_default(self):
        mill = self.mill()
        mill["processing_inventory"].update(wheat=10, corn=10)
        try_produce_feed(mill)
        import json
        restored = initialize_feed_mill(json.loads(json.dumps(mill)))
        self.assertFalse(try_produce_feed(restored))
        self.assertTrue(_validate_inventory(restored))
        del restored["feed_produced_week"]
        initialize_feed_mill(restored)
        self.assertFalse(try_produce_feed(restored))

    def test_storage_limit_blocks_conversion_atomically(self):
        mill = self.mill()
        mill["processing_inventory"].update(wheat=5, corn=5, chicken_feed=190)
        before = deepcopy(mill)
        self.assertFalse(try_produce_feed(mill))
        self.assertEqual(mill, before)
        self.assertIn("Gyártás: nincs elegendő raktárhely", get_feed_mill_status_lines(mill))

    def test_status_reports_each_missing_input_and_transit(self):
        mill = self.mill()
        mill["processing_in_transit"]["corn"] = 5
        mill["feed_supply_reasons"] = {"wheat": "szabad traktorra vár"}
        before = deepcopy(mill)
        lines = get_feed_mill_status_lines(mill)
        self.assertIn("Búza: 5 db hiányzik – szabad traktorra vár", lines)
        self.assertIn("Kukorica: 5 db hiányzik – 5 db szállítás alatt", lines)
        self.assertEqual(mill, before)


if __name__ == "__main__":
    unittest.main()
