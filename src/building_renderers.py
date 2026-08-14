import math

import pygame

from buildings import (
    BUILDING_TYPES, FARMHOUSE_DEFAULT_LEVEL, FARMHOUSE_LEVELS,
    GARAGE_PARKING_SLOT_SIZE, GARAGE_PARKING_SLOTS,
)
from constants import TILE_SIZE
from screen_layout import world_to_screen


# A procedurális objektumok közös alapértelmezett fényiránya: bal alsó.
# A vetett árnyék ennek ellentétes irányába, jobbra és felfelé tolódik.
PROCEDURAL_LIGHT_DIRECTION = (-1, 1)
PROCEDURAL_SHADOW_OFFSET = (4, -4)
PROCEDURAL_SHADOW_COLOR = (61, 105, 58)

FARMHOUSE_FOUNDATION = (118, 78, 48)
FARMHOUSE_ROOF_LIGHT = (205, 91, 54)
FARMHOUSE_ROOF_DARK = (174, 66, 43)
FARMHOUSE_ROOF_LOWER_LEFT_LIGHT = (209, 95, 57)
FARMHOUSE_ROOF_UPPER_RIGHT_DARK = (170, 63, 42)
FARMHOUSE_OUTLINE = (76, 43, 28)
FARMHOUSE_RIDGE = (112, 49, 34)
FARMHOUSE_CHIMNEY = (224, 207, 166)
FARMHOUSE_CHIMNEY_OUTLINE = (112, 88, 63)
FARMHOUSE_PORCH = (190, 145, 91)
FARMHOUSE_PORCH_DARK = (126, 86, 51)
FARMHOUSE_FENCE_COLOR = (48, 104, 55)
FARMHOUSE_FENCE_WIDTH = 4
FARMHOUSE_BUILDING_INSET = 4

WAREHOUSE_FOUNDATION = (91, 82, 72)
WAREHOUSE_ROOF_LIGHT = (139, 133, 122)
WAREHOUSE_ROOF_DARK = (112, 108, 101)
WAREHOUSE_ROOF_LOWER_LEFT_LIGHT = (147, 141, 129)
WAREHOUSE_ROOF_UPPER_RIGHT_DARK = (103, 99, 93)
WAREHOUSE_OUTLINE = (58, 54, 49)
WAREHOUSE_RIDGE = (78, 75, 70)
WAREHOUSE_PANEL_LINE = (94, 91, 86)
WAREHOUSE_DOOR = (76, 82, 83)
WAREHOUSE_DOOR_FRAME = (45, 48, 48)
WAREHOUSE_RAMP = (165, 155, 137)
WAREHOUSE_RAMP_OUTLINE = (91, 82, 70)
WAREHOUSE_VENT = (68, 72, 72)

MARKET_FOUNDATION = (151, 127, 91)
MARKET_CANOPY_RED = (190, 61, 53)
MARKET_CANOPY_RED_LIGHT = (204, 70, 60)
MARKET_CANOPY_WHITE = (231, 220, 195)
MARKET_CANOPY_WHITE_LIGHT = (240, 230, 207)
MARKET_CANOPY_SHADE = (126, 55, 47)
MARKET_OUTLINE = (74, 47, 35)
MARKET_POST = (111, 72, 42)
MARKET_POST_LIGHT = (145, 98, 55)
MARKET_COUNTER = (190, 143, 82)
MARKET_COUNTER_OUTLINE = (103, 67, 39)
MARKET_CRATE = (151, 99, 52)
MARKET_CRATE_LINE = (91, 58, 34)
MARKET_SACK = (207, 184, 132)
MARKET_SACK_OUTLINE = (125, 102, 67)

GARAGE_FLOOR = (126, 119, 106)
GARAGE_FLOOR_LIGHT = (137, 130, 116)
GARAGE_FLOOR_SHADE = (111, 105, 95)
GARAGE_OUTLINE = (55, 57, 55)
GARAGE_ROOF_LIGHT = (126, 126, 116)
GARAGE_ROOF_DARK = (97, 100, 96)
GARAGE_ROOF_PANEL = (75, 79, 76)
GARAGE_POST = (75, 73, 66)
GARAGE_POST_LIGHT = (111, 105, 91)
GARAGE_PARKING_MARK = (157, 151, 137)

