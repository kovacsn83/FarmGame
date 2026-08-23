from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from crops import CROPS, get_crop_week_intervals
from notification_system import NotificationManager


class NotificationManagerTests(unittest.TestCase):
    def test_priority_message_preempts_and_preserves_current_message(self):
        manager = NotificationManager(start_ticks=0)
        manager.enqueue("Korábbi üzenet")

        self.assertTrue(manager.enqueue_priority("Kritikus üzenet"))

        self.assertEqual(manager.current_message, "Kritikus üzenet")
        manager.update(10_000, time_running=True)
        self.assertEqual(manager.current_message, "Korábbi üzenet")

    def test_message_expires_after_ten_running_seconds(self):
        manager = NotificationManager(start_ticks=0)
        manager.enqueue("Teszt")
        manager.update(9_999, time_running=True)
        self.assertEqual(manager.current_message, "Teszt")
        manager.update(10_000, time_running=True)
        self.assertIsNone(manager.current_message)

    def test_pause_freezes_real_time_countdown(self):
        manager = NotificationManager(start_ticks=0)
        manager.enqueue("Teszt")
        manager.update(4_000, time_running=True)
        manager.update(20_000, time_running=False)
        self.assertEqual(manager.remaining_ms, 6_000)
        manager.update(25_999, time_running=True)
        self.assertEqual(manager.current_message, "Teszt")
        manager.update(26_000, time_running=True)
        self.assertIsNone(manager.current_message)

    def test_queue_displays_every_message_in_fifo_order(self):
        manager = NotificationManager(start_ticks=0)
        manager.enqueue("Első")
        manager.enqueue("Második")
        manager.enqueue("Harmadik")
        self.assertEqual(manager.current_message, "Első")
        manager.update(10_000)
        self.assertEqual(manager.current_message, "Második")
        manager.update(20_000)
        self.assertEqual(manager.current_message, "Harmadik")
        manager.update(30_000)
        self.assertIsNone(manager.current_message)

    def test_each_crop_period_start_creates_one_annual_event(self):
        manager = NotificationManager()
        expected_count = sum(
            len(get_crop_week_intervals(crop, interval_name) or ())
            for crop in CROPS.values()
            for interval_name in ("planting_weeks", "harvest_weeks")
        )
        added_count = 0
        for week in range(1, 53):
            elapsed = week - 1
            added_count += manager.process_week(elapsed)
            self.assertEqual(manager.process_week(elapsed), 0)
        self.assertEqual(added_count, expected_count)
        self.assertEqual(1 + len(manager.queue), expected_count)

    def test_same_period_can_notify_again_in_next_year(self):
        manager = NotificationManager()
        self.assertEqual(manager.process_week(39), 1)  # 1. év, 40. hét
        self.assertEqual(manager.process_week(39), 0)
        self.assertEqual(manager.process_week(91), 1)  # 2. év, 40. hét
        self.assertEqual(len(manager.queue), 1)

    def test_reset_discards_unsaved_messages_without_false_replay(self):
        manager = NotificationManager(start_ticks=0)
        manager.process_week(39)
        manager.enqueue("Sorban álló esemény")
        manager.reset(current_ticks=500)
        self.assertIsNone(manager.current_message)
        self.assertEqual(len(manager.queue), 0)
        manager.update(20_000)
        self.assertIsNone(manager.current_message)


if __name__ == "__main__":
    unittest.main()
