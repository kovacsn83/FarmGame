from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from animals import (
    ANIMAL_TYPES, SLAUGHTER_STATE_KEY, SLAUGHTER_WAITING_FOR_STORAGE,
    produce_weekly_animal_products, retry_waiting_animal_slaughters,
)
from economy import Economy
from notification_system import NotificationManager
from progress_tooltips import get_animal_progress_lines
from save_system import _migrate_legacy_crop_data, _validate_animals
from storage_blocking import StorageBlockManager
from time_system import GameTime, TIME_NORMAL, TIME_PAUSED


class AnimalStorageBlockingTests(unittest.TestCase):
    def setUp(self):
        self.pen = {
            "type": "animal_pen", "row": 10, "col": 10,
            "width": 4, "height": 4,
        }
        self.warehouse = {
            "type": "warehouse", "row": 2, "col": 2,
            "width": 5, "height": 4, "capacity": 500,
            "inventory": {},
        }
        self.buildings = [self.pen, self.warehouse]
        self.notifications = NotificationManager(start_ticks=0)
        self.game_time = GameTime(current_time_speed=TIME_NORMAL, start_ticks=0)
        self.guard = StorageBlockManager(self.notifications, self.game_time)

    @staticmethod
    def _animal(animal_type, visual_id=1, waiting=False):
        production = next(iter(
            ANIMAL_TYPES[animal_type]["periodic_products"].values()
        ))
        animal = {
            "type": animal_type,
            "row": 10, "col": 10 + visual_id - 1,
            "pen_row": 10, "pen_col": 10,
            "visual_id": visual_id, "facing_direction": "down",
            production["counter_key"]: production["interval_weeks"],
        }
        if waiting:
            animal[SLAUGHTER_STATE_KEY] = SLAUGHTER_WAITING_FOR_STORAGE
        return animal

    def test_each_species_waits_at_maximum_counter_and_pauses_once(self):
        for animal_type in ("pig", "chicken", "cattle"):
            with self.subTest(animal_type=animal_type):
                self.setUp()
                animal = self._animal(animal_type)
                production = next(iter(
                    ANIMAL_TYPES[animal_type]["periodic_products"].values()
                ))
                weekly_total = sum(
                    ANIMAL_TYPES[animal_type].get("weekly_products", {}).values()
                )
                self.warehouse["capacity"] = weekly_total + production["amount"] - 1
                animals = [animal]

                produce_weekly_animal_products(
                    animals, self.buildings,
                    notification_manager=self.notifications,
                    storage_block_manager=self.guard,
                )

                self.assertEqual(animals, [animal])
                self.assertEqual(
                    animal[production["counter_key"]],
                    production["interval_weeks"],
                )
                self.assertEqual(
                    animal[SLAUGHTER_STATE_KEY],
                    SLAUGHTER_WAITING_FOR_STORAGE,
                )
                self.assertEqual(self.game_time.current_time_speed, TIME_PAUSED)
                self.assertIn("Nincs elegendő hely", self.notifications.current_message)
                queue_size = len(self.notifications.queue)
                produce_weekly_animal_products(
                    animals, self.buildings,
                    notification_manager=self.notifications,
                    storage_block_manager=self.guard,
                )
                self.assertEqual(len(self.notifications.queue), queue_size)

    def test_capacity_release_retries_without_another_week(self):
        pig = self._animal("pig", waiting=True)
        animals = [pig]
        self.warehouse["capacity"] = 10
        self.warehouse["inventory"] = {"wheat": 10, "pork": 0}
        self.guard.report("storage:animal_slaughter:pig", "blocked")
        self.warehouse["inventory"]["wheat"] = 0

        resumed = retry_waiting_animal_slaughters(
            animals, self.buildings, self.notifications, self.guard,
        )

        self.assertEqual(resumed, 1)
        self.assertEqual(animals, [])
        self.assertEqual(self.warehouse["inventory"]["pork"], 10)
        self.assertNotIn("storage:animal_slaughter:pig", self.guard.active_events)

    def test_partial_capacity_slaughters_only_animals_whose_meat_fits(self):
        animals = [self._animal("pig", index, waiting=True) for index in (1, 2, 3)]
        self.warehouse["capacity"] = 25

        resumed = retry_waiting_animal_slaughters(
            animals, self.buildings, self.notifications, self.guard,
        )

        self.assertEqual(resumed, 2)
        self.assertEqual(len(animals), 1)
        self.assertEqual(self.warehouse["inventory"]["pork"], 20)
        self.assertEqual(
            animals[0][SLAUGHTER_STATE_KEY], SLAUGHTER_WAITING_FOR_STORAGE,
        )
        self.assertIn("Nincs elegendő hely", self.notifications.current_message)

    def test_market_sale_emits_capacity_changed_event_and_retries(self):
        pig = self._animal("pig", waiting=True)
        animals = [pig]
        self.warehouse["capacity"] = 20
        self.warehouse["inventory"] = {"wheat": 20, "pork": 0}
        self.buildings.append({
            "type": "market", "row": 2, "col": 10,
            "width": 4, "height": 4,
        })
        economy = Economy()
        economy.bind_storage_capacity_changed(
            lambda: retry_waiting_animal_slaughters(
                animals, self.buildings, self.notifications, self.guard,
            )
        )

        self.assertTrue(economy.sell_item(self.buildings, "wheat"))

        self.assertEqual(animals, [])
        self.assertEqual(self.warehouse["inventory"]["pork"], 10)

    def test_waiting_state_is_visible_in_tooltip(self):
        lines = get_animal_progress_lines(
            self._animal("pig", waiting=True), ANIMAL_TYPES,
        )

        self.assertIn("Levágásra vár", lines)
        self.assertIn("Nincs elegendő hely a Raktárban", lines)

    def test_waiting_state_and_maximum_counter_are_save_compatible(self):
        pig = self._animal("pig", waiting=True)
        data = {"animals": [pig], "buildings": self.buildings, "fields": []}

        _migrate_legacy_crop_data(data)

        self.assertTrue(_validate_animals(data))
        self.assertEqual(
            pig[SLAUGHTER_STATE_KEY], SLAUGHTER_WAITING_FOR_STORAGE,
        )


if __name__ == "__main__":
    unittest.main()