PROCESSING_FOUNDATION = (191, 181, 158)
PROCESSING_WALL = (202, 193, 171)
PROCESSING_ROOF = (103, 108, 107)
PROCESSING_ROOF_LIGHT = (126, 130, 126)
PROCESSING_ROOF_DARK = (77, 82, 82)
PROCESSING_OUTLINE = (66, 62, 55)
PROCESSING_PANEL_LINE = (87, 91, 90)
PROCESSING_GATE = (83, 88, 88)
PROCESSING_GATE_LINE = (52, 56, 56)
PROCESSING_WINDOW = (106, 153, 163)
PROCESSING_WINDOW_LIGHT = (157, 192, 193)
PROCESSING_VENT = (76, 80, 78)
PROCESSING_VENT_LIGHT = (142, 143, 132)

POND_SHORE = (111, 101, 73)
POND_SHORE_DARK = (80, 76, 59)
POND_SHORE_LIGHT = (137, 124, 86)
POND_SHALLOW_WATER = (91, 153, 164)
POND_MAIN_WATER = (65, 133, 153)
POND_DEEP_WATER = (48, 111, 140)
POND_WATER_DARK = (43, 96, 124)
POND_WATER_LIGHT = (132, 184, 187)
POND_DARK_PATCH = (48, 105, 132)
POND_RENDER_SCALE = 2

_POND_SURFACE_CACHE = {}


def _building_rect(building):
    """Az épület változatlan tile-méretéből képernyőtéglalapot számít."""
    screen_x, screen_y = world_to_screen(
        building["col"] * TILE_SIZE,
        building["row"] * TILE_SIZE,
    )
    return pygame.Rect(
        round(screen_x),
        round(screen_y),
        building["width"] * TILE_SIZE,
        building["height"] * TILE_SIZE,
    )


def _draw_building_shadow(screen, footprint, color):
    """Közös, bal alsó fényirányhoz igazított vetett árnyékot rajzol."""
    shadow = footprint.move(*PROCEDURAL_SHADOW_OFFSET)
    pygame.draw.rect(screen, color, shadow, border_radius=2)


def _draw_building_outline(screen, footprint, color):
    """Vékony, egységes külső körvonalat rajzol az épület köré."""
    pygame.draw.rect(screen, color, footprint, 2, border_radius=2)


def _draw_farmhouse_fence(screen, plot):
    """A Farmház teljes telkének egyszerű, procedurális zöld kerítése."""
    pygame.draw.rect(
        screen, FARMHOUSE_FENCE_COLOR, plot, FARMHOUSE_FENCE_WIDTH,
    )


def _draw_farmhouse_body(screen, footprint):
    """A korábbi 4×4-es Farmház-grafikát változatlan elemekből rajzolja."""

    # A bal alsó fényforrás finom árnyéka felül és a jobb oldalon látszik.
    _draw_building_shadow(screen, footprint, PROCEDURAL_SHADOW_COLOR)

    # A teljes foglalási területet lefedő alap megakadályozza a háttér áttűnését.
    pygame.draw.rect(
        screen, FARMHOUSE_FOUNDATION, footprint, border_radius=2,
    )

    roof = pygame.Rect(
        footprint.x + 3,
        footprint.y + 3,
        footprint.width - 6,
        footprint.height - 19,
    )
    ridge_x = roof.centerx

    # A két enyhén eltérő tetősík közös gerincnél találkozik.
    left_plane = [
        roof.topleft,
        (ridge_x, roof.top),
        (ridge_x, roof.bottom),
        roof.bottomleft,
    ]
    right_plane = [
        (ridge_x, roof.top),
        roof.topright,
        roof.bottomright,
        (ridge_x, roof.bottom),
    ]
    pygame.draw.polygon(screen, FARMHOUSE_ROOF_LIGHT, left_plane)
    pygame.draw.polygon(screen, FARMHOUSE_ROOF_DARK, right_plane)

    # Finom irányfény: bal alul világosabb, jobb felül kissé sötétebb.
    pygame.draw.polygon(
        screen,
        FARMHOUSE_ROOF_LOWER_LEFT_LIGHT,
        [
            roof.bottomleft,
            (ridge_x, roof.bottom),
            (roof.left, roof.centery),
        ],
    )
    pygame.draw.polygon(
        screen,
        FARMHOUSE_ROOF_UPPER_RIGHT_DARK,
        [
            (ridge_x, roof.top),
            roof.topright,
            (roof.right, roof.centery),
        ],
    )
    pygame.draw.rect(screen, FARMHOUSE_OUTLINE, roof, 2)
    pygame.draw.line(
        screen,
        FARMHOUSE_RIDGE,
        (ridge_x, roof.top + 2),
        (ridge_x, roof.bottom - 2),
        2,
    )

    # Kis bézs kémény a világosabb tetősík felső részén.
    chimney = pygame.Rect(roof.x + 10, roof.y + 9, 10, 12)
    pygame.draw.rect(screen, FARMHOUSE_CHIMNEY, chimney)
    pygame.draw.rect(screen, FARMHOUSE_CHIMNEY_OUTLINE, chimney, 1)

    # Az alsó sáv keskeny, felülnézetes tornáctető.
    porch = pygame.Rect(
        footprint.x + 7,
        footprint.bottom - 16,
        footprint.width - 14,
        13,
    )
    pygame.draw.rect(screen, FARMHOUSE_PORCH, porch)
    pygame.draw.rect(screen, FARMHOUSE_PORCH_DARK, porch, 2)
    pygame.draw.line(
        screen,
        FARMHOUSE_PORCH_DARK,
        (porch.left + 4, porch.centery),
        (porch.right - 4, porch.centery),
        1,
    )

    # Vékony, egységes külső körvonal.
    _draw_building_outline(screen, footprint, FARMHOUSE_OUTLINE)


