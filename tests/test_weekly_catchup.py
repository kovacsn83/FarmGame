import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from calendar_utils import get_year_and_week
from challenge import ChallengeManager
from challenge_results import ChallengeResultStore
from economy import Economy
from field_automation import AUTOMATED_FIELD_HARVESTING_UPGRADE, run_field_automation
from game_identity import generate_game_id
from simulation import SimulationBot
from time_system import BASE_WEEK_DURATION_MS, GameTime, TIME_PAUSED, TIME_SLOW
import test_field_storage_blocking as storage_fixture
from fields import CROPS


class WeeklyCatchupTests(unittest.TestCase):
    def test_each_callback_observes_its_own_week_and_financial_date(self):
        for count in (1, 5, 10):
            with self.subTest(count=count):
                clock = GameTime(TIME_SLOW, start_ticks=0)
                clock.elapsed_weeks = 49
                economy = Economy()
                economy.bind_game_time(clock)
                seen = []
                for elapsed in clock.iter_weekly_updates(count * BASE_WEEK_DURATION_MS):
                    seen.append((elapsed, clock.elapsed_weeks, clock.year, clock.week))
                    economy.record_expense("maintenance", 1)
                self.assertEqual(seen, [(w, w, *get_year_and_week(w))
                                        for w in range(50, 50 + count)])
                self.assertEqual([r["week"] for r in economy.financial_history],
                                 list(range(50, 50 + count)))
                self.assertEqual(clock.update(count * BASE_WEEK_DURATION_MS), [])

    def test_pause_discards_remaining_whole_weeks_but_keeps_fraction(self):
        clock = GameTime(TIME_SLOW, start_ticks=0)
        now = 5 * BASE_WEEK_DURATION_MS + BASE_WEEK_DURATION_MS // 2
        seen = []
        for elapsed in clock.iter_weekly_updates(now):
            seen.append(elapsed)
            if elapsed == 2:
                clock.set_time_speed(TIME_PAUSED, current_ticks=now)
        self.assertEqual(seen, [1, 2])
        self.assertEqual(clock.elapsed_time_in_week_ms, BASE_WEEK_DURATION_MS // 2)
        clock.set_time_speed(TIME_SLOW, current_ticks=now)
        self.assertEqual(clock.update(now), [])
        self.assertEqual(clock.update(now + BASE_WEEK_DURATION_MS // 2), [3])

    def test_challenge_boundary_stops_catchup_even_when_persistence_fails(self):
        for persist in (True, False):
            with self.subTest(persist=persist), tempfile.TemporaryDirectory() as root:
                state = SimulationBot(1200).state
                state.game_id = generate_game_id()
                state.game_time.set_time_speed(TIME_SLOW, current_ticks=0)
                state.game_time.last_week_change = 0
                state.game_time.elapsed_weeks = 517
                store = ChallengeResultStore(Path(root) / "results.json")
                manager = ChallengeManager(SimpleNamespace(
                    player_id=generate_game_id(), player_name="Catch-up"), result_store=store)
                now = 5 * BASE_WEEK_DURATION_MS
                seen = []
                with patch("time_system.pygame.time.get_ticks", return_value=now), \
                        patch.object(store, "_write", return_value=persist):
                    for elapsed in state.game_time.iter_weekly_updates(now):
                        seen.append(elapsed)
                        manager.handle_week_transition(elapsed - 1, elapsed, state)
                self.assertEqual(seen, [518, 519, 520])
                self.assertEqual(state.game_time.elapsed_weeks, 520)
                self.assertEqual(state.game_time.current_time_speed, TIME_PAUSED)
                snapshot = manager.result
                self.assertIsNotNone(snapshot)
                self.assertEqual((snapshot.completed_year, snapshot.completed_week), (10, 52))
                self.assertIsNone(manager.handle_week_transition(519, 520, state))
                self.assertIs(manager.result, snapshot)

    def test_automatic_harvest_uses_central_calendar_at_boundaries(self):
        class Vehicles:
            def __init__(self):
                self.calls = []

            def start_harvesting(self, *args, **kwargs):
                self.calls.append(kwargs)
                return True

        for elapsed in (0, 25, 51, 52, 103, 104):
            with self.subTest(elapsed=elapsed):
                vehicles = Vehicles()
                run_field_automation([], [], object(), [{"crop": "wheat"}], vehicles,
                                     {AUTOMATED_FIELD_HARVESTING_UPGRADE},
                                     current_week=99, current_elapsed_week=elapsed)
                self.assertEqual(vehicles.calls[0]["current_week"],
                                 get_year_and_week(elapsed)[1])
                self.assertEqual(vehicles.calls[0]["current_elapsed_week"], elapsed)

    def test_real_dispatcher_first_harvest_week_and_duplicate_protection(self):
        fixture = storage_fixture.FieldStorageBlockingTests()
        fixture.setUp()
        fixture.warehouse["inventory"].clear()
        for elapsed, expected in ((24, 0), (25, 1), (26, 0)):
            self.assertEqual(run_field_automation(
                fixture.world, fixture.buildings, fixture.economy,
                [fixture.field], fixture.manager,
                {AUTOMATED_FIELD_HARVESTING_UPGRADE}, current_ticks=0,
                current_elapsed_week=elapsed), expected)

    def test_real_dispatcher_year_boundary_windows(self):
        # Synthetic windows exercise calendar boundaries without changing balance.
        for elapsed in (51, 52):
            with self.subTest(elapsed=elapsed), patch.dict(
                    CROPS["wheat"], {"harvest_weeks": ((52, 52), (1, 1))}):
                fixture = storage_fixture.FieldStorageBlockingTests()
                fixture.setUp()
                fixture.warehouse["inventory"].clear()
                self.assertEqual(run_field_automation(
                    fixture.world, fixture.buildings, fixture.economy,
                    [fixture.field], fixture.manager,
                    {AUTOMATED_FIELD_HARVESTING_UPGRADE}, current_ticks=0,
                    current_elapsed_week=elapsed), 1)


if __name__ == "__main__":
    unittest.main()
