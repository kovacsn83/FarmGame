import pygame

from animals import ANIMAL_TYPES
from asset_loader import (
    load_hud_calendar_icon, load_hud_menu_icon, load_quest_icon,
    load_time_speed_icons,
    load_toolbar_icons, toolbar_icon_path,
)
from buildings import (
    BUILD_OPTIONS, BUILDING_TYPES, get_total_capacity, get_total_inventory,
)
from bank import LOAN_TERM_WEEKS
from constants import (
    BOTTOM_BAR_HEIGHT, COLOR_BUTTON, COLOR_BUTTON_ACTIVE, COLOR_BUTTON_BORDER,
    COLOR_FIELD, COLOR_ROAD, COLOR_TEXT, COLOR_TOOLBAR, COLOR_TOOLBAR_LINE,
    TOOL_ANIMAL_HUSBANDRY, TOOL_BUILD, TOOL_BULLDOZER, TOOL_HARVEST,
    TOOL_FERTILIZE, TOOL_INSPECT, TOOL_ORCHARD, TOOL_PLANT, TOOL_ROAD,
    TOOL_WATERING,
    TOP_BAR_HEIGHT,
)
from crops import CROPS, get_crop_growth_weeks, get_crop_week_intervals
from game_rules import (
    UPGRADES, get_upgrade_status, is_build_option_unlocked,
)
from inventory import (
    get_inventory_item_ids, get_inventory_item_name, get_marketable_item_ids,
)
from maintenance import format_annual_maintenance_rate
from money_format import format_money
from financial_history import (
    EXPENSE_ANIMAL_FEED, EXPENSE_ANIMAL_PURCHASE, EXPENSE_CONSTRUCTION,
    EXPENSE_FRUIT_TREE, EXPENSE_LOAN_REPAYMENT, EXPENSE_MAINTENANCE,
    EXPENSE_PLANTING, EXPENSE_PROCESSING_INPUT, EXPENSE_SHIPPING,
    EXPENSE_UPGRADE, EXPENSE_VEHICLE,
    INCOME_CROP_SALES, INCOME_LIVESTOCK_SALES, INCOME_LOAN,
    INCOME_ORCHARD_SALES, INCOME_PROCESSED_PRODUCT_SALES,
)
from orchards import TREE_TYPES
from processing import (
    PROCESSING_RECIPES, PROCESSING_STATUS_FULL, PROCESSING_STATUS_IN_TRANSIT,
    PROCESSING_STATUS_NO_MONEY, PROCESSING_STATUS_PROCESSING,
    PROCESSING_STATUS_READY, PROCESSING_STATUS_STOPPED,
    get_processing_inventory_used, get_processing_output_ids,
    get_processing_recipe_ids, initialize_processing_plant,
    select_processing_recipe,
)
from time_system import (
    SEASON_PERIODS, TIME_NORMAL, WEEKS_PER_YEAR, Season, format_game_time,
    get_season_for_week, get_time_speed_indicator, get_year_and_week,
)
from vehicle_types import VEHICLE_TYPE_DEFINITIONS, VehicleType
from screen_layout import get_screen_center, get_screen_size, get_toolbar_top


BUTTON_SIZE = 30
ICON_SIZE = 24
PLACEHOLDER_SIZE = 20
BUTTON_GAP = 10
TOOLBAR_GROUP_SPACING = 18
TOOLBAR_UTILITY_RIGHT_MARGIN = 12
TOOLBAR_UTILITY_MIN_GAP = 36
TOOLTIP_PADDING_X = 8
TOOLTIP_PADDING_Y = 5
TOOLTIP_OFFSET = 12
TOOLTIP_MAX_WIDTH = 440
TOOLTIP_LINE_GAP = 2
HUD_RIGHT_MARGIN = 12
HUD_LEFT_MARGIN = 12
HUD_TIME_GAP = 8
HUD_BLOCK_GAP = 20
HUD_TIME_ICON_SIZE = 20
HUD_MENU_BUTTON_SIZE = 30
HUD_MENU_ICON_SIZE = 20
HUD_MENU_GAP = 12
HUD_CALENDAR_BUTTON_SIZE = 30
HUD_CALENDAR_ICON_SIZE = 20
HUD_CALENDAR_GAP = 8

FINANCE_PANEL_WIDTH = 980
FINANCE_PANEL_HEIGHT = 700
FINANCE_PANEL_PADDING = 24
FINANCE_ROW_HEIGHT = 24
FINANCE_SECTION_GAP = 10
FINANCE_COLUMN_GAP = 28
FINANCE_HEADER_HEIGHT = 72
FINANCE_NET_HEIGHT = 52
FINANCE_SCROLL_STEP = 48
FINANCE_INCOME_COLOR = (45, 125, 70)
FINANCE_EXPENSE_COLOR = (160, 70, 55)
FINANCE_SEPARATOR_COLOR = (150, 150, 140)

NEWS_BAR_LEFT_MARGIN = 12
NEWS_BAR_BOTTOM_MARGIN = 10
NEWS_BAR_MAX_WIDTH = 560
NEWS_BAR_PADDING_X = 12
NEWS_BAR_PADDING_Y = 8
NEWS_BAR_BACKGROUND = (245, 243, 230, 220)
NEWS_BAR_BORDER = (105, 105, 95)
NEWS_BAR_TEXT_COLOR = (35, 35, 32)

CALENDAR_PANEL_WIDTH = 720
CALENDAR_PANEL_HEIGHT = 390
CALENDAR_PANEL_PADDING = 24
CALENDAR_TITLE_GAP = 12
CALENDAR_TIMELINE_TOP_GAP = 32
CALENDAR_TIMELINE_HEIGHT = 18
CALENDAR_ROW_HEIGHT = 42
CALENDAR_ROW_LABEL_WIDTH = 110
CALENDAR_TIMELINE_BORDER = (100, 100, 95)
CALENDAR_SEASON_SEPARATOR = (90, 90, 85)
CALENDAR_CURRENT_WEEK_COLOR = (190, 75, 55)
CALENDAR_CROP_TIMELINE_COLOR = (235, 233, 222)
CALENDAR_PLANTING_PERIOD_COLOR = (75, 160, 85)
CALENDAR_HARVEST_PERIOD_COLOR = (218, 174, 55)
CALENDAR_SEASON_COLORS = {
    Season.WINTER: (205, 218, 226),
    Season.SPRING: (196, 222, 188),
    Season.SUMMER: (226, 220, 160),
    Season.AUTUMN: (211, 184, 151),
}

QUEST_PANEL_RIGHT_MARGIN = 12
QUEST_PANEL_TOP_MARGIN = 12
QUEST_ICON_SIZE = 100
QUEST_LABEL_GAP = 8
QUEST_LABEL_PADDING_X = 10
QUEST_LABEL_PADDING_Y = 7
QUEST_LABEL_BACKGROUND = (245, 245, 240, 200)
QUEST_IMAGE_BORDER_WIDTH = 2
QUEST_IMAGE_BORDER_COLOR = (110, 110, 110)
QUEST_COMPLETED_COLOR = (45, 150, 65)
QUEST_CHECK_SIZE = 16

PROCESSING_RECIPE_ROW_HEIGHT = 30
PROCESSING_RECIPE_VISIBLE_ROWS = 4
PROCESSING_RECIPE_CHECKBOX_SIZE = 18
PROCESSING_RECIPE_CHECK_COLOR = (55, 105, 65)
QUEST_CHECK_GAP = 6
QUEST_LABEL_MAX_TEXT_WIDTH = 300
QUEST_LABEL_LINE_GAP = 2

INFO_PANEL_WIDTH = 360
INFO_PANEL_PADDING = 20
INFO_PANEL_ITEM_SPACING = 22
INFO_PANEL_BACKGROUND = (245, 245, 240)
INFO_PANEL_BORDER = (60, 60, 60)
INFO_PANEL_SEPARATOR = (140, 140, 140)

CROP_PANEL_WIDTH = 440
CROP_CARD_HEIGHT = 114
CROP_CARD_GAP = 12
CROP_CARD_BACKGROUND = (232, 232, 225)
CROP_CARD_HOVER = (220, 230, 210)

ANIMAL_HUSBANDRY_PANEL_WIDTH = 440
ANIMAL_CARD_HEIGHT = 82
ANIMAL_CARD_GAP = 12

MARKET_PANEL_WIDTH = 760
MARKET_PANEL_MAX_HEIGHT = 700
MARKET_TWO_COLUMN_MIN_WIDTH = 600
MARKET_COLUMN_GAP = 14
MARKET_CARD_HEIGHT = 108
MARKET_CARD_GAP = 12
MARKET_LIST_TOP = 58
MARKET_LIST_BOTTOM_PADDING = 20
MARKET_SCROLL_STEP = 60

BUILDING_PANEL_WIDTH = 760
BUILDING_CARD_HEIGHT = 112
BUILDING_CARD_GAP = 12

UPGRADE_PANEL_WIDTH = 480
UPGRADE_CARD_HEIGHT = 92
UPGRADE_CARD_GAP = 10
UPGRADE_INFO_HITBOX_SIZE = 20
UPGRADE_INFO_MARGIN = 9
UPGRADE_INFO_FILL = (218, 220, 213)
UPGRADE_INFO_BORDER = (95, 95, 88)

POPUP_TITLES = {
    "warehouse": "Raktár",
    "market": "Piac",
    "crop_selection": "Ültetés",
    "building_selection": "Épületek",
    "farmhouse": "Farmház - Fejlesztések",
    "garage": "Garázs",
    "pond": "Tó",
    "animal_husbandry": "Állattartás",
    "orchard_selection": "Gyümölcsös",
    "processing_plant": "Feldolgozó üzem",
}

PRIMARY_TOOL_GROUPS = [
    [
        {"name": "Info", "icon_color": (255, 255, 255),
         "icon_path": toolbar_icon_path("cursor_24.png"),
         "tool": TOOL_INSPECT},
    ],
    [
        {"name": "Út", "icon_color": COLOR_ROAD,
         "icon_path": toolbar_icon_path("road_24.png"),
         "tool": TOOL_ROAD},
        {"name": "Épületek", "icon_color": COLOR_FIELD,
         "icon_path": toolbar_icon_path("house_24.png"),
         "tool": TOOL_BUILD},
    ],
    [
        {"name": "Ültetés", "icon_color": (50, 170, 50),
         "icon_path": toolbar_icon_path("plant_24.png"),
         "tool": TOOL_PLANT},
        {"name": "Locsolás", "icon_color": (65, 145, 185),
         "icon_path": toolbar_icon_path("watering-24.png"),
         "tool": TOOL_WATERING},
        {"name": "Trágyázás", "icon_color": (116, 83, 52),
         "icon_path": toolbar_icon_path("toolbar-fertilizer-24.png"),
         "tool": TOOL_FERTILIZE},
        {"name": "Aratás", "icon_color": (220, 50, 50),
         "icon_path": toolbar_icon_path("tractor_24.png"),
         "tool": TOOL_HARVEST},
    ],
    [
        {"name": "Állattartás", "icon_color": (145, 100, 65),
         "icon_path": toolbar_icon_path("animal_husbandry_24.png"),
         "tool": TOOL_ANIMAL_HUSBANDRY},
    ],
    [
        {"name": "Gyümölcsös", "icon_color": (80, 135, 65),
         "icon_path": toolbar_icon_path("fruit_tree_24.png"),
         "tool": TOOL_ORCHARD},
    ],
]