def _draw_farmhouse_level_one(screen, footprint):
    """Szerényebb, valódi 3×3-as Farmház I. grafikát rajzol."""
    _draw_building_shadow(screen, footprint, PROCEDURAL_SHADOW_COLOR)
    pygame.draw.rect(
        screen, FARMHOUSE_FOUNDATION, footprint, border_radius=2,
    )
    roof = pygame.Rect(
        footprint.x + 3, footprint.y + 3,
        footprint.width - 6, footprint.height - 15,
    )
    ridge_x = roof.centerx
    pygame.draw.polygon(screen, FARMHOUSE_ROOF_LIGHT, [
        roof.topleft, (ridge_x, roof.top),
        (ridge_x, roof.bottom), roof.bottomleft,
    ])
    pygame.draw.polygon(screen, FARMHOUSE_ROOF_DARK, [
        (ridge_x, roof.top), roof.topright,
        roof.bottomright, (ridge_x, roof.bottom),
    ])
    pygame.draw.polygon(screen, FARMHOUSE_ROOF_LOWER_LEFT_LIGHT, [
        roof.bottomleft, (ridge_x, roof.bottom), (roof.left, roof.centery),
    ])
    pygame.draw.polygon(screen, FARMHOUSE_ROOF_UPPER_RIGHT_DARK, [
        (ridge_x, roof.top), roof.topright, (roof.right, roof.centery),
    ])
    pygame.draw.rect(screen, FARMHOUSE_OUTLINE, roof, 2)
    pygame.draw.line(
        screen, FARMHOUSE_RIDGE,
        (ridge_x, roof.top + 2), (ridge_x, roof.bottom - 2), 2,
    )
    # A kisebb házon egyetlen kémény és keskenyebb tornác jelzi az alapszintet.
    chimney = pygame.Rect(roof.x + 7, roof.y + 7, 7, 9)
    pygame.draw.rect(screen, FARMHOUSE_CHIMNEY, chimney)
    pygame.draw.rect(screen, FARMHOUSE_CHIMNEY_OUTLINE, chimney, 1)
    porch = pygame.Rect(
        footprint.x + 6, footprint.bottom - 12,
        footprint.width - 12, 9,
    )
    pygame.draw.rect(screen, FARMHOUSE_PORCH, porch)
    pygame.draw.rect(screen, FARMHOUSE_PORCH_DARK, porch, 1)
    _draw_building_outline(screen, footprint, FARMHOUSE_OUTLINE)


def draw_farmhouse(screen, building):
    """A füves Farmház-telket, kerítést és jobb alsó házat rajzolja."""
    plot = _building_rect(building)
    is_legacy = (
        building.get("legacy_footprint", False)
        or building.get("width") != BUILDING_TYPES["farmhouse"]["width"]
        or building.get("height") != BUILDING_TYPES["farmhouse"]["height"]
    )
    if is_legacy:
        _draw_farmhouse_body(screen, plot)
        return

    _draw_farmhouse_fence(screen, plot)
    level = building.get("farmhouse_level", 2)
    definition = FARMHOUSE_LEVELS.get(
        level, FARMHOUSE_LEVELS[FARMHOUSE_DEFAULT_LEVEL],
    )
    house_width, house_height = definition["size"]
    footprint = pygame.Rect(
        plot.right - house_width * TILE_SIZE + FARMHOUSE_BUILDING_INSET,
        plot.bottom - house_height * TILE_SIZE + FARMHOUSE_BUILDING_INSET,
        house_width * TILE_SIZE - FARMHOUSE_BUILDING_INSET * 2,
        house_height * TILE_SIZE - FARMHOUSE_BUILDING_INSET * 2,
    )
    if level == 1:
        _draw_farmhouse_level_one(screen, footprint)
    else:
        _draw_farmhouse_body(screen, footprint)


