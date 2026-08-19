from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pygame


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app_state import AppState, AppStateManager, SPLASH_DURATION_MS
from asset_loader import load_splash_image
from screen_layout import set_screen_size
from startup_ui import MainMenu, SplashScreen
import main as main_module


class StartupFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_application_starts_in_splash_and_changes_after_three_seconds(self):
        manager = AppStateManager(start_ticks=100)
        self.assertEqual(SPLASH_DURATION_MS, 3000)
        self.assertEqual(manager.state, AppState.SPLASH)
        self.assertFalse(manager.update(100 + SPLASH_DURATION_MS - 1))
        self.assertEqual(manager.state, AppState.SPLASH)
        self.assertTrue(manager.update(100 + SPLASH_DURATION_MS))
        self.assertEqual(manager.state, AppState.MAIN_MENU)

    def test_new_or_loaded_game_can_enter_playing_state(self):
        manager = AppStateManager(start_ticks=0)
        manager.show_main_menu()
        manager.start_playing()
        self.assertEqual(manager.state, AppState.PLAYING)

    def test_real_splash_asset_loads(self):
        image = load_splash_image()
        self.assertIsNotNone(image)
        self.assertEqual(image.get_size(), (1024, 1024))

    def test_splash_cover_preserves_aspect_ratio_and_fills_window(self):
        image = pygame.Surface((1024, 1024), pygame.SRCALPHA)
        splash = SplashScreen(image)
        rect = splash.get_image_rect((1500, 1000))
        self.assertEqual(rect, pygame.Rect(0, 0, 1500, 1000))
        self.assertEqual(rect.center, (750, 500))
        cover_size = splash.get_cover_size((1500, 1000))
        self.assertGreaterEqual(cover_size[0], 1500)
        self.assertGreaterEqual(cover_size[1], 1000)
        self.assertEqual(
            cover_size[0] / cover_size[1],
            image.get_width() / image.get_height(),
        )

    def test_splash_has_no_edge_gap_at_multiple_window_sizes(self):
        image = pygame.Surface((1024, 1024))
        image.fill((31, 31, 31))
        splash = SplashScreen(image)
        for size in ((1500, 1000), (1001, 777), (800, 1200), (641, 479)):
            with self.subTest(size=size):
                target = pygame.Surface(size)
                target.fill((0, 0, 0))
                splash.draw(target)
                self.assertEqual(splash._scaled_image.get_size(), size)
                edge_points = (
                    [(x, 0) for x in range(size[0])]
                    + [(x, size[1] - 1) for x in range(size[0])]
                    + [(0, y) for y in range(size[1])]
                    + [(size[0] - 1, y) for y in range(size[1])]
                )
                self.assertTrue(all(
                    target.get_at(point)[:3] != (0, 0, 0)
                    for point in edge_points
                ))

    def test_main_menu_exposes_only_the_three_startup_actions(self):
        set_screen_size(1500, 1000)
        menu = MainMenu()
        self.assertEqual(
            [item["id"] for item in menu.items],
            ["new_game", "load_game", "exit_game"],
        )
        for action in ("new_game", "load_game", "exit_game"):
            event = pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"button": 1, "pos": menu.button_rects[action].center},
            )
            self.assertTrue(menu.handle_event(event))
            self.assertEqual(menu.take_action(), action)

    def test_main_menu_does_not_initialize_the_farm_before_a_choice(self):
        manager = AppStateManager(start_ticks=0)
        manager.show_main_menu()
        quit_event = pygame.event.Event(pygame.QUIT)
        with (
            patch.object(main_module, "AppStateManager", return_value=manager),
            patch.object(main_module, "create_world") as create_world,
            patch.object(pygame.event, "get", return_value=[quit_event]),
        ):
            main_module.main()
        create_world.assert_not_called()
        pygame.init()
        pygame.display.set_mode((1, 1))

    def test_new_game_choice_initializes_once_and_enters_playing(self):
        set_screen_size(1500, 1000)
        manager = AppStateManager(start_ticks=0)
        manager.show_main_menu()
        menu = MainMenu()
        new_game_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": menu.button_rects["new_game"].center},
        )
        quit_event = pygame.event.Event(pygame.QUIT)
        real_create_world = main_module.create_world
        with (
            patch.object(main_module, "AppStateManager", return_value=manager),
            patch.object(
                main_module, "create_world", wraps=real_create_world,
            ) as create_world,
            patch.object(
                pygame.event, "get",
                side_effect=[[new_game_event], [quit_event]],
            ),
        ):
            main_module.main()
        self.assertEqual(manager.state, AppState.PLAYING)
        create_world.assert_called_once_with()
        pygame.init()
        pygame.display.set_mode((1, 1))


if __name__ == "__main__":
    unittest.main()
