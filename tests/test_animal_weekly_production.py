from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from animal_troughs import FOOD_STOCK_KEY, WATER_STOCK_KEY
from animals import PIG_FATTENING_WEEKS, run_weekly_animal_cycle


class AnimalWeeklyProductionTests(unittest.TestCase):
    def setUp(self):
        self.warehouse = {
            "type": "warehouse", "row": 2, "col": 2,
            "width": 5, "height": 4, "capacity": 5_000,
            "inventory": {},
        }

    @staticmethod
    def _pens(row, start_col, count):
        return [
            {
                "type": "animal_pen", "row": row,
                "col": start_col + index * 4,
                "width": 4, "height": 4,
            }
            for index in range(count)
        ]

    @staticmethod
    def _animals(animal_type, count, pens, finishing_count=0):
        tiles = [
            (pen["row"] + row, pen["col"] + col)
            for pen in pens
            for row in range(pen["height"])
            for col in range(pen["width"])
        ]
        animals = []
        for index in range(count):
            animal = {
                "type": animal_type,
                "row": tiles[index][0], "col": tiles[index][1],
                "pen_row": pens[0]["row"], "pen_col": pens[0]["col"],
                "visual_id": index + 1,
                "facing_direction": "down",
            }
            if animal_type == "pig":
                animal["fattening_weeks"] = (
                    PIG_FATTENING_WEEKS - 1 if index < finishing_count else 0
                )
            animals.append(animal)
        return animals

    @staticmethod
    def _supply_group(pens, animal_count, food=None, water=None):
        pens[0][FOOD_STOCK_KEY] = animal_count if food is None else food
        pens[0][WATER_STOCK_KEY] = animal_count if water is None else water

    def _run_population(
            self, cattle_count, pig_count, finishing_pigs=0,
            pig_food=None, pig_water=None):
        cattle_pens = self._pens(10, 10, 1) if cattle_count else []
        pig_pen_count = (pig_count + 3) // 4
        pig_pens = self._pens(20, 10, pig_pen_count) if pig_count else []
        cattle = self._animals("cattle", cattle_count, cattle_pens)
        pigs = self._animals(
            "pig", pig_count, pig_pens, finishing_count=finishing_pigs,
        )
        if cattle:
            self._supply_group(cattle_pens, cattle_count)
        if pigs:
            self._supply_group(
                pig_pens, pig_count, food=pig_food, water=pig_water,
            )
        animals = cattle + pigs
        buildings = [self.warehouse, *cattle_pens, *pig_pens]

        run_weekly_animal_cycle(animals, buildings, economy=None)

        return animals, self.warehouse["inventory"]

    def test_four_cattle_produce_four_milk_and_four_manure(self):
        _animals, inventory = self._run_population(4, 0)
        self.assertEqual(inventory.get("milk"), 4)
        self.assertEqual(inventory.get("manure"), 4)

    def test_twenty_four_pigs_produce_twenty_four_manure(self):
        _animals, inventory = self._run_population(0, 24)
        self.assertEqual(inventory.get("manure"), 24)

    def test_combined_population_produces_exact_total(self):
        _animals, inventory = self._run_population(4, 24)
        self.assertEqual(inventory.get("milk"), 4)
        self.assertEqual(inventory.get("manure"), 28)

    def test_finishing_pigs_produce_manure_before_removal(self):
        animals, inventory = self._run_population(0, 24, finishing_pigs=2)
        self.assertEqual(inventory.get("manure"), 24)
        self.assertEqual(inventory.get("pork"), 20)
        self.assertEqual(len(animals), 22)

    def test_all_finishing_pigs_are_processed_without_iteration_skips(self):
        animals, inventory = self._run_population(0, 24, finishing_pigs=24)
        self.assertEqual(inventory.get("manure"), 24)
        self.assertEqual(inventory.get("pork"), 240)
        self.assertEqual(animals, [])

    def test_under_supplied_group_has_no_partial_production(self):
        _animals, inventory = self._run_population(
            0, 24, pig_food=24, pig_water=22,
        )
        self.assertEqual(inventory.get("manure", 0), 0)
        self.assertEqual(inventory.get("pork", 0), 0)


if __name__ == "__main__":
    unittest.main()