def draw_warehouse(screen, building):
    """Felülnézetes, ipari Raktárt rajzol kizárólag Pygame-primitívekkel."""
    footprint = _building_rect(building)

    # A közös bal alsó fényirány miatt az árnyék felül és jobbra jelenik meg.
    _draw_building_shadow(screen, footprint, PROCEDURAL_SHADOW_COLOR)
    pygame.draw.rect(
        screen, WAREHOUSE_FOUNDATION, footprint, border_radius=2,
    )

    roof = pygame.Rect(
        footprint.x + 3,
        footprint.y + 3,
        footprint.width - 6,
        footprint.height - 22,
    )
    ridge_y = roof.centery

    # A hosszanti gerinc két oldalán eltérő, ipari szürkésbarna tetősíkok futnak.
    upper_plane = [
        roof.topleft,
        roof.topright,
        (roof.right, ridge_y),
        (roof.left, ridge_y),
    ]
    lower_plane = [
        (roof.left, ridge_y),
        (roof.right, ridge_y),
        roof.bottomright,
        roof.bottomleft,
    ]
    pygame.draw.polygon(screen, WAREHOUSE_ROOF_DARK, upper_plane)
    pygame.draw.polygon(screen, WAREHOUSE_ROOF_LIGHT, lower_plane)

    # Finom irányfény: bal alul világosabb, jobb felül sötétebb.
    pygame.draw.polygon(
        screen,
        WAREHOUSE_ROOF_LOWER_LEFT_LIGHT,
        [
            roof.bottomleft,
            (roof.centerx, roof.bottom),
            (roof.left, ridge_y),
        ],
    )
    pygame.draw.polygon(
        screen,
        WAREHOUSE_ROOF_UPPER_RIGHT_DARK,
        [
            (roof.centerx, roof.top),
            roof.topright,
            (roof.right, ridge_y),
        ],
    )

    pygame.draw.rect(screen, WAREHOUSE_OUTLINE, roof, 2)
    pygame.draw.line(
        screen,
        WAREHOUSE_RIDGE,
        (roof.left + 2, ridge_y),
        (roof.right - 2, ridge_y),
        2,
    )

    # A párhuzamos, visszafogott vonalak a fém tetőpaneljeit jelzik.
    panel_spacing = 14
    for panel_x in range(
        roof.left + panel_spacing,
        roof.right,
        panel_spacing,
    ):
        pygame.draw.line(
            screen,
            WAREHOUSE_PANEL_LINE,
            (panel_x, roof.top + 3),
            (panel_x, roof.bottom - 3),
            1,
        )

    # Kis tetőszellőző, amely később más ipari épületeknél is mintául szolgálhat.
    vent = pygame.Rect(roof.right - 18, roof.top + 8, 8, 7)
    pygame.draw.rect(screen, WAREHOUSE_VENT, vent)
    pygame.draw.rect(screen, WAREHOUSE_OUTLINE, vent, 1)

    # Az alsó, út felőli oldalon tagolt rakodókapu és keskeny rakodórámpa látszik.
    loading_door = pygame.Rect(
        footprint.x + 21,
        footprint.bottom - 19,
        footprint.width - 42,
        13,
    )
    pygame.draw.rect(screen, WAREHOUSE_DOOR, loading_door)
    pygame.draw.rect(screen, WAREHOUSE_DOOR_FRAME, loading_door, 2)
    divider_spacing = loading_door.width // 4
    for divider_index in range(1, 4):
        divider_x = loading_door.left + divider_index * divider_spacing
        pygame.draw.line(
            screen,
            WAREHOUSE_DOOR_FRAME,
            (divider_x, loading_door.top + 2),
            (divider_x, loading_door.bottom - 2),
            1,
        )

    ramp = pygame.Rect(
        loading_door.left - 4,
        footprint.bottom - 6,
        loading_door.width + 8,
        4,
    )
    pygame.draw.rect(screen, WAREHOUSE_RAMP, ramp)
    pygame.draw.rect(screen, WAREHOUSE_RAMP_OUTLINE, ramp, 1)

    _draw_building_outline(screen, footprint, WAREHOUSE_OUTLINE)


