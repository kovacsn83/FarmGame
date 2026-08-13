from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from time_system import (
    TIME_NORMAL, TIME_PAUSED, TIME_SLOW, TIME_SPEED_MULTIPLIERS,
    TIME_WEEK_LENGTHS_MS,
)
from tractor import (
    FEED_LOAD_DURATION_MS, TRACTOR_STEP_INTERVAL_MS,
    WATER_FILL_DURATION_MS, WATER_UNLOAD_DURATION_MS,
)


class SpeedTimingTests(unittest.TestCase):
    def test_week_lengths_use_twelve_and_six_seconds(self):
        self.assertIsNone(TIME_WEEK_LENGTHS_MS[TIME_PAUSED])
        self.assertEqual(TIME_WEEK_LENGTHS_MS[TIME_SLOW], 12000)
        self.assertEqual(TIME_WEEK_LENGTHS_MS[TIME_NORMAL], 6000)

    def test_vehicle_step_times_use_eighty_and_forty_milliseconds(self):
        self.assertEqual(TRACTOR_STEP_INTERVAL_MS, 80)
        self.assertEqual(
            TRACTOR_STEP_INTERVAL_MS / TIME_SPEED_MULTIPLIERS[TIME_SLOW],
            80,
        )
        self.assertEqual(
            TRACTOR_STEP_INTERVAL_MS / TIME_SPEED_MULTIPLIERS[TIME_NORMAL],
            40,
        )

    def test_other_operation_durations_remain_unchanged(self):
        self.assertEqual(WATER_FILL_DURATION_MS, 800)
        self.assertEqual(WATER_UNLOAD_DURATION_MS, 800)
        self.assertEqual(FEED_LOAD_DURATION_MS, 1000)


if __name__ == "__main__":
    unittest.main()
