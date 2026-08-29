import pygame

from constants import FIELD_SIZE, TILE_SIZE
from crops import CROPS
from screen_layout import world_to_screen


# A művelt talaj és a bal alsó fényirány központi palettája.
FIELD_SOIL_COLOR = (137, 105, 67)
FIELD_SOIL_FERTILIZED_COLOR = (124, 91, 57)
FIELD_SOIL_WATERED_COLOR = (128, 97, 62)
FIELD_SOIL_FERTILIZED_WATERED_COLOR = (116, 84, 53)
FIELD_FURROW_COLOR = (105, 75, 48)
FIELD_BORDER_COLOR = (83, 61, 42)
# Meleg, természetes aranybarna jelzi a ténylegesen indítható aratást.
FIELD_HARVEST_READY_BORDER_COLOR = (176, 128, 52)
# A két pótaratási hét veszélyeztetett termésének visszafogott pirosa.
FIELD_LATE_HARVEST_BORDER_COLOR = (166, 62, 52)
FIELD_SHADOW_COLOR = (94, 69, 47)
FIELD_HIGHLIGHT_COLOR = (164, 132, 89)
FIELD_BORDER_WIDTH = 2
FURROW_WIDTH = 6

# A Veteményes bal felső sarkában megjelenő, közös állapotjelölők.
FIELD_STATUS_MARKER_POSITION = (7, 7)
FIELD_STATUS_MARKER_SPACING = 8
FIELD_STATUS_MARKER_RADIUS = 3
FERTILIZED_MARKER_COLOR = (101, 67, 38)
FERTILIZED_MARKER_BORDER_COLOR = (66, 46, 29)
WATERED_MARKER_COLOR = (72, 116, 158)
WATERED_MARKER_BORDER_COLOR = (48, 79, 108)

GROWTH_SEEDED = 0
GROWTH_EARLY = 1
GROWTH_DEVELOPED = 2
GROWTH_MATURE = 3

_FIELD_SURFACE_CACHE = {}
MAX_FIELD_SURFACE_CACHE_SIZE = 256


def get_visual_growth_phase(field):
    """A játék százalékos állapotát négy tisztán vizuális fázisra képezi."""
    growth = field.get("growth", 0)
    if growth <= 0:
        return GROWTH_SEEDED
    if growth < 40:
        return GROWTH_EARLY
    if growth < 100:
        return GROWTH_DEVELOPED
    return GROWTH_MATURE


def _stable_value(field, crop_id, row, col, salt=0):
    """Folyamatonként is azonos, globális random állapottól független zaj."""
    crop_value = sum((index + 1) * ord(char) for index, char in enumerate(crop_id))
    value = (
        (field.get("row", 0) + row + 1) * 73856093
        ^ (field.get("col", 0) + col + 1) * 19349663
        ^ crop_value * 83492791
        ^ salt * 2654435761
    ) & 0xFFFFFFFF
    value ^= value >> 16
    return value


def _shift_color(color, amount):
    return tuple(max(0, min(255, channel + amount)) for channel in color)


def _plant_anchor(row, col, variation):
    x = col * TILE_SIZE + TILE_SIZE // 2 + variation % 3 - 1
    y = (row + 1) * TILE_SIZE - 4
    return x, y


def get_field_border_color(harvest_ready=False, late_harvest=False):
    """Az aktuális, mentés nélküli arathatóságból választ keretszínt."""
    if harvest_ready and late_harvest:
        return FIELD_LATE_HARVEST_BORDER_COLOR
    return (
        FIELD_HARVEST_READY_BORDER_COLOR
        if harvest_ready else FIELD_BORDER_COLOR
    )


def draw_harvest_ready_border(surface, rect=None, late_harvest=False):
    """A közös arathatósági keretet rajzolja a megadott területre."""
    pygame.draw.rect(
        surface, get_field_border_color(True, late_harvest),
        surface.get_rect() if rect is None else rect, FIELD_BORDER_WIDTH,
    )