def draw_market(screen, building):
    """Nyitott, piros-fehér ponyvatetős Piacot rajzol felülnézetből."""
    footprint = _building_rect(building)

    _draw_building_shadow(screen, footprint, PROCEDURAL_SHADOW_COLOR)
    pygame.draw.rect(
        screen, MARKET_FOUNDATION, footprint, border_radius=2,
    )

    canopy = pygame.Rect(
        footprint.x + 3,
        footprint.y + 3,
        footprint.width - 6,
        footprint.height - 22,
    )

    # Ritka, jól olvasható váltakozó csíkok alkotják a ponyvatetőt.
    stripe_width = 12
    stripe_index = 0
    stripe_x = canopy.left
    while stripe_x < canopy.right:
        stripe_right = min(stripe_x + stripe_width, canopy.right)
        stripe_rect = pygame.Rect(
            stripe_x,
            canopy.top,
            stripe_right - stripe_x,
            canopy.height,
        )
        stripe_color = (
            MARKET_CANOPY_RED
            if stripe_index % 2 == 0
            else MARKET_CANOPY_WHITE
        )
        pygame.draw.rect(screen, stripe_color, stripe_rect)

        # A csíkok alsó éle a bal alsó fényforrás miatt kissé világosabb.
        light_color = (
            MARKET_CANOPY_RED_LIGHT
            if stripe_index % 2 == 0
            else MARKET_CANOPY_WHITE_LIGHT
        )
        pygame.draw.line(
            screen,
            light_color,
            (stripe_rect.left, stripe_rect.bottom - 2),
            (stripe_rect.right - 1, stripe_rect.bottom - 2),
            2,
        )
        stripe_x = stripe_right
        stripe_index += 1

    # A jobb és felső belső perem finom sötétítése követi a közös fényirányt.
    pygame.draw.line(
        screen,
        MARKET_CANOPY_SHADE,
        (canopy.left + 1, canopy.top + 1),
        (canopy.right - 2, canopy.top + 1),
        1,
    )
    pygame.draw.line(
        screen,
        MARKET_CANOPY_SHADE,
        (canopy.right - 2, canopy.top + 1),
        (canopy.right - 2, canopy.bottom - 2),
        1,
    )
    pygame.draw.rect(screen, MARKET_OUTLINE, canopy, 2)

    # A négy visszafogott faoszlop a ponyva sarkainál látszik.
    post_size = 5
    for post_center in (
        (canopy.left + 5, canopy.top + 5),
        (canopy.right - 6, canopy.top + 5),
        (canopy.left + 5, canopy.bottom - 6),
        (canopy.right - 6, canopy.bottom - 6),
    ):
        post = pygame.Rect(0, 0, post_size, post_size)
        post.center = post_center
        pygame.draw.rect(screen, MARKET_POST, post)
        pygame.draw.line(
            screen,
            MARKET_POST_LIGHT,
            post.bottomleft,
            post.bottomright,
            1,
        )

    # Az alsó nyitott sávban jelenik meg az árusítópult és a kirakott áru.
    counter = pygame.Rect(
        footprint.x + 17,
        footprint.bottom - 18,
        footprint.width - 34,
        9,
    )
    pygame.draw.rect(screen, MARKET_COUNTER, counter)
    pygame.draw.rect(screen, MARKET_COUNTER_OUTLINE, counter, 1)
    pygame.draw.line(
        screen,
        MARKET_COUNTER_OUTLINE,
        (counter.left + 3, counter.centery),
        (counter.right - 3, counter.centery),
        1,
    )

    crate = pygame.Rect(footprint.x + 5, footprint.bottom - 16, 9, 9)
    pygame.draw.rect(screen, MARKET_CRATE, crate)
    pygame.draw.rect(screen, MARKET_CRATE_LINE, crate, 1)
    pygame.draw.line(
        screen, MARKET_CRATE_LINE, crate.topleft, crate.bottomright, 1,
    )
    pygame.draw.line(
        screen, MARKET_CRATE_LINE, crate.topright, crate.bottomleft, 1,
    )

    sack_center = (footprint.right - 10, footprint.bottom - 11)
    pygame.draw.circle(screen, MARKET_SACK, sack_center, 5)
    pygame.draw.circle(screen, MARKET_SACK_OUTLINE, sack_center, 5, 1)
    pygame.draw.line(
        screen,
        MARKET_SACK_OUTLINE,
        (sack_center[0] - 2, sack_center[1] - 3),
        (sack_center[0] + 2, sack_center[1] - 3),
        1,
    )

    _draw_building_outline(screen, footprint, MARKET_OUTLINE)


