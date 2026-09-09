import math

import pygame

from asset_loader import load_splash_image
from constants import COLOR_TEXT
from game_version import get_version_display
from screen_layout import get_screen_center, get_screen_size
from player_profile import MAX_PLAYER_NAME_LENGTH
from save_slots_ui import TextInput
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

PROFILE_PANEL_WIDTH = 520
PROFILE_PANEL_HEIGHT = 270
PROFILE_PADDING = 30


class SplashScreen:
    """Torzítás és háttérrés nélkül tölti ki a stúdióképpel az ablakot."""

    def __init__(self, image=None):
        self.image = image if image is not None else load_splash_image()
        self._scaled_image = None
        self._scaled_for = None

    def get_image_rect(self, screen_size=None):
        screen_width, screen_height = screen_size or get_screen_size()
        if self.image is None:
            return pygame.Rect(0, 0, 0, 0)
        return pygame.Rect(0, 0, screen_width, screen_height)

    def get_cover_size(self, screen_size=None):
        """A képarányt őrző, az egész célfelületet lefedő méretet adja."""
        screen_width, screen_height = screen_size or get_screen_size()
        image_width, image_height = self.image.get_size()
        scale = max(screen_width / image_width, screen_height / image_height)
        return (
            max(screen_width, math.ceil(image_width * scale)),
            max(screen_height, math.ceil(image_height * scale)),
        )

    def _create_cover_image(self, screen_size):
        """Középre vágott, pontosan célméretű képet készít háttérrés nélkül."""
        cover_size = self.get_cover_size(screen_size)
        cover = pygame.transform.smoothscale(self.image, cover_size)
        crop_rect = pygame.Rect((0, 0), screen_size)
        crop_rect.center = cover.get_rect().center
        result = pygame.Surface(screen_size, flags=cover.get_flags(), depth=32)
        result.blit(cover, (0, 0), crop_rect)
        return result

    def draw(self, screen):
        screen.fill((0, 0, 0))
        if self.image is None:
            return
        image_rect = self.get_image_rect(screen.get_size())
        cache_key = screen.get_size()
        if self._scaled_image is None or self._scaled_for != cache_key:
            self._scaled_image = self._create_cover_image(cache_key)
            self._scaled_for = cache_key
        screen.blit(self._scaled_image, image_rect)


class MainMenu:
    """A játékmenettől független, háromgombos FarmGame főmenü."""

    def __init__(self, items=MAIN_MENU_ITEMS):
        self.items = tuple(items)
        self.pending_action = None
        self.rect = pygame.Rect(0, 0, MAIN_MENU_WIDTH, 300)
        self.button_rects = {}
        self.version_display = get_version_display()
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
        version_surface = font.render(self.version_display, True, (205, 218, 200))
        screen.blit(
            version_surface,
            version_surface.get_rect(
                bottomright=(screen.get_width() - 12, screen.get_height() - 10),
            ),
        )


class PlayerNamePrompt:
    """Modális első-indítási névbekérő, sérült profilnál explicit recoveryvel."""

    def __init__(self, recovery_required=False, error_message=None):
        self.recovery_required = bool(recovery_required)
        self.error_message = error_message
        self.text_input = TextInput(max_length=MAX_PLAYER_NAME_LENGTH)
        self.rect = pygame.Rect(0, 0, PROFILE_PANEL_WIDTH, PROFILE_PANEL_HEIGHT)
        self.continue_rect = pygame.Rect(0, 0, 220, 44)
        self.validation_error = None
        self.submitted_name = None
        self.open()

    def open(self):
        self.text_input.activate()
        self.update_layout()

    def close(self):
        self.text_input.deactivate()

    def update_layout(self):
        width, height = get_screen_size()
        self.rect.size = (
            min(PROFILE_PANEL_WIDTH, max(300, width - 20)),
            min(PROFILE_PANEL_HEIGHT, max(250, height - 20)),
        )
        self.rect.center = get_screen_center()
        self.text_input.rect = pygame.Rect(
            self.rect.left + PROFILE_PADDING,
            self.rect.top + 132,
            self.rect.width - PROFILE_PADDING * 2,
            40,
        )
        self.continue_rect.size = (min(220, self.rect.width - 60), 44)
        self.continue_rect.center = (self.rect.centerx, self.rect.bottom - 55)

    def _submit(self):
        if not self.text_input.is_valid:
            self.validation_error = "Adj meg legalább egy nem szóköz karaktert."
            return
        self.validation_error = None
        self.submitted_name = self.text_input.normalized_text

    def handle_event(self, event):
        self.update_layout()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.continue_rect.collidepoint(event.pos):
                self._submit()
            return True
        result = self.text_input.handle_event(event)
        if result == "submit":
            self._submit()
        return event.type in (
            pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT,
            pygame.MOUSEWHEEL, pygame.WINDOWFOCUSLOST,
        )

    def update(self, current_ticks=None):
        self.text_input.update(current_ticks)

    def take_submission(self):
        name = self.submitted_name
        self.submitted_name = None
        return name

    @staticmethod
    def _draw_left(screen, font, text, position, color=COLOR_TEXT):
        screen.blit(font.render(text, True, color), position)

    def draw(self, screen, font):
        self.update_layout()
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 115))
        screen.blit(overlay, (0, 0))
        pygame.draw.rect(screen, INFO_PANEL_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)
        x = self.rect.left + PROFILE_PADDING
        self._draw_left(screen, font, "Üdvözöl a FarmGame!", (x, self.rect.top + 25))
        if self.recovery_required:
            self._draw_left(
                screen, font,
                "A játékosprofil sérült. Adj meg nevet az új profilhoz.",
                (x, self.rect.top + 61), (150, 45, 35),
            )
        else:
            self._draw_left(screen, font, "Add meg a játékosneved:", (x, self.rect.top + 75))
        self.text_input.draw(screen, font)
        color = CROP_CARD_HOVER if self.continue_rect.collidepoint(pygame.mouse.get_pos()) else CROP_CARD_BACKGROUND
        pygame.draw.rect(screen, color, self.continue_rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.continue_rect, 1)
        label = "Új profil létrehozása" if self.recovery_required else "Folytatás"
        rendered = font.render(label, True, COLOR_TEXT)
        screen.blit(rendered, rendered.get_rect(center=self.continue_rect.center))
        if self.validation_error:
            self._draw_left(screen, font, self.validation_error, (x, self.rect.bottom - 24), (170, 40, 35))