def _draw_field_base(surface, field, harvest_ready=False):
    fertilized = field.get("fertilized", False)
    watered = field.get("watered", False)
    if fertilized and watered:
        base_color = FIELD_SOIL_FERTILIZED_WATERED_COLOR
    elif fertilized:
        base_color = FIELD_SOIL_FERTILIZED_COLOR
    elif watered:
        base_color = FIELD_SOIL_WATERED_COLOR
    else:
        base_color = FIELD_SOIL_COLOR
    surface.fill(base_color)
    width, height = surface.get_size()

    # A sötétebb barázdák a növénysorok közepe alatt futnak.
    for col in range(field.get("width", FIELD_SIZE)):
        center_x = col * TILE_SIZE + TILE_SIZE // 2
        pygame.draw.rect(
            surface, FIELD_FURROW_COLOR,
            (center_x - FURROW_WIDTH // 2, 1, FURROW_WIDTH, height - 2),
        )

    if harvest_ready:
        draw_harvest_ready_border(
            surface, late_harvest=field.get("late_harvest_active", False),
        )
    else:
        pygame.draw.rect(
            surface, get_field_border_color(), surface.get_rect(),
            FIELD_BORDER_WIDTH,
        )
    pygame.draw.line(surface, FIELD_SHADOW_COLOR, (1, 2), (width - 2, 2), 1)
    pygame.draw.line(surface, FIELD_SHADOW_COLOR, (width - 3, 1), (width - 3, height - 2), 1)
    pygame.draw.line(surface, FIELD_HIGHLIGHT_COLOR, (2, height - 3), (width - 3, height - 3), 1)
    pygame.draw.line(surface, FIELD_HIGHLIGHT_COLOR, (2, 2), (2, height - 3), 1)


def _draw_wheat(surface, field, phase):
    colors = ((65, 112, 48), (75, 148, 55), (143, 153, 54), (215, 174, 63))
    stem_count = (1, 2, 3, 4)[phase]
    base_height = (2, 6, 10, 13)[phase]
    for row in range(field["height"]):
        for col in range(field["width"]):
            variation = _stable_value(field, "wheat", row, col)
            anchor_x, anchor_y = _plant_anchor(row, col, variation)
            if phase == GROWTH_SEEDED:
                pygame.draw.circle(surface, (72, 51, 34), (anchor_x, anchor_y), 1)
                continue
            for stem in range(stem_count):
                stem_variation = _stable_value(field, "wheat", row, col, stem + 1)
                x = anchor_x + stem * 2 - stem_count + 1
                height = base_height + stem_variation % 3 - 1
                color = _shift_color(colors[phase], (stem_variation % 7) - 3)
                pygame.draw.line(surface, color, (x, anchor_y), (x, anchor_y - height), 1)
                if phase == GROWTH_MATURE:
                    pygame.draw.ellipse(surface, _shift_color(color, 8), (x - 1, anchor_y - height - 2, 3, 3))


def _draw_corn(surface, field, phase):
    colors = ((55, 110, 50), (47, 139, 57), (37, 126, 48), (31, 111, 42))
    heights = (2, 7, 12, 15)
    for row in range(field["height"]):
        for col in range(field["width"]):
            variation = _stable_value(field, "corn", row, col)
            x, y = _plant_anchor(row, col, variation)
            if phase == GROWTH_SEEDED:
                pygame.draw.circle(surface, (68, 49, 32), (x, y), 1)
                continue
            height = heights[phase] + variation % 3 - 1
            top = y - height
            color = _shift_color(colors[phase], variation % 7 - 3)
            pygame.draw.line(surface, color, (x, y), (x, top), 2)
            if phase >= GROWTH_DEVELOPED:
                pygame.draw.line(surface, color, (x, top + 5), (x - 4, top + 8), 2)
                pygame.draw.line(surface, color, (x, top + 7), (x + 4, top + 10), 2)
            if phase == GROWTH_MATURE:
                pygame.draw.ellipse(surface, (220, 174, 48), (x + 1, top + 6, 3, 5))


def _draw_tomato(surface, field, phase):
    leaf_colors = ((55, 112, 50), (49, 139, 55), (39, 125, 48), (34, 113, 43))
    radius = (1, 2, 3, 4)[phase]
    for row in range(field["height"]):
        for col in range(field["width"]):
            variation = _stable_value(field, "tomato", row, col)
            x, y = _plant_anchor(row, col, variation)
            y -= max(0, radius - 1)
            if phase == GROWTH_SEEDED:
                pygame.draw.circle(surface, (57, 91, 44), (x, y), 1)
                continue
            leaf = _shift_color(leaf_colors[phase], variation % 7 - 3)
            for offset_x, offset_y in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                pygame.draw.circle(surface, leaf, (x + offset_x, y + offset_y), radius)
            if phase == GROWTH_MATURE:
                pygame.draw.circle(surface, (205, 48, 42), (x - 2, y - 1), 2)
                pygame.draw.circle(surface, (225, 65, 48), (x + 3, y + 1), 2)


def _draw_alfalfa(surface, field, phase):
    colors = ((74, 126, 64), (70, 156, 70), (53, 145, 61), (42, 127, 52))
    cluster_count = (1, 3, 6, 9)[phase]
    radius = 1 if phase < GROWTH_DEVELOPED else 2
    for row in range(field["height"]):
        for col in range(field["width"]):
            variation = _stable_value(field, "alfalfa", row, col)
            x, y = _plant_anchor(row, col, variation)
            if phase == GROWTH_SEEDED:
                pygame.draw.circle(surface, (61, 84, 43), (x, y), 1)
                continue
            for cluster in range(cluster_count):
                cluster_value = _stable_value(field, "alfalfa", row, col, cluster + 1)
                offset_x = cluster_value % 9 - 4
                offset_y = (cluster_value // 9) % 6
                color = _shift_color(colors[phase], cluster_value % 9 - 4)
                pygame.draw.circle(surface, color, (x + offset_x, y - offset_y), radius)


def _draw_hops(surface, field, phase):
    """Keskeny támrendszeren felfutó, tobozos Komló-sorokat rajzol."""
    vine_colors = ((78, 111, 52), (61, 137, 54), (43, 119, 45), (34, 101, 39))
    heights = (2, 7, 12, 15)
    for row in range(field["height"]):
        for col in range(field["width"]):
            variation = _stable_value(field, "hops", row, col)
            x, y = _plant_anchor(row, col, variation)
            if phase == GROWTH_SEEDED:
                pygame.draw.circle(surface, (65, 78, 40), (x, y), 1)
                continue
            height = heights[phase] + variation % 3 - 1
            top = y - height
            # A világos támhuzal és a rátekeredő zöld inda a többi
            # szántóföldi növénytől kis méretben is jól elkülöníti.
            pygame.draw.line(surface, (116, 103, 73), (x, y), (x, top), 1)
            vine = _shift_color(vine_colors[phase], variation % 7 - 3)
            for offset in range(2, height, 3):
                side = -1 if (offset // 3 + variation) % 2 else 1
                pygame.draw.circle(surface, vine, (x + side * 2, y - offset), 2)
            if phase == GROWTH_MATURE:
                cone = (176, 183, 72)
                pygame.draw.polygon(
                    surface, cone,
                    ((x - 2, top + 3), (x + 2, top + 3), (x, top + 7)),
                )


CROP_RENDERERS = {
    "wheat": _draw_wheat,
    "corn": _draw_corn,
    "tomato": _draw_tomato,
    "alfalfa": _draw_alfalfa,
    "hops": _draw_hops,
}


def _draw_fertilized_detail(surface, field):
    if not field.get("fertilized", False):
        return
    width, height = surface.get_size()
    for index in range(min(12, field["width"] * field["height"])):
        value = _stable_value(field, field.get("crop") or "soil", index, 0, 97)
        x = 6 + value % max(1, width - 12)
        y = 6 + (value // 17) % max(1, height - 12)
        pygame.draw.circle(surface, (80, 54, 34), (x, y), 1)


def _draw_field_status_markers(surface, field):
    """Az aktív mezőállapotokat azonos méretű, egymás mellé rendezett pontokkal jelzi."""
    markers = []
    if field.get("fertilized", False):
        markers.append((
            FERTILIZED_MARKER_COLOR,
            FERTILIZED_MARKER_BORDER_COLOR,
        ))
    if field.get("watered", False):
        markers.append((WATERED_MARKER_COLOR, WATERED_MARKER_BORDER_COLOR))

    start_x, marker_y = FIELD_STATUS_MARKER_POSITION
    for index, (color, border_color) in enumerate(markers):
        center = (start_x + index * FIELD_STATUS_MARKER_SPACING, marker_y)
        pygame.draw.circle(
            surface, color, center, FIELD_STATUS_MARKER_RADIUS,
        )
        pygame.draw.circle(
            surface, border_color, center, FIELD_STATUS_MARKER_RADIUS, 1,
        )


def _cache_key(field, harvest_ready=False):
    crop_id = field.get("crop")
    phase = get_visual_growth_phase(field) if crop_id else None
    return (
        field.get("row", 0), field.get("col", 0),
        field.get("width", FIELD_SIZE), field.get("height", FIELD_SIZE),
        crop_id, phase, bool(field.get("harvest_count", 0)),
        bool(field.get("fertilized", False)),
        bool(field.get("watered", False)),
        bool(field.get("late_harvest_active", False)),
        bool(harvest_ready),
    )


def _create_field_surface(field, harvest_ready=False):
    surface = pygame.Surface(
        (field.get("width", FIELD_SIZE) * TILE_SIZE,
         field.get("height", FIELD_SIZE) * TILE_SIZE)
    )
    _draw_field_base(surface, field, harvest_ready)
    crop_id = field.get("crop")
    renderer = CROP_RENDERERS.get(crop_id)
    if renderer is not None and crop_id in CROPS:
        renderer(surface, field, get_visual_growth_phase(field))
    _draw_fertilized_detail(surface, field)
    _draw_field_status_markers(surface, field)
    return surface


def draw_field(screen, field, harvest_ready=False):
    """A teljes Veteményest egyetlen gyorsítótárazott Surface-ként rajzolja."""
    key = _cache_key(field, harvest_ready)
    surface = _FIELD_SURFACE_CACHE.get(key)
    if surface is None:
        surface = _create_field_surface(field, harvest_ready)
        if len(_FIELD_SURFACE_CACHE) >= MAX_FIELD_SURFACE_CACHE_SIZE:
            _FIELD_SURFACE_CACHE.pop(next(iter(_FIELD_SURFACE_CACHE)))
        _FIELD_SURFACE_CACHE[key] = surface
    screen.blit(
        surface,
        world_to_screen(field["col"] * TILE_SIZE, field["row"] * TILE_SIZE),
    )


def clear_field_render_cache():
    """Teszteléshez vagy grafikai konfigurációváltáshoz üríti a cache-t."""
    _FIELD_SURFACE_CACHE.clear()