def _garage_parking_rect(footprint, row_offset, col_offset):
    """A logikai garázshely tile-eltolásából képernyőtéglalapot készít."""
    return pygame.Rect(
        footprint.x + col_offset * TILE_SIZE,
        footprint.y + row_offset * TILE_SIZE,
        GARAGE_PARKING_SLOT_SIZE * TILE_SIZE,
        GARAGE_PARKING_SLOT_SIZE * TILE_SIZE,
    )


def draw_garage(screen, building):
    """Nyitott gépszínt és a négy valódi parkolóhely jelölését rajzolja."""
    footprint = _building_rect(building)

    _draw_building_shadow(screen, footprint, PROCEDURAL_SHADOW_COLOR)
    pygame.draw.rect(
        screen, GARAGE_FLOOR, footprint, border_radius=2,
    )

    # Finom burkolati fény és árnyék jelzi a közös bal alsó fényirányt.
    pygame.draw.line(
        screen,
        GARAGE_FLOOR_LIGHT,
        (footprint.left + 2, footprint.bottom - 2),
        (footprint.right - 2, footprint.bottom - 2),
        2,
    )
    pygame.draw.line(
        screen,
        GARAGE_FLOOR_SHADE,
        (footprint.right - 2, footprint.top + 2),
        (footprint.right - 2, footprint.bottom - 2),
        2,
    )

    # A jelölések ugyanabból a négy logikai parkolóhelyből készülnek,
    # amelyeket a traktorok parkolási rendszere is használ.
    for row_offset, col_offset in GARAGE_PARKING_SLOTS:
        parking_rect = _garage_parking_rect(
            footprint, row_offset, col_offset,
        ).inflate(-6, -6)
        pygame.draw.rect(
            screen, GARAGE_PARKING_MARK, parking_rect, 1,
        )

    # A hátsó keskeny fémtető nem fedi el a nyitott parkolóterületet.
    roof = pygame.Rect(
        footprint.x + 3,
        footprint.y + 3,
        footprint.width - 6,
        14,
    )
    roof_split = roof.centery
    pygame.draw.rect(
        screen,
        GARAGE_ROOF_DARK,
        (roof.left, roof.top, roof.width, roof_split - roof.top),
    )
    pygame.draw.rect(
        screen,
        GARAGE_ROOF_LIGHT,
        (roof.left, roof_split, roof.width, roof.bottom - roof_split),
    )
    for panel_x in range(roof.left + 13, roof.right, 13):
        pygame.draw.line(
            screen,
            GARAGE_ROOF_PANEL,
            (panel_x, roof.top + 2),
            (panel_x, roof.bottom - 2),
            1,
        )
    pygame.draw.rect(screen, GARAGE_OUTLINE, roof, 2)

    # A két oldalsó tartósor szabadon hagyja az alsó behajtási oldalt.
    post_size = 5
    for post_center in (
        (footprint.left + 5, footprint.top + 8),
        (footprint.right - 6, footprint.top + 8),
        (footprint.left + 5, footprint.centery),
        (footprint.right - 6, footprint.centery),
        (footprint.left + 5, footprint.bottom - 12),
        (footprint.right - 6, footprint.bottom - 12),
    ):
        post = pygame.Rect(0, 0, post_size, post_size)
        post.center = post_center
        pygame.draw.rect(screen, GARAGE_POST, post)
        pygame.draw.line(
            screen,
            GARAGE_POST_LIGHT,
            post.bottomleft,
            post.bottomright,
            1,
        )

    # A gépszín külső kerete alul nyitva marad a behajtáshoz.
    pygame.draw.line(
        screen,
        GARAGE_OUTLINE,
        footprint.topleft,
        footprint.topright,
        2,
    )
    pygame.draw.line(
        screen,
        GARAGE_OUTLINE,
        footprint.topleft,
        footprint.bottomleft,
        2,
    )
    pygame.draw.line(
        screen,
        GARAGE_OUTLINE,
        footprint.topright,
        footprint.bottomright,
        2,
    )


