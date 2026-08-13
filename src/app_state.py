from enum import Enum

import pygame


SPLASH_DURATION_MS = 3000


class AppState(Enum):
    """A FarmGame egymást kizáró, később egyszerűen bővíthető állapotai."""

    SPLASH = "splash"
    MAIN_MENU = "main_menu"
    PLAYING = "playing"


class AppStateManager:
    """Az alkalmazásszintű képernyők közötti átmeneteket kezeli."""

    def __init__(self, start_ticks=None, splash_duration_ms=SPLASH_DURATION_MS):
        self.state = AppState.SPLASH
        self.splash_started_at = (
            pygame.time.get_ticks() if start_ticks is None else int(start_ticks)
        )
        self.splash_duration_ms = int(splash_duration_ms)

    def update(self, current_ticks=None):
        now = pygame.time.get_ticks() if current_ticks is None else int(current_ticks)
        if (
            self.state == AppState.SPLASH
            and now - self.splash_started_at >= self.splash_duration_ms
        ):
            self.state = AppState.MAIN_MENU
            return True
        return False

    def show_main_menu(self):
        self.state = AppState.MAIN_MENU

    def start_playing(self):
        self.state = AppState.PLAYING
