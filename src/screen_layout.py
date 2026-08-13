import pygame

from constants import (
    BOTTOM_BAR_HEIGHT, TOP_BAR_HEIGHT, WINDOW_HEIGHT, WINDOW_WIDTH,
)


_screen_width = WINDOW_WIDTH
_screen_height = WINDOW_HEIGHT
_camera = None
_developer_console_height = 0


def set_camera(camera):
    """A renderelés és input közös, aktuális kameráját regisztrálja."""
    global _camera
    _camera = camera
    _update_camera_viewport()


def _update_camera_viewport():
    if _camera is not None:
        play_area = get_play_area_rect()
        _camera.update_viewport(play_area.width, play_area.height)


def set_screen_size(width, height):
    """Az átméretezési eseményből központilag frissíti a viewport méretét."""
    global _screen_width, _screen_height
    _screen_width = max(1, int(width))
    _screen_height = max(1, int(height))
    _update_camera_viewport()


def set_developer_console_height(height):
    """A toolbar fölötti fejlesztői overlay aktuális magasságát állítja."""
    global _developer_console_height
    _developer_console_height = max(0, int(height))


def get_screen_size():
    return _screen_width, _screen_height


def get_screen_center():
    return _screen_width // 2, _screen_height // 2


def get_play_area_rect():
    """A felső HUD és az alsó toolbar közötti aktuális viewportot adja."""
    return pygame.Rect(
        0,
        TOP_BAR_HEIGHT,
        _screen_width,
        max(0, _screen_height - TOP_BAR_HEIGHT - BOTTOM_BAR_HEIGHT),
    )


def get_developer_console_rect():
    """A teljes világ-render fölötti, toolbarhoz igazított overlay helye."""
    return pygame.Rect(
        0,
        _screen_height - BOTTOM_BAR_HEIGHT - _developer_console_height,
        _screen_width,
        _developer_console_height,
    )


def get_toolbar_top():
    return _screen_height - BOTTOM_BAR_HEIGHT


def world_to_screen(world_x, world_y):
    """Világpozícióból a központi kamerán át képernyőpozíciót képez."""
    if _camera is not None:
        world_x, world_y = _camera.world_to_screen(world_x, world_y)
    return world_x, world_y + TOP_BAR_HEIGHT


def screen_to_world(screen_x, screen_y):
    """Képernyőpozícióból a központi kamerán át világpozíciót képez."""
    world_x, world_y = screen_x, screen_y - TOP_BAR_HEIGHT
    if _camera is not None:
        world_x, world_y = _camera.screen_to_world(world_x, world_y)
    return world_x, world_y


def center_rect(rect):
    rect.center = get_screen_center()
    return rect