UTILITY_TOOL_GROUPS = [
    [
        {"name": "Buldózer", "icon_color": (255, 220, 0),
         "icon_path": toolbar_icon_path("bulldozer_24.png"),
         "tool": TOOL_BULLDOZER},
    ],
]

# Kompatibilis, lapos bejárási sorrend a közös ikon-, rajzoló- és tooltip-rendszerhez.
TOOL_GROUPS = PRIMARY_TOOL_GROUPS + UTILITY_TOOL_GROUPS

# Az ikonbetöltés és kirajzolás továbbra is egyetlen lapos definíciólistát kap.
TOOLS = [tool for group in TOOL_GROUPS for tool in group]

HUD_BUTTON_TOOLTIPS = {
    "menu": "Menü",
    "calendar": "Gazdálkodási naptár",
}


def responsive_panel_width(desired_width, minimum_width=280):
    """A popup szélességét az aktuális ablakon belül tartja."""
    screen_width, _ = get_screen_size()
    return min(desired_width, max(minimum_width, screen_width - 20))


def _toolbar_groups_width(groups):
    """Egy konfigurált Toolbar-csoport teljes vízszintes helyigénye."""
    button_count = sum(len(group) for group in groups)
    inner_gap_count = sum(max(0, len(group) - 1) for group in groups)
    group_gap_count = max(0, len(groups) - 1)
    return (
        button_count * BUTTON_SIZE
        + inner_gap_count * BUTTON_GAP
        + group_gap_count * TOOLBAR_GROUP_SPACING
    )


def _position_toolbar_groups(buttons, groups, start_x, button_y):
    """A megadott eszközcsoportokat a közös térközszabályokkal helyezi el."""
    button_x = start_x
    for group_index, group in enumerate(groups):
        for tool_index, tool in enumerate(group):
            buttons[tool["tool"]] = pygame.Rect(
                button_x,
                button_y,
                BUTTON_SIZE,
                BUTTON_SIZE,
            )
            button_x += BUTTON_SIZE
            if tool_index < len(group) - 1:
                button_x += BUTTON_GAP
        if group_index < len(groups) - 1:
            button_x += TOOLBAR_GROUP_SPACING


def create_buttons():
    screen_width, _ = get_screen_size()
    primary_width = _toolbar_groups_width(PRIMARY_TOOL_GROUPS)
    utility_width = _toolbar_groups_width(UTILITY_TOOL_GROUPS)
    primary_start_x = (screen_width - primary_width) // 2
    utility_start_x = (
        screen_width - TOOLBAR_UTILITY_RIGHT_MARGIN - utility_width
    )

    # Keskeny ablaknál is megmarad a két csoport jól látható elkülönítése.
    primary_start_x = min(
        primary_start_x,
        utility_start_x - TOOLBAR_UTILITY_MIN_GAP - primary_width,
    )
    primary_start_x = max(0, primary_start_x)
    toolbar_top = get_toolbar_top()
    button_y = toolbar_top + (BOTTOM_BAR_HEIGHT - BUTTON_SIZE) // 2
    buttons = {}
    _position_toolbar_groups(
        buttons, PRIMARY_TOOL_GROUPS, primary_start_x, button_y,
    )
    _position_toolbar_groups(
        buttons, UTILITY_TOOL_GROUPS, utility_start_x, button_y,
    )
    return buttons


def create_toolbar_icons():
    """Előkészíti az opcionális ikonokat a központi toolbar-definíciókból."""
    return load_toolbar_icons(TOOLS, ICON_SIZE)


def create_time_speed_icons():
    """Induláskor előkészíti a HUD idősebesség-ikonjait."""
    return load_time_speed_icons(HUD_TIME_ICON_SIZE)


def create_menu_button():
    """A felső HUD legelső, balra igazított elemének téglalapja."""
    return pygame.Rect(
        HUD_LEFT_MARGIN,
        (TOP_BAR_HEIGHT - HUD_MENU_BUTTON_SIZE) // 2,
        HUD_MENU_BUTTON_SIZE,
        HUD_MENU_BUTTON_SIZE,
    )


def create_menu_icon():
    """A menüikont a projekt közös assetbetöltő rendszerével készíti elő."""
    return load_hud_menu_icon(HUD_MENU_ICON_SIZE)


def create_calendar_button(menu_button=None):
    """A FarmGame gomb és az év/hét kijelzés közötti Naptár gomb helye."""
    left = (
        menu_button.right + HUD_CALENDAR_GAP
        if menu_button is not None
        else HUD_LEFT_MARGIN
    )
    return pygame.Rect(
        left,
        (TOP_BAR_HEIGHT - HUD_CALENDAR_BUTTON_SIZE) // 2,
        HUD_CALENDAR_BUTTON_SIZE,
        HUD_CALENDAR_BUTTON_SIZE,
    )


def create_calendar_icon():
    """A Naptár gomb ikonját a közös assetbetöltővel készíti elő."""
    return load_hud_calendar_icon(HUD_CALENDAR_ICON_SIZE)


def create_quest_icon():
    """Induláskor egyszer betölti a Quest megjelenítés 100×100 pixeles képét."""
    return load_quest_icon(QUEST_ICON_SIZE)


class QuestPanel:
    """Az aktuális küldetést kompakt ikon és szövegcímke formájában jeleníti meg."""

    def __init__(self, icon=None):
        self.icon = icon
        framed_icon_size = QUEST_ICON_SIZE + QUEST_IMAGE_BORDER_WIDTH * 2
        self.rect = pygame.Rect(0, 0, 0, framed_icon_size)
        self.image_rect = pygame.Rect(
            0, 0, framed_icon_size, framed_icon_size,
        )
        self.icon_rect = pygame.Rect(0, 0, QUEST_ICON_SIZE, QUEST_ICON_SIZE)
        self.label_rect = pygame.Rect(0, 0, 0, 0)

    def update_layout(self, label_size=(0, 0)):
        """Az elemet mindig a játéktér jobb felső sarkához igazítja."""
        screen_width, _ = get_screen_size()
        self.image_rect.topright = (
            screen_width - QUEST_PANEL_RIGHT_MARGIN,
            TOP_BAR_HEIGHT + QUEST_PANEL_TOP_MARGIN,
        )
        self.icon_rect.topleft = (
            self.image_rect.left + QUEST_IMAGE_BORDER_WIDTH,
            self.image_rect.top + QUEST_IMAGE_BORDER_WIDTH,
        )
        label_width = label_size[0] + QUEST_LABEL_PADDING_X * 2
        label_height = label_size[1] + QUEST_LABEL_PADDING_Y * 2
        self.label_rect = pygame.Rect(0, 0, label_width, label_height)
        self.label_rect.midright = (
            self.image_rect.left - QUEST_LABEL_GAP,
            self.image_rect.centery,
        )
        self.rect = self.image_rect.union(self.label_rect)
        return self.rect

    def draw(self, screen, font, quest_manager):
        quest = quest_manager.current_quest
        if not quest_manager.visible or quest is None:
            return

        display_text = quest.title
        if quest.target and quest.target > 1 and not quest.completed:
            display_text += f"\n{quest.progress} / {quest.target}"
        quest_lines = self._render_text_lines(font, display_text)
        text_width = max(line.get_width() for line in quest_lines)
        text_height = (
            sum(line.get_height() for line in quest_lines)
            + QUEST_LABEL_LINE_GAP * (len(quest_lines) - 1)
        )
        completed = quest.completed
        label_content_width = text_width
        if completed:
            label_content_width += QUEST_CHECK_SIZE + QUEST_CHECK_GAP

        self.update_layout((label_content_width, text_height))
        label_surface = pygame.Surface(
            self.label_rect.size, pygame.SRCALPHA,
        )
        label_surface.fill(QUEST_LABEL_BACKGROUND)
        screen.blit(label_surface, self.label_rect)
        text_x = self.label_rect.left + QUEST_LABEL_PADDING_X
        if completed:
            check_left = text_x
            check_center_y = self.label_rect.centery
            pygame.draw.lines(
                screen,
                QUEST_COMPLETED_COLOR,
                False,
                (
                    (check_left, check_center_y),
                    (check_left + 5, check_center_y + 5),
                    (check_left + QUEST_CHECK_SIZE, check_center_y - 6),
                ),
                3,
            )
            text_x += QUEST_CHECK_SIZE + QUEST_CHECK_GAP
        text_y = self.label_rect.top + QUEST_LABEL_PADDING_Y
        for line in quest_lines:
            screen.blit(line, (text_x, text_y))
            text_y += line.get_height() + QUEST_LABEL_LINE_GAP

        if self.icon is not None:
            pygame.draw.rect(
                screen, QUEST_IMAGE_BORDER_COLOR, self.image_rect,
            )
            screen.blit(self.icon, self.icon_rect)

    @staticmethod
    def _render_text_lines(font, text):
        """A hosszú Quest-szöveget változatlan betűmérettel több sorba tördeli."""
        lines = []
        for paragraph in text.splitlines():
            words = paragraph.split()
            current_line = ""
            for word in words:
                candidate = f"{current_line} {word}".strip()
                if (
                    current_line
                    and font.size(candidate)[0] > QUEST_LABEL_MAX_TEXT_WIDTH
                ):
                    lines.append(font.render(current_line, True, COLOR_TEXT))
                    current_line = word
                else:
                    current_line = candidate
            if current_line:
                lines.append(font.render(current_line, True, COLOR_TEXT))
        return lines or [font.render("", True, COLOR_TEXT)]


def clicked_tool(buttons, position):
    for tool, button in buttons.items():
        if button.collidepoint(position):
            return tool
    return None


def draw_button(screen, button_rect, icon_color, active, icon=None):
    button_color = COLOR_BUTTON_ACTIVE if active else COLOR_BUTTON
    pygame.draw.rect(screen, button_color, button_rect)
    pygame.draw.rect(screen, COLOR_BUTTON_BORDER, button_rect, 2)

    if icon is not None:
        screen.blit(icon, icon.get_rect(center=button_rect.center))
    else:
        icon_rect = pygame.Rect(0, 0, PLACEHOLDER_SIZE, PLACEHOLDER_SIZE)
        icon_rect.center = button_rect.center
        pygame.draw.rect(screen, icon_color, icon_rect)


def wrap_tooltip_lines(font, text, max_content_width):
    """Megőrzi a teljes szöveget, és csak a maximális szélességnél töri meg."""
    source_lines = str(text).splitlines() if isinstance(text, str) else list(text)
    source_lines = [str(line) for line in source_lines] or [""]
    wrapped_lines = []
    for source_line in source_lines:
        if not source_line:
            wrapped_lines.append("")
            continue
        current_line = ""
        for word in source_line.split():
            candidate = word if not current_line else f"{current_line} {word}"
            if font.size(candidate)[0] <= max_content_width:
                current_line = candidate
                continue
            if current_line:
                wrapped_lines.append(current_line)
                current_line = ""
            while word and font.size(word)[0] > max_content_width:
                split_at = len(word)
                while split_at > 1 and font.size(word[:split_at])[0] > max_content_width:
                    split_at -= 1
                wrapped_lines.append(word[:split_at])
                word = word[split_at:]
            current_line = word
        if current_line:
            wrapped_lines.append(current_line)
    return wrapped_lines or [""]


