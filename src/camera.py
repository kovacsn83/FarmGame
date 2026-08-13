from math import hypot

from constants import GRID_COLS, GRID_ROWS, TILE_SIZE


CAMERA_DRAG_THRESHOLD = 8


class Camera:
    """A világ nézetét és a küszöbös bal egérgombos húzást kezeli."""

    def __init__(self):
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.viewport_width = 0
        self.viewport_height = 0
        self.pending_drag = False
        self.dragging_camera = False
        self.drag_start_mouse = None
        self.drag_start_camera = None
        self.world_width_tiles = GRID_COLS
        self.world_height_tiles = GRID_ROWS

    @property
    def world_width(self):
        return self.world_width_tiles * TILE_SIZE

    @property
    def world_height(self):
        return self.world_height_tiles * TILE_SIZE

    def update_world_size(self, width_tiles, height_tiles):
        """A ténylegesen betöltött világhoz igazítja a kamerahatárokat."""
        self.world_width_tiles = max(0, int(width_tiles))
        self.world_height_tiles = max(0, int(height_tiles))
        self._clamp()

    def update_viewport(self, width, height):
        self.viewport_width = max(0, int(width))
        self.viewport_height = max(0, int(height))
        self._clamp()

    def _clamp(self):
        max_x = max(0.0, self.world_width - self.viewport_width)
        max_y = max(0.0, self.world_height - self.viewport_height)
        self.camera_x = min(max(0.0, self.camera_x), max_x)
        self.camera_y = min(max(0.0, self.camera_y), max_y)

    def reset(self):
        """Új játék és betöltés után az alapértelmezett nézetre áll."""
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.cancel_drag()
        self._clamp()

    def world_to_screen(self, world_x, world_y):
        return world_x - self.camera_x, world_y - self.camera_y

    def screen_to_world(self, screen_x, screen_y):
        return screen_x + self.camera_x, screen_y + self.camera_y

    def begin_drag(self, mouse_position):
        self.pending_drag = True
        self.dragging_camera = False
        self.drag_start_mouse = tuple(mouse_position)
        self.drag_start_camera = (self.camera_x, self.camera_y)

    def update_drag(self, mouse_position):
        if not self.pending_drag:
            return False
        delta_x = mouse_position[0] - self.drag_start_mouse[0]
        delta_y = mouse_position[1] - self.drag_start_mouse[1]
        if (not self.dragging_camera
                and hypot(delta_x, delta_y) <= CAMERA_DRAG_THRESHOLD):
            return False
        self.dragging_camera = True
        # Grab-and-drag: a világ képe az egérrel azonos irányba mozdul.
        self.camera_x = self.drag_start_camera[0] - delta_x
        self.camera_y = self.drag_start_camera[1] - delta_y
        self._clamp()
        return True

    def finish_drag(self):
        """Visszaadja a kezdő kattintási pontot és hogy valódi húzás történt-e."""
        if not self.pending_drag:
            return None, False
        start_position = self.drag_start_mouse
        was_dragging = self.dragging_camera
        self.cancel_drag()
        return start_position, was_dragging

    def cancel_drag(self):
        self.pending_drag = False
        self.dragging_camera = False
        self.drag_start_mouse = None
        self.drag_start_camera = None
