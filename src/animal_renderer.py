import pygame

from constants import TILE_SIZE
from screen_layout import world_to_screen


CATTLE_BODY_COLOR = (153, 94, 57)
CATTLE_BODY_BORDER_COLOR = (92, 53, 32)
CATTLE_LEG_COLOR = (71, 43, 28)
CATTLE_SHADOW_COLOR = (35, 31, 27, 55)
CATTLE_SPRITE_SIZE = 20
CATTLE_DIRECTIONS = ("up", "right", "down", "left")
CATTLE_ROTATION_ANGLES = {
    "up": 0,
    "right": -90,
    "down": 180,
    "left": 90,
}
MAX_CATTLE_SPRITE_CACHE_SIZE = 256
PIG_BODY_COLOR = (222, 145, 153)
PIG_BODY_BORDER_COLOR = (139, 78, 86)
PIG_LEG_COLOR = (119, 68, 76)
PIG_SNOUT_COLOR = (194, 112, 123)
CHICKEN_BODY_COLOR = (239, 228, 190)
CHICKEN_BODY_BORDER_COLOR = (151, 132, 91)
CHICKEN_BEAK_COLOR = (226, 174, 48)
CHICKEN_COMB_COLOR = (185, 58, 48)

_CATTLE_SPRITE_CACHE = {}
_PIG_SPRITE_CACHE = {}
_CHICKEN_SPRITE_CACHE = {}


def _stable_value(value, salt=0):
    result = ((int(value) + 1) * 2654435761 ^ (salt + 1) * 2246822519) & 0xFFFFFFFF
    result ^= result >> 16
    return result


def _get_animal_visual_value(animal, fallback_index=0):
    """Mentett azonosítóból renderelésenként változatlan értéket képez."""
    visual_id = animal.get("visual_id")
    if not isinstance(visual_id, int) or isinstance(visual_id, bool):
        visual_id = (
            (animal.get("pen_row", 0) + 1) * 101
            + (animal.get("pen_col", 0) + 1) * 37
            + fallback_index + 1
        )
    return _stable_value(visual_id) % 13


def get_cattle_visual_variant(animal, fallback_index=0):
    """A vizuális azonosítóból stabil barna árnyalatot képez."""
    # A visszafogott árnyalatváltás nem bontja meg az egyszínű sziluettet.
    value = _get_animal_visual_value(animal, fallback_index)
    return {
        "key": value,
        "body_shift": value % 13 - 6,
    }


def get_pig_visual_variant(animal, fallback_index=0):
    """A Sertés egyszínű rózsaszín testének stabil árnyalatát adja."""
    value = _get_animal_visual_value(animal, fallback_index)
    return {
        "key": value,
        "body_shift": value % 9 - 4,
    }


def _shift_color(color, amount):
    return tuple(max(0, min(255, channel + amount)) for channel in color)


def draw_cattle_legs(surface, variant):
    """Rövid, a testhez simuló lábjelöléseket rajzol."""
    for x in (4, 14):
        for y in (7, 14):
            pygame.draw.rect(surface, CATTLE_LEG_COLOR, (x, y, 2, 3), border_radius=1)


def draw_cattle_body(surface, variant):
    """A nagy, egyszerű test adja a Szarvasmarha fő sziluettjét."""
    rect = pygame.Rect(4, 5, 12, 13)
    body_color = _shift_color(CATTLE_BODY_COLOR, variant["body_shift"])
    pygame.draw.rect(surface, CATTLE_BODY_BORDER_COLOR, rect.inflate(2, 2), border_radius=5)
    pygame.draw.rect(surface, body_color, rect, border_radius=4)


def draw_cattle_head(surface, variant):
    """Részletek nélküli ovális fejet és két apró fület rajzol."""
    head_color = _shift_color(CATTLE_BODY_COLOR, variant["body_shift"])
    pygame.draw.polygon(surface, CATTLE_BODY_BORDER_COLOR, ((7, 3), (4, 1), (7, 1)))
    pygame.draw.polygon(surface, CATTLE_BODY_BORDER_COLOR, ((13, 3), (16, 1), (13, 1)))
    pygame.draw.ellipse(surface, CATTLE_BODY_BORDER_COLOR, (5, 0, 10, 8))
    pygame.draw.ellipse(surface, head_color, (6, 1, 8, 6))


