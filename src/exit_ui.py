"""Modal confirmation shown before abandoning an unsaved game session."""

import pygame

from constants import COLOR_TEXT
from screen_layout import get_screen_center, get_screen_size
from ui import (
    CROP_CARD_BACKGROUND, CROP_CARD_HOVER, INFO_PANEL_BACKGROUND,
    INFO_PANEL_BORDER,
)


PANEL_WIDTH = 660
PANEL_HEIGHT = 250
BUTTON_HEIGHT = 44
BUTTON_GAP = 12


class ExitConfirmationPanel:
    def __init__(self):
        self.visible = False
        self.previous_time_speed = None
        self.pending_action = None
        self.feedback = None
        self.rect = pygame.Rect(0, 0, PANEL_WIDTH, PANEL_HEIGHT)
        self.save_exit_rect = pygame.Rect(0, 0, 220, BUTTON_HEIGHT)
        self.discard_rect = pygame.Rect(0, 0, 220, BUTTON_HEIGHT)
        self.cancel_rect = pygame.Rect(0, 0, 120, BUTTON_HEIGHT)
        self._update_layout()

    def _update_layout(self):
        width, height = get_screen_size()
        self.rect.size = (
            min(PANEL_WIDTH, max(360, width - 20)),
            min(PANEL_HEIGHT, max(230, height - 20)),
        )
        self.rect.center = get_screen_center()
        available = self.rect.width - 40 - BUTTON_GAP * 2
        desired = (220, 220, 120)
        total_desired = sum(desired)
        widths = tuple(
            max(70, available * item // total_desired) for item in desired
        )
        widths = (widths[0] + available - sum(widths), widths[1], widths[2])
        y = self.rect.bottom - 68
        total = sum(widths) + BUTTON_GAP * 2
        self.save_exit_rect = pygame.Rect(
            self.rect.centerx - total // 2, y, widths[0], BUTTON_HEIGHT,
        )
        self.discard_rect = pygame.Rect(
            self.save_exit_rect.right + BUTTON_GAP, y, widths[1], BUTTON_HEIGHT,
        )
        self.cancel_rect = pygame.Rect(
            self.discard_rect.right + BUTTON_GAP, y, widths[2], BUTTON_HEIGHT,
        )

    def open(self, previous_time_speed):
        if self.visible:
            return False
        self.visible = True
        self.previous_time_speed = previous_time_speed
        self.pending_action = None
        self.feedback = None
        self._update_layout()
        return True

    def close(self):
        self.visible = False

    def set_feedback(self, message):
        self.feedback = str(message)

    def take_action(self):
        action = self.pending_action
        self.pending_action = None
        return action

    def handle_event(self, event):
        if not self.visible:
            return False
        self._update_layout()
        if event.type == pygame.QUIT:
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pending_action = "cancel"
            return True
        if event.type != pygame.MOUSEBUTTONDOWN:
            return event.type in (
                pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT,
                pygame.MOUSEWHEEL,
            )
        if event.button != 1:
            return True
        if not self.rect.collidepoint(event.pos):
            return True
        if self.save_exit_rect.collidepoint(event.pos):
            self.pending_action = "save_and_exit"
        elif self.discard_rect.collidepoint(event.pos):
            self.pending_action = "discard"
        elif self.cancel_rect.collidepoint(event.pos):
            self.pending_action = "cancel"
        return True

    @staticmethod
    def _text(screen, font, text, position, center=False, color=COLOR_TEXT):
        rendered = font.render(str(text), True, color)
        rect = rendered.get_rect(center=position) if center else rendered.get_rect(
            topleft=position,
        )
        screen.blit(rendered, rect)

    def _button(self, screen, font, rect, label):
        color = (
            CROP_CARD_HOVER if rect.collidepoint(pygame.mouse.get_pos())
            else CROP_CARD_BACKGROUND
        )
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 1)
        self._text(screen, font, label, rect.center, center=True)

    def draw(self, screen, font):
        if not self.visible:
            return
        self._update_layout()
        pygame.draw.rect(screen, INFO_PANEL_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)
        self._text(
            screen, font, "Mentetlen játék",
            (self.rect.centerx, self.rect.top + 32), center=True,
        )
        self._text(
            screen, font, "A játék nincs elmentve.",
            (self.rect.centerx, self.rect.top + 78), center=True,
        )
        self._text(
            screen, font, "Szeretnéd elmenteni kilépés előtt?",
            (self.rect.centerx, self.rect.top + 108), center=True,
        )
        if self.feedback:
            self._text(
                screen, font, self.feedback,
                (self.rect.centerx, self.rect.top + 142), center=True,
                color=(150, 45, 35),
            )
        self._button(screen, font, self.save_exit_rect, "Mentés és kilépés")
        self._button(screen, font, self.discard_rect, "Kilépés mentés nélkül")
        self._button(screen, font, self.cancel_rect, "Mégse")
