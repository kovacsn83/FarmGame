"""FarmGame-styled Top 10 leaderboard popup."""

import pygame

from constants import COLOR_TEXT
from money_format import format_money
from screen_layout import get_screen_center, get_screen_size
from ui import (
    CROP_CARD_BACKGROUND, CROP_CARD_HOVER, INFO_PANEL_BACKGROUND,
    INFO_PANEL_BORDER, is_outside_popup_click,
)


PANEL_WIDTH = 760
PANEL_HEIGHT = 570
PADDING = 26
ROW_HEIGHT = 36
BUTTON_HEIGHT = 40
HEADER_BACKGROUND = (220, 220, 212)
TOP_ROW_BACKGROUNDS = ((242, 231, 180), (226, 229, 232), (224, 205, 183))


class ChallengeLeaderboardPanel:
    def __init__(self, controller):
        self.controller = controller
        self.visible = False
        self.rect = pygame.Rect(0, 0, PANEL_WIDTH, PANEL_HEIGHT)
        self.action_rect = pygame.Rect(0, 0, 170, BUTTON_HEIGHT)
        self.close_rect = pygame.Rect(0, 0, 150, BUTTON_HEIGHT)
        self._update_layout()

    def _update_layout(self):
        width, height = get_screen_size()
        self.rect.size = (
            min(PANEL_WIDTH, max(400, width - 20)),
            min(PANEL_HEIGHT, max(450, height - 20)),
        )
        self.rect.center = get_screen_center()
        gap = 18
        total = self.action_rect.width + gap + self.close_rect.width
        self.action_rect.topleft = (
            self.rect.centerx - total // 2, self.rect.bottom - 62,
        )
        self.close_rect.topleft = (
            self.action_rect.right + gap, self.action_rect.top,
        )

    def open(self):
        self.visible = True
        self._update_layout()
        self.controller.request()

    def close(self):
        self.visible = False

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
        if is_outside_popup_click(event, self.rect):
            self.close()
            return True
        if self.close_rect.collidepoint(event.pos):
            self.close()
        elif self.action_rect.collidepoint(event.pos) and not self.controller.loading:
            self.controller.request()
        return True

    @staticmethod
    def _text(screen, font, text, x, y, color=COLOR_TEXT):
        screen.blit(font.render(str(text), True, color), (x, y))

    @staticmethod
    def _fit_text(font, text, max_width):
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text
        ellipsis = "…"
        while text and font.size(text + ellipsis)[0] > max_width:
            text = text[:-1]
        return text + ellipsis

    def _draw_button(self, screen, font, rect, label, enabled=True):
        color = CROP_CARD_BACKGROUND
        if enabled and rect.collidepoint(pygame.mouse.get_pos()):
            color = CROP_CARD_HOVER
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 1)
        rendered = font.render(
            label, True, COLOR_TEXT if enabled else (130, 130, 125),
        )
        screen.blit(rendered, rendered.get_rect(center=rect.center))

    def draw(self, screen, font):
        if not self.visible:
            return
        self._update_layout()
        pygame.draw.rect(screen, INFO_PANEL_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)
        left = self.rect.left + PADDING
        self._text(screen, font, "10 éves Challenge – Top 10", left, self.rect.top + 20)
        table = pygame.Rect(
            left, self.rect.top + 62, self.rect.width - 2 * PADDING,
            min(11 * ROW_HEIGHT, self.rect.height - 142),
        )
        row_height = min(ROW_HEIGHT, max(26, table.height // 11))
        pygame.draw.rect(screen, HEADER_BACKGROUND, (
            table.left, table.top, table.width, row_height,
        ))
        rank_x = table.left + 12
        player_x = table.left + 66
        value_x = table.left + int(table.width * 0.58)
        version_x = table.left + int(table.width * 0.84)
        for label, x in (("#", rank_x), ("Játékos", player_x),
                         ("Gazdaság értéke", value_x), ("Verzió", version_x)):
            self._text(screen, font, label, x, table.top + 6)
        pygame.draw.line(screen, INFO_PANEL_BORDER,
                         (table.left, table.top + row_height),
                         (table.right, table.top + row_height))

        state = self.controller.state
        if state.status == "success":
            for index, entry in enumerate(state.entries[:10]):
                row_y = table.top + row_height * (index + 1)
                if index < 3:
                    pygame.draw.rect(screen, TOP_ROW_BACKGROUNDS[index], (
                        table.left, row_y, table.width, row_height,
                    ))
                self._text(screen, font, f"{entry['rank']}.", rank_x, row_y + 6)
                player = self._fit_text(
                    font, entry["player_name"], max(40, value_x - player_x - 12),
                )
                self._text(screen, font, player, player_x, row_y + 6)
                self._text(screen, font, format_money(entry["farm_value"]),
                           value_x, row_y + 6)
                self._text(screen, font, entry["game_version"],
                           version_x, row_y + 6)
        else:
            for index, line in enumerate(state.message.splitlines() or [""]):
                rendered = font.render(line, True, COLOR_TEXT)
                screen.blit(rendered, rendered.get_rect(
                    center=(table.centerx, table.top + 90 + index * 30),
                ))

        action_label = (
            "Betöltés..." if self.controller.loading else
            "Frissítés" if state.status in ("success", "empty") else
            "Újrapróbálkozás"
        )
        self._draw_button(screen, font, self.action_rect, action_label,
                          enabled=not self.controller.loading)
        self._draw_button(screen, font, self.close_rect, "Bezárás")