def draw_tooltip(screen, font, text, button_rect):
    screen_width, screen_height = get_screen_size()
    max_content_width = max(
        1,
        min(
            TOOLTIP_MAX_WIDTH,
            screen_width - TOOLTIP_PADDING_X * 2,
        ),
    )
    lines = wrap_tooltip_lines(font, text, max_content_width)
    rendered_lines = [font.render(line, True, (255, 255, 255)) for line in lines]
    content_width = max(line.get_width() for line in rendered_lines)
    content_height = sum(line.get_height() for line in rendered_lines)
    content_height += TOOLTIP_LINE_GAP * (len(rendered_lines) - 1)
    tooltip_rect = pygame.Rect(
        0, 0,
        content_width + TOOLTIP_PADDING_X * 2,
        content_height + TOOLTIP_PADDING_Y * 2,
    )
    tooltip_rect.midbottom = (
        button_rect.centerx,
        button_rect.top - TOOLTIP_OFFSET,
    )

    # A felső HUD gombjainál nincs hely a gomb fölött, ezért ugyanaz a
    # tooltip automatikusan a gomb alatt jelenik meg.
    if tooltip_rect.top < 0:
        tooltip_rect.midtop = (
            button_rect.centerx,
            button_rect.bottom + TOOLTIP_OFFSET,
        )

    if tooltip_rect.left < 0:
        tooltip_rect.left = 0
    if tooltip_rect.right > screen_width:
        tooltip_rect.right = screen_width
    if tooltip_rect.top < 0:
        tooltip_rect.top = 0
    if tooltip_rect.bottom > screen_height:
        tooltip_rect.bottom = screen_height

    pygame.draw.rect(screen, (0, 0, 0), tooltip_rect)
    line_y = tooltip_rect.y + TOOLTIP_PADDING_Y
    for rendered_line in rendered_lines:
        screen.blit(rendered_line, (tooltip_rect.x + TOOLTIP_PADDING_X, line_y))
        line_y += rendered_line.get_height() + TOOLTIP_LINE_GAP
    return tooltip_rect


def draw_notification_bar(screen, font, notification_manager, bottom_y):
    """A Developer Console fölött kirajzolja az aktuális nyilvános értesítést."""
    message = notification_manager.current_message
    if not message:
        return None
    screen_width, _ = get_screen_size()
    max_content_width = max(
        80,
        min(NEWS_BAR_MAX_WIDTH, screen_width - NEWS_BAR_LEFT_MARGIN * 2)
        - NEWS_BAR_PADDING_X * 2,
    )
    words = message.split()
    text_lines = []
    current_line = ""
    for word in words:
        candidate = word if not current_line else f"{current_line} {word}"
        if font.size(candidate)[0] <= max_content_width or not current_line:
            current_line = candidate
        else:
            text_lines.append(current_line)
            current_line = word
    if current_line:
        text_lines.append(current_line)
    text_lines = text_lines[:2]
    rendered = [font.render(line, True, NEWS_BAR_TEXT_COLOR) for line in text_lines]
    width = max(line.get_width() for line in rendered) + NEWS_BAR_PADDING_X * 2
    height = sum(line.get_height() for line in rendered) + NEWS_BAR_PADDING_Y * 2
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(
        panel, NEWS_BAR_BACKGROUND, panel.get_rect(), border_radius=5,
    )
    pygame.draw.rect(
        panel, NEWS_BAR_BORDER, panel.get_rect(), width=1, border_radius=5,
    )
    line_y = NEWS_BAR_PADDING_Y
    for line in rendered:
        panel.blit(line, (NEWS_BAR_PADDING_X, line_y))
        line_y += line.get_height()
    rect = panel.get_rect(
        left=NEWS_BAR_LEFT_MARGIN,
        bottom=max(height, int(bottom_y) - NEWS_BAR_BOTTOM_MARGIN),
    )
    screen.blit(panel, rect)
    return rect


