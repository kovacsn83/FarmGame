import pygame

from asset_loader import load_splash_image
from constants import COLOR_TEXT
from screen_layout import get_screen_center, get_screen_size
from ui import (
    CROP_CARD_BACKGROUND, CROP_CARD_HOVER, INFO_PANEL_BACKGROUND,
    INFO_PANEL_BORDER,
)


MAIN_MENU_BACKGROUND = (74, 105, 65)
MAIN_MENU_WIDTH = 420
MAIN_MENU_PADDING = 30
MAIN_MENU_TITLE_HEIGHT = 70
MAIN_MENU_BUTTON_HEIGHT = 46
MAIN_MENU_BUTTON_GAP = 14
MAIN_MENU_ITEMS = (
    {"id": "new_game", "label": "Új játék"},
    {"id": "load_game", "label": "Betöltés"},
    {"id": "exit_game", "label": "Kilépés"},
)


class SplashScreen:
    """Fekete háttéren, torzítás nélkül jeleníti meg a stúdióképet."""

    def __init__(self, image=None):
        self.image = image if image is not None else load_splash_image()
        self._scaled_image = None
        self._scaled_for = None

    def get_image_rect(self, screen_size=None):
        screen_width, screen_height = screen_size or get_screen_size()
        if self.image is None:
            return pygame.Rect(0, 0, 0, 0)
        image_width, image_height = self.image.get_size()
        scale = min(screen_width / image_width, screen_height / image_height)
        width = max(1, round(image_width * scale))
        height = max(1, round(image_height * scale))
        return pygame.Rect(
            (screen_width - width) // 2,
            (screen_height - height) // 2,
            width,
            height,
        )

    def draw(self, screen):
        screen.fill((0, 0, 0))
        if self.image is None:
            return
        image_rect = self.get_image_rect(screen.get_size())
        cache_key = image_rect.size
        if self._scaled_image is None or self._scaled_for != cache_key:
            self._scaled_image = pygame.transform.smoothscale(
                self.image, image_rect.size,
            )
            self._scaled_for = cache_key
        screen.blit(self._scaled_image, image_rect)


class MainMenu:
    """A játékmenettől független, háromgombos FarmGame főmenü."""

    def __init__(self, items=MAIN_MENU_ITEMS):
        self.items = tuple(items)
        self.pending_action = None
        self.rect = pygame.Rect(0, 0, MAIN_MENU_WIDTH, 300)
        self.button_rects = {}
        self.update_layout()

    def update_layout(self):
        screen_width, screen_height = get_screen_size()
        content_height = (
            MAIN_MENU_PADDING * 2 + MAIN_MENU_TITLE_HEIGHT
            + len(self.items) * MAIN_MENU_BUTTON_HEIGHT
            + max(0, len(self.items) - 1) * MAIN_MENU_BUTTON_GAP
        )
        self.rect.size = (
            min(MAIN_MENU_WIDTH, max(280, screen_width - 20)),
            min(content_height, max(260, screen_height - 20)),
        )
        self.rect.center = get_screen_center()
        y = self.rect.top + MAIN_MENU_PADDING + MAIN_MENU_TITLE_HEIGHT
        self.button_rects = {}
        for item in self.items:
            self.button_rects[item["id"]] = pygame.Rect(
                self.rect.left + MAIN_MENU_PADDING,
                y,
                self.rect.width - MAIN_MENU_PADDING * 2,
                MAIN_MENU_BUTTON_HEIGHT,
            )
            y += MAIN_MENU_BUTTON_HEIGHT + MAIN_MENU_BUTTON_GAP

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        self.update_layout()
        for item in self.items:
            if self.button_rects[item["id"]].collidepoint(event.pos):
                self.pending_action = item["id"]
                return True
        return self.rect.collidepoint(event.pos)

    def take_action(self):
        action = self.pending_action
        self.pending_action = None
        return action

    @staticmethod
    def _draw_text(screen, font, text, center):
        rendered = font.render(text, True, COLOR_TEXT)
        screen.blit(rendered, rendered.get_rect(center=center))

    def draw(self, screen, font):
        self.update_layout()
        screen.fill(MAIN_MENU_BACKGROUND)
        pygame.draw.rect(screen, INFO_PANEL_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)
        self._draw_text(
            screen, font, "FarmGame",
            (self.rect.centerx, self.rect.top + MAIN_MENU_PADDING + 18),
        )
        mouse_position = pygame.mouse.get_pos()
        for item in self.items:
            rect = self.button_rects[item["id"]]
            color = (
                CROP_CARD_HOVER
                if rect.collidepoint(mouse_position)
                else CROP_CARD_BACKGROUND
            )
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 1)
            self._draw_text(screen, font, item["label"], rect.center)
