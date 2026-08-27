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

from save_slots_ui import (
    BACKSPACE_REPEAT_DELAY_MS, BACKSPACE_REPEAT_INTERVAL_MS,
    LoadSlotsMenu, SaveSlotsMenu, TextInput,
)
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


class SaveNameBackspaceRepeatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        set_screen_size(1500, 1000)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    @staticmethod
    def key_event(event_type, key):
        return pygame.event.Event(event_type, {"key": key})

    def test_single_press_deletes_once_and_waits_for_initial_delay(self):
        text_input = TextInput()
        text_input.activate("abcdef")
        result = text_input.handle_event(
            self.key_event(pygame.KEYDOWN, pygame.K_BACKSPACE),
            current_ticks=1000,
        )
        self.assertEqual("changed", result)
        self.assertEqual("abcde", text_input.text)
        self.assertFalse(text_input.update(
            1000 + BACKSPACE_REPEAT_DELAY_MS - 1,
        ))
        self.assertEqual("abcde", text_input.text)

    def test_held_backspace_repeats_at_natural_interval(self):
        text_input = TextInput()
        text_input.activate("abcdefghij")
        text_input.handle_event(
            self.key_event(pygame.KEYDOWN, pygame.K_BACKSPACE),
            current_ticks=2000,
        )
        self.assertTrue(text_input.update(
            2000 + BACKSPACE_REPEAT_DELAY_MS,
        ))
        self.assertEqual("abcdefgh", text_input.text)
        self.assertFalse(text_input.update(
            2000 + BACKSPACE_REPEAT_DELAY_MS
            + BACKSPACE_REPEAT_INTERVAL_MS - 1,
        ))
        self.assertTrue(text_input.update(
            2000 + BACKSPACE_REPEAT_DELAY_MS
            + BACKSPACE_REPEAT_INTERVAL_MS,
        ))
        self.assertEqual("abcdefg", text_input.text)

    def test_key_release_stops_repeat_immediately(self):
        text_input = TextInput()
        text_input.activate("abcdef")
        text_input.handle_event(
            self.key_event(pygame.KEYDOWN, pygame.K_BACKSPACE),
            current_ticks=3000,
        )
        text_input.handle_event(
            self.key_event(pygame.KEYUP, pygame.K_BACKSPACE),
            current_ticks=3010,
        )
        self.assertFalse(text_input.update(10000))
        self.assertEqual("abcde", text_input.text)

    def test_empty_or_unfocused_input_is_safe(self):
        text_input = TextInput()
        text_input.text = "abc"
        text_input.handle_event(
            self.key_event(pygame.KEYDOWN, pygame.K_BACKSPACE),
            current_ticks=0,
        )
        self.assertEqual("abc", text_input.text)
        text_input.activate("")
        text_input.handle_event(
            self.key_event(pygame.KEYDOWN, pygame.K_BACKSPACE),
            current_ticks=0,
        )
        self.assertFalse(text_input.update(1000))
        self.assertEqual("", text_input.text)

    def test_leaving_name_state_resets_repeat(self):
        menu = SaveSlotsMenu()
        with patch("save_slots_ui.get_save_slots", return_value=empty_slots()):
            menu.open()
        menu.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": menu.slot_rects[1].center},
        ), 0)
        menu.text_input.text = "abcdef"
        menu.text_input.handle_event(
            self.key_event(pygame.KEYDOWN, pygame.K_BACKSPACE),
            current_ticks=0,
        )
        menu.state = "slots"
        self.assertFalse(menu.update(1000))
        self.assertEqual("abcde", menu.text_input.text)

    def test_window_focus_loss_stops_repeat(self):
        text_input = TextInput()
        text_input.activate("abcdef")
        text_input.handle_event(
            self.key_event(pygame.KEYDOWN, pygame.K_BACKSPACE),
            current_ticks=0,
        )
        text_input.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(text_input.update(1000))
        self.assertEqual("abcde", text_input.text)

    def test_save_cancel_and_escape_paths_remain_unchanged(self):
        menu = SaveSlotsMenu()
        with patch("save_slots_ui.get_save_slots", return_value=empty_slots()):
            menu.open()
        menu.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": menu.slot_rects[1].center},
        ), 0)
        screen = pygame.display.get_surface()
        font = pygame.font.SysFont(None, 24)
        menu.draw(screen, font)
        menu.text_input.text = "Saját mentés"
        menu.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": menu.name_save_rect.center},
        ), 0)
        self.assertEqual((1, "Saját mentés"), menu.take_save_request())

        menu.state = "name"
        menu.text_input.activate("Mégse")
        menu.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": menu.name_cancel_rect.center},
        ), 0)
        self.assertEqual("slots", menu.state)
        self.assertFalse(menu.text_input.active)

        menu._begin_name_input(1, 0)
        menu.handle_event(
            self.key_event(pygame.KEYDOWN, pygame.K_ESCAPE), 0,
        )
        self.assertEqual("slots", menu.state)
        self.assertFalse(menu.text_input.active)


if __name__ == "__main__":
    unittest.main()
