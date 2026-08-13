from pathlib import Path
import sys
import unittest
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from animals import (
    AnimalMovementSystem, animal_move_crosses_forbidden,
    animal_position_is_forbidden, get_animal_placement_error,
)
from animal_troughs import get_forbidden_movement_rects


class DirectionSequence:
    def __init__(self, *directions):
        self.directions = iter(directions)

    def __call__(self, _choices):
        return next(self.directions)


class WaitSequence:
    def __init__(self, *wait_times):
        self.wait_times = iter(wait_times)

    def __call__(self, minimum, maximum):
        wait_time = next(self.wait_times)
        if not minimum <= wait_time <= maximum:
            raise AssertionError("A teszt várakozási ideje kívül esik a tartományon.")
        return wait_time


class AnimalMovementObstacleTests(unittest.TestCase):
    def setUp(self):
        self.pen = {
            "type": "animal_pen", "row": 10, "col": 10,
            "width": 4, "height": 4,
        }
        self.game_time = SimpleNamespace(time_speed_multiplier=1)

    def _animal(self, animal_type="cattle", row=11, col=10):
        return {
            "type": animal_type, "row": row, "col": col,
            "pen_row": 10, "pen_col": 10,
            "facing_direction": "down",
        }

    def test_both_species_reject_both_trough_tiles(self):
        forbidden = get_forbidden_movement_rects([self.pen])
        for animal_type in ("cattle", "pig", "chicken"):
            with self.subTest(animal_type=animal_type, trough="food"):
                self.assertTrue(animal_position_is_forbidden(10, 10, forbidden))
                self.assertIsNotNone(get_animal_placement_error(
                    [], [self.pen], 10, 10, animal_type,
                ))
            with self.subTest(animal_type=animal_type, trough="water"):
                self.assertTrue(animal_position_is_forbidden(10, 11, forbidden))
                self.assertIsNotNone(get_animal_placement_error(
                    [], [self.pen], 10, 11, animal_type,
                ))

    def test_invalid_target_is_retried_without_crossing_trough(self):
        animal = self._animal()
        movement = AnimalMovementSystem(DirectionSequence((-1, 0), (0, 1)))
        movement.reset(current_ticks=0)

        moved = movement.update(
            [animal], [self.pen], self.game_time, current_ticks=9000,
        )

        self.assertEqual(moved, 1)
        self.assertEqual((animal["row"], animal["col"]), (11, 11))
        forbidden = get_forbidden_movement_rects([self.pen])
        self.assertFalse(animal_position_is_forbidden(11, 11, forbidden))
        self.assertTrue(animal_move_crosses_forbidden(
            (11, 10), (10, 10), forbidden,
        ))

    def test_loaded_animal_is_relocated_even_while_paused(self):
        animal = self._animal(row=10, col=10)
        movement = AnimalMovementSystem()
        paused_time = SimpleNamespace(time_speed_multiplier=0)

        movement.update([animal], [self.pen], paused_time, current_ticks=0)

        forbidden = get_forbidden_movement_rects([self.pen])
        self.assertFalse(animal_position_is_forbidden(
            animal["row"], animal["col"], forbidden,
        ))
        self.assertIn(
            (animal["row"], animal["col"]),
            {(10 + row, 10 + col) for row in range(4) for col in range(4)},
        )

    def test_each_pen_group_has_only_its_own_obstacles(self):
        other_pen = {
            "type": "animal_pen", "row": 20, "col": 20,
            "width": 4, "height": 4,
        }
        first_rects = get_forbidden_movement_rects([self.pen])
        second_rects = get_forbidden_movement_rects([other_pen])

        self.assertTrue(animal_position_is_forbidden(10, 10, first_rects))
        self.assertFalse(animal_position_is_forbidden(20, 20, first_rects))
        self.assertTrue(animal_position_is_forbidden(20, 20, second_rects))
        self.assertFalse(animal_position_is_forbidden(10, 10, second_rects))

    def test_each_cycle_gets_a_new_wait_between_six_and_nine_seconds(self):
        animal = self._animal(row=12, col=12)
        movement = AnimalMovementSystem(
            DirectionSequence((0, 1), (0, -1)),
            WaitSequence(6200, 8700, 7000),
        )
        movement.reset(current_ticks=0)

        self.assertEqual(movement.update(
            [animal], [self.pen], self.game_time, current_ticks=6199,
        ), 0)
        self.assertEqual(movement.update(
            [animal], [self.pen], self.game_time, current_ticks=6200,
        ), 1)
        self.assertEqual(
            movement.movement_wait_times[id(animal)], 8700,
        )
        self.assertEqual(movement.update(
            [animal], [self.pen], self.game_time, current_ticks=14899,
        ), 0)
        self.assertEqual(movement.update(
            [animal], [self.pen], self.game_time, current_ticks=14900,
        ), 1)

    def test_double_speed_halves_real_wait_and_pause_stops_movement(self):
        animal = self._animal(row=12, col=12)
        movement = AnimalMovementSystem(
            DirectionSequence((0, 1)), WaitSequence(8000, 7000),
        )
        movement.reset(current_ticks=0)
        double_speed = SimpleNamespace(time_speed_multiplier=2)

        self.assertEqual(movement.update(
            [animal], [self.pen], double_speed, current_ticks=3999,
        ), 0)
        self.assertEqual(movement.update(
            [animal], [self.pen], double_speed, current_ticks=4000,
        ), 1)

        paused_time = SimpleNamespace(time_speed_multiplier=0)
        position = animal["row"], animal["col"]
        self.assertEqual(movement.update(
            [animal], [self.pen], paused_time, current_ticks=20000,
        ), 0)
        self.assertEqual((animal["row"], animal["col"]), position)

    def test_animals_keep_independent_wait_times(self):
        animals = [
            self._animal(row=12, col=11),
            self._animal(row=12, col=12),
        ]
        movement = AnimalMovementSystem(
            DirectionSequence((1, 0)), WaitSequence(6100, 8900),
        )
        movement.reset(current_ticks=0)
        movement.update(animals, [self.pen], self.game_time, current_ticks=1)

        self.assertEqual(
            [movement.movement_wait_times[id(animal)] for animal in animals],
            [6100, 8900],
        )

    def test_failed_cycle_also_receives_a_new_wait_time(self):
        animal = self._animal(row=13, col=13)
        movement = AnimalMovementSystem(
            DirectionSequence((1, 0), (1, 0), (1, 0), (1, 0)),
            WaitSequence(6000, 8500),
        )
        movement.reset(current_ticks=0)

        self.assertEqual(movement.update(
            [animal], [self.pen], self.game_time, current_ticks=6000,
        ), 0)
        self.assertEqual((animal["row"], animal["col"]), (13, 13))
        self.assertEqual(
            movement.movement_wait_times[id(animal)], 8500,
        )


if __name__ == "__main__":
    unittest.main()
