import pygame

from constants import COLOR_TEXT
from screen_layout import get_screen_center, get_screen_size
from save_system import MAX_SAVE_NAME_LENGTH, get_save_slots
from time_system import format_game_time, legacy_day_to_elapsed_weeks
from ui import (
    CROP_CARD_BACKGROUND, CROP_CARD_HOVER, INFO_PANEL_BACKGROUND,
    INFO_PANEL_BORDER, INFO_PANEL_PADDING, is_outside_popup_click,
)


PANEL_WIDTH = 620
PANEL_HEIGHT = 690
SLOT_HEIGHT = 56
SLOT_GAP = 6
ACTION_BUTTON_HEIGHT = 40
EMPTY_SLOT_COLOR = (238, 238, 234)
CORRUPT_SLOT_COLOR = (235, 205, 200)
SELECTED_SLOT_COLOR = (210, 228, 205)
TEXT_INPUT_BACKGROUND = (255, 255, 252)


class TextInput:
    """Egyszerű Unicode szövegmező mentésnevekhez."""

    def __init__(self, max_length=MAX_SAVE_NAME_LENGTH):
        self.text = ""
        self.max_length = max_length
        self.active = False
        self.rect = pygame.Rect(0, 0, 0, 0)

    def activate(self, text=""):
        self.text = str(text)[:self.max_length]
        self.active = True
        pygame.key.start_text_input()

    def deactivate(self):
        self.active = False
        pygame.key.stop_text_input()

    def handle_event(self, event):
        if not self.active:
            return None
        if event.type == pygame.TEXTINPUT:
            available = self.max_length - len(self.text)
            if available > 0:
                self.text += "".join(
                    character for character in event.text[:available]
                    if character.isprintable()
                )
            return "changed"
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
            return "changed"
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return "submit"
        return None

    @property
    def normalized_text(self):
        return self.text.strip()

    @property
    def is_valid(self):
        return bool(self.normalized_text)

    def draw(self, screen, font):
        pygame.draw.rect(screen, TEXT_INPUT_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)
        visible_text = self.text + ("|" if self.active else "")
        rendered = font.render(visible_text, True, COLOR_TEXT)
        screen.blit(rendered, rendered.get_rect(
            midleft=(self.rect.x + 10, self.rect.centery),
        ))


class ConfirmationDialog:
    """A mentési és betöltési nézet közös Igen/Nem kérdése."""

    def __init__(self):
        self.message_lines = ()
        self.yes_rect = pygame.Rect(0, 0, 0, 0)
        self.no_rect = pygame.Rect(0, 0, 0, 0)

    def configure(self, *message_lines):
        self.message_lines = tuple(message_lines)

    def layout(self, parent_rect):
        width = 120
        gap = 20
        y = parent_rect.centery + 35
        self.yes_rect = pygame.Rect(
            parent_rect.centerx - gap // 2 - width, y,
            width, ACTION_BUTTON_HEIGHT,
        )
        self.no_rect = pygame.Rect(
            parent_rect.centerx + gap // 2, y,
            width, ACTION_BUTTON_HEIGHT,
        )


