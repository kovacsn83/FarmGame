import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from buildings import get_total_inventory, place_building
from constants import GRASS
from economy import Economy
from game_state import GameState
from inventory import get_marketable_item_ids
from orchards import (
    ORCHARD_TREE_SLOT_OFFSETS, TREE_TYPES, can_plant_tree, find_tree_at,
    draw_orchard_trees, get_tree_age_years, get_tree_tooltip_lines, plant_tree,
    run_weekly_orchard_cycle, TREE_CANOPY_LIGHT_OFFSET,
    TREE_GROUND_SHADOW_OFFSET,
)
from building_renderers import (
    PROCEDURAL_LIGHT_DIRECTION, PROCEDURAL_SHADOW_OFFSET,
)
from save_system import load_game, save_game
from screen_layout import set_camera, set_screen_size
from time_system import GameTime
from ui import OrchardSelectionPanel


class OrchardTreeTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        set_screen_size(1000, 800)
        set_camera(None)
        self.world = [[GRASS for _ in range(100)] for _ in range(80)]
        self.buildings = []
        self.orchard = place_building(
            self.world, self.buildings, 10, 10, "orchard",
        )
        self.warehouse = place_building(
            self.world, self.buildings, 20, 20, "warehouse",
        )
        self.economy = Economy(1000)

    def test_tree_catalog_and_popup_offer_apple(self):
        apple = TREE_TYPES["apple"]
        self.assertEqual("Alma", apple["name"])
        self.assertEqual(100, apple["planting_cost"])
        self.assertEqual(3, apple["first_yield_age_years"])
        self.assertEqual(30, apple["last_yield_age_years"])
        self.assertEqual(20, apple["annual_yield"])

        panel = OrchardSelectionPanel()
        panel.open()
        self.assertTrue(panel.visible)
        self.assertIn("apple", panel.card_rects)
        handled = panel.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": panel.card_rects["apple"].center},
        ))
        self.assertTrue(handled)
        self.assertEqual("apple", panel.take_selection())
        self.assertFalse(panel.visible)

    def test_orchard_has_four_fixed_slots_and_rejects_duplicate(self):
        self.assertEqual(4, len(ORCHARD_TREE_SLOT_OFFSETS))
        click_positions = ((10, 10), (10, 12), (12, 10), (12, 12))
        for expected_slot, (row, col) in enumerate(click_positions):
            tree = plant_tree(
                self.buildings, self.economy, row, col, "apple",
            )
            self.assertIsNotNone(tree)
            self.assertEqual(expected_slot, tree["slot"])
        self.assertEqual(4, len(self.orchard["trees"]))
        self.assertEqual(600, self.economy.money)

        self.assertFalse(can_plant_tree(
            self.buildings, 11, 11, "apple",
        ))
        self.assertIsNone(plant_tree(
            self.buildings, self.economy, 11, 11, "apple",
        ))
        self.assertEqual(600, self.economy.money)

    def test_tree_is_only_plantable_inside_orchard(self):
        self.assertFalse(can_plant_tree(self.buildings, 1, 1, "apple"))
        self.assertIsNone(plant_tree(
            self.buildings, self.economy, 1, 1, "apple",
        ))
        self.assertEqual(1000, self.economy.money)

    def test_apple_tree_first_produces_at_three_years_then_once_per_year(self):
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "apple",
        )
        for _ in range(3 * 52 - 1):
            self.assertEqual({}, run_weekly_orchard_cycle(self.buildings))
        self.assertEqual(0, get_total_inventory(self.buildings)["apple"])

        self.assertEqual(
            {"apple": 20}, run_weekly_orchard_cycle(self.buildings),
        )
        self.assertEqual(3, get_tree_age_years(tree))
        self.assertEqual(20, get_total_inventory(self.buildings)["apple"])
        self.assertEqual({}, run_weekly_orchard_cycle(self.buildings))
        self.assertEqual(20, get_total_inventory(self.buildings)["apple"])

        for _ in range(51):
            run_weekly_orchard_cycle(self.buildings)
        self.assertEqual(40, get_total_inventory(self.buildings)["apple"])

    def test_thirtieth_year_is_last_productive_year(self):
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "apple",
        )
        tree["age_weeks"] = 30 * 52 - 1
        self.assertEqual(
            {"apple": 20}, run_weekly_orchard_cycle(self.buildings),
        )
        for _ in range(52):
            self.assertEqual({}, run_weekly_orchard_cycle(self.buildings))
        self.assertEqual(31, get_tree_age_years(tree))
        self.assertEqual(20, get_total_inventory(self.buildings)["apple"])
        self.assertIn("Már nem termő", get_tree_tooltip_lines(tree))

    def test_apple_is_stored_but_not_marketable(self):
        self.assertNotIn("apple", get_marketable_item_ids())
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "apple",
        )
        tree["age_weeks"] = 3 * 52 - 1
        run_weekly_orchard_cycle(self.buildings)
        self.assertEqual(20, self.warehouse["inventory"]["apple"])

    def test_tree_has_procedural_graphic_and_age_tooltip(self):
        tree = plant_tree(
            self.buildings, self.economy, 10, 10, "apple",
        )
        surface = pygame.Surface((1000, 800))
        surface.fill((0, 0, 0))
        draw_orchard_trees(surface, self.buildings)
        # A bal felső fahely közepe: (11, 11) csempe, a felső HUD eltolásával.
        self.assertNotEqual((0, 0, 0), surface.get_at((220, 270))[:3])
        self.assertEqual(
            TREE_TYPES["apple"]["canopy_light_color"],
            surface.get_at((216, 274))[:3],
        )
        self.assertEqual(
            TREE_TYPES["apple"]["canopy_color"],
            surface.get_at((228, 262))[:3],
        )

        tree["age_weeks"] = 2 * 52
        tooltip = get_tree_tooltip_lines(tree)
        self.assertIn("Még nem termő", tooltip)
        self.assertIn("1 év múlva", tooltip)
        tree["age_weeks"] = 5 * 52
        tree["last_produced_year"] = 5
        tooltip = get_tree_tooltip_lines(tree)
        self.assertIn("Termő", tooltip)
        self.assertIn("6. életév", tooltip)

    def test_tree_shading_uses_the_shared_lower_left_light_direction(self):
        self.assertEqual((-1, 1), PROCEDURAL_LIGHT_DIRECTION)
        self.assertEqual((-4, 4), TREE_CANOPY_LIGHT_OFFSET)
        self.assertEqual(
            PROCEDURAL_SHADOW_OFFSET,
            TREE_GROUND_SHADOW_OFFSET,
        )
        self.assertGreater(TREE_GROUND_SHADOW_OFFSET[0], 0)
        self.assertLess(TREE_GROUND_SHADOW_OFFSET[1], 0)

    def test_tree_round_trip_and_old_empty_orchard_compatibility(self):
        tree = plant_tree(
            self.buildings, self.economy, 12, 12, "apple",
        )
        tree["age_weeks"] = 5 * 52 + 12
        tree["last_produced_year"] = 5
        state = GameState(
            self.world, [], self.buildings, self.economy,
            GameTime(start_ticks=0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orchard-trees.json"
            self.assertTrue(save_game(state, path))
            self.orchard["trees"].clear()
            self.assertTrue(load_game(state, path))

        loaded_orchard = next(
            item for item in state.buildings if item["type"] == "orchard"
        )
        loaded_tree = loaded_orchard["trees"][0]
        self.assertEqual("apple", loaded_tree["type"])
        self.assertEqual(5 * 52 + 12, loaded_tree["age_weeks"])
        self.assertEqual(5, loaded_tree["last_produced_year"])
        self.assertIsNotNone(find_tree_at(state.buildings, 13, 13))

        loaded_orchard.pop("trees")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-empty-orchard.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))
        self.assertEqual([], next(
            item for item in state.buildings if item["type"] == "orchard"
        )["trees"])


if __name__ == "__main__":
    unittest.main()
