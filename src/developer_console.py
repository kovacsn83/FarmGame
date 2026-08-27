import pygame

from game_logger import get_logger
from screen_layout import (
    get_developer_console_rect, set_developer_console_height,
)


DEVELOPER_CONSOLE_HEIGHT = 100
DEVELOPER_CONSOLE_TEXT_COLOR = (15, 15, 15)
DEVELOPER_CONSOLE_HEADER_COLOR = (15, 15, 15)
DEVELOPER_CONSOLE_SEPARATOR_COLOR = (120, 120, 120, 150)
DEVELOPER_CONSOLE_PADDING_X = 10
DEVELOPER_CONSOLE_PADDING_Y = 6
DEVELOPER_CONSOLE_HEADER_HEIGHT = 20
DEVELOPER_CONSOLE_LINE_GAP = 2
DEVELOPER_CONSOLE_SCROLL_LINES = 3
DEVELOPER_CONSOLE_FONT_SIZE = 16


class DeveloperConsole:
    """Click-through, görgethető fejlesztői napló-overlay."""

    def __init__(self, logger=None, visible=True):
        self.logger = logger or get_logger()
        self.visible = bool(visible)
        self.scroll_offset = 0
        self._f3_down = False
        self._cached_surface = None
        self._cache_key = None
        self._last_total_lines = 0
        self._last_visible_lines = 1
        self.font = pygame.font.SysFont("consolas", DEVELOPER_CONSOLE_FONT_SIZE)
        set_developer_console_height(
            DEVELOPER_CONSOLE_HEIGHT if self.visible else 0,
        )

    @property
    def rect(self):
        return get_developer_console_rect()

    def set_visible(self, visible):
        visible = bool(visible)
        if self.visible == visible:
            return False
        self.visible = visible
        set_developer_console_height(
            DEVELOPER_CONSOLE_HEIGHT if visible else 0,
        )
        self._invalidate()
        return True

    def toggle(self):
        return self.set_visible(not self.visible)

    def handle_global_shortcut(self, event):
        """Az ismételt KEYDOWN eseményeket is egyetlen F3 váltásra szűri."""
        if event.type == pygame.KEYUP and event.key == pygame.K_F3:
            self._f3_down = False
            return True
        if event.type != pygame.KEYDOWN or event.key != pygame.K_F3:
            return False
        if not self._f3_down:
            self._f3_down = True
            self.toggle()
        return True

    def handle_event(self, event, mouse_position=None):
        """Csak a konzol feletti görgetést fogyasztja el; kattintást soha."""
        if not self.visible or event.type != pygame.MOUSEWHEEL:
            return False
        position = mouse_position or pygame.mouse.get_pos()
        if not self.rect.collidepoint(position):
            return False
        max_scroll = max(
            0, self._last_total_lines - self._last_visible_lines,
        )
        if event.y > 0:
            self.scroll_offset = min(
                max_scroll,
                self.scroll_offset
                + event.y * DEVELOPER_CONSOLE_SCROLL_LINES,
            )
        elif event.y < 0:
            self.scroll_offset = max(
                0,
                self.scroll_offset
                + event.y * DEVELOPER_CONSOLE_SCROLL_LINES,
            )
        self._invalidate()
        return True

    def draw(self, screen):
        if not self.visible:
            return
        rect = self.rect
        cache_key = (
            rect.size, self.logger.revision, self.scroll_offset,
        )
        if self._cached_surface is None or cache_key != self._cache_key:
            self._cached_surface = self._render_surface(rect.size)
            self._cache_key = cache_key
        screen.blit(self._cached_surface, rect.topleft)

    def _render_surface(self, size):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))
        pygame.draw.line(
            surface, DEVELOPER_CONSOLE_SEPARATOR_COLOR,
            (0, size[1] - 1), (size[0], size[1] - 1), 1,
        )
        header = self.font.render(
            "Developer Console — F3", True,
            DEVELOPER_CONSOLE_HEADER_COLOR,
        )
        surface.blit(header, (DEVELOPER_CONSOLE_PADDING_X, 3))

        content_top = DEVELOPER_CONSOLE_HEADER_HEIGHT
        content_height = max(
            0, size[1] - content_top - DEVELOPER_CONSOLE_PADDING_Y,
        )
        line_height = self.font.get_linesize() + DEVELOPER_CONSOLE_LINE_GAP
        self._last_visible_lines = max(1, content_height // line_height)
        max_width = max(1, size[0] - DEVELOPER_CONSOLE_PADDING_X * 2)
        lines = []
        for entry in self.logger.entries:
            lines.extend(self._wrap_text(entry.format(), max_width))
        self._last_total_lines = len(lines)
        max_scroll = max(0, len(lines) - self._last_visible_lines)
        self.scroll_offset = min(self.scroll_offset, max_scroll)
        end = max(0, len(lines) - self.scroll_offset)
        start = max(0, end - self._last_visible_lines)
        visible_lines = lines[start:end]
        first_y = content_top + max(
            0, content_height - len(visible_lines) * line_height,
        )
        for index, line in enumerate(visible_lines):
            rendered = self.font.render(
                line, True, DEVELOPER_CONSOLE_TEXT_COLOR,
            )
            surface.blit(
                rendered,
                (DEVELOPER_CONSOLE_PADDING_X, first_y + index * line_height),
            )
        return surface

    def _wrap_text(self, text, max_width):
        """Szóhatáron tör, a túl hosszú tokeneket pedig karakterenként bontja."""
        if not text:
            return [""]
        lines = []
        current = ""
        for word in text.split():
            candidate = word if not current else f"{current} {word}"
            if self.font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            while word and self.font.size(word)[0] > max_width:
                split_at = self._fitting_prefix_length(word, max_width)
                lines.append(word[:split_at])
                word = word[split_at:]
            current = word
        if current:
            lines.append(current)
        return lines or [""]

    def _fitting_prefix_length(self, text, max_width):
        low, high = 1, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if self.font.size(text[:middle])[0] <= max_width:
                low = middle
            else:
                high = middle - 1
        return max(1, low)

    def _invalidate(self):
        self._cached_surface = None
        self._cache_key = None