class SaveSlotsBase:
    """A nyolc slot közös listázási, navigációs és rajzolási alapja."""

    title = ""

    def __init__(self):
        self.visible = False
        self.state = "slots"
        self.slots = []
        self.selected_slot_id = None
        self.feedback = None
        self.pending_navigation = None
        self.rect = pygame.Rect(0, 0, PANEL_WIDTH, PANEL_HEIGHT)
        self.rect.center = get_screen_center()
        self.slot_rects = {}
        self.confirmation = ConfirmationDialog()
        self._layout_slots()

    def _layout_slots(self):
        screen_width, screen_height = get_screen_size()
        self.rect.size = (
            min(PANEL_WIDTH, max(360, screen_width - 20)),
            min(PANEL_HEIGHT, max(360, screen_height - 20)),
        )
        self.rect.center = get_screen_center()
        self.slot_rects = {}
        y = self.rect.y + 58
        slot_height = max(
            28,
            min(
                SLOT_HEIGHT,
                (self.rect.height - 58 - 76 - SLOT_GAP * 7) // 8,
            ),
        )
        for slot_id in range(1, 9):
            self.slot_rects[slot_id] = pygame.Rect(
                self.rect.x + INFO_PANEL_PADDING,
                y,
                self.rect.width - INFO_PANEL_PADDING * 2,
                slot_height,
            )
            y += slot_height + SLOT_GAP
        self.cancel_rect = pygame.Rect(
            self.rect.centerx - 100,
            self.rect.bottom - INFO_PANEL_PADDING - ACTION_BUTTON_HEIGHT,
            200,
            ACTION_BUTTON_HEIGHT,
        )

    def open(self):
        self.visible = True
        self.state = "slots"
        self.selected_slot_id = None
        self.feedback = None
        self.pending_navigation = None
        self.refresh()

    def close(self):
        self.visible = False

    def refresh(self):
        self.slots = get_save_slots()

    def slot(self, slot_id):
        return next(slot for slot in self.slots if slot["slot_id"] == slot_id)

    def take_navigation(self):
        navigation = self.pending_navigation
        self.pending_navigation = None
        return navigation

    def _back(self):
        if self.state == "slots":
            self._close_to_parent()
        else:
            self.state = "slots"
            self.feedback = None

    def _close_to_parent(self):
        """Bezárja a teljes slotablakot, és visszalép a megnyitó menübe."""
        self.close()
        self.pending_navigation = "game_menu"

    def _handle_outside_click(self, event):
        """A közös popup-szabály szerint elfogyasztja a külső bal kattintást."""
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and is_outside_popup_click(event, self.rect)
        ):
            self._close_to_parent()
            return True
        return False

    def _slot_at(self, position):
        return next((slot_id for slot_id, rect in self.slot_rects.items()
                     if rect.collidepoint(position)), None)

    @staticmethod
    def _draw_text(screen, font, text, position, center=False):
        rendered = font.render(text, True, COLOR_TEXT)
        rect = rendered.get_rect(center=position) if center else rendered.get_rect(
            topleft=position,
        )
        screen.blit(rendered, rect)

    def _draw_button(self, screen, font, rect, label):
        color = CROP_CARD_HOVER if rect.collidepoint(
            pygame.mouse.get_pos()
        ) else CROP_CARD_BACKGROUND
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 1)
        self._draw_text(screen, font, label, rect.center, center=True)

    def _draw_frame(self, screen, font):
        pygame.draw.rect(screen, INFO_PANEL_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)
        self._draw_text(
            screen, font, self.title,
            (self.rect.centerx, self.rect.y + 28), center=True,
        )

    def _draw_slots(self, screen, font):
        for slot in self.slots:
            rect = self.slot_rects[slot["slot_id"]]
            if slot["slot_id"] == self.selected_slot_id:
                color = SELECTED_SLOT_COLOR
            elif slot["status"] == "corrupt":
                color = CORRUPT_SLOT_COLOR
            elif slot["status"] == "empty":
                color = EMPTY_SLOT_COLOR
            else:
                color = (
                    CROP_CARD_HOVER if rect.collidepoint(pygame.mouse.get_pos())
                    else CROP_CARD_BACKGROUND
                )
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(
                screen, INFO_PANEL_BORDER, rect,
                3 if slot["slot_id"] == self.selected_slot_id else 1,
            )
            x = rect.x + 12
            if slot["status"] == "valid":
                self._draw_text(
                    screen, font,
                    f"{slot['slot_id']}. {slot['save_name']}", (x, rect.y + 6),
                )
                if rect.height >= 48:
                    self._draw_text(
                        screen, font,
                        f"{format_game_time(legacy_day_to_elapsed_weeks(slot['game_day']))}"
                        f"  |  {slot['saved_at']}",
                        (x, rect.y + 30),
                    )
            elif slot["status"] == "corrupt":
                self._draw_text(
                    screen, font, f"{slot['slot_id']}. Sérült mentés",
                    (x, rect.y + 18),
                )
            else:
                self._draw_text(
                    screen, font, f"{slot['slot_id']}. Üres mentési hely",
                    (x, rect.y + 18),
                )

    def _draw_confirmation(self, screen, font):
        self.confirmation.layout(self.rect)
        start_y = self.rect.centery - 55
        for index, line in enumerate(self.confirmation.message_lines):
            self._draw_text(
                screen, font, line,
                (self.rect.centerx, start_y + index * 26), center=True,
            )
        self._draw_button(
            screen, font, self.confirmation.yes_rect, "Igen",
        )
        self._draw_button(
            screen, font, self.confirmation.no_rect, "Nem",
        )


