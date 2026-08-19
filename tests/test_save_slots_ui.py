import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from save_slots_ui import LoadSlotsMenu, SaveSlotsMenu
from screen_layout import set_screen_size


def empty_slots():
    return [
        {"slot_id": slot_id, "status": "empty"}
        for slot_id in range(1, 9)
    ]


def slots_with_valid_first():
    slots = empty_slots()
    slots[0] = {
        "slot_id": 1, "status": "valid", "save_name": "Teszt",
        "game_day": 1, "saved_at": "2026-08-19 08:00",
    }
    return slots


class SaveSlotsPopupBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        set_screen_size(1500, 1000)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def _open(self, menu):
        with patch("save_slots_ui.get_save_slots", return_value=empty_slots()):
            menu.open()
        return menu

    @staticmethod
    def _outside_event(menu, button=1):
        return pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": button, "pos": (menu.rect.left - 1, menu.rect.top)},
        )

    def test_save_popup_outside_click_closes_and_is_consumed(self):
        menu = self._open(SaveSlotsMenu())
        self.assertTrue(menu.handle_event(self._outside_event(menu), 0))
        self.assertFalse(menu.visible)
        self.assertEqual("game_menu", menu.take_navigation())

    def test_load_popup_outside_click_closes_and_is_consumed(self):
        menu = self._open(LoadSlotsMenu())
        self.assertTrue(menu.handle_event(self._outside_event(menu)))
        self.assertFalse(menu.visible)
        self.assertEqual("game_menu", menu.take_navigation())

    def test_inside_click_keeps_both_popups_open(self):
        for menu in (SaveSlotsMenu(), LoadSlotsMenu()):
            with self.subTest(menu=type(menu).__name__):
                self._open(menu)
                event = pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {"button": 1, "pos": menu.rect.center},
                )
                if isinstance(menu, SaveSlotsMenu):
                    self.assertTrue(menu.handle_event(event, 0))
                else:
                    self.assertTrue(menu.handle_event(event))
                self.assertTrue(menu.visible)

    def test_mouse_wheel_does_not_close_popups(self):
        for menu in (SaveSlotsMenu(), LoadSlotsMenu()):
            with self.subTest(menu=type(menu).__name__):
                self._open(menu)
                wheel = pygame.event.Event(
                    pygame.MOUSEWHEEL, {"x": 0, "y": -1},
                )
                if isinstance(menu, SaveSlotsMenu):
                    self.assertTrue(menu.handle_event(wheel, 0))
                else:
                    self.assertTrue(menu.handle_event(wheel))
                self.assertTrue(menu.visible)

    def test_legacy_wheel_button_does_not_close_popups(self):
        for menu in (SaveSlotsMenu(), LoadSlotsMenu()):
            with self.subTest(menu=type(menu).__name__):
                self._open(menu)
                wheel = self._outside_event(menu, button=4)
                if isinstance(menu, SaveSlotsMenu):
                    self.assertTrue(menu.handle_event(wheel, 0))
                else:
                    self.assertTrue(menu.handle_event(wheel))
                self.assertTrue(menu.visible)

    def test_slot_selection_behavior_is_unchanged(self):
        save_menu = self._open(SaveSlotsMenu())
        self.assertTrue(save_menu.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": save_menu.slot_rects[1].center},
        ), 0))
        self.assertEqual("name", save_menu.state)
        self.assertEqual(1, save_menu.selected_slot_id)

        load_menu = LoadSlotsMenu()
        with patch(
            "save_slots_ui.get_save_slots", return_value=slots_with_valid_first(),
        ):
            load_menu.open()
        self.assertTrue(load_menu.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": load_menu.slot_rects[1].center},
        )))
        self.assertEqual(1, load_menu.selected_slot_id)
        self.assertTrue(load_menu.visible)

    def test_outside_click_deactivates_save_name_input(self):
        menu = self._open(SaveSlotsMenu())
        menu.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": menu.slot_rects[1].center},
        ), 0)
        self.assertTrue(menu.text_input.active)
        self.assertTrue(menu.handle_event(self._outside_event(menu), 0))
        self.assertFalse(menu.text_input.active)
        self.assertFalse(menu.visible)

    def test_escape_still_closes_slot_view(self):
        escape = pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_ESCAPE},
        )
        for menu in (SaveSlotsMenu(), LoadSlotsMenu()):
            with self.subTest(menu=type(menu).__name__):
                self._open(menu)
                if isinstance(menu, SaveSlotsMenu):
                    self.assertTrue(menu.handle_event(escape, 0))
                else:
                    self.assertTrue(menu.handle_event(escape))
                self.assertFalse(menu.visible)
                self.assertEqual("game_menu", menu.take_navigation())


if __name__ == "__main__":
    unittest.main()
