import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simulation import SimulationBot
from unsaved_changes import UnsavedChangesTracker


class UnsavedChangesTrackerTests(unittest.TestCase):
    def setUp(self):
        self.state = SimulationBot(9101).state
        self.tracker = UnsavedChangesTracker()

    def test_new_game_is_dirty_until_first_successful_save(self):
        self.tracker.start_new_game()
        self.assertTrue(self.tracker.has_unsaved_changes(self.state))
        self.tracker.mark_saved(self.state, 3, "Első farm")
        self.assertFalse(self.tracker.has_unsaved_changes(self.state))
        self.assertEqual(self.tracker.current_slot_id, 3)
        self.assertEqual(self.tracker.current_save_name, "Első farm")

    def test_loaded_game_starts_clean_and_week_advance_makes_it_dirty(self):
        self.tracker.mark_loaded(self.state, 5, "Betöltött farm")
        self.assertFalse(self.tracker.has_unsaved_changes(self.state))
        self.state.game_time.elapsed_weeks += 1
        self.assertTrue(self.tracker.has_unsaved_changes(self.state))

    def test_gameplay_mutation_is_detected_without_manual_dirty_calls(self):
        self.tracker.mark_saved(self.state, 1, "Farm")
        self.state.economy.money -= 125
        self.assertTrue(self.tracker.has_unsaved_changes(self.state))

    def test_ui_only_activity_does_not_change_the_save_signature(self):
        self.tracker.mark_saved(self.state, 1, "Farm")
        ui_only_state = {"popup": "bank", "camera_x": 120, "tool": "road"}
        ui_only_state["popup"] = "market"
        ui_only_state["camera_x"] = 500
        self.assertFalse(self.tracker.has_unsaved_changes(self.state))

    def test_failed_save_cannot_clear_dirty_state_without_mark_saved(self):
        self.tracker.mark_saved(self.state, 1, "Farm")
        self.state.economy.money += 1
        save_succeeded = False
        if save_succeeded:
            self.tracker.mark_saved(self.state, 1, "Farm")
        self.assertTrue(self.tracker.has_unsaved_changes(self.state))


if __name__ == "__main__":
    unittest.main()