class SaveSlotsMenu(SaveSlotsBase):
    title = "Játék mentése"

    def __init__(self):
        super().__init__()
        self.text_input = TextInput()
        self.pending_save = None
        self.name_save_rect = pygame.Rect(0, 0, 170, ACTION_BUTTON_HEIGHT)
        self.name_cancel_rect = pygame.Rect(0, 0, 170, ACTION_BUTTON_HEIGHT)

    def close(self):
        self.text_input.deactivate()
        super().close()

    def _begin_name_input(self, slot_id, elapsed_weeks):
        self.selected_slot_id = slot_id
        slot = self.slot(slot_id)
        default_name = (
            slot["save_name"] if slot["status"] == "valid"
            else f"Farm - {format_game_time(elapsed_weeks)}"
        )
        self.text_input.activate(default_name)
        self.state = "name"
        self.feedback = None

    def _request_save(self):
        if not self.text_input.is_valid:
            self.feedback = "A mentés neve nem lehet üres."
            return
        slot = self.slot(self.selected_slot_id)
        if slot["status"] != "empty":
            self.state = "overwrite"
            self.confirmation.configure(
                "Ez a mentési hely már foglalt.",
                "Biztosan felülírod?",
            )
            return
        self.pending_save = (
            self.selected_slot_id, self.text_input.normalized_text,
        )

    def take_save_request(self):
        request = self.pending_save
        self.pending_save = None
        return request

    def complete_save(self, success):
        self.refresh()
        self.state = "slots"
        self.text_input.deactivate()
        self.feedback = (
            "Játék sikeresen elmentve."
            if success else "A játék mentése nem sikerült."
        )

    def handle_event(self, event, elapsed_weeks):
        if not self.visible:
            return False
        if self._handle_outside_click(event):
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.state in ("overwrite", "name"):
                self.state = "name" if self.state == "overwrite" else "slots"
                if self.state == "slots":
                    self.text_input.deactivate()
            else:
                self._back()
            return True
        if self.state == "name":
            result = self.text_input.handle_event(event)
            if result == "submit":
                self._request_save()
                return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return True
        if self.state == "slots":
            slot_id = self._slot_at(event.pos)
            if slot_id is not None:
                self._begin_name_input(slot_id, elapsed_weeks)
            elif self.cancel_rect.collidepoint(event.pos):
                self._back()
        elif self.state == "name":
            if self.name_save_rect.collidepoint(event.pos):
                self._request_save()
            elif self.name_cancel_rect.collidepoint(event.pos):
                self.text_input.deactivate()
                self.state = "slots"
        elif self.state == "overwrite":
            if self.confirmation.yes_rect.collidepoint(event.pos):
                self.pending_save = (
                    self.selected_slot_id, self.text_input.normalized_text,
                )
            elif self.confirmation.no_rect.collidepoint(event.pos):
                self.state = "name"
        return True

    def draw(self, screen, font):
        if not self.visible:
            return
        self._layout_slots()
        self._draw_frame(screen, font)
        if self.state == "slots":
            self._draw_slots(screen, font)
            self._draw_button(screen, font, self.cancel_rect, "Mégse")
            if self.feedback:
                self._draw_text(
                    screen, font, self.feedback,
                    (self.rect.centerx, self.rect.bottom - 76), center=True,
                )
        elif self.state == "name":
            self._draw_text(
                screen, font, f"{self.selected_slot_id}. mentési hely",
                (self.rect.centerx, self.rect.y + 105), center=True,
            )
            self._draw_text(
                screen, font, "Mentés neve:",
                (self.rect.x + 80, self.rect.y + 170),
            )
            self.text_input.rect = pygame.Rect(
                self.rect.x + 80, self.rect.y + 205,
                self.rect.width - 160, 44,
            )
            self.text_input.draw(screen, font)
            self.name_save_rect = pygame.Rect(
                self.rect.centerx - 180, self.rect.y + 285,
                170, ACTION_BUTTON_HEIGHT,
            )
            self.name_cancel_rect = pygame.Rect(
                self.rect.centerx + 10, self.rect.y + 285,
                170, ACTION_BUTTON_HEIGHT,
            )
            self._draw_button(screen, font, self.name_save_rect, "Mentés")
            self._draw_button(screen, font, self.name_cancel_rect, "Mégse")
            if self.feedback:
                self._draw_text(
                    screen, font, self.feedback,
                    (self.rect.centerx, self.rect.y + 360), center=True,
                )
        else:
            self._draw_confirmation(screen, font)


