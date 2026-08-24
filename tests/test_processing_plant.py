import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame

from building_renderers import (
    draw_processing_plant, has_procedural_renderer,
)
from buildings import (
    BUILDING_TYPES, BUILD_OPTIONS, can_place_building, place_building,
    remove_building,
)
from constants import (
    BUILDING, GRASS, PROCESSING_PLANT_BUILD_COST, ROAD, TILE_SIZE,
)
from economy import Economy
from game_state import GameState
from maintenance import calculate_annual_maintenance
from processing import (
    PROCESSING_RECIPES, complete_processing_batch, start_processing_batch,
    select_processing_recipe,
)
from save_system import load_game, save_game
from screen_layout import set_camera, set_screen_size, world_to_screen
from time_system import GameTime
from ui import BuildingSelectionPanel, InfoPanel


class ProcessingPlantTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1, 1))
        set_screen_size(1000, 800)
        set_camera(None)
        self.world = [[GRASS for _ in range(40)] for _ in range(35)]
        self.buildings = []

    def tearDown(self):
        pygame.quit()

    def _add_road_above(self, row, col):
        for offset in range(6):
            self.world[row - 1][col + offset] = ROAD

    def test_catalog_and_building_menu_use_the_central_definition(self):
        definition = BUILDING_TYPES["processing_plant"]
        self.assertIs(BUILD_OPTIONS["processing_plant"], definition)
        self.assertEqual("Feldolgozó üzem", definition["name"])
        self.assertEqual((6, 5), (definition["width"], definition["height"]))
        self.assertEqual(3000.0, definition["build_cost"])
        self.assertEqual(PROCESSING_PLANT_BUILD_COST, definition["build_cost"])
        self.assertEqual(300.0, calculate_annual_maintenance(3000.0))
        self.assertEqual(
            ("canned_tomato", "cheese", "apple_juice"),
            definition["recipes"],
        )

        panel = BuildingSelectionPanel()
        panel.open()
        self.assertIn("processing_plant", panel.card_rects)

    def test_road_rule_and_full_footprint_are_enforced(self):
        self.assertFalse(can_place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        ))
        self._add_road_above(8, 8)
        self.assertTrue(can_place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        ))
        plant = place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        )
        self.assertTrue(all(
            self.world[row][col] == BUILDING
            for row in range(8, 13) for col in range(8, 14)
        ))
        self.assertFalse(can_place_building(
            self.world, self.buildings, 9, 9, "warehouse",
        ))

        self.assertTrue(remove_building(self.world, self.buildings, plant))
        self.assertTrue(all(
            self.world[row][col] == GRASS
            for row in range(8, 13) for col in range(8, 14)
        ))

    def test_renderer_and_information_view_are_registered(self):
        plant = place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        )
        self.assertTrue(has_procedural_renderer("processing_plant"))
        surface = pygame.Surface((1000, 800))
        surface.fill((1, 2, 3))
        draw_processing_plant(surface, plant)
        x, y = map(round, world_to_screen(8 * TILE_SIZE, 8 * TILE_SIZE))
        self.assertNotEqual((1, 2, 3), surface.get_at((x + 10, y + 10))[:3])

        info = InfoPanel()
        self.assertTrue(info.open_for_building(plant))
        self.assertEqual("processing_plant", info.building_type)

    def test_selected_product_row_toggles_the_plant_off_and_on(self):
        plant = place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        )
        info = InfoPanel()
        self.assertTrue(info.open_for_building(plant))
        surface = pygame.Surface((1000, 800))
        font = pygame.font.Font(None, 20)
        state = GameState(
            self.world, [], self.buildings, Economy(),
            GameTime(start_ticks=0),
        )
        info.draw(surface, font, state)
        row = info.processing_recipe_rects["canned_tomato"]

        info.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": row.center, "button": 1},
        ))
        self.assertIsNone(plant["active_recipe"])

        captured_text = []
        original_draw_text = info.draw_text

        def capture_text(screen, draw_font, text, x, y):
            captured_text.append(text)
            original_draw_text(screen, draw_font, text, x, y)

        with patch.object(info, "draw_text", side_effect=capture_text):
            info.draw(surface, font, state)
        self.assertIn("Állapot: Leállítva", captured_text)
        self.assertIn("  Nincs kiválasztott termék.", captured_text)

        row = info.processing_recipe_rects["canned_tomato"]
        info.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": row.center, "button": 1},
        ))
        self.assertEqual("canned_tomato", plant["active_recipe"])

    def test_cheese_recipe_is_selectable_and_updates_input_and_output_rows(self):
        plant = place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        )
        info = InfoPanel()
        self.assertTrue(info.open_for_building(plant))
        surface = pygame.Surface((1000, 800))
        font = pygame.font.Font(None, 20)
        state = GameState(
            self.world, [], self.buildings, Economy(), GameTime(start_ticks=0),
        )
        info.draw(surface, font, state)
        self.assertEqual(
            {"canned_tomato", "cheese", "apple_juice"},
            set(info.processing_recipe_rects),
        )
        cheese_row = info.processing_recipe_rects["cheese"]
        info.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": cheese_row.center, "button": 1},
        ))
        self.assertEqual("cheese", plant["active_recipe"])

        captured_text = []
        with patch.object(
                info, "draw_text",
                side_effect=lambda screen, draw_font, text, x, y:
                captured_text.append(text)):
            info.draw(surface, font, state)
        self.assertIn("  Tej: 0 db", captured_text)
        self.assertIn("  Paradicsomkonzerv: 0 db", captured_text)
        self.assertIn("  Sajt: 0 db", captured_text)
        self.assertIn("  Almalé: 0 db", captured_text)

    def test_product_rows_select_the_next_recipe_without_stopping_active_batch(self):
        second_recipe = {
            "name": "Almalé",
            "input_product": "wheat",
            "input_amount": 1,
            "output_product": "apple",
            "output_amount": 1,
            "weekly_capacity": 5,
        }
        with (
            patch.dict(PROCESSING_RECIPES, {"apple_juice": second_recipe}),
            patch.dict(
                BUILDING_TYPES["processing_plant"],
                {"recipes": ("canned_tomato", "apple_juice")},
            ),
        ):
            plant = place_building(
                self.world, self.buildings, 8, 8, "processing_plant",
            )
            plant["processing_inventory"]["tomato"] = 1
            plant["processing_inventory"]["wheat"] = 5
            self.assertEqual(1, start_processing_batch(plant, 1))

            info = InfoPanel()
            self.assertTrue(info.open_for_building(plant))
            surface = pygame.Surface((1000, 800))
            font = pygame.font.Font(None, 20)
            state = GameState(
                self.world, [], self.buildings, Economy(),
                GameTime(start_ticks=0),
            )
            captured_text = []
            original_draw_text = info.draw_text

            def capture_text(screen, draw_font, text, x, y):
                captured_text.append(text)
                original_draw_text(screen, draw_font, text, x, y)

            with patch.object(info, "draw_text", side_effect=capture_text):
                info.draw(surface, font, state)

            self.assertNotIn("Aktív recept", "\n".join(captured_text))
            self.assertIn("Gyártandó termék:", captured_text)
            self.assertEqual(
                {"canned_tomato", "apple_juice"},
                set(info.processing_recipe_rects),
            )

            row = info.processing_recipe_rects["apple_juice"]
            info.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, {"pos": row.center, "button": 1},
            ))
            self.assertEqual("apple_juice", plant["active_recipe"])
            self.assertEqual(
                "canned_tomato", plant["processing_batch"]["recipe_id"],
            )

            self.assertEqual(1, complete_processing_batch(plant, 2))
            self.assertEqual(5, start_processing_batch(plant, 2))
            self.assertEqual(
                "apple_juice", plant["processing_batch"]["recipe_id"],
            )

            captured_text.clear()
            with patch.object(info, "draw_text", side_effect=capture_text):
                info.draw(surface, font, state)
            self.assertIn("  Búza: 0 db", captured_text)
            self.assertIn("  Paradicsomkonzerv: 1 db", captured_text)
            self.assertIn("  Alma: 0 db", captured_text)

            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "selected-processing-recipe.json"
                self.assertTrue(save_game(state, path))
                self.assertTrue(load_game(state, path))
            loaded = state.buildings[0]
            self.assertEqual("apple_juice", loaded["active_recipe"])
            self.assertEqual(
                "apple_juice", loaded["processing_batch"]["recipe_id"],
            )

    def test_save_load_preserves_position_and_footprint(self):
        plant = place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        )
        plant["processing_inventory"]["tomato"] = 4
        plant["processing_inventory"]["canned_tomato"] = 7
        plant["processing_inventory"]["cheese"] = 9
        plant["processing_week"] = 12
        plant["processed_this_week"] = 3
        plant["processing_batch"] = {
            "recipe_id": "canned_tomato",
            "started_week": 12,
            "inputs": {"tomato": 3},
            "outputs": {"canned_tomato": 3},
        }
        plant["active_recipe"] = None
        state = GameState(
            self.world, [], self.buildings, Economy(), GameTime(start_ticks=0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "processing-plant.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(remove_building(self.world, self.buildings, plant))
            self.assertTrue(load_game(state, path))

        loaded = state.buildings[0]
        self.assertEqual("processing_plant", loaded["type"])
        self.assertEqual((8, 8, 6, 5), (
            loaded["row"], loaded["col"], loaded["width"], loaded["height"],
        ))
        self.assertEqual(4, loaded["processing_inventory"]["tomato"])
        self.assertEqual(7, loaded["processing_inventory"]["canned_tomato"])
        self.assertEqual(9, loaded["processing_inventory"]["cheese"])
        self.assertEqual(12, loaded["processing_week"])
        self.assertEqual(3, loaded["processed_this_week"])
        self.assertEqual(12, loaded["processing_batch"]["started_week"])
        self.assertIsNone(loaded["active_recipe"])
        self.assertEqual(
            3, loaded["processing_batch"]["outputs"]["canned_tomato"],
        )

    def test_save_load_preserves_active_cheese_batch_and_inventory(self):
        plant = place_building(
            self.world, self.buildings, 8, 8, "processing_plant",
        )
        self.assertTrue(select_processing_recipe(plant, "cheese"))
        plant["processing_inventory"]["milk"] = 8
        self.assertEqual(5, start_processing_batch(plant, 12))
        plant["processing_inventory"]["cheese"] = 4
        state = GameState(
            self.world, [], self.buildings, Economy(), GameTime(start_ticks=0),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cheese-processing.json"
            self.assertTrue(save_game(state, path))
            self.assertTrue(load_game(state, path))

        loaded = state.buildings[0]
        self.assertEqual("cheese", loaded["active_recipe"])
        self.assertEqual(3, loaded["processing_inventory"]["milk"])
        self.assertEqual(4, loaded["processing_inventory"]["cheese"])
        self.assertEqual("cheese", loaded["processing_batch"]["recipe_id"])
        self.assertEqual({"milk": 5}, loaded["processing_batch"]["inputs"])
        self.assertEqual({"cheese": 5}, loaded["processing_batch"]["outputs"])


if __name__ == "__main__":
    unittest.main()
