import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame

from game_menu import GameMenu


class GameMenuEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.menu = GameMenu()
        self.menu.open()

    def test_escape_closes_menu_and_consumes_event(self):
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)

        self.assertTrue(self.menu.handle_event(event))
        self.assertFalse(self.menu.visible)

    def test_outside_click_closes_menu_and_consumes_event(self):
        outside_position = (self.menu.rect.left - 1, self.menu.rect.top)
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=outside_position,
        )

        self.assertTrue(self.menu.handle_event(event))
        self.assertFalse(self.menu.visible)
        self.assertIsNone(self.menu.take_action())

    def test_inside_click_does_not_close_menu_without_button_action(self):
        position = (self.menu.rect.left + 1, self.menu.rect.bottom - 1)
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=position,
        )

        self.assertTrue(self.menu.handle_event(event))
        self.assertTrue(self.menu.visible)
        self.assertIsNone(self.menu.take_action())

    def test_menu_button_click_keeps_existing_action(self):
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=self.menu.item_rects["save_game"].center,
        )

        self.assertTrue(self.menu.handle_event(event))
        self.assertTrue(self.menu.visible)
        self.assertEqual("save_game", self.menu.take_action())

    def test_game_data_is_between_load_and_exit_and_opens_without_confirmation(self):
        self.assertEqual(
            [item["id"] for item in self.menu.items],
            ["new_game", "save_game", "load_game", "game_data", "exit_game"],
        )
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=self.menu.item_rects["game_data"].center,
        )
        self.assertTrue(self.menu.handle_event(event))
        self.assertEqual(self.menu.take_action(), "game_data")
        self.assertIsNone(self.menu.confirmation)

    def test_exit_action_is_forwarded_to_the_central_exit_flow(self):
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": self.menu.item_rects["exit_game"].center},
        )
        self.assertTrue(self.menu.handle_event(event))
        self.assertEqual(self.menu.take_action(), "exit_game")
        self.assertIsNone(self.menu.confirmation)


if __name__ == "__main__":
    unittest.main()
