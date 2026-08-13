import pygame

from constants import COLOR_TEXT
from screen_layout import get_screen_center, get_screen_size
from ui import (
    CROP_CARD_BACKGROUND, CROP_CARD_HOVER, INFO_PANEL_BACKGROUND,
    INFO_PANEL_BORDER, INFO_PANEL_PADDING, is_outside_popup_click,
)


GAME_MENU_ITEMS = (
    {"id": "new_game", "label": "Új játék", "confirmation": "new_game"},
    {"id": "save_game", "label": "Játék mentése"},
    {"id": "load_game", "label": "Játék betöltése"},
    {"id": "exit_game", "label": "Kilépés", "confirmation": "exit_game"},
)

CONFIRMATIONS = {
    "new_game": "Biztosan új játékot szeretnél kezdeni?",
    "exit_game": "Biztosan ki szeretnél lépni?",
}

MENU_WIDTH = 400
MENU_BUTTON_HEIGHT = 42
MENU_BUTTON_GAP = 10
MENU_TITLE_HEIGHT = 42
MENU_MESSAGE_HEIGHT = 30
MENU_FEEDBACK_MS = 2500


class GameMenu:
    """Bővíthető, modális játékmenü saját rajzolással és eseménykezeléssel."""

    def __init__(self, items=GAME_MENU_ITEMS):
        self.items = tuple(items)
        self.visible = False
        self.confirmation = None
        self.pending_action = None
        self.feedback = None
        self.feedback_until = 0
        self.rect = pygame.Rect(0, 0, MENU_WIDTH, 320)
        self.item_rects = {}
        self.confirmation_rects = {}
        self._update_layout()

    def _update_layout(self):
        screen_width, screen_height = get_screen_size()
        content_height = (
            INFO_PANEL_PADDING * 2 + MENU_TITLE_HEIGHT
            + len(self.items) * MENU_BUTTON_HEIGHT
            + max(0, len(self.items) - 1) * MENU_BUTTON_GAP
            + MENU_MESSAGE_HEIGHT
        )
        self.rect.size = (
            min(MENU_WIDTH, max(280, screen_width - 20)),
            min(content_height, max(260, screen_height - 20)),
        )
        self.rect.center = get_screen_center()
        self.item_rects = {}
        y = self.rect.y + INFO_PANEL_PADDING + MENU_TITLE_HEIGHT
        for item in self.items:
            self.item_rects[item["id"]] = pygame.Rect(
                self.rect.x + INFO_PANEL_PADDING,
                y,
                self.rect.width - INFO_PANEL_PADDING * 2,
                MENU_BUTTON_HEIGHT,
            )
            y += MENU_BUTTON_HEIGHT + MENU_BUTTON_GAP

    def open(self):
        self.visible = True
        self.confirmation = None
        self._update_layout()

    def close(self):
        self.visible = False
        self.confirmation = None

    def toggle(self):
        if self.visible:
            self.close()
        else:
            self.open()

    def set_feedback(self, message, current_ticks=None):
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks
        self.feedback = message
        self.feedback_until = now + MENU_FEEDBACK_MS

    def take_action(self):
        action = self.pending_action
        self.pending_action = None
        return action

    def handle_event(self, event):
        """Nyitott állapotban minden billentyű- és egéreseményt modálisan kezel."""
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        if event.type != pygame.MOUSEBUTTONDOWN:
            return event.type in (pygame.KEYDOWN, pygame.KEYUP)
        if event.button != 1:
            return True
        if is_outside_popup_click(event, self.rect):
            self.close()
            return True

        if self.confirmation is not None:
            if self.confirmation_rects.get("yes", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                self.pending_action = self.confirmation
                self.close()
            elif self.confirmation_rects.get("no", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                self.confirmation = None
            return True

        for item in self.items:
            if not self.item_rects[item["id"]].collidepoint(event.pos):
                continue
            confirmation = item.get("confirmation")
            if confirmation is not None:
                self.confirmation = confirmation
            else:
                self.pending_action = item["id"]
            return True
        return True

    @staticmethod
    def _draw_text(screen, font, text, position, center=False):
        rendered = font.render(text, True, COLOR_TEXT)
        rect = (
            rendered.get_rect(center=position)
            if center else rendered.get_rect(topleft=position)
        )
        screen.blit(rendered, rect)

    def _draw_button(self, screen, font, rect, label):
        color = (
            CROP_CARD_HOVER
            if rect.collidepoint(pygame.mouse.get_pos())
            else CROP_CARD_BACKGROUND
        )
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 1)
        self._draw_text(screen, font, label, rect.center, center=True)

    def draw(self, screen, font, current_ticks=None):
        if not self.visible:
            return
        self._update_layout()
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks
        if self.feedback is not None and now >= self.feedback_until:
            self.feedback = None

        pygame.draw.rect(screen, INFO_PANEL_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)
        self._draw_text(
            screen, font, "FarmGame",
            (self.rect.centerx, self.rect.y + INFO_PANEL_PADDING + 10),
            center=True,
        )

        if self.confirmation is None:
            for item in self.items:
                self._draw_button(
                    screen, font, self.item_rects[item["id"]], item["label"],
                )
            if self.feedback:
                self._draw_text(
                    screen, font, self.feedback,
                    (self.rect.centerx, self.rect.bottom - 18), center=True,
                )
            return

        question = CONFIRMATIONS[self.confirmation]
        self._draw_text(
            screen, font, question,
            (self.rect.centerx, self.rect.centery - 35), center=True,
        )
        button_width = 120
        gap = 20
        y = self.rect.centery + 10
        self.confirmation_rects = {
            "yes": pygame.Rect(
                self.rect.centerx - gap // 2 - button_width, y,
                button_width, MENU_BUTTON_HEIGHT,
            ),
            "no": pygame.Rect(
                self.rect.centerx + gap // 2, y,
                button_width, MENU_BUTTON_HEIGHT,
            ),
        }
        self._draw_button(
            screen, font, self.confirmation_rects["yes"], "Igen",
        )
        self._draw_button(
            screen, font, self.confirmation_rects["no"], "Nem",
        )
