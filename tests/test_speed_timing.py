from pathlib import Path
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from time_system import (
    BASE_WEEK_DURATION_MS, GameTime, TIME_NORMAL, TIME_PAUSED, TIME_SLOW,
    TIME_SPEED_MULTIPLIERS,
    TIME_WEEK_LENGTHS_MS,
)
from tractor import (
    FEED_LOAD_DURATION_MS, TRACTOR_STEP_INTERVAL_MS,
    WATER_FILL_DURATION_MS, WATER_UNLOAD_DURATION_MS,
)
from save_system import load_game, save_game
from simulation import SimulationBot


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

    def test_one_week_passes_after_twelve_seconds_at_1x(self):
        game_time = GameTime(TIME_SLOW, start_ticks=0)
        self.assertEqual(game_time.update(11999), [])
        self.assertEqual(game_time.update(12000), [1])

    def test_one_week_passes_after_six_seconds_at_2x(self):
        game_time = GameTime(TIME_NORMAL, start_ticks=0)
        self.assertEqual(game_time.update(6000), [1])

    def test_switching_speed_preserves_partial_week(self):
        game_time = GameTime(TIME_SLOW, start_ticks=0)
        game_time.update(4000)
        self.assertAlmostEqual(game_time.week_progress, 1 / 3)
        game_time.set_time_speed(TIME_NORMAL, current_ticks=4000)
        self.assertAlmostEqual(game_time.week_progress, 1 / 3)
        self.assertEqual(game_time.update(7999), [])
        self.assertEqual(game_time.update(8000), [1])

    def test_progress_is_monotonic_through_repeated_speed_switches(self):
        game_time = GameTime(TIME_SLOW, start_ticks=0)
        progress_values = []
        ticks = 0
        for index in range(100):
            ticks += 50
            game_time.update(ticks)
            progress_values.append(game_time.week_progress)
            speed = TIME_NORMAL if index % 2 == 0 else TIME_SLOW
            game_time.set_time_speed(speed, current_ticks=ticks)
        self.assertEqual(progress_values, sorted(progress_values))
        self.assertGreater(game_time.week_progress, 0)
        self.assertEqual(game_time.update(ticks + 10000), [1])

    def test_switching_without_intermediate_updates_cannot_freeze_week(self):
        game_time = GameTime(TIME_SLOW, start_ticks=0)
        for index in range(1, 101):
            speed = TIME_NORMAL if index % 2 else TIME_SLOW
            game_time.set_time_speed(speed, current_ticks=index * 100)
        self.assertGreaterEqual(game_time.elapsed_time_in_week_ms, 12000)
        self.assertEqual(game_time.update(10000), [1])

    def test_pause_preserves_progress_and_resume_continues_from_it(self):
        game_time = GameTime(TIME_SLOW, start_ticks=0)
        game_time.update(6500)
        game_time.set_time_speed(TIME_PAUSED, current_ticks=6500)
        game_time.update(50000)
        self.assertAlmostEqual(game_time.week_progress, 6500 / 12000)
        game_time.set_time_speed(TIME_NORMAL, current_ticks=50000)
        self.assertEqual(game_time.update(52749), [])
        self.assertEqual(game_time.update(52750), [1])

    def test_large_delta_advances_every_crossed_week_once(self):
        game_time = GameTime(TIME_NORMAL, start_ticks=0)
        self.assertEqual(game_time.update(15000), [1, 2])
        self.assertEqual(game_time.elapsed_weeks, 2)
        self.assertAlmostEqual(game_time.week_progress, 0.5)

    def test_week_progress_restore_is_safe_and_exact(self):
        game_time = GameTime(TIME_SLOW, start_ticks=0)
        game_time.restore_week_progress(0.63)
        self.assertAlmostEqual(
            game_time.elapsed_time_in_week_ms,
            BASE_WEEK_DURATION_MS * 0.63,
        )
        game_time.restore_week_progress(2)
        self.assertEqual(game_time.week_progress, 0)

    def test_week_progress_round_trips_through_save(self):
        original = SimulationBot(101)
        original.state.game_time.restore_week_progress(0.63)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "time-progress.json"
            self.assertTrue(save_game(original.state, path))
            loaded = SimulationBot(102)
            self.assertTrue(load_game(loaded.state, path))
        self.assertAlmostEqual(loaded.state.game_time.week_progress, 0.63)

    def test_legacy_save_without_week_progress_starts_week_safely(self):
        original = SimulationBot(103)
        original.state.game_time.restore_week_progress(0.63)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-time.json"
            self.assertTrue(save_game(original.state, path))
            document = json.loads(path.read_text(encoding="utf-8"))
            document.pop("week_progress")
            path.write_text(
                json.dumps(document, ensure_ascii=False), encoding="utf-8",
            )
            loaded = SimulationBot(104)
            self.assertTrue(load_game(loaded.state, path))
        self.assertEqual(loaded.state.game_time.week_progress, 0)


if __name__ == "__main__":
    unittest.main()