def _create_cattle_sprite(variant, direction):
    canonical = pygame.Surface((CATTLE_SPRITE_SIZE, CATTLE_SPRITE_SIZE), pygame.SRCALPHA)
    draw_cattle_legs(canonical, variant)
    draw_cattle_body(canonical, variant)
    draw_cattle_head(canonical, variant)
    return pygame.transform.rotate(canonical, CATTLE_ROTATION_ANGLES[direction])


def _get_cattle_sprite(animal, direction, fallback_index=0):
    variant = get_cattle_visual_variant(animal, fallback_index)
    key = variant["key"], direction
    sprite = _CATTLE_SPRITE_CACHE.get(key)
    if sprite is None:
        sprite = _create_cattle_sprite(variant, direction)
        if len(_CATTLE_SPRITE_CACHE) >= MAX_CATTLE_SPRITE_CACHE_SIZE:
            _CATTLE_SPRITE_CACHE.pop(next(iter(_CATTLE_SPRITE_CACHE)))
        _CATTLE_SPRITE_CACHE[key] = sprite
    return sprite


def draw_animal_shadow(screen, center, direction, long_size=15, short_size=8):
    """Közös, finom ovális talajárnyékot rajzol az állatok alá."""
    horizontal = direction in ("left", "right")
    width, height = (
        (long_size, short_size) if horizontal else (short_size, long_size)
    )
    shadow = pygame.Surface((width + 4, height + 4), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, CATTLE_SHADOW_COLOR, (2, 2, width, height))
    rect = shadow.get_rect(center=(round(center[0] + 1), round(center[1] - 1)))
    screen.blit(shadow, rect)


def draw_cattle_shadow(screen, center, direction):
    draw_animal_shadow(screen, center, direction)


def draw_cattle(screen, animal, fallback_index=0):
    direction = animal.get("facing_direction", "down")
    if direction not in CATTLE_DIRECTIONS:
        direction = "down"
    world_x = animal["col"] * TILE_SIZE + TILE_SIZE // 2
    world_y = animal["row"] * TILE_SIZE + TILE_SIZE // 2
    center = world_to_screen(world_x, world_y)
    draw_cattle_shadow(screen, center, direction)
    sprite = _get_cattle_sprite(animal, direction, fallback_index)
    screen.blit(sprite, sprite.get_rect(center=(round(center[0]), round(center[1]))))


def draw_pig_legs(surface, variant):
    """Négy rövid, testhez simuló lábjelölést rajzol."""
    for x in (4, 14):
        for y in (8, 14):
            pygame.draw.rect(
                surface, PIG_LEG_COLOR, (x, y, 2, 3), border_radius=1,
            )


def draw_pig_body(surface, variant):
    """A Sertés tömzsi, rózsaszín testét rajzolja."""
    body_color = _shift_color(PIG_BODY_COLOR, variant["body_shift"])
    pygame.draw.ellipse(surface, PIG_BODY_BORDER_COLOR, (3, 5, 14, 14))
    pygame.draw.ellipse(surface, body_color, (4, 6, 12, 12))


def draw_pig_head(surface, variant):
    """Kis fejet, füleket és egyszerű, szem nélküli ormányt rajzol."""
    head_color = _shift_color(PIG_BODY_COLOR, variant["body_shift"])
    pygame.draw.polygon(surface, PIG_BODY_BORDER_COLOR, ((7, 3), (5, 1), (8, 2)))
    pygame.draw.polygon(surface, PIG_BODY_BORDER_COLOR, ((13, 3), (15, 1), (12, 2)))
    pygame.draw.ellipse(surface, PIG_BODY_BORDER_COLOR, (5, 0, 10, 8))
    pygame.draw.ellipse(surface, head_color, (6, 1, 8, 6))
    pygame.draw.ellipse(surface, PIG_SNOUT_COLOR, (8, 0, 4, 3))