def draw_time_hud(
        screen, font, elapsed_weeks, time_speed, time_speed_icons,
        start_x=HUD_LEFT_MARGIN):
    """Kirajzolja a balra igazított év–hét és idősebességblokkot."""
    time_text = font.render(
        format_game_time(elapsed_weeks), True, COLOR_TEXT,
    )
    time_rect = time_text.get_rect(
        midleft=(start_x, TOP_BAR_HEIGHT // 2),
    )
    screen.blit(time_text, time_rect)

    icon = time_speed_icons.get(time_speed)
    icon_x = time_rect.right + HUD_TIME_GAP
    if icon is not None:
        indicator_rect = icon.get_rect(
            midleft=(icon_x, TOP_BAR_HEIGHT // 2),
        )
        screen.blit(icon, indicator_rect)
    else:
        fallback = get_time_speed_indicator(time_speed)
        fallback_text = font.render(fallback, True, COLOR_TEXT)
        indicator_rect = fallback_text.get_rect(
            midleft=(icon_x, TOP_BAR_HEIGHT // 2),
        )
        screen.blit(fallback_text, indicator_rect)

    return time_rect.union(indicator_rect)


def draw_economy_hud(screen, font, buildings, economy):
    """Kirajzolja a jobbra igazított pénz- és raktárblokkot."""
    screen_width, _ = get_screen_size()
    stored_amount = sum(get_total_inventory(buildings).values())
    capacity = get_total_capacity(buildings)
    money = economy.money if economy is not None else 0.0
    text = font.render(
        f"Pénz: {format_money(money)} | Raktár: {stored_amount} / {capacity}",
        True,
        COLOR_TEXT,
    )
    text_rect = text.get_rect(
        midright=(screen_width - HUD_RIGHT_MARGIN, TOP_BAR_HEIGHT // 2),
    )
    money_rect = get_money_hud_rect(font, buildings, economy)
    if money_rect.collidepoint(pygame.mouse.get_pos()):
        hover_rect = money_rect.inflate(8, 6)
        pygame.draw.rect(screen, COLOR_BUTTON, hover_rect)
        pygame.draw.rect(screen, COLOR_BUTTON_BORDER, hover_rect, 1)
    screen.blit(text, text_rect)
    return text_rect


def get_money_hud_rect(font, buildings, economy):
    """A kombinált jobb oldali HUD-on belül csak a pénz felirat hitboxa."""
    screen_width, _ = get_screen_size()
    money = economy.money if economy is not None else 0.0
    stored_amount = sum(get_total_inventory(buildings).values())
    capacity = get_total_capacity(buildings)
    money_text = font.render(f"Pénz: {format_money(money)}", True, COLOR_TEXT)
    suffix_width = font.size(
        f" | Raktár: {stored_amount} / {capacity}"
    )[0]
    return money_text.get_rect(
        midright=(screen_width - HUD_RIGHT_MARGIN, TOP_BAR_HEIGHT // 2),
    ).move(-suffix_width, 0)


def draw_hud(
    screen, font, buildings, elapsed_weeks=0, economy=None,
    time_speed=TIME_NORMAL,
    time_speed_icons=None, time_start_x=HUD_LEFT_MARGIN,
):
    """Kirajzolja a két, egymástól elkülönülő HUD-blokkot."""
    time_rect = draw_time_hud(
        screen, font, elapsed_weeks, time_speed,
        time_speed_icons or {}, time_start_x,
    )
    economy_rect = draw_economy_hud(screen, font, buildings, economy)

    # A jelenlegi ablakméretnél a blokkok önállóan igazodnak a két szélhez.
    # Ez az érték a későbbi, változó szélességű elrendezéshez is ellenőrizhető.
    available_gap = economy_rect.left - time_rect.right
    return time_rect, economy_rect, available_gap >= HUD_BLOCK_GAP


def is_outside_popup_click(event, rect):
    """Igaz, ha egy egérkattintás a megadott panelen kívül történt."""
    return (
        event.type == pygame.MOUSEBUTTONDOWN
        and not rect.collidepoint(event.pos)
    )


class PopupWindow:
    """A felugró ablakok közös megjelenését és bezárási működését kezeli."""

    def __init__(self, width, height):
        self.visible = False
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = get_screen_center()

    def open(self):
        self.visible = True

    def close(self):
        self.visible = False

    def handle_event(self, event):
        """ESC-re vagy külső kattintásra bezár, a belső kattintást továbbadja."""
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            if is_outside_popup_click(event, self.rect):
                self.close()
                return True
            return self._handle_content_click(event.pos)
        return False

    def _handle_content_click(self, position):
        return True

    def draw_frame(self, screen):
        pygame.draw.rect(screen, INFO_PANEL_BACKGROUND, self.rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, self.rect, 2)

    @staticmethod
    def draw_text(screen, font, text, x, y):
        rendered_text = font.render(text, True, COLOR_TEXT)
        screen.blit(rendered_text, (x, y))


class BankPanel(PopupWindow):
    """A negatív egyenlegkor megjelenő, modális hitelajánlat."""

    WIDTH = 520
    HEIGHT = 360
    BUTTON_HEIGHT = 42
    BUTTON_GAP = 16

    def __init__(self):
        super().__init__(self.WIDTH, self.HEIGHT)
        self.pending_decision = None
        self.previous_time_speed = None
        self.button_rects = {}
        self.market_active = False

    def open(self, previous_time_speed):
        self.pending_decision = None
        self.previous_time_speed = previous_time_speed
        self.market_active = False
        self.rect.center = get_screen_center()
        super().open()

    def handle_event(self, event):
        """A panel csak egy egyértelmű elfogadó vagy elutasító döntéssel zárul."""
        if not self.visible:
            return False
        if self.market_active:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.pending_decision = "decline"
            self.close()
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rects.get("market", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                self.pending_decision = "market"
            elif self.button_rects.get("accept", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                self.pending_decision = "accept"
                self.close()
            elif self.button_rects.get("decline", pygame.Rect(0, 0, 0, 0)).collidepoint(event.pos):
                self.pending_decision = "decline"
                self.close()
            return True
        return event.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONUP)

    def begin_market(self):
        """A Bankot háttérben tartja, amíg a meglévő Piac panel aktív."""
        self.market_active = True

    def finish_market(self):
        self.market_active = False

    def take_decision(self):
        decision = self.pending_decision
        self.pending_decision = None
        return decision

    def _draw_button(self, screen, font, rect, label):
        color = CROP_CARD_HOVER if rect.collidepoint(pygame.mouse.get_pos()) else CROP_CARD_BACKGROUND
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 1)
        rendered = font.render(label, True, COLOR_TEXT)
        screen.blit(rendered, rendered.get_rect(center=rect.center))

    def draw(self, screen, font, bank_system):
        if not self.visible:
            return
        self.rect.center = get_screen_center()
        self.draw_frame(screen)
        left = self.rect.left + INFO_PANEL_PADDING
        top = self.rect.top + INFO_PANEL_PADDING
        loan = bank_system.loan
        lines = (
            "Bank",
            "A gazdaság pénzegyenlege negatívba fordult.",
            "",
            f"Hitelösszeg: {format_money(loan.principal_cents / 100)}",
            f"Kamat: {loan.interest_percent}%",
            f"Teljes visszafizetés: {format_money(loan.total_repayment_cents / 100)}",
            f"Futamidő: {LOAN_TERM_WEEKS} hét",
            f"Heti törlesztőrészlet: {format_money(loan.weekly_payment_cents / 100)}",
        )
        for index, line in enumerate(lines):
            self.draw_text(screen, font, line, left, top + index * 28)
        button_width = (
            self.rect.width - INFO_PANEL_PADDING * 2 - self.BUTTON_GAP * 2
        ) // 3
        button_y = self.rect.bottom - INFO_PANEL_PADDING - self.BUTTON_HEIGHT
        self.button_rects = {
            "market": pygame.Rect(left, button_y, button_width, self.BUTTON_HEIGHT),
            "accept": pygame.Rect(
                left + button_width + self.BUTTON_GAP,
                button_y, button_width, self.BUTTON_HEIGHT,
            ),
            "decline": pygame.Rect(
                left + (button_width + self.BUTTON_GAP) * 2, button_y,
                button_width, self.BUTTON_HEIGHT,
            ),
        }
        self._draw_button(
            screen, font, self.button_rects["market"], "Piac",
        )
        self._draw_button(
            screen, font, self.button_rects["accept"], "Hitel felvétele",
        )
        self._draw_button(
            screen, font, self.button_rects["decline"], "Elutasítás",
        )


class FinancialSummaryPanel(PopupWindow):
    """Az utolsó 52 hét mentett tranzakcióiból készített kimutatás."""

    INCOME_LABELS = (
        (INCOME_CROP_SALES, "Növényértékesítés"),
        (INCOME_LIVESTOCK_SALES, "Állati termékek értékesítése"),
        (INCOME_ORCHARD_SALES, "Gyümölcsértékesítés"),
        (
            INCOME_PROCESSED_PRODUCT_SALES,
            "Feldolgozott termékek értékesítése",
        ),
        (INCOME_LOAN, "Felvett hitel"),
    )
    EXPENSE_LABELS = (
        (EXPENSE_MAINTENANCE, "Fenntartási költségek"),
        (EXPENSE_SHIPPING, "Szállítási költségek"),
        (EXPENSE_PLANTING, "Vetési költségek"),
        (EXPENSE_PROCESSING_INPUT, "Feldolgozóipari alapanyag-beszerzés"),
        (EXPENSE_ANIMAL_FEED, "Takarmánybeszerzés"),
        (EXPENSE_ANIMAL_PURCHASE, "Állatvásárlás"),
        (EXPENSE_FRUIT_TREE, "Gyümölcsfa-vásárlás"),
        (EXPENSE_CONSTRUCTION, "Építés"),
        (EXPENSE_VEHICLE, "Járművásárlás"),
        (EXPENSE_UPGRADE, "Fejlesztések"),
        (EXPENSE_LOAN_REPAYMENT, "Hiteltörlesztés"),
    )

    def __init__(self):
        super().__init__(FINANCE_PANEL_WIDTH, FINANCE_PANEL_HEIGHT)
        self.scroll_offset = 0
        self.max_scroll = 0

    def open(self):
        screen_width, screen_height = get_screen_size()
        self.rect.width = min(FINANCE_PANEL_WIDTH, screen_width - 40)
        self.rect.height = min(FINANCE_PANEL_HEIGHT, screen_height - 80)
        self.rect.center = get_screen_center()
        self.scroll_offset = 0
        super().open()

    def handle_event(self, event):
        if not self.visible:
            return False
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_offset = max(
                    0, min(self.max_scroll,
                           self.scroll_offset - event.y * FINANCE_SCROLL_STEP),
                )
                return True
        return super().handle_event(event)

    @staticmethod
    def _subcategory_name(item_id):
        if item_id in get_inventory_item_ids():
            return get_inventory_item_name(item_id)
        if item_id in ANIMAL_TYPES:
            return ANIMAL_TYPES[item_id]["name"]
        if item_id in TREE_TYPES:
            return TREE_TYPES[item_id]["tree_name"]
        definition = next((
            data for vehicle_type, data in VEHICLE_TYPE_DEFINITIONS.items()
            if vehicle_type.value == item_id
        ), None)
        if definition is not None:
            return definition["name"]
        option = BUILD_OPTIONS.get(item_id)
        return option["name"] if option is not None else item_id.replace("_", " ").capitalize()

    def _column_rows(self, summary, transaction_type):
        """Egy bevételi vagy kiadási oszlop sorait állítja össze."""
        if transaction_type == "income":
            labels = self.INCOME_LABELS
            total_kind, total_label = "total_income", "Összes bevétel"
        else:
            labels = self.EXPENSE_LABELS
            total_kind, total_label = "total_expense", "Összes kiadás"
        rows = []
        for category_id, label in labels:
            data = summary[transaction_type].get(
                category_id, {"total": 0, "items": {}},
            )
            rows.append((transaction_type, label, data["total"]))
            for item_id, amount in data["items"].items():
                rows.append((
                    "detail", f"  {self._subcategory_name(item_id)}", amount,
                ))
        rows.append((total_kind, total_label, summary[f"{transaction_type}_total"]))
        return rows

    def _layout_rects(self):
        """A reszponzív fejléc-, oszlop- és fix egyenlegsáv geometriája."""
        content_left = self.rect.left + FINANCE_PANEL_PADDING
        content_width = self.rect.width - FINANCE_PANEL_PADDING * 2
        column_width = max(1, (content_width - FINANCE_COLUMN_GAP) // 2)
        columns_top = self.rect.top + FINANCE_HEADER_HEIGHT
        net_rect = pygame.Rect(
            content_left,
            self.rect.bottom - FINANCE_PANEL_PADDING - FINANCE_NET_HEIGHT,
            content_width,
            FINANCE_NET_HEIGHT,
        )
        columns_height = max(1, net_rect.top - FINANCE_SECTION_GAP - columns_top)
        income_rect = pygame.Rect(
            content_left, columns_top, column_width, columns_height,
        )
        expense_rect = pygame.Rect(
            income_rect.right + FINANCE_COLUMN_GAP,
            columns_top, column_width, columns_height,
        )
        return income_rect, expense_rect, net_rect

    @staticmethod
    def _row_color(kind):
        if kind in ("income", "total_income"):
            return FINANCE_INCOME_COLOR
        if kind in ("expense", "total_expense"):
            return FINANCE_EXPENSE_COLOR
        return COLOR_TEXT

    def _draw_column(self, screen, font, rect, heading, rows):
        x = rect.left
        value_right = rect.right
        y = rect.top - self.scroll_offset
        rendered_heading = font.render(heading, True, COLOR_TEXT)
        screen.blit(rendered_heading, (x, y))
        y += FINANCE_ROW_HEIGHT
        for kind, label, value in rows:
            color = self._row_color(kind)
            rendered = font.render(label, True, color)
            screen.blit(rendered, (x, y))
            rendered_value = font.render(format_money(value), True, color)
            screen.blit(rendered_value, rendered_value.get_rect(
                top=y, right=value_right,
            ))
            y += FINANCE_ROW_HEIGHT

    def draw(self, screen, font, economy):
        if not self.visible:
            return
        self.rect.center = get_screen_center()
        self.draw_frame(screen)
        summary = economy.get_financial_summary(52)
        income_rows = self._column_rows(summary, "income")
        expense_rows = self._column_rows(summary, "expense")
        income_rect, expense_rect, net_rect = self._layout_rects()
        longest_column_height = (
            max(len(income_rows), len(expense_rows)) + 1
        ) * FINANCE_ROW_HEIGHT
        self.max_scroll = max(0, longest_column_height - income_rect.height)
        self.scroll_offset = min(self.scroll_offset, self.max_scroll)

        title_x = self.rect.left + FINANCE_PANEL_PADDING
        title_y = self.rect.top + FINANCE_PANEL_PADDING
        self.draw_text(screen, font, "Pénzügyi összesítő", title_x, title_y)
        self.draw_text(screen, font, "Utolsó 52 hét", title_x, title_y + 26)

        old_clip = screen.get_clip()
        columns_clip = income_rect.union(expense_rect)
        screen.set_clip(columns_clip)
        self._draw_column(screen, font, income_rect, "BEVÉTELEK", income_rows)
        self._draw_column(screen, font, expense_rect, "KIADÁSOK", expense_rows)
        screen.set_clip(old_clip)

        separator_x = income_rect.right + FINANCE_COLUMN_GAP // 2
        pygame.draw.line(
            screen, FINANCE_SEPARATOR_COLOR,
            (separator_x, income_rect.top), (separator_x, income_rect.bottom), 1,
        )
        pygame.draw.line(
            screen, FINANCE_SEPARATOR_COLOR,
            (net_rect.left, net_rect.top), (net_rect.right, net_rect.top), 1,
        )
        net_color = (
            FINANCE_INCOME_COLOR if summary["net"] >= 0
            else FINANCE_EXPENSE_COLOR
        )
        net_y = net_rect.centery - font.get_height() // 2
        net_label = font.render("52 hetes egyenleg", True, net_color)
        screen.blit(net_label, (net_rect.left, net_y))
        net_value = format_money(summary["net"])
        if summary["net"] > 0:
            net_value = "+" + net_value
        rendered_net = font.render(net_value, True, net_color)
        screen.blit(rendered_net, rendered_net.get_rect(
            right=net_rect.right, centery=net_rect.centery,
        ))


class CalendarPanel(PopupWindow):
    """Az éves és növényenkénti idővonalak bővíthető alapfelülete."""

    def __init__(self):
        super().__init__(CALENDAR_PANEL_WIDTH, CALENDAR_PANEL_HEIGHT)

    def _update_layout(self):
        self.rect.width = responsive_panel_width(CALENDAR_PANEL_WIDTH, 420)
        self.rect.height = CALENDAR_PANEL_HEIGHT
        self.rect.center = get_screen_center()

    def open(self):
        self._update_layout()
        super().open()

    @staticmethod
    def _week_marker_x(timeline_rect, week):
        """Egy 1–52 közötti hetet az idővonal arányos középpontjára képez."""
        normalized_week = max(1, min(WEEKS_PER_YEAR, int(week)))
        return round(
            timeline_rect.left
            + (normalized_week - 0.5) * timeline_rect.width / WEEKS_PER_YEAR
        )

    @staticmethod
    def _season_segment_rects(timeline_rect):
        """A központi heti tartományokat arányos, hézagmentes téglalapokra képezi."""
        segments = []
        for period in SEASON_PERIODS:
            left = round(
                timeline_rect.left
                + (period.start_week - 1)
                * timeline_rect.width / WEEKS_PER_YEAR
            )
            right = round(
                timeline_rect.left
                + period.end_week * timeline_rect.width / WEEKS_PER_YEAR
            )
            segments.append((
                period,
                pygame.Rect(
                    left, timeline_rect.top,
                    max(0, right - left), timeline_rect.height,
                ),
            ))
        return segments

    @classmethod
    def _draw_season_timeline(cls, screen, rect):
        """Az 52 hetet az adatvezérelt évszakhatárok szerint rajzolja."""
        segments = cls._season_segment_rects(rect)
        for period, segment_rect in segments:
            pygame.draw.rect(
                screen, CALENDAR_SEASON_COLORS[period.season], segment_rect,
            )
        for _, segment_rect in segments[:-1]:
            pygame.draw.line(
                screen, CALENDAR_SEASON_SEPARATOR,
                (segment_rect.right, rect.top),
                (segment_rect.right, rect.bottom - 1),
                2,
            )
        pygame.draw.rect(screen, CALENDAR_TIMELINE_BORDER, rect, 1)

    @staticmethod
    def _draw_crop_timeline(screen, rect):
        """Egységes alapot rajzol a későbbi növényi munkafázisok számára."""
        pygame.draw.rect(screen, CALENDAR_CROP_TIMELINE_COLOR, rect)
        pygame.draw.rect(screen, CALENDAR_TIMELINE_BORDER, rect, 1)

    @staticmethod
    def _week_interval_rects(timeline_rect, intervals):
        """Tetszőleges számú heti intervallumot képez a közös 52 hetes skálára."""
        interval_rects = []
        for start_week, end_week in intervals or ():
            parts = (
                ((start_week, end_week),)
                if start_week <= end_week
                else ((start_week, WEEKS_PER_YEAR), (1, end_week))
            )
            for part_start, part_end in parts:
                left = round(
                    timeline_rect.left
                    + (part_start - 1)
                    * timeline_rect.width / WEEKS_PER_YEAR
                )
                right = round(
                    timeline_rect.left
                    + part_end * timeline_rect.width / WEEKS_PER_YEAR
                )
                interval_rects.append(pygame.Rect(
                    left, timeline_rect.top + 2,
                    max(0, right - left), max(1, timeline_rect.height - 4),
                ))
        return interval_rects

    @classmethod
    def _draw_crop_periods(cls, screen, rect, crop_data):
        """Felirat nélkül rárajzolja a növény adatvezérelt vetési és aratási sávjait."""
        for interval_rect in cls._week_interval_rects(
                rect, get_crop_week_intervals(crop_data, "planting_weeks")):
            pygame.draw.rect(
                screen, CALENDAR_PLANTING_PERIOD_COLOR, interval_rect,
            )
        for interval_rect in cls._week_interval_rects(
                rect, get_crop_week_intervals(crop_data, "harvest_weeks")):
            pygame.draw.rect(
                screen, CALENDAR_HARVEST_PERIOD_COLOR, interval_rect,
            )
        pygame.draw.rect(screen, CALENDAR_TIMELINE_BORDER, rect, 1)

    def draw(self, screen, font, elapsed_weeks):
        if not self.visible:
            return

        self._update_layout()
        self.draw_frame(screen)
        left = self.rect.left + CALENDAR_PANEL_PADDING
        top = self.rect.top + CALENDAR_PANEL_PADDING
        self.draw_text(screen, font, "Gazdálkodási naptár", left, top)
        _, current_week = get_year_and_week(elapsed_weeks)
        current_season = get_season_for_week(current_week)
        self.draw_text(
            screen, font,
            f"{format_game_time(elapsed_weeks)} • {current_season.value}",
            left, top + 30,
        )

        timeline_left = left + CALENDAR_ROW_LABEL_WIDTH
        timeline_width = max(
            WEEKS_PER_YEAR,
            self.rect.right - CALENDAR_PANEL_PADDING - timeline_left,
        )
        annual_rect = pygame.Rect(
            timeline_left,
            top + 30 + CALENDAR_TIMELINE_TOP_GAP,
            timeline_width,
            CALENDAR_TIMELINE_HEIGHT,
        )
        self.draw_text(screen, font, "Év", left, annual_rect.top - 3)
        self._draw_season_timeline(screen, annual_rect)
        marker_x = self._week_marker_x(annual_rect, current_week)
        pygame.draw.line(
            screen, CALENDAR_CURRENT_WEEK_COLOR,
            (marker_x, annual_rect.top - 6),
            (marker_x, annual_rect.bottom + 6),
            3,
        )

        row_top = annual_rect.bottom + 28
        for row_index, crop_data in enumerate(CROPS.values()):
            row_y = row_top + row_index * CALENDAR_ROW_HEIGHT
            self.draw_text(screen, font, crop_data["name"], left, row_y - 3)
            crop_timeline = pygame.Rect(
                timeline_left, row_y,
                timeline_width, CALENDAR_TIMELINE_HEIGHT,
            )
            self._draw_crop_timeline(screen, crop_timeline)
            self._draw_crop_periods(screen, crop_timeline, crop_data)


class SelectionPanel(PopupWindow):
    """A kártyás választóablakok közös kijelölési és bezárási működése."""

    def __init__(self, width, height):
        super().__init__(width, height)
        self.card_rects = {}
        self.pending_selection = None

    def open(self):
        self.pending_selection = None
        self._update_layout()
        super().open()

    def take_selection(self):
        selection = self.pending_selection
        self.pending_selection = None
        return selection

    def _handle_content_click(self, position):
        for item_id, card_rect in self.card_rects.items():
            if card_rect.collidepoint(position):
                self.pending_selection = item_id
                self.close()
                return True
        return True

    def _update_layout(self):
        raise NotImplementedError


class InfoPanel(PopupWindow):
    """Később további épülettípusokkal bővíthető információs panel."""

    def __init__(self):
        super().__init__(INFO_PANEL_WIDTH, 200)
        self.building_type = None
        self.market_card_rects = {}
        self.market_list_rect = pygame.Rect(0, 0, 0, 0)
        self.market_scroll_offset = 0
        self.market_max_scroll = 0
        self.market_column_count = 1
        self.pending_sale_selection = None
        self.upgrade_card_rects = {}
        self.upgrade_info_rects = {}
        self.pending_upgrade_selection = None
        self.building = None
        self.garage_purchase_rects = {}
        self.pending_vehicle_purchase = None
        self.processing_recipe_rects = {}
        self.processing_recipe_view_rect = pygame.Rect(0, 0, 0, 0)
        self.processing_recipe_scroll = 0
        self.processing_recipe_max_scroll = 0

    def open_for_building(self, building):
        """Megnyitja a panelt, ha az épülettípushoz már tartozik nézet."""
        if building["type"] not in (
                "warehouse", "market", "farmhouse", "garage", "pond",
                "processing_plant"):
            return False
        self.building_type = building["type"]
        self.building = building
        self.pending_sale_selection = None
        self.pending_upgrade_selection = None
        self.pending_vehicle_purchase = None
        self.garage_purchase_rects = {}
        self.processing_recipe_rects = {}
        self.processing_recipe_scroll = 0
        self.market_card_rects = {}
        self.market_scroll_offset = 0
        self.open()
        return True

    def handle_event(self, event):
        if self.visible and self.building_type == "market":
            if event.type == pygame.MOUSEWHEEL:
                self._scroll_market(-event.y * MARKET_SCROLL_STEP)
                return True
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (4, 5):
                    direction = -1 if event.button == 4 else 1
                    self._scroll_market(direction * MARKET_SCROLL_STEP)
                    return True
                if event.button != 1:
                    return True
                if is_outside_popup_click(event, self.rect):
                    self.close()
                    return True
                return self._handle_content_click(event.pos)
        if (
            self.visible
            and self.building_type == "processing_plant"
            and event.type == pygame.MOUSEWHEEL
            and self.processing_recipe_view_rect.collidepoint(
                pygame.mouse.get_pos()
            )
        ):
            self.processing_recipe_scroll = max(
                0,
                min(
                    self.processing_recipe_max_scroll,
                    self.processing_recipe_scroll
                    - event.y * PROCESSING_RECIPE_ROW_HEIGHT,
                ),
            )
            return True
        return super().handle_event(event)

    def _scroll_market(self, amount):
        self.market_scroll_offset = max(
            0,
            min(
                self.market_max_scroll,
                self.market_scroll_offset + amount,
            ),
        )

    def take_sale_selection(self):
        selection = self.pending_sale_selection
        self.pending_sale_selection = None
        return selection

    def take_upgrade_selection(self):
        selection = self.pending_upgrade_selection
        self.pending_upgrade_selection = None
        return selection

    def take_vehicle_purchase(self):
        vehicle_type = self.pending_vehicle_purchase
        self.pending_vehicle_purchase = None
        if vehicle_type is None:
            return None
        return self.building, vehicle_type

    def take_tractor_purchase(self):
        """Kompatibilis hozzáférés a korábbi, csak Traktoros Garázs UI-hoz."""
        if self.pending_vehicle_purchase != VehicleType.TRACTOR:
            return None
        self.pending_vehicle_purchase = None
        return self.building

    def _handle_content_click(self, position):
        if self.building_type == "market":
            for item_id, card_rect in self.market_card_rects.items():
                if card_rect.collidepoint(position):
                    self.pending_sale_selection = item_id
                    return True
        elif self.building_type == "farmhouse":
            for upgrade_id, card_rect in self.upgrade_card_rects.items():
                info_rect = self.upgrade_info_rects.get(upgrade_id)
                if info_rect is not None and info_rect.collidepoint(position):
                    return True
                if card_rect.collidepoint(position):
                    self.pending_upgrade_selection = upgrade_id
                    return True
        elif self.building_type == "garage":
            for vehicle_type, purchase_rect in self.garage_purchase_rects.items():
                if purchase_rect.collidepoint(position):
                    self.pending_vehicle_purchase = vehicle_type
                    return True
        elif self.building_type == "processing_plant":
            for recipe_id, row_rect in self.processing_recipe_rects.items():
                if row_rect.collidepoint(position):
                    select_processing_recipe(self.building, recipe_id)
                    return True
        return True

    def close(self):
        super().close()
        self.building_type = None
        self.market_card_rects = {}
        self.market_list_rect = pygame.Rect(0, 0, 0, 0)
        self.market_scroll_offset = 0
        self.market_max_scroll = 0
        self.market_column_count = 1
        self.pending_sale_selection = None
        self.upgrade_card_rects = {}
        self.upgrade_info_rects = {}
        self.pending_upgrade_selection = None
        self.building = None
        self.garage_purchase_rects = {}
        self.pending_vehicle_purchase = None
        self.processing_recipe_rects = {}
        self.processing_recipe_view_rect = pygame.Rect(0, 0, 0, 0)
        self.processing_recipe_scroll = 0
        self.processing_recipe_max_scroll = 0

    def draw(self, screen, font, game_state):
        if not self.visible:
            return
        if self.building_type == "warehouse":
            self._draw_warehouse(screen, font, game_state)
        elif self.building_type == "market":
            self._draw_market(screen, font, game_state)
        elif self.building_type == "farmhouse":
            self._draw_farmhouse(screen, font, game_state)
        elif self.building_type == "garage":
            self._draw_garage(screen, font, game_state)
        elif self.building_type == "pond":
            self._draw_pond(screen, font)
        elif self.building_type == "processing_plant":
            self._draw_processing_plant(screen, font)

    def _draw_processing_plant(self, screen, font):
        """Az üzem termékválasztását, készletét és állapotát mutatja."""
        initialize_processing_plant(self.building)
        active_recipe_id = self.building.get("active_recipe")
        recipe = PROCESSING_RECIPES.get(active_recipe_id)
        inventory = self.building["processing_inventory"]
        recipe_ids = get_processing_recipe_ids(self.building)
        output_ids = get_processing_output_ids(self.building)
        status_labels = {
            PROCESSING_STATUS_READY: "Termelésre kész",
            PROCESSING_STATUS_IN_TRANSIT: "Szállítás folyamatban",
            PROCESSING_STATUS_NO_MONEY: (
                "Nincs elegendő pénz az alapanyag beszerzéséhez"
            ),
            PROCESSING_STATUS_FULL: "Üzemi raktár megtelt",
            PROCESSING_STATUS_PROCESSING: "Gyártás folyamatban",
            PROCESSING_STATUS_STOPPED: "Leállítva",
            "waiting_input": "Alapanyagra vár",
        }
        weekly_capacity = (
            recipe["weekly_capacity"] if recipe is not None
            else max(
                (PROCESSING_RECIPES[item_id]["weekly_capacity"]
                 for item_id in recipe_ids),
                default=0,
            )
        )
        visible_recipe_rows = min(
            len(recipe_ids), PROCESSING_RECIPE_VISIBLE_ROWS,
        )
        recipe_view_height = visible_recipe_rows * PROCESSING_RECIPE_ROW_HEIGHT
        self.rect.size = (
            responsive_panel_width(INFO_PANEL_WIDTH),
            320 + recipe_view_height + len(output_ids) * 28,
        )
        self.rect.center = get_screen_center()
        self.draw_frame(screen)
        x = self.rect.x + INFO_PANEL_PADDING
        y = self.rect.y + INFO_PANEL_PADDING
        self.draw_text(screen, font, POPUP_TITLES["processing_plant"], x, y)
        y += 38
        self.draw_text(
            screen, font,
            f"Heti kapacitás: {weekly_capacity} db", x, y,
        )
        y += 28
        self.draw_text(
            screen, font,
            f"Üzemi raktár: {get_processing_inventory_used(self.building)} / "
            f"{self.building['processing_capacity']}", x, y,
        )
        y += 38

        self.draw_text(screen, font, "Gyártandó termék:", x, y)
        y += 26
        list_width = self.rect.width - INFO_PANEL_PADDING * 2
        self.processing_recipe_view_rect = pygame.Rect(
            x, y, list_width, recipe_view_height,
        )
        total_recipe_height = len(recipe_ids) * PROCESSING_RECIPE_ROW_HEIGHT
        self.processing_recipe_max_scroll = max(
            0, total_recipe_height - recipe_view_height,
        )
        self.processing_recipe_scroll = min(
            self.processing_recipe_scroll, self.processing_recipe_max_scroll,
        )
        self.processing_recipe_rects = {}
        previous_clip = screen.get_clip()
        screen.set_clip(self.processing_recipe_view_rect)
        for index, recipe_id in enumerate(recipe_ids):
            row_y = (
                y + index * PROCESSING_RECIPE_ROW_HEIGHT
                - self.processing_recipe_scroll
            )
            row_rect = pygame.Rect(
                x, row_y, list_width, PROCESSING_RECIPE_ROW_HEIGHT,
            )
            if row_rect.colliderect(self.processing_recipe_view_rect):
                self.processing_recipe_rects[recipe_id] = row_rect.clip(
                    self.processing_recipe_view_rect,
                )
            checkbox = pygame.Rect(
                x + 2,
                row_y + (
                    PROCESSING_RECIPE_ROW_HEIGHT
                    - PROCESSING_RECIPE_CHECKBOX_SIZE
                ) // 2,
                PROCESSING_RECIPE_CHECKBOX_SIZE,
                PROCESSING_RECIPE_CHECKBOX_SIZE,
            )
            pygame.draw.rect(screen, INFO_PANEL_BORDER, checkbox, 1)
            if recipe_id == active_recipe_id:
                pygame.draw.lines(
                    screen, PROCESSING_RECIPE_CHECK_COLOR, False,
                    (
                        (checkbox.left + 4, checkbox.centery),
                        (checkbox.left + 8, checkbox.bottom - 4),
                        (checkbox.right - 3, checkbox.top + 4),
                    ),
                    2,
                )
            output_name = PROCESSING_RECIPES[recipe_id]["name"]
            self.draw_text(
                screen, font, output_name, checkbox.right + 8, row_y + 4,
            )
        screen.set_clip(previous_clip)
        y += recipe_view_height + 18

        self.draw_text(screen, font, "Alapanyag:", x, y)
        y += 26
        if recipe is None:
            self.draw_text(screen, font, "  Nincs kiválasztott termék.", x, y)
        else:
            input_id = recipe["input_product"]
            self.draw_text(
                screen, font,
                f"  {get_inventory_item_name(input_id)}: "
                f"{inventory.get(input_id, 0)} db", x, y,
            )
        y += 38
        self.draw_text(screen, font, "Késztermékek:", x, y)
        y += 26
        for output_id in output_ids:
            self.draw_text(
                screen, font,
                f"  {get_inventory_item_name(output_id)}: "
                f"{inventory.get(output_id, 0)} db", x, y,
            )
            y += 28
        y += 10
        self.draw_text(
            screen, font,
            "Állapot: Leállítva" if active_recipe_id is None else
            f"Állapot: {status_labels.get(self.building['processing_status'], 'Alapanyagra vár')}",
            x, y,
        )

    def _draw_pond(self, screen, font):
        """A későbbi öntözéshez előkészített Tó statikus adatlapja."""
        definition = BUILDING_TYPES["pond"]
        self.rect.size = (responsive_panel_width(INFO_PANEL_WIDTH), 220)
        self.rect.center = get_screen_center()
        self.draw_frame(screen)
        x = self.rect.x + INFO_PANEL_PADDING
        y = self.rect.y + INFO_PANEL_PADDING
        self.draw_text(screen, font, POPUP_TITLES["pond"], x, y)
        y += 38
        self.draw_text(
            screen, font,
            f"Méret: {definition['width']}x{definition['height']}", x, y,
        )
        y += 28
        self.draw_text(
            screen, font,
            f"Éves költség: {format_annual_maintenance_rate()}", x, y,
        )
        y += 34
        self.draw_text(screen, font, "Funkció:", x, y)
        y += 26
        max_width = self.rect.width - INFO_PANEL_PADDING * 2
        line = ""
        for word in definition["description"].split():
            candidate = f"{line} {word}".strip()
            if line and font.size(candidate)[0] > max_width:
                self.draw_text(screen, font, line, x, y)
                y += 24
                line = word
            else:
                line = candidate
        if line:
            self.draw_text(screen, font, line, x, y)

    def _draw_garage(self, screen, font, game_state):
        manager = game_state.vehicles
        status = manager.garage_status(self.building)
        garage_assets = manager.assets_in_garage(self.building)
        self.rect.size = (
            responsive_panel_width(INFO_PANEL_WIDTH),
            700 + len(garage_assets) * 24,
        )
        self.rect.center = get_screen_center()
        self.draw_frame(screen)
        x = self.rect.x + INFO_PANEL_PADDING
        y = self.rect.y + INFO_PANEL_PADDING
        self.draw_text(screen, font, POPUP_TITLES["garage"], x, y)
        y += 42
        self.draw_text(
            screen, font,
            f"Parkolóhelyek: {status['occupied']} / {status['capacity']}", x, y,
        )
        y += 28
        self.draw_text(
            screen, font,
            f"Traktorok: {manager.count_by_type(VehicleType.TRACTOR)}", x, y,
        )
        y += 28
        self.draw_text(
            screen, font,
            f"Kombájnok: {manager.count_by_type(VehicleType.COMBINE)}", x, y,
        )
        y += 28
        self.draw_text(
            screen, font,
            "Gyümölcs szüretelőgépek: "
            f"{manager.count_by_type(VehicleType.FRUIT_HARVESTER)}", x, y,
        )
        y += 28
        self.draw_text(
            screen, font,
            f"Locsolótartályok: "
            f"{manager.count_by_type(VehicleType.WATER_TANK)}", x, y,
        )
        y += 28
        self.draw_text(
            screen, font,
            f"Pótkocsik: {manager.count_by_type(VehicleType.TRAILER)}", x, y,
        )
        y += 28
        self.draw_text(screen, font, f"Szabad hely: {status['free']}", x, y)
        y += 30
        self.draw_text(screen, font, "Parkoló eszközök:", x, y)
        y += 28
        if garage_assets:
            for asset in garage_assets:
                definition = VEHICLE_TYPE_DEFINITIONS[asset.vehicle_type]
                status_text = ""
                if definition.get("towable"):
                    status_text = (
                        " – Felcsatolva"
                        if asset.is_attached
                        else " – Garázsban"
                    )
                self.draw_text(
                    screen, font,
                    f"{definition['name']} #{asset.vehicle_id}{status_text}",
                    x + 12, y,
                )
                y += 24
        else:
            self.draw_text(screen, font, "–", x + 12, y)
            y += 24
        y += 10
        self.garage_purchase_rects = {}
        for vehicle_type in (
                VehicleType.TRACTOR, VehicleType.COMBINE,
                VehicleType.FRUIT_HARVESTER,
                VehicleType.WATER_TANK, VehicleType.TRAILER):
            definition = VEHICLE_TYPE_DEFINITIONS[vehicle_type]
            purchase_rect = pygame.Rect(
                x, y, self.rect.width - INFO_PANEL_PADDING * 2, 54,
            )
            self.garage_purchase_rects[vehicle_type] = purchase_rect
            hovered = purchase_rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(
                screen, CROP_CARD_HOVER if hovered else CROP_CARD_BACKGROUND,
                purchase_rect,
            )
            pygame.draw.rect(screen, INFO_PANEL_BORDER, purchase_rect, 1)
            title = font.render(
                f"{definition['name']} – {format_money(definition['purchase_price'])}",
                True, COLOR_TEXT,
            )
            category = (
                "vontatmány" if definition.get("towable") else "önjáró"
            )
            details = font.render(
                f"Éves költség: {format_annual_maintenance_rate()} | "
                f"Típus: {category}",
                True, COLOR_TEXT,
            )
            screen.blit(
                title,
                title.get_rect(center=(purchase_rect.centerx, purchase_rect.y + 17)),
            )
            screen.blit(
                details,
                details.get_rect(center=(purchase_rect.centerx, purchase_rect.y + 38)),
            )
            y += 62

    def _draw_warehouse(self, screen, font, game_state):
        inventory = {
            item: amount
            for item, amount in get_total_inventory(game_state.buildings).items()
            if amount > 0
        }
        stored_amount = sum(inventory.values())
        capacity = get_total_capacity(game_state.buildings)
        visible_item_count = max(1, len(inventory))
        panel_height = 178 + visible_item_count * INFO_PANEL_ITEM_SPACING
        self.rect.size = (responsive_panel_width(INFO_PANEL_WIDTH), panel_height)
        self.rect.center = get_screen_center()

        self.draw_frame(screen)

        x = self.rect.x + INFO_PANEL_PADDING
        y = self.rect.y + INFO_PANEL_PADDING
        self.draw_text(screen, font, POPUP_TITLES["warehouse"], x, y)
        y += 34
        self.draw_text(screen, font, "Kapacitás", x, y)
        y += 24
        self.draw_text(screen, font, f"{stored_amount} / {capacity}", x, y)
        y += 32

        pygame.draw.line(
            screen,
            INFO_PANEL_SEPARATOR,
            (x, y),
            (self.rect.right - INFO_PANEL_PADDING, y),
            1,
        )
        y += 16
        self.draw_text(screen, font, "Készlet", x, y)
        y += 28

        if not inventory:
            self.draw_text(screen, font, "A készlet üres.", x, y)
            return

        for item, amount in inventory.items():
            item_name = get_inventory_item_name(item)
            self.draw_text(screen, font, f"{item_name}: {amount}", x, y)
            y += INFO_PANEL_ITEM_SPACING

    def _draw_market(self, screen, font, game_state):
        quotes = {}
        for item_id in get_marketable_item_ids():
            quote = game_state.economy.get_sale_quote(
                game_state.buildings, item_id
            )
            if quote is not None and quote["amount"] > 0:
                quotes[item_id] = quote

        _, screen_height = get_screen_size()
        panel_width = responsive_panel_width(MARKET_PANEL_WIDTH)
        self.market_column_count = (
            2 if panel_width >= MARKET_TWO_COLUMN_MIN_WIDTH else 1
        )
        card_count = len(quotes)
        row_count = (
            (card_count + self.market_column_count - 1)
            // self.market_column_count
        )
        content_height = (
            row_count * MARKET_CARD_HEIGHT
            + max(0, row_count - 1) * MARKET_CARD_GAP
        )
        natural_height = (
            MARKET_LIST_TOP + content_height + MARKET_LIST_BOTTOM_PADDING
            if card_count else 104
        )
        available_height = max(104, screen_height - 80)
        panel_height = min(MARKET_PANEL_MAX_HEIGHT, natural_height, available_height)
        self.rect.size = (panel_width, panel_height)
        self.rect.center = get_screen_center()

        content_left = self.rect.x + INFO_PANEL_PADDING
        content_width = self.rect.width - INFO_PANEL_PADDING * 2
        self.market_list_rect = pygame.Rect(
            content_left,
            self.rect.y + MARKET_LIST_TOP,
            content_width,
            max(0, panel_height - MARKET_LIST_TOP - MARKET_LIST_BOTTOM_PADDING),
        )
        self.market_max_scroll = max(
            0, content_height - self.market_list_rect.height,
        )
        self.market_scroll_offset = min(
            self.market_scroll_offset, self.market_max_scroll,
        )
        card_width = (
            content_width
            - (self.market_column_count - 1) * MARKET_COLUMN_GAP
        ) // self.market_column_count
        self.market_card_rects = {}
        card_layout = {}
        for index, item_id in enumerate(quotes):
            row, column = divmod(index, self.market_column_count)
            card_rect = pygame.Rect(
                content_left + column * (card_width + MARKET_COLUMN_GAP),
                self.market_list_rect.top
                + row * (MARKET_CARD_HEIGHT + MARKET_CARD_GAP)
                - self.market_scroll_offset,
                card_width,
                MARKET_CARD_HEIGHT,
            )
            card_layout[item_id] = card_rect
            visible_hitbox = card_rect.clip(self.market_list_rect)
            if visible_hitbox.width > 0 and visible_hitbox.height > 0:
                self.market_card_rects[item_id] = visible_hitbox

        self.draw_frame(screen)
        x = self.rect.x + INFO_PANEL_PADDING
        self.draw_text(
            screen, font, POPUP_TITLES["market"],
            x, self.rect.y + INFO_PANEL_PADDING,
        )
        if not quotes:
            self.draw_text(
                screen, font, "Nincs eladható termék.", x, self.rect.y + 62
            )
            return

        mouse_position = pygame.mouse.get_pos()
        previous_clip = screen.get_clip()
        screen.set_clip(self.market_list_rect)
        for item_id, quote in quotes.items():
            card_rect = card_layout[item_id]
            visible_hitbox = self.market_card_rects.get(item_id)
            card_color = (
                CROP_CARD_HOVER
                if visible_hitbox is not None
                and visible_hitbox.collidepoint(mouse_position)
                else CROP_CARD_BACKGROUND
            )
            pygame.draw.rect(screen, card_color, card_rect)
            pygame.draw.rect(screen, INFO_PANEL_BORDER, card_rect, 1)
            text_x = card_rect.x + 14
            text_y = card_rect.y + 8
            self.draw_text(
                screen, font, get_inventory_item_name(item_id), text_x, text_y,
            )
            self.draw_text(
                screen, font, f"Készlet: {quote['amount']} db",
                text_x, text_y + 24,
            )
            self.draw_text(
                screen, font, f"Egységár: {format_money(quote['unit_price'])}",
                text_x, text_y + 48,
            )
            self.draw_text(
                screen, font, f"Teljes érték: {format_money(quote['total_value'])}",
                text_x, text_y + 72,
            )
        screen.set_clip(previous_clip)

    def _draw_farmhouse(self, screen, font, game_state):
        farmhouse = self.building
        farmhouse_level = (
            farmhouse.get("farmhouse_level", 2) if farmhouse is not None else None
        )
        upgrade_count = len(UPGRADES)
        panel_height = 104 + upgrade_count * UPGRADE_CARD_HEIGHT
        panel_height += max(0, upgrade_count - 1) * UPGRADE_CARD_GAP + 20
        self.rect.size = (responsive_panel_width(UPGRADE_PANEL_WIDTH), panel_height)
        self.rect.center = get_screen_center()

        self.upgrade_card_rects = {}
        self.upgrade_info_rects = {}
        card_y = self.rect.y + 58
        for upgrade_id in UPGRADES:
            card_rect = pygame.Rect(
                self.rect.x + INFO_PANEL_PADDING,
                card_y,
                self.rect.width - INFO_PANEL_PADDING * 2,
                UPGRADE_CARD_HEIGHT,
            )
            self.upgrade_card_rects[upgrade_id] = card_rect
            self.upgrade_info_rects[upgrade_id] = pygame.Rect(
                card_rect.right - UPGRADE_INFO_MARGIN - UPGRADE_INFO_HITBOX_SIZE,
                card_rect.top + UPGRADE_INFO_MARGIN,
                UPGRADE_INFO_HITBOX_SIZE,
                UPGRADE_INFO_HITBOX_SIZE,
            )
            card_y += UPGRADE_CARD_HEIGHT + UPGRADE_CARD_GAP

        self.draw_frame(screen)
        x = self.rect.x + INFO_PANEL_PADDING
        self.draw_text(
            screen, font,
            f"Farmház {self._roman_level(farmhouse_level)}. - Fejlesztések",
            x, self.rect.y + INFO_PANEL_PADDING,
        )
        mouse_position = pygame.mouse.get_pos()
        hovered_info = None
        for upgrade_id, upgrade in UPGRADES.items():
            card_rect = self.upgrade_card_rects[upgrade_id]
            info_rect = self.upgrade_info_rects[upgrade_id]
            target_level = upgrade.get("target_level")
            purchased = (
                farmhouse_level is not None
                and target_level is not None
                and farmhouse_level >= target_level
            ) or (
                target_level is None
                and upgrade_id in game_state.purchased_upgrades
            )
            card_color = CROP_CARD_BACKGROUND
            if (
                not purchased
                and card_rect.collidepoint(mouse_position)
                and not info_rect.collidepoint(mouse_position)
            ):
                card_color = CROP_CARD_HOVER
            pygame.draw.rect(screen, card_color, card_rect)
            pygame.draw.rect(screen, INFO_PANEL_BORDER, card_rect, 1)

            text_x = card_rect.x + 14
            text_y = card_rect.y + 8
            self.draw_text(screen, font, upgrade["name"], text_x, text_y)
            self.draw_text(
                screen, font, f"Fejlesztés ára: {format_money(upgrade['price'])}",
                text_x, text_y + 26,
            )
            status = get_upgrade_status(
                upgrade_id, game_state.purchased_upgrades, farmhouse_level,
            )
            self.draw_text(
                screen, font, f"Fejlesztés: {status}", text_x, text_y + 52
            )

            pygame.draw.ellipse(screen, UPGRADE_INFO_FILL, info_rect)
            pygame.draw.ellipse(screen, UPGRADE_INFO_BORDER, info_rect, 1)
            info_text = font.render("i", True, COLOR_TEXT)
            screen.blit(info_text, info_text.get_rect(center=info_rect.center))
            if info_rect.collidepoint(mouse_position):
                hovered_info = (upgrade["description"], info_rect)

        if hovered_info is not None:
            description, info_rect = hovered_info
            draw_tooltip(screen, font, description, info_rect)

    @staticmethod
    def _roman_level(level):
        """A felhasználói felületen használt Farmház-szintjelölés."""
        return {1: "I", 2: "II"}.get(level, str(level or 1))


class AnimalHusbandryPanel(SelectionPanel):
    """A későbbi állatkártyák közös kiválasztópanelének alapja."""

    def __init__(self):
        super().__init__(ANIMAL_HUSBANDRY_PANEL_WIDTH, 170)

    def _update_layout(self):
        animal_count = max(1, len(ANIMAL_TYPES))
        self.rect.width = responsive_panel_width(
            ANIMAL_HUSBANDRY_PANEL_WIDTH,
        )
        self.rect.height = (
            78 + animal_count * ANIMAL_CARD_HEIGHT
            + max(0, animal_count - 1) * ANIMAL_CARD_GAP + 20
        )
        self.rect.center = get_screen_center()

        self.card_rects = {}
        card_y = self.rect.y + 58
        for animal_type in ANIMAL_TYPES:
            self.card_rects[animal_type] = pygame.Rect(
                self.rect.x + INFO_PANEL_PADDING,
                card_y,
                self.rect.width - INFO_PANEL_PADDING * 2,
                ANIMAL_CARD_HEIGHT,
            )
            card_y += ANIMAL_CARD_HEIGHT + ANIMAL_CARD_GAP

    def draw(self, screen, font):
        if not self.visible:
            return
        self._update_layout()
        self.draw_frame(screen)
        x = self.rect.x + INFO_PANEL_PADDING
        self.draw_text(
            screen, font, POPUP_TITLES["animal_husbandry"],
            x, self.rect.y + INFO_PANEL_PADDING,
        )
        mouse_position = pygame.mouse.get_pos()
        for animal_type, animal_data in ANIMAL_TYPES.items():
            card_rect = self.card_rects[animal_type]
            card_color = (
                CROP_CARD_HOVER
                if card_rect.collidepoint(mouse_position)
                else CROP_CARD_BACKGROUND
            )
            pygame.draw.rect(screen, card_color, card_rect)
            pygame.draw.rect(screen, INFO_PANEL_BORDER, card_rect, 1)
            text_x = card_rect.x + 14
            text_y = card_rect.y + 12
            self.draw_text(
                screen, font, animal_data["name"], text_x, text_y,
            )
            self.draw_text(
                screen, font,
                f"Vásárlási ár: {format_money(animal_data['purchase_price'])}",
                text_x, text_y + 30,
            )


class CropSelectionPanel(SelectionPanel):
    """A központi növénydefiníciókból felépülő, kártyás növényválasztó."""

    def __init__(self):
        super().__init__(CROP_PANEL_WIDTH, 188)

    def _update_layout(self):
        crop_count = max(1, len(CROPS))
        _, screen_height = get_screen_size()
        self.rect.width = responsive_panel_width(CROP_PANEL_WIDTH)
        max_panel_height = max(
            140, screen_height - TOP_BAR_HEIGHT - BOTTOM_BAR_HEIGHT - 40,
        )
        desired_height = 76 + crop_count * CROP_CARD_HEIGHT
        desired_height += max(0, crop_count - 1) * CROP_CARD_GAP + 20
        self.rect.height = min(desired_height, max_panel_height)
        self.rect.center = get_screen_center()

        self.card_rects = {}
        card_y = self.rect.y + 58
        for crop_id in CROPS:
            self.card_rects[crop_id] = pygame.Rect(
                self.rect.x + INFO_PANEL_PADDING,
                card_y,
                self.rect.width - INFO_PANEL_PADDING * 2,
                CROP_CARD_HEIGHT,
            )
            card_y += CROP_CARD_HEIGHT + CROP_CARD_GAP

    def draw(self, screen, font):
        if not self.visible:
            return
        self._update_layout()
        self.draw_frame(screen)

        x = self.rect.x + INFO_PANEL_PADDING
        self.draw_text(
            screen, font, POPUP_TITLES["crop_selection"],
            x, self.rect.y + INFO_PANEL_PADDING,
        )

        mouse_position = pygame.mouse.get_pos()
        previous_clip = screen.get_clip()
        screen.set_clip(self.rect.inflate(-2, -2))
        for crop_id, crop_data in CROPS.items():
            card_rect = self.card_rects[crop_id]
            if card_rect.bottom <= self.rect.top or card_rect.top >= self.rect.bottom:
                continue
            card_color = (
                CROP_CARD_HOVER
                if card_rect.collidepoint(mouse_position)
                else CROP_CARD_BACKGROUND
            )
            pygame.draw.rect(screen, card_color, card_rect)
            pygame.draw.rect(screen, INFO_PANEL_BORDER, card_rect, 1)

            text_x = card_rect.x + 14
            text_y = card_rect.y + 10
            self.draw_text(screen, font, crop_data["name"], text_x, text_y)
            self.draw_text(
                screen,
                font,
                f"Érési idő: {get_crop_growth_weeks(crop_data)} hét",
                text_x,
                text_y + 26,
            )
            self.draw_text(
                screen,
                font,
                f"Hozam: {crop_data['yield']} db",
                text_x,
                text_y + 52,
            )
            self.draw_text(
                screen,
                font,
                f"Eladási ár: {format_money(crop_data['price'])} / db",
                text_x,
                text_y + 78,
            )
        screen.set_clip(previous_clip)


class OrchardSelectionPanel(SelectionPanel):
    """Az adatvezérelt gyümölcsfajták közös kiválasztóablaka."""

    def __init__(self):
        super().__init__(520, 220)

    def _update_layout(self):
        self.rect.width = responsive_panel_width(520)
        self.rect.height = 220
        self.rect.center = get_screen_center()
        self.card_rects = {}
        card_y = self.rect.y + 58
        for tree_type in TREE_TYPES:
            self.card_rects[tree_type] = pygame.Rect(
                self.rect.x + INFO_PANEL_PADDING,
                card_y,
                self.rect.width - INFO_PANEL_PADDING * 2,
                140,
            )
            card_y += 152

    def draw(self, screen, font):
        if not self.visible:
            return
        self._update_layout()
        self.draw_frame(screen)
        self.draw_text(
            screen, font, POPUP_TITLES["orchard_selection"],
            self.rect.x + INFO_PANEL_PADDING,
            self.rect.y + INFO_PANEL_PADDING,
        )
        mouse_position = pygame.mouse.get_pos()
        for tree_type, definition in TREE_TYPES.items():
            card_rect = self.card_rects[tree_type]
            card_color = (
                CROP_CARD_HOVER
                if card_rect.collidepoint(mouse_position)
                else CROP_CARD_BACKGROUND
            )
            pygame.draw.rect(screen, card_color, card_rect)
            pygame.draw.rect(screen, INFO_PANEL_BORDER, card_rect, 1)
            text_x = card_rect.x + 14
            text_y = card_rect.y + 10
            lines = (
                definition["name"],
                f"Ültetési ár: {format_money(definition['planting_cost'])}",
                f"Első termés: {definition['first_yield_age_years']} év után",
                f"Éves termés: {definition['annual_yield']} db "
                f"{definition['name'].lower()}",
                "Termő időszak: "
                f"{definition['first_yield_age_years']}–"
                f"{definition['last_yield_age_years']} éves kor",
            )
            for index, line in enumerate(lines):
                self.draw_text(
                    screen, font, line, text_x, text_y + index * 25,
                )


class BuildingSelectionPanel(SelectionPanel):
    """A központi építési katalógusból felépülő épületválasztó."""

    def __init__(self):
        super().__init__(BUILDING_PANEL_WIDTH, 200)
        self.purchased_upgrades = set()

    def open(self, game_state=None):
        if game_state is not None:
            self.purchased_upgrades = game_state.purchased_upgrades
        super().open()

    def _available_options(self):
        return {
            option_id: option
            for option_id, option in BUILD_OPTIONS.items()
            if is_build_option_unlocked(option, self.purchased_upgrades)
        }

    def _update_layout(self):
        available_options = self._available_options()
        option_count = len(available_options)
        screen_width, screen_height = get_screen_size()
        self.rect.width = responsive_panel_width(BUILDING_PANEL_WIDTH, 320)
        column_count = 2 if self.rect.width >= 600 else 1
        row_count = (option_count + column_count - 1) // column_count
        desired_height = 78 + row_count * BUILDING_CARD_HEIGHT
        desired_height += max(0, row_count - 1) * BUILDING_CARD_GAP + 20
        self.rect.height = min(
            desired_height,
            max(140, screen_height - TOP_BAR_HEIGHT - BOTTOM_BAR_HEIGHT - 40),
        )
        self.rect.center = get_screen_center()

        self.card_rects = {}
        card_width = (
            self.rect.width - INFO_PANEL_PADDING * 2 - BUILDING_CARD_GAP
        ) // column_count
        for index, option_id in enumerate(available_options):
            row = index // column_count
            col = index % column_count
            self.card_rects[option_id] = pygame.Rect(
                self.rect.x + INFO_PANEL_PADDING
                + col * (card_width + BUILDING_CARD_GAP),
                self.rect.y + 58 + row * (
                    BUILDING_CARD_HEIGHT + BUILDING_CARD_GAP
                ),
                card_width,
                BUILDING_CARD_HEIGHT,
            )

    def draw(self, screen, font, game_state=None):
        if not self.visible:
            return
        if game_state is not None:
            self.purchased_upgrades = game_state.purchased_upgrades
        self._update_layout()
        self.draw_frame(screen)
        x = self.rect.x + INFO_PANEL_PADDING
        self.draw_text(
            screen, font, POPUP_TITLES["building_selection"],
            x, self.rect.y + INFO_PANEL_PADDING,
        )

        mouse_position = pygame.mouse.get_pos()
        for option_id, option in self._available_options().items():
            card_rect = self.card_rects[option_id]
            card_color = (
                CROP_CARD_HOVER
                if card_rect.collidepoint(mouse_position)
                else CROP_CARD_BACKGROUND
            )
            pygame.draw.rect(screen, card_color, card_rect)
            pygame.draw.rect(screen, INFO_PANEL_BORDER, card_rect, 1)

            text_x = card_rect.x + 14
            text_y = card_rect.y + 8
            self.draw_text(screen, font, option["name"], text_x, text_y)
            self.draw_text(
                screen, font, f"Építési ár: {format_money(option['build_cost'])}",
                text_x, text_y + 24,
            )
            self.draw_text(
                screen, font,
                f"Éves költség: {format_annual_maintenance_rate()}",
                text_x, text_y + 48,
            )
            self.draw_text(
                screen, font, f"Méret: {option['width']}x{option['height']}",
                text_x, text_y + 72,
            )


def draw_ui(
    screen, font, buttons, selected_tool, buildings=None, elapsed_weeks=0,
    economy=None,
    time_speed=TIME_NORMAL, toolbar_icons=None, time_speed_icons=None,
    menu_button=None, menu_icon=None, menu_open=False,
    calendar_button=None, calendar_icon=None, calendar_open=False,
):
    screen_width, screen_height = get_screen_size()
    # A felső sáv kizárólag a játékállapotot mutatja.
    pygame.draw.rect(screen, COLOR_TOOLBAR, (0, 0, screen_width, TOP_BAR_HEIGHT))
    pygame.draw.line(
        screen,
        COLOR_TOOLBAR_LINE,
        (0, TOP_BAR_HEIGHT),
        (screen_width, TOP_BAR_HEIGHT),
        2,
    )

    # Az eszközgombok az alsó, különálló sávban helyezkednek el.
    toolbar_top = screen_height - BOTTOM_BAR_HEIGHT
    pygame.draw.rect(
        screen,
        COLOR_TOOLBAR,
        (0, toolbar_top, screen_width, BOTTOM_BAR_HEIGHT),
    )
    pygame.draw.line(
        screen,
        COLOR_TOOLBAR_LINE,
        (0, toolbar_top),
        (screen_width, toolbar_top),
        2,
    )

    mouse_position = pygame.mouse.get_pos()
    hovered_tooltip = None
    toolbar_icons = toolbar_icons or {}

    for tool_data in TOOLS:
        tool = tool_data["tool"]
        button = buttons[tool]
        draw_button(
            screen,
            button,
            tool_data["icon_color"],
            selected_tool == tool,
            toolbar_icons.get(tool),
        )
        if button.collidepoint(mouse_position):
            hovered_tooltip = (tool_data["name"], button)

    # A HUD mindig a buildings lista pillanatnyi állapotából számol.
    time_start_x = HUD_LEFT_MARGIN
    if menu_button is not None:
        draw_button(
            screen, menu_button, (245, 245, 240), menu_open, menu_icon,
        )
        if menu_button.collidepoint(mouse_position):
            hovered_tooltip = (HUD_BUTTON_TOOLTIPS["menu"], menu_button)
        time_start_x = menu_button.right + HUD_MENU_GAP
    if calendar_button is not None:
        draw_button(
            screen, calendar_button, (245, 245, 240),
            calendar_open, calendar_icon,
        )
        if calendar_button.collidepoint(mouse_position):
            hovered_tooltip = (
                HUD_BUTTON_TOOLTIPS["calendar"], calendar_button,
            )
        time_start_x = calendar_button.right + HUD_MENU_GAP
    hud_layout = draw_hud(
        screen, font, buildings or [], elapsed_weeks, economy, time_speed,
        time_speed_icons, time_start_x,
    )

    if hovered_tooltip is not None:
        tooltip_text, tooltip_button = hovered_tooltip
        draw_tooltip(screen, font, tooltip_text, tooltip_button)
    return hud_layout
