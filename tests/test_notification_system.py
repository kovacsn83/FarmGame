from pathlib import Path
import sys
import unittest

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from crops import CROPS, get_crop_week_intervals
from notification_system import NotificationManager
from screen_layout import set_screen_size
from ui import draw_notification_bar


class NotificationManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def test_priority_message_is_immediately_visible_and_preserves_others(self):
        manager = NotificationManager(start_ticks=0)
        manager.enqueue("Korábbi üzenet")

        self.assertTrue(manager.enqueue_priority("Kritikus üzenet"))

        self.assertEqual(manager.current_message, "Kritikus üzenet")
        self.assertEqual(
            manager.active_messages,
            ("Kritikus üzenet", "Korábbi üzenet"),
        )
        manager.update(10_000, time_running=True)
        self.assertIsNone(manager.current_message)

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

    def test_first_three_messages_are_visible_immediately(self):
        manager = NotificationManager(start_ticks=0)
        manager.enqueue("Első")
        manager.enqueue("Második")
        manager.enqueue("Harmadik")
        self.assertEqual(manager.active_messages, ("Első", "Második", "Harmadik"))
        self.assertEqual(len(manager.pending_notifications), 0)

    def test_each_visible_message_has_an_independent_timer(self):
        manager = NotificationManager(start_ticks=0)
        manager.enqueue("Első")
        manager.update(2_000)
        manager.enqueue("Második")
        manager.update(4_000)
        manager.enqueue("Harmadik")

        self.assertEqual(
            [entry.remaining_ms for entry in manager.active_notifications],
            [6_000, 8_000, 10_000],
        )
        manager.update(10_000)
        self.assertEqual(manager.active_messages, ("Második", "Harmadik"))
        self.assertEqual(
            [entry.remaining_ms for entry in manager.active_notifications],
            [2_000, 4_000],
        )

    def test_fourth_message_waits_and_activates_when_slot_opens(self):
        manager = NotificationManager(start_ticks=0)
        manager.enqueue("Első")
        manager.update(2_000)
        manager.enqueue("Második")
        manager.enqueue("Harmadik")
        manager.enqueue("Negyedik")

        self.assertEqual(len(manager.active_notifications), 3)
        self.assertEqual(len(manager.pending_notifications), 1)
        manager.update(10_000)
        self.assertEqual(
            manager.active_messages,
            ("Második", "Harmadik", "Negyedik"),
        )
        self.assertEqual(manager.active_notifications[-1].remaining_ms, 10_000)

    def test_never_displays_more_than_three_notifications(self):
        manager = NotificationManager(start_ticks=0)
        for index in range(10):
            manager.enqueue(f"Üzenet {index}")
        self.assertEqual(len(manager.active_notifications), 3)
        self.assertEqual(len(manager.pending_notifications), 7)

    def test_event_id_deduplication_checks_active_and_pending_messages(self):
        manager = NotificationManager(start_ticks=0)
        self.assertTrue(manager.enqueue("Első", event_id="same-event"))
        self.assertFalse(manager.enqueue("Duplikált", event_id="same-event"))
        self.assertEqual(manager.active_messages, ("Első",))

    def test_three_bubbles_stack_upward_and_stay_inside_screen(self):
        set_screen_size(640, 420)
        screen = pygame.Surface((640, 420))
        font = pygame.font.Font(None, 22)
        manager = NotificationManager(start_ticks=0)
        manager.enqueue("Első értesítés")
        manager.enqueue("Második, valamivel hosszabb értesítés")
        manager.enqueue("Harmadik értesítés")

        rects = draw_notification_bar(screen, font, manager, bottom_y=370)

        self.assertEqual(len(rects), 3)
        self.assertEqual(rects[0].bottom, 360)
        self.assertLess(rects[1].bottom, rects[0].top)
        self.assertLess(rects[2].bottom, rects[1].top)
        for rect in rects:
            self.assertGreaterEqual(rect.left, 0)
            self.assertGreaterEqual(rect.top, 0)
            self.assertLessEqual(rect.right, 640)
            self.assertLessEqual(rect.bottom, 420)

        constrained_rects = draw_notification_bar(
            screen, font, manager, bottom_y=60,
        )
        self.assertEqual(constrained_rects[-1].top, 0)

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