def _create_pig_sprite(variant, direction):
    canonical = pygame.Surface(
        (CATTLE_SPRITE_SIZE, CATTLE_SPRITE_SIZE), pygame.SRCALPHA,
    )
    draw_pig_legs(canonical, variant)
    draw_pig_body(canonical, variant)
    draw_pig_head(canonical, variant)
    return pygame.transform.rotate(canonical, CATTLE_ROTATION_ANGLES[direction])


def _get_pig_sprite(animal, direction, fallback_index=0):
    variant = get_pig_visual_variant(animal, fallback_index)
    key = variant["key"], direction
    sprite = _PIG_SPRITE_CACHE.get(key)
    if sprite is None:
        sprite = _create_pig_sprite(variant, direction)
        if len(_PIG_SPRITE_CACHE) >= MAX_CATTLE_SPRITE_CACHE_SIZE:
            _PIG_SPRITE_CACHE.pop(next(iter(_PIG_SPRITE_CACHE)))
        _PIG_SPRITE_CACHE[key] = sprite
    return sprite


def draw_pig(screen, animal, fallback_index=0):
    direction = animal.get("facing_direction", "down")
    if direction not in CATTLE_DIRECTIONS:
        direction = "down"
    world_x = animal["col"] * TILE_SIZE + TILE_SIZE // 2
    world_y = animal["row"] * TILE_SIZE + TILE_SIZE // 2
    center = world_to_screen(world_x, world_y)
    draw_animal_shadow(screen, center, direction, long_size=14, short_size=9)
    sprite = _get_pig_sprite(animal, direction, fallback_index)
    screen.blit(sprite, sprite.get_rect(center=(round(center[0]), round(center[1]))))


def _create_chicken_sprite(direction):
    """Egyszerű, kis méretben is felismerhető felülnézeti Csirkét rajzol."""
    canonical = pygame.Surface(
        (CATTLE_SPRITE_SIZE, CATTLE_SPRITE_SIZE), pygame.SRCALPHA,
    )
    pygame.draw.ellipse(canonical, CHICKEN_BODY_BORDER_COLOR, (4, 5, 12, 14))
    pygame.draw.ellipse(canonical, CHICKEN_BODY_COLOR, (5, 6, 10, 12))
    pygame.draw.ellipse(canonical, CHICKEN_BODY_BORDER_COLOR, (6, 1, 8, 8))
    pygame.draw.ellipse(canonical, CHICKEN_BODY_COLOR, (7, 2, 6, 6))
    pygame.draw.polygon(canonical, CHICKEN_BEAK_COLOR, ((8, 2), (12, 2), (10, 0)))
    pygame.draw.circle(canonical, CHICKEN_COMB_COLOR, (8, 2), 2)
    pygame.draw.circle(canonical, CHICKEN_COMB_COLOR, (11, 2), 2)
    return pygame.transform.rotate(canonical, CATTLE_ROTATION_ANGLES[direction])


def _get_chicken_sprite(direction):
    sprite = _CHICKEN_SPRITE_CACHE.get(direction)
    if sprite is None:
        sprite = _create_chicken_sprite(direction)
        _CHICKEN_SPRITE_CACHE[direction] = sprite
    return sprite


def draw_chicken(screen, animal, fallback_index=0):
    direction = animal.get("facing_direction", "down")
    if direction not in CATTLE_DIRECTIONS:
        direction = "down"
    world_x = animal["col"] * TILE_SIZE + TILE_SIZE // 2
    world_y = animal["row"] * TILE_SIZE + TILE_SIZE // 2
    center = world_to_screen(world_x, world_y)
    draw_animal_shadow(screen, center, direction, long_size=12, short_size=7)
    sprite = _get_chicken_sprite(direction)
    screen.blit(sprite, sprite.get_rect(center=(round(center[0]), round(center[1]))))


ANIMAL_RENDERERS = {
    "cattle": draw_cattle,
    "pig": draw_pig,
    "chicken": draw_chicken,
}


def draw_animal(screen, animal, fallback_index=0):
    renderer = ANIMAL_RENDERERS.get(animal.get("type"))
    if renderer is not None:
        renderer(screen, animal, fallback_index)


def clear_animal_render_cache():
    _CATTLE_SPRITE_CACHE.clear()
    _PIG_SPRITE_CACHE.clear()
    _CHICKEN_SPRITE_CACHE.clear()
