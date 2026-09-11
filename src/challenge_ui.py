"""Dedicated completion dialog for the ten-year Challenge."""

import pygame

from constants import COLOR_TEXT
from money_format import format_money
from screen_layout import get_screen_center, get_screen_size
from ui import (
    CROP_CARD_BACKGROUND, CROP_CARD_HOVER, INFO_PANEL_BACKGROUND,
    INFO_PANEL_BORDER,
)


PANEL_WIDTH = 600
PANEL_HEIGHT = 390
BUTTON_HEIGHT = 42


class ChallengeCompletionPanel:
    def __init__(self, submission_controller):
        self.submission_controller = submission_controller
        self.visible = False
        self.record = None
        self.rect = pygame.Rect(0, 0, PANEL_WIDTH, PANEL_HEIGHT)
        self.submit_rect = pygame.Rect(0, 0, 230, BUTTON_HEIGHT)
        self.leaderboard_rect = pygame.Rect(0, 0, 155, BUTTON_HEIGHT)
        self.close_rect = pygame.Rect(0, 0, 115, BUTTON_HEIGHT)
        self._leaderboard_requested = False
        self._update_layout()

    def _update_layout(self):
        width, height = get_screen_size()
        self.rect.size = (
            min(PANEL_WIDTH, max(360, width - 20)),
            min(PANEL_HEIGHT, max(330, height - 20)),
        )
        self.rect.center = get_screen_center()
        buttons_y = self.rect.bottom - 66
        gap = 12
        available_width = self.rect.width - 40 - gap * 2
        desired_widths = (230, 155, 115)
        desired_total = sum(desired_widths)
        widths = tuple(
            max(70, available_width * width // desired_total)
            for width in desired_widths
        )
        width_difference = available_width - sum(widths)
        widths = (widths[0] + width_difference, widths[1], widths[2])
        self.submit_rect.size = (widths[0], BUTTON_HEIGHT)
        self.leaderboard_rect.size = (widths[1], BUTTON_HEIGHT)
        self.close_rect.size = (widths[2], BUTTON_HEIGHT)
        total = sum(widths) + gap * 2
        self.submit_rect.topleft = (self.rect.centerx - total // 2, buttons_y)
        self.leaderboard_rect.topleft = (
            self.submit_rect.right + gap, buttons_y,
        )
        self.close_rect.topleft = (
            self.leaderboard_rect.right + gap, buttons_y,
        )

    def open(self, record):
        if record is None:
            return False
        self.record = record
        self.visible = True
        self._leaderboard_requested = False
        self._update_layout()
        return True

    def close(self):
        self.visible = False

    def take_leaderboard_request(self):
        requested = self._leaderboard_requested
        self._leaderboard_requested = False
        return requested

    def handle_event(self, event):
        if not self.visible:
            return False
        self._update_layout()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        if event.type != pygame.MOUSEBUTTONDOWN:
            return event.type in (
                pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT,
                pygame.MOUSEWHEEL,
            )
        if event.button != 1:
            return True
        # Milestone dialog: outside clicks are consumed but do not dismiss it.
        if not self.rect.collidepoint(event.pos):
            return True
        if self.close_rect.collidepoint(event.pos):
            self.close()
        elif self.leaderboard_rect.collidepoint(event.pos):
            self._leaderboard_requested = True
            self.close()
        elif self.submit_rect.collidepoint(event.pos) and self.can_submit:
            self.submission_controller.request(self.record)
        return True

    @property
    def current_record(self):
        if self.record is None:
            return None
        return self.submission_controller.get_record(
            self.record.game_id, self.record.challenge_years,
        ) or self.record

    @property
    def can_submit(self):
        record = self.current_record
        return (
            record is not None
            and record.submission_status != "submitted"
            and not self.submission_controller.submitting
        )

    @staticmethod
    def _text(screen, font, value, x, y, color=COLOR_TEXT):
        screen.blit(font.render(str(value), True, color), (x, y))

    def _button(self, screen, font, rect, label, enabled=True):
        color = CROP_CARD_BACKGROUND
        if enabled and rect.collidepoint(pygame.mouse.get_pos()):
            color = CROP_CARD_HOVER
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 1)
        text_color = COLOR_TEXT if enabled else (130, 130, 125)
        rendered = font.render(label, True, text_color)
        screen.blit(rendered, rendered.get_rect(center=rect.center))

    def draw(self, screen, font):
        if not self.visible or self.current_record is None:
            return
        self._update_layout()
        record = self.current_record
        pygame.draw.rect(screen, INFO_PANEL_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)
        x = self.rect.left + 28
        self._text(screen, font, "10 éves Challenge teljesítve!", x,
                   self.rect.top + 24)
        self._text(screen, font, "10 év teljesítve", x, self.rect.top + 70)
        self._text(screen, font, f"Játékos: {record.player_name}", x,
                   self.rect.top + 112)
        self._text(screen, font,
                   f"Gazdaság értéke: {format_money(record.farm_value)}", x,
                   self.rect.top + 150)
        self._text(screen, font, f"Játékverzió: {record.game_version}", x,
                   self.rect.top + 188)
        feedback = self.submission_controller.feedback
        if feedback.message:
            self._text(screen, font, feedback.message, x, self.rect.top + 232)
        submitted = record.submission_status == "submitted"
        label = "Beküldve" if submitted else (
            "Beküldés..." if self.submission_controller.submitting
            else "Beküldés a ranglistára"
        )
        self._button(screen, font, self.submit_rect, label, self.can_submit)
        self._button(
            screen, font, self.leaderboard_rect, "Top 10 ranglista",
        )
        self._button(
            screen, font, self.close_rect,
            "Bezárás" if submitted else "Később",
        )