class LoadSlotsMenu(SaveSlotsBase):
    title = "Játék betöltése"

    def __init__(self):
        super().__init__()
        self.pending_load = None
        self.load_rect = pygame.Rect(0, 0, 170, ACTION_BUTTON_HEIGHT)

    def take_load_request(self):
        request = self.pending_load
        self.pending_load = None
        return request

    def complete_load(self, success):
        if success:
            self.close()
        else:
            self.state = "slots"
            self.feedback = "A mentés betöltése nem sikerült."
            self.refresh()

    def handle_event(self, event):
        if not self.visible:
            return False
        if self._handle_outside_click(event):
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.state == "confirm":
                self.state = "slots"
            else:
                self._back()
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return True
        if self.state == "slots":
            slot_id = self._slot_at(event.pos)
            if slot_id is not None:
                slot = self.slot(slot_id)
                if slot["status"] == "valid":
                    self.selected_slot_id = slot_id
                    self.feedback = None
                elif slot["status"] == "empty":
                    self.feedback = "Ez a mentési hely üres."
                else:
                    self.feedback = "Ez a mentés sérült."
            elif self.load_rect.collidepoint(event.pos):
                if self.selected_slot_id is not None:
                    self.state = "confirm"
                    self.confirmation.configure(
                        "Biztosan betöltöd ezt a mentést?",
                        "A jelenlegi, nem mentett játékállapot elveszhet.",
                    )
            elif self.cancel_rect.collidepoint(event.pos):
                self._back()
        elif self.state == "confirm":
            if self.confirmation.yes_rect.collidepoint(event.pos):
                self.pending_load = self.selected_slot_id
            elif self.confirmation.no_rect.collidepoint(event.pos):
                self.state = "slots"
        return True

    def draw(self, screen, font):
        if not self.visible:
            return
        self._layout_slots()
        self._draw_frame(screen, font)
        if self.state == "confirm":
            self._draw_confirmation(screen, font)
            return
        self._draw_slots(screen, font)
        self.load_rect = pygame.Rect(
            self.rect.centerx - 180,
            self.rect.bottom - INFO_PANEL_PADDING - ACTION_BUTTON_HEIGHT,
            170,
            ACTION_BUTTON_HEIGHT,
        )
        self.cancel_rect = pygame.Rect(
            self.rect.centerx + 10,
            self.rect.bottom - INFO_PANEL_PADDING - ACTION_BUTTON_HEIGHT,
            170,
            ACTION_BUTTON_HEIGHT,
        )
        self._draw_button(screen, font, self.load_rect, "Betöltés")
        self._draw_button(screen, font, self.cancel_rect, "Mégse")
        if self.feedback:
            self._draw_text(
                screen, font, self.feedback,
                (self.rect.centerx, self.rect.bottom - 76), center=True,
            )
