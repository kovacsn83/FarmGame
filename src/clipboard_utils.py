"""Kis, UI-független vágólapsegéd a technikai azonosítók másolásához."""

import pygame


def copy_text_to_clipboard(text):
    if not isinstance(text, str) or not text:
        return False
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8") + b"\0")
        return True
    except (pygame.error, TypeError):
        return False