def draw_processing_plant(screen, building):
    """Kompakt, felülnézetes ipari üzemet rajzol Pygame primitívekből."""
    footprint = _building_rect(building)
    _draw_building_shadow(screen, footprint, PROCEDURAL_SHADOW_COLOR)
    pygame.draw.rect(
        screen, PROCESSING_FOUNDATION, footprint, border_radius=2,
    )

    body = footprint.inflate(-6, -6)
    pygame.draw.rect(screen, PROCESSING_WALL, body, border_radius=2)
    roof = pygame.Rect(
        body.left + 3, body.top + 3, body.width - 6, body.height - 25,
    )
    pygame.draw.rect(screen, PROCESSING_ROOF, roof)

    # A bal alsó fényforrás a tető alsó és bal peremét világosítja,
    # a felső és jobb oldalt pedig finoman sötétíti.
    pygame.draw.line(
        screen, PROCESSING_ROOF_LIGHT,
        (roof.left + 1, roof.bottom - 1),
        (roof.right - 1, roof.bottom - 1), 3,
    )
    pygame.draw.line(
        screen, PROCESSING_ROOF_LIGHT,
        (roof.left + 1, roof.top + 1),
        (roof.left + 1, roof.bottom - 1), 2,
    )
    pygame.draw.line(
        screen, PROCESSING_ROOF_DARK, roof.topleft, roof.topright, 3,
    )
    pygame.draw.line(
        screen, PROCESSING_ROOF_DARK, roof.topright, roof.bottomright, 3,
    )
    for panel_x in range(roof.left + 18, roof.right, 18):
        pygame.draw.line(
            screen, PROCESSING_PANEL_LINE,
            (panel_x, roof.top + 4), (panel_x, roof.bottom - 4), 1,
        )

    # A déli oldali nagy kapu és rakodóperon kis méretben is ipari jelleget ad.
    gate = pygame.Rect(0, 0, min(46, body.width // 2), 17)
    gate.midbottom = (body.centerx, body.bottom - 2)
    pygame.draw.rect(screen, PROCESSING_GATE, gate)
    pygame.draw.rect(screen, PROCESSING_GATE_LINE, gate, 2)
    for gate_y in range(gate.top + 5, gate.bottom, 5):
        pygame.draw.line(
            screen, PROCESSING_GATE_LINE,
            (gate.left + 2, gate_y), (gate.right - 2, gate_y), 1,
        )
    apron = pygame.Rect(gate.left - 5, gate.bottom, gate.width + 10, 4)
    pygame.draw.rect(screen, PROCESSING_ROOF_LIGHT, apron)
    pygame.draw.rect(screen, PROCESSING_OUTLINE, apron, 1)

    for window_x in (body.left + 10, body.right - 18):
        window = pygame.Rect(window_x, body.bottom - 17, 8, 6)
        pygame.draw.rect(screen, PROCESSING_WINDOW, window)
        pygame.draw.line(
            screen, PROCESSING_WINDOW_LIGHT,
            window.bottomleft, window.bottomright, 1,
        )
        pygame.draw.rect(screen, PROCESSING_OUTLINE, window, 1)

    # Egyszerű tetőszellőző és kémény, erős részletezés nélkül.
    vent = pygame.Rect(roof.right - 22, roof.top + 11, 13, 11)
    pygame.draw.rect(screen, PROCESSING_VENT, vent)
    pygame.draw.line(
        screen, PROCESSING_VENT_LIGHT,
        vent.bottomleft, vent.bottomright, 2,
    )
    pygame.draw.rect(screen, PROCESSING_OUTLINE, vent, 1)
    for vent_x in range(vent.left + 3, vent.right - 1, 4):
        pygame.draw.line(
            screen, PROCESSING_OUTLINE,
            (vent_x, vent.top + 2), (vent_x, vent.bottom - 2), 1,
        )
    chimney = pygame.Rect(roof.left + 12, roof.top + 9, 9, 9)
    pygame.draw.rect(screen, PROCESSING_VENT_LIGHT, chimney)
    pygame.draw.rect(screen, PROCESSING_OUTLINE, chimney, 2)

    _draw_building_outline(screen, footprint, PROCESSING_OUTLINE)


def _pond_variant(building):
    """A Tó pozíciójából stabil, villogásmentes grafikai változatot képez."""
    return (
        (building["row"] + 1) * 73856093
        ^ (building["col"] + 1) * 19349663
    ) & 3


def _organic_pond_points(width, height, inset, variant, point_count=48):
    """Sokpontos, determinisztikus és finoman szabálytalan tókontúrt készít."""
    center_x = width / 2
    center_y = height / 2
    radius_x = max(1, width / 2 - inset)
    radius_y = max(1, height / 2 - inset)
    phase = variant * 0.71
    points = []
    for index in range(point_count):
        angle = math.tau * index / point_count
        variation = (
            1.0
            + 0.045 * math.sin(angle * 3 + phase)
            + 0.025 * math.sin(angle * 5 - phase * 1.4)
            + 0.014 * math.cos(angle * 7 + phase * 0.6)
        )
        points.append((
            round(center_x + math.cos(angle) * radius_x * variation),
            round(center_y + math.sin(angle) * radius_y * variation),
        ))
    return points


def _create_pond_surface(width, height, variant):
    """Egyetlen cache-elhető Surface-re rajzolja a teljes Tó grafikáját."""
    scale = POND_RENDER_SCALE
    render_size = width * scale, height * scale
    surface = pygame.Surface(render_size, pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    shore = _organic_pond_points(*render_size, 7 * scale, variant)
    shallow = _organic_pond_points(*render_size, 10 * scale, variant)
    main_water = _organic_pond_points(*render_size, 14 * scale, variant)
    deep = _organic_pond_points(*render_size, 23 * scale, variant)

    pygame.draw.polygon(surface, POND_SHORE, shore)
    pygame.draw.polygon(surface, POND_SHALLOW_WATER, shallow)
    pygame.draw.polygon(surface, POND_MAIN_WATER, main_water)
    pygame.draw.polygon(surface, POND_DEEP_WATER, deep)

    # Felső és jobb oldalon sötétebb, bal és alsó oldalon világosabb perem
    # jelzi a játék egységes, bal alsó irányból érkező fényét.
    pygame.draw.lines(
        surface, POND_SHORE_DARK, False, shore[35:] + shore[:5], 2 * scale,
    )
    pygame.draw.lines(
        surface, POND_SHORE_LIGHT, False, shore[10:27], 2 * scale,
    )
    pygame.draw.lines(
        surface, POND_WATER_DARK, False, deep[35:] + deep[:5], scale,
    )
    pygame.draw.lines(
        surface, POND_WATER_LIGHT, False, deep[10:27], scale,
    )

    # A részletek kizárólag a stabil változatból származnak, ezért nem villognak.
    for index in range(2):
        wave_y = (round(height * (0.39 + index * 0.19)) + variant - 1) * scale
        wave_x = round(width * (0.31 + ((index + variant) % 2) * 0.22)) * scale
        wave_length = max(7, width // 11) * scale
        pygame.draw.line(
            surface, POND_WATER_LIGHT,
            (wave_x, wave_y), (wave_x + wave_length, wave_y), scale,
        )
    for index in range(2):
        patch_x = (round(width * (0.42 + index * 0.15)) + variant) * scale
        patch_y = round(height * (0.64 - index * 0.12)) * scale
        pygame.draw.circle(
            surface, POND_DARK_PATCH, (patch_x, patch_y), 2 * scale,
        )
    return pygame.transform.smoothscale(surface, (width, height))


def draw_pond(screen, building):
    """Természetes hatású, valódi felülnézetes Tavat rajzol."""
    footprint = _building_rect(building)
    variant = _pond_variant(building)
    cache_key = footprint.width, footprint.height, variant
    pond_surface = _POND_SURFACE_CACHE.get(cache_key)
    if pond_surface is None:
        pond_surface = _create_pond_surface(
            footprint.width, footprint.height, variant,
        )
        _POND_SURFACE_CACHE[cache_key] = pond_surface
    screen.blit(pond_surface, footprint.topleft)


# Új, típusonkénti procedurális épületgrafika egyetlen regisztrációval adható hozzá.
BUILDING_RENDERERS = {
    "farmhouse": draw_farmhouse,
    "warehouse": draw_warehouse,
    "market": draw_market,
    "garage": draw_garage,
    "pond": draw_pond,
    "processing_plant": draw_processing_plant,
}


def has_procedural_renderer(building_type):
    return building_type in BUILDING_RENDERERS


def draw_procedural_buildings(screen, buildings):
    """A regisztrált épülettípusokat saját procedurális rajzolójukhoz irányítja."""
    # A talajjellegű Tó az önálló épületek előtt kerül a világ fölé.
    for building in buildings:
        if building.get("type") != "pond":
            continue
        renderer = BUILDING_RENDERERS.get("pond")
        renderer(screen, building)
    for building in buildings:
        if building.get("type") == "pond":
            continue
        renderer = BUILDING_RENDERERS.get(building.get("type"))
        if renderer is not None:
            renderer(screen, building)
