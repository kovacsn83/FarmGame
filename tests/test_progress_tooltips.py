from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from progress_tooltips import (
    format_progress, get_animal_progress_lines, get_field_progress_lines,
)
from fields import prepare_harvest, preview_harvest_yield


ANIMAL_TYPES = {
    "pig": {
        "name": "Sertés",
        "periodic_products": {
            "pork": {
                "interval_weeks": 52,
                "counter_key": "fattening_weeks",
            },
        },
    },
    "cattle": {
        "name": "Szarvasmarha",
        "periodic_products": {
            "beef": {
                "interval_weeks": 104,
                "counter_key": "age_weeks",
                "progress_label": "Életkor",
                "remove_animal_after_production": True,
            },
        },
    },
}


def make_field(crop, growth_weeks, harvest_count=0, harvestable=False):
    return {
        "crop": crop,
        "growth_weeks": growth_weeks,
        "growth": 100 if harvestable else 0,
        "harvestable": harvestable,
        "harvest_count": harvest_count,
        "expires_at_week": None,
    }


class ProgressTooltipTests(unittest.TestCase):
    def test_generic_progress_clamps_and_marks_completion(self):
        self.assertEqual(
            format_progress("Érés", 40, 38, True, "Aratható"),
            ["Érés:", "38 / 38 hét", "Aratható"],
        )

    def test_wheat_and_corn_initial_growth(self):
        self.assertIn("18 / 38 hét", get_field_progress_lines(
            make_field("wheat", 18), 18,
        ))
        self.assertIn("7 / 21 hét", get_field_progress_lines(
            make_field("corn", 7), 7,
        ))

    def test_tomato_initial_and_regrowth_cycles(self):
        initial = get_field_progress_lines(make_field("tomato", 9, 0, True), 9)
        self.assertIn("9 / 9 hét", initial)
        self.assertIn("Aratható", initial)
        regrowth = get_field_progress_lines(make_field("tomato", 2, 1), 11)
        self.assertIn("Újratermés:", regrowth)
        self.assertIn("2 / 3 hét", regrowth)

    def test_alfalfa_regrowth_and_lifespan_end(self):
        initial = get_field_progress_lines(make_field("alfalfa", 4), 4)
        self.assertIn("4 / 10 hét", initial)
        regrowth = get_field_progress_lines(make_field("alfalfa", 5, 1, True), 15)
        self.assertIn("Aratások száma: 1", regrowth)
        self.assertFalse(any("..." in line for line in regrowth))
        self.assertIn("5 / 5 hét", regrowth)
        expired = make_field("alfalfa", 2, 4)
        expired["expires_at_week"] = 135
        self.assertIn(
            "Élettartama véget ért",
            get_field_progress_lines(expired, 135),
        )

    def test_mature_alfalfa_respects_harvest_season(self):
        field = make_field("alfalfa", 5, 4, True)
        in_season = get_field_progress_lines(
            field, current_elapsed_week=500, current_week=20,
        )
        self.assertIn("Aratható", in_season)
        out_of_season = get_field_progress_lines(
            field, current_elapsed_week=531, current_week=51,
            harvest_block_reason="outside_harvest_window",
        )
        self.assertNotIn("Aratható", out_of_season)
        self.assertIn("Érett – aratás csak a 15–40. hét", out_of_season)

    def test_season_rules_apply_to_all_mature_crops(self):
        cases = (
            ("wheat", 38, 0, 20, "26–33. hét"),
            ("corn", 21, 0, 20, "36–43. hét"),
            ("tomato", 9, 0, 20, "28–39. hét"),
            ("tomato", 3, 1, 20, "28–39. hét"),
        )
        for crop, weeks, harvest_count, current_week, interval in cases:
            with self.subTest(crop=crop, harvest_count=harvest_count):
                lines = get_field_progress_lines(
                    make_field(crop, weeks, harvest_count, True),
                    current_elapsed_week=100,
                    current_week=current_week,
                    harvest_block_reason="outside_harvest_window",
                )
                self.assertNotIn("Aratható", lines)
                self.assertTrue(any(interval in line for line in lines))

    def test_task_and_capacity_block_reasons_replace_harvestable(self):
        field = make_field("wheat", 38, 0, True)
        active = get_field_progress_lines(
            field, 100, 30, "harvest_active",
        )
        waiting = get_field_progress_lines(
            field, 100, 30, "harvest_waiting",
        )
        no_capacity = get_field_progress_lines(
            field, 100, 30, "no_capacity",
        )
        self.assertIn("Aratás folyamatban", active)
        self.assertIn("Aratás várakozik", waiting)
        self.assertIn("Érett – nincs elegendő Raktárkapacitás", no_capacity)
        self.assertNotIn("Aratható", active + waiting + no_capacity)

    def test_harvest_preview_matches_transaction_without_consuming_randomness(self):
        field = make_field("wheat", 38, 0, True)
        field["field_type"] = "field_4x4"
        warehouse = {
            "type": "warehouse", "capacity": 500,
            "inventory": {"wheat": 0},
        }
        random.seed(12345)
        state_before = random.getstate()
        preview = preview_harvest_yield(field)
        self.assertEqual(random.getstate(), state_before)
        prepared = prepare_harvest(field, [warehouse])
        self.assertEqual(preview, prepared["amount"])

    def test_pig_fattening_and_ready_state(self):
        progress = get_animal_progress_lines(
            {"type": "pig", "fattening_weeks": 31}, ANIMAL_TYPES,
        )
        self.assertIn("31 / 52 hét", progress)
        ready = get_animal_progress_lines(
            {"type": "pig", "fattening_weeks": 52}, ANIMAL_TYPES,
        )
        self.assertIn("Vágásra kész", ready)

    def test_cattle_age_progress(self):
        progress = get_animal_progress_lines(
            {"type": "cattle", "age_weeks": 58}, ANIMAL_TYPES,
        )
        self.assertIn("Életkor:", progress)
        self.assertIn("58 / 104 hét", progress)


if __name__ == "__main__":
    unittest.main()
