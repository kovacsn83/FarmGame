import pygame

from app_state import AppState, AppStateManager
from animals import (
    ANIMAL_TYPES, AnimalMovementSystem, animal_pen_demolition_block_reason, draw_animals,
    purchase_and_place_animal, run_weekly_animal_cycle,
)
from animal_troughs import (
    draw_pen_troughs, find_trough_at, get_trough_tooltip,
    synchronize_pen_group_stocks,
)
from animal_automation import run_weekly_animal_supply_automation
from asset_loader import load_grass_tiles
from bank import BankSystem
from camera import Camera
from buildings import (
    BUILD_OPTIONS, can_place_building, find_building_data, place_building,
    print_building_info, remove_building,
)
from constants import (
    COLOR_GRASS, GRASS, TILE_SIZE,
    TOOL_ANIMAL_HUSBANDRY, TOOL_BUILD, TOOL_BULLDOZER, TOOL_HARVEST,
    TOOL_FERTILIZE, TOOL_INSPECT, TOOL_ORCHARD, TOOL_PLANT, TOOL_ROAD,
    TOOL_WATERING,
    WINDOW_HEIGHT, WINDOW_WIDTH,
)
from developer_console import DeveloperConsole
from economy import Economy
from fields import (
    can_place_field, find_field_data, grow_crops,
    is_field, place_field, print_field_info,
    remove_field, remove_field_data,
)
from game_state import GameState
from game_rules import FIELD_TYPES, is_build_option_unlocked
from game_menu import GameMenu
from game_logger import get_logger
from notification_system import NotificationManager
from orchards import (
    draw_orchard_trees, find_tree_at, plant_tree, run_weekly_orchard_cycle,
)
from quest_system import (
    QUEST_EVENT_ANIMAL_PEN_BUILT, QUEST_EVENT_CALENDAR_OPENED,
    QUEST_EVENT_CATTLE_COUNT_CHANGED, QUEST_EVENT_FARMHOUSE_BUILT,
    QUEST_EVENT_FIELD_COUNT_CHANGED, QUEST_EVENT_FIELD_DEMOLISHED,
    QUEST_EVENT_GARAGE_BUILT, QUEST_EVENT_MARKET_BUILT,
    QUEST_EVENT_MILK_SOLD, QUEST_EVENT_ROAD_BUILT,
    QUEST_EVENT_POND_BUILT,
    QUEST_EVENT_TIME_PAUSED_BY_KEY, QUEST_EVENT_TIME_STARTED_BY_KEY,
    QUEST_EVENT_WAREHOUSE_BUILT, QuestManager,
)
from progress_tooltips import find_timed_object_tooltip
from road_building import RoadDragState, build_road_segment
from save_slots_ui import LoadSlotsMenu, SaveSlotsMenu
from save_system import (
    load_game, load_game_from_slot, save_game, save_game_to_slot,
)
from screen_layout import set_camera, set_screen_size, world_to_screen
from startup_ui import MainMenu, SplashScreen
from time_system import (
    TIME_NORMAL, TIME_PAUSED, TIME_SLOW, GameTime,
    format_game_time,
)
from vehicle_manager import VehicleManager
from ui import (
    AnimalHusbandryPanel, BankPanel, BuildingSelectionPanel, CalendarPanel,
    CropSelectionPanel, InfoPanel, OrchardSelectionPanel, QuestPanel, clicked_tool,
    create_buttons, create_calendar_button, create_calendar_icon,
    create_menu_button, create_menu_icon, create_quest_icon,
    create_time_speed_icons, create_toolbar_icons, draw_ui,
    draw_notification_bar, draw_tooltip,
)
from world import (
    create_world, draw_animal_pen_fences, draw_grid, draw_orchard_fences,
    draw_preview, draw_world,
    screen_to_grid,
)


def main():
    pygame.init()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    screen = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE,
    )
    set_screen_size(*screen.get_size())
    camera = Camera()
    set_camera(camera)
    pygame.display.set_caption("FarmGame")

    app_state = AppStateManager()
    splash_screen = SplashScreen()
    main_menu = MainMenu()
    load_slots_menu = LoadSlotsMenu()
    logger = get_logger()

    # A tényleges farmállapot kizárólag Új játék vagy Betöltés választásakor készül el.
    world = fields = buildings = animals = None
    animal_movement = None
    selected_tool = selected_crop = selected_building = selected_animal = None
    selected_tree = None
    buttons = toolbar_icons = time_speed_icons = None
    menu_button = menu_icon = calendar_button = calendar_icon = None
    grass_tiles = game_time = developer_console = notification_manager = None
    economy = bank_system = vehicles = game_state = None
    info_panel = crop_selection_panel = building_selection_panel = None
    animal_husbandry_panel = orchard_selection_panel = calendar_panel = bank_panel = None
    game_menu = save_slots_menu = quest_manager = quest_panel = road_drag = None

    def initialize_game_session(start_quest):
        """Egyetlen helyen hozza létre az új vagy betöltendő farm teljes állapotát."""
        nonlocal world, fields, buildings, animals, animal_movement
        nonlocal selected_tool, selected_crop, selected_building, selected_animal
        nonlocal selected_tree
        nonlocal buttons, toolbar_icons, time_speed_icons
        nonlocal menu_button, menu_icon, calendar_button, calendar_icon
        nonlocal grass_tiles, game_time, developer_console, notification_manager
        nonlocal economy, bank_system, vehicles, game_state
        nonlocal info_panel, crop_selection_panel, building_selection_panel
        nonlocal animal_husbandry_panel, orchard_selection_panel
        nonlocal calendar_panel, bank_panel
        nonlocal game_menu, save_slots_menu, quest_manager, quest_panel, road_drag

        world = create_world()
        fields, buildings, animals = [], [], []
        animal_movement = AnimalMovementSystem()
        selected_tool = TOOL_INSPECT
        selected_crop = selected_building = selected_animal = selected_tree = None
        buttons = create_buttons()
        toolbar_icons = create_toolbar_icons()
        time_speed_icons = create_time_speed_icons()
        menu_button = create_menu_button()
        menu_icon = create_menu_icon()
        calendar_button = create_calendar_button(menu_button)
        calendar_icon = create_calendar_icon()
        grass_tiles = load_grass_tiles(TILE_SIZE)
        game_time = GameTime(current_time_speed=TIME_SLOW)
        logger.reset()
        logger.set_timestamp_provider(
            lambda: format_game_time(game_time.elapsed_weeks),
        )
        developer_console = DeveloperConsole(logger, visible=True)
        notification_manager = NotificationManager(
            start_ticks=pygame.time.get_ticks(),
        )
        economy = Economy()
        bank_system = BankSystem(economy)
        vehicles = VehicleManager()
        quest_manager = QuestManager()
        game_state = GameState(
            world, fields, buildings, economy, game_time,
            tractor=vehicles, vehicles=vehicles, animals=animals,
            bank_system=bank_system, quest_manager=quest_manager,
        )
        info_panel = InfoPanel()
        crop_selection_panel = CropSelectionPanel()
        building_selection_panel = BuildingSelectionPanel()
        animal_husbandry_panel = AnimalHusbandryPanel()
        orchard_selection_panel = OrchardSelectionPanel()
        calendar_panel = CalendarPanel()
        bank_panel = BankPanel()
        game_menu = GameMenu()
        save_slots_menu = SaveSlotsMenu()
        if start_quest:
            quest_manager.start_new_game()
        else:
            quest_manager.hide()
        vehicles.quest_event_handler = quest_manager.record_event
        quest_panel = QuestPanel(create_quest_icon())
        road_drag = RoadDragState()
        camera.update_world_size(len(world[0]), len(world))
        camera.reset()
        logger.log(
            "Developer Console elindult. F3: megjelenítés/elrejtés.",
            "System",
        )
        if start_quest:
            logger.log("Új játék inicializálva.", "System")

    def finish_loaded_session():
        """A sikeres betöltés után egységesen előkészíti a játékmenetet."""
        bank_panel.close()
        notification_manager.reset(pygame.time.get_ticks())
        camera.update_world_size(len(world[0]) if world else 0, len(world))
        camera.reset()
        animal_movement.reset()
        app_state.start_playing()

    def resume_after_bank():
        """A Bank lezárása után visszaállítja a korábbi idősebességet."""
        game_time.set_time_speed(bank_panel.previous_time_speed)
        vehicles.synchronize_time()
        animal_movement.synchronize()

    def handle_info_panel_event(event):
        """Egy helyen kezeli az információs panelek minden műveletét."""
        handled = info_panel.handle_event(event)
        item_to_sell = info_panel.take_sale_selection()
        if item_to_sell is not None:
            if economy.sell_item(buildings, item_to_sell):
                if item_to_sell == "milk":
                    quest_manager.record_event(QUEST_EVENT_MILK_SOLD)
        upgrade_to_purchase = info_panel.take_upgrade_selection()
        if upgrade_to_purchase is not None:
            economy.purchase_upgrade(game_state, upgrade_to_purchase)
        vehicle_purchase = info_panel.take_vehicle_purchase()
        if vehicle_purchase is not None:
            garage, vehicle_type = vehicle_purchase
            vehicles.purchase_vehicle(
                world, buildings, economy, garage, vehicle_type,
            )
        return handled

    def road_drag_tile_at(position):
        """Csak valódi, UI-val nem takart játéktéri csempét ad vissza."""
        if (
            developer_console.visible
            and developer_console.rect.collidepoint(position)
        ):
            return None
        row, col = screen_to_grid(*position, world)
        return (row, col) if row >= 0 else None
    
    
    def handle_gameplay_click(position):
        """A kamera küszöbe alatt maradó bal kattintás régi játékműveletei."""
        if selected_tool == TOOL_INSPECT:
            trough = find_trough_at(position, buildings, animals)
            if trough is not None:
                vehicles.start_trough_supply(
                    world, buildings, economy, animals, trough,
                )
                return
        mouse_row, mouse_col = screen_to_grid(*position, world)
        if mouse_row < 0:
            return
    
        if selected_tool == TOOL_INSPECT:
            field = find_field_data(fields, mouse_row, mouse_col)
            if field:
                print_field_info(field)
            else:
                building = find_building_data(buildings, mouse_row, mouse_col)
                if building:
                    if not info_panel.open_for_building(building):
                        print_building_info(building)
        elif selected_tool == TOOL_ROAD:
            build_road_segment(
                world, [(mouse_row, mouse_col)], economy,
                road_built_handler=lambda amount: quest_manager.record_event(
                    QUEST_EVENT_ROAD_BUILT, amount=amount,
                ),
            )
        elif selected_tool == TOOL_BULLDOZER:
            building = find_building_data(buildings, mouse_row, mouse_col)
            field = find_field_data(fields, mouse_row, mouse_col)
            block_reason = animal_pen_demolition_block_reason(
                building, buildings, animals,
            ) or vehicles.demolition_block_reason(
                mouse_row, mouse_col, building, field,
            )
            if block_reason:
                logger.log(block_reason, "Building")
            elif building:
                if remove_building(world, buildings, building):
                    synchronize_pen_group_stocks(buildings, animals)
            elif is_field(world, mouse_row, mouse_col):
                if field:
                    remove_field(
                        world, field["row"], field["col"],
                        field["width"], field["height"],
                    )
                    remove_field_data(fields, field["row"], field["col"])
                    quest_manager.record_event(
                        QUEST_EVENT_FIELD_COUNT_CHANGED,
                        current_value=len(fields),
                    )
                    quest_manager.record_event(QUEST_EVENT_FIELD_DEMOLISHED)
            else:
                world[mouse_row][mouse_col] = GRASS
        elif selected_tool == TOOL_ORCHARD and selected_tree is not None:
            plant_tree(
                buildings, economy, mouse_row, mouse_col, selected_tree,
            )
        elif selected_tool == TOOL_BUILD and selected_building is not None:
            cost = BUILD_OPTIONS[selected_building]["build_cost"]
            option = BUILD_OPTIONS[selected_building]
            if not is_build_option_unlocked(
                    option, game_state.purchased_upgrades):
                logger.log("Ez az építhető elem még nincs feloldva.", "Building")
            elif selected_building in FIELD_TYPES:
                if can_place_field(
                        world, mouse_row, mouse_col,
                        option["width"], option["height"]):
                    if economy.can_build(cost):
                        place_field(
                            world, fields, mouse_row, mouse_col,
                            selected_building,
                        )
                        economy.spend(cost)
                        quest_manager.record_event(
                            QUEST_EVENT_FIELD_COUNT_CHANGED,
                            current_value=len(fields),
                        )
            elif (can_place_building(
                    world, buildings, mouse_row, mouse_col,
                    selected_building, show_limit_message=True,
                    animals=animals)
                    and economy.can_build(cost)):
                new_building = place_building(
                    world, buildings, mouse_row, mouse_col,
                    selected_building,
                )
                economy.spend(cost)
                logger.log(
                    f"{option['name']} megépült: ({mouse_row}, {mouse_col}).",
                    "Building",
                )
                if selected_building == "farmhouse":
                    quest_manager.record_event(QUEST_EVENT_FARMHOUSE_BUILT)
                    vehicles.on_farmhouse_built(
                        world, buildings, new_building,
                    )
                elif selected_building == "warehouse":
                    quest_manager.record_event(QUEST_EVENT_WAREHOUSE_BUILT)
                elif selected_building == "animal_pen":
                    synchronize_pen_group_stocks(
                        buildings, animals, cap_merged=True,
                    )
                    quest_manager.record_event(QUEST_EVENT_ANIMAL_PEN_BUILT)
                elif selected_building == "market":
                    quest_manager.record_event(QUEST_EVENT_MARKET_BUILT)
                elif selected_building == "garage":
                    quest_manager.record_event(QUEST_EVENT_GARAGE_BUILT)
                    vehicles.on_garage_built(
                        world, buildings, new_building,
                    )
                elif selected_building == "pond":
                    quest_manager.record_event(QUEST_EVENT_POND_BUILT)
        elif selected_tool == TOOL_PLANT:
            field = find_field_data(fields, mouse_row, mouse_col)
            if field and selected_crop is not None:
                vehicles.start_planting(
                    world, buildings, economy, field, selected_crop,
                    current_week=game_time.week,
                )
        elif selected_tool == TOOL_HARVEST:
            orchard_target = find_tree_at(buildings, mouse_row, mouse_col)
            if orchard_target is not None:
                orchard, tree = orchard_target
                vehicles.start_orchard_harvest(
                    world, buildings, economy, orchard, tree,
                )
            else:
                field = find_field_data(fields, mouse_row, mouse_col)
                if field:
                    vehicles.start_harvesting(
                        world, buildings, economy, field,
                        current_week=game_time.week,
                        current_elapsed_week=game_time.elapsed_weeks,
                    )
        elif selected_tool == TOOL_FERTILIZE:
            field = find_field_data(fields, mouse_row, mouse_col)
            if field:
                vehicles.start_fertilizing(
                    world, buildings, economy, field,
                )
            else:
                logger.log(
                    "Nincs trágyázható növény a kijelölt területen.",
                    "Fertilizing",
                )
        elif selected_tool == TOOL_WATERING:
            field = find_field_data(fields, mouse_row, mouse_col)
            vehicles.start_watering(
                world, buildings, economy, field,
            )
        elif selected_tool == TOOL_ANIMAL_HUSBANDRY and selected_animal is not None:
            animal_purchased = purchase_and_place_animal(
                animals, buildings, economy, mouse_row, mouse_col,
                selected_animal,
            )
            if animal_purchased and selected_animal == "cattle":
                quest_manager.record_event(
                    QUEST_EVENT_CATTLE_COUNT_CHANGED,
                    current_value=sum(
                        animal.get("type") == "cattle" for animal in animals
                    ),
                )
    
    running = True
    while running:
        events = pygame.event.get()

        if app_state.state == AppState.SPLASH:
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    set_screen_size(*screen.get_size())
            app_state.update()
            splash_screen.draw(screen)
            pygame.display.flip()
            clock.tick(60)
            continue

        if app_state.state == AppState.MAIN_MENU:
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    continue
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if load_slots_menu.visible:
                        load_slots_menu.close()
                    else:
                        running = False
                    continue
                if event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    set_screen_size(*screen.get_size())
                    continue

                if load_slots_menu.visible:
                    load_slots_menu.handle_event(event)
                    slot_id = load_slots_menu.take_load_request()
                    if slot_id is not None:
                        initialize_game_session(start_quest=False)
                        loaded = load_game_from_slot(game_state, slot_id)
                        load_slots_menu.complete_load(loaded)
                        if loaded:
                            finish_loaded_session()
                    if load_slots_menu.take_navigation() == "game_menu":
                        load_slots_menu.close()
                    continue

                main_menu.handle_event(event)
                menu_action = main_menu.take_action()
                if menu_action == "new_game":
                    initialize_game_session(start_quest=True)
                    app_state.start_playing()
                elif menu_action == "load_game":
                    load_slots_menu.open()
                elif menu_action == "exit_game":
                    running = False

            if not running:
                break
            main_menu.draw(screen, font)
            load_slots_menu.draw(screen, font)
            pygame.display.flip()
            clock.tick(60)
            continue

        for event in events:
            if event.type == pygame.QUIT:
                running = False
                continue

            if developer_console.handle_global_shortcut(event):
                camera.cancel_drag()
                road_drag.cancel()
                continue
    
            if event.type == pygame.VIDEORESIZE:
                road_drag.cancel()
                screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                set_screen_size(*screen.get_size())
                buttons = create_buttons()
                menu_button = create_menu_button()
                calendar_button = create_calendar_button(menu_button)
                continue

            if developer_console.handle_event(
                    event, pygame.mouse.get_pos()):
                continue

            if bank_panel.visible:
                if bank_panel.market_active:
                    handle_info_panel_event(event)
                    if not info_panel.visible:
                        bank_panel.finish_market()
                        if bank_system.resolve_offer_after_market():
                            bank_panel.close()
                            resume_after_bank()
                    continue

                bank_panel.handle_event(event)
                bank_decision = bank_panel.take_decision()
                if bank_decision == "market":
                    market = next(
                        (item for item in buildings if item["type"] == "market"),
                        None,
                    )
                    if market is not None and info_panel.open_for_building(market):
                        bank_panel.begin_market()
                    else:
                        logger.log(
                            "A Piac megnyitásához legalább egy Piac szükséges.",
                            "Bank",
                        )
                elif bank_decision == "accept":
                    bank_system.accept_offer()
                elif bank_decision == "decline":
                    bank_system.decline_offer()
                if bank_decision in ("accept", "decline"):
                    resume_after_bank()
                continue
    
            if save_slots_menu.visible:
                save_slots_menu.handle_event(event, game_time.elapsed_weeks)
                save_request = save_slots_menu.take_save_request()
                if save_request is not None:
                    slot_id, save_name = save_request
                    save_slots_menu.complete_save(save_game_to_slot(
                        game_state, slot_id, save_name,
                    ))
                if save_slots_menu.take_navigation() == "game_menu":
                    game_menu.open()
                continue
    
            if load_slots_menu.visible:
                load_slots_menu.handle_event(event)
                slot_id = load_slots_menu.take_load_request()
                if slot_id is not None:
                    loaded = load_game_from_slot(game_state, slot_id)
                    if loaded:
                        road_drag.cancel()
                        finish_loaded_session()
                    load_slots_menu.complete_load(loaded)
                if load_slots_menu.take_navigation() == "game_menu":
                    game_menu.open()
                continue

            if calendar_panel.handle_event(event):
                continue

            calendar_button_clicked = (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and calendar_button.collidepoint(event.pos)
            )
            if calendar_button_clicked:
                camera.cancel_drag()
                road_drag.cancel()
                info_panel.close()
                crop_selection_panel.close()
                building_selection_panel.close()
                animal_husbandry_panel.close()
                orchard_selection_panel.close()
                calendar_panel.open()
                quest_manager.record_event(QUEST_EVENT_CALENDAR_OPENED)
                continue
    
            menu_button_clicked = (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and menu_button.collidepoint(event.pos)
            )
            escape_pressed = (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            )
            if menu_button_clicked or escape_pressed:
                camera.cancel_drag()
                road_drag.cancel()
                game_menu.toggle()
                if game_menu.visible:
                    info_panel.close()
                    crop_selection_panel.close()
                    building_selection_panel.close()
                    animal_husbandry_panel.close()
                    orchard_selection_panel.close()
                    calendar_panel.close()
                continue
    
            if game_menu.visible:
                game_menu.handle_event(event)
                menu_action = game_menu.take_action()
                if menu_action == "save_game":
                    game_menu.close()
                    save_slots_menu.open()
                elif menu_action == "load_game":
                    game_menu.close()
                    load_slots_menu.open()
                elif menu_action == "new_game":
                    screen = pygame.display.set_mode(
                        (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE,
                    )
                    set_screen_size(*screen.get_size())
                    initialize_game_session(start_quest=True)
                elif menu_action == "exit_game":
                    running = False
                continue
    
            if building_selection_panel.handle_event(event):
                building_selection = building_selection_panel.take_selection()
                if building_selection is not None:
                    road_drag.cancel()
                    selected_building = building_selection
                    selected_tool = TOOL_BUILD
                continue
    
            if animal_husbandry_panel.handle_event(event):
                animal_selection = animal_husbandry_panel.take_selection()
                if animal_selection is not None:
                    road_drag.cancel()
                    selected_animal = animal_selection
                    selected_tool = TOOL_ANIMAL_HUSBANDRY
                continue

            if orchard_selection_panel.handle_event(event):
                tree_selection = orchard_selection_panel.take_selection()
                if tree_selection is not None:
                    road_drag.cancel()
                    selected_tree = tree_selection
                    selected_building = None
                    selected_tool = TOOL_ORCHARD
                continue
    
            if crop_selection_panel.handle_event(event):
                crop_selection = crop_selection_panel.take_selection()
                if crop_selection is not None:
                    road_drag.cancel()
                    selected_crop = crop_selection
                    selected_tool = TOOL_PLANT
                continue
    
            if handle_info_panel_event(event):
                continue
    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F5:
                    save_game(game_state)
                elif event.key == pygame.K_F9:
                    if load_game(game_state):
                        road_drag.cancel()
                        finish_loaded_session()
                elif event.key == pygame.K_g:
                    # Ideiglenes fejlesztői gyorsbillentyű: a hetet nem lépteti.
                    grow_crops(fields, game_time.elapsed_weeks)
                elif event.key in (pygame.K_0, pygame.K_KP0):
                    was_paused = game_time.current_time_speed == TIME_PAUSED
                    if (
                        game_time.set_time_speed(TIME_PAUSED)
                        and not was_paused
                        and game_time.current_time_speed == TIME_PAUSED
                    ):
                        quest_manager.record_event(
                            QUEST_EVENT_TIME_PAUSED_BY_KEY,
                        )
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    was_paused = game_time.current_time_speed == TIME_PAUSED
                    if (
                        game_time.set_time_speed(TIME_SLOW)
                        and was_paused
                        and game_time.current_time_speed == TIME_SLOW
                    ):
                        quest_manager.record_event(
                            QUEST_EVENT_TIME_STARTED_BY_KEY,
                        )
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    game_time.set_time_speed(TIME_NORMAL)
    
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    tool = clicked_tool(buttons, event.pos)
                    if tool is not None:
                        road_drag.cancel()
                        if tool == TOOL_PLANT:
                            crop_selection_panel.open()
                        elif tool == TOOL_BUILD:
                            building_selection_panel.open(game_state)
                        elif tool == TOOL_ANIMAL_HUSBANDRY:
                            animal_husbandry_panel.open()
                        elif tool == TOOL_ORCHARD:
                            orchard_selection_panel.open()
                        else:
                            selected_tool = tool
                        continue
                    clicked_tile = road_drag_tile_at(event.pos)
                    if clicked_tile is not None:
                        clicked_row, clicked_col = clicked_tile
                        if selected_tool == TOOL_ROAD:
                            camera.cancel_drag()
                            road_drag.begin((clicked_row, clicked_col))
                        else:
                            camera.begin_drag(event.pos)
                elif event.button == 3:
                    camera.cancel_drag()
                    road_drag.cancel()
                    selected_tool = TOOL_INSPECT
    
            elif event.type == pygame.MOUSEMOTION:
                if road_drag.active:
                    drag_tile = road_drag_tile_at(event.pos)
                    if drag_tile is None:
                        road_drag.cancel()
                    else:
                        road_drag.update(drag_tile)
                else:
                    camera.update_drag(event.pos)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if road_drag.active:
                    drag_tile = road_drag_tile_at(event.pos)
                    if drag_tile is not None:
                        road_drag.update(drag_tile)
                        build_road_segment(
                            world, road_drag.tiles, economy,
                            road_built_handler=lambda amount: (
                                quest_manager.record_event(
                                    QUEST_EVENT_ROAD_BUILT, amount=amount,
                                )
                            ),
                        )
                    road_drag.cancel()
                    continue
                click_position, was_dragging = camera.finish_drag()
                if click_position is not None and not was_dragging:
                    handle_gameplay_click(click_position)
    
        menu_system_active = (
            game_menu.visible
            or save_slots_menu.visible
            or load_slots_menu.visible
            or bank_panel.visible
        )
        if menu_system_active:
            game_time.synchronize()
            vehicles.synchronize_time()
            animal_movement.synchronize()
        else:
            vehicles.update(world, buildings, economy, game_time)
            animal_movement.update(animals, buildings, game_time)
    
            # Minden ténylegesen eltelt játékbeli héthez pontosan egy frissítés tartozik.
            for elapsed_week in game_time.update():
                logger.log(
                    f"Új hét kezdődött: {format_game_time(elapsed_week)}",
                    "Time",
                )
                economy.apply_weekly_costs(
                    world, buildings, fields,
                    vehicle_count=len(vehicles.vehicles),
                    vehicle_weekly_cost=vehicles.weekly_cost,
                )
                bank_system.apply_weekly_repayment()
                grow_crops(fields, elapsed_week, notification_manager)
                run_weekly_animal_cycle(
                    animals, buildings, economy, notification_manager,
                )
                run_weekly_orchard_cycle(buildings)
                run_weekly_animal_supply_automation(
                    world, buildings, economy, animals, vehicles,
                    game_state.purchased_upgrades,
                    current_ticks=pygame.time.get_ticks(),
                )
                notification_manager.process_week(elapsed_week)

        notification_manager.update(
            pygame.time.get_ticks(),
            time_running=(
                not menu_system_active
                and game_time.current_time_speed != TIME_PAUSED
            ),
        )

        if not bank_panel.visible and bank_system.observe_balance():
            previous_time_speed = game_time.current_time_speed
            game_time.set_time_speed(TIME_PAUSED)
            vehicles.synchronize_time()
            animal_movement.synchronize()
            camera.cancel_drag()
            road_drag.cancel()
            info_panel.close()
            crop_selection_panel.close()
            building_selection_panel.close()
            animal_husbandry_panel.close()
            orchard_selection_panel.close()
            calendar_panel.close()
            game_menu.close()
            bank_panel.open(previous_time_speed)
    
        quest_manager.update()
    
        mouse_x, mouse_y = pygame.mouse.get_pos()
        mouse_row, mouse_col = screen_to_grid(mouse_x, mouse_y, world)
        if camera.dragging_camera:
            mouse_row, mouse_col = -1, -1
    
        screen.fill(COLOR_GRASS)
        draw_world(
            screen, world, fields, buildings, grass_tiles,
            harvest_availability=lambda field: (
                vehicles.get_harvest_block_reason(
                    world, buildings, field,
                    current_week=game_time.week,
                    current_elapsed_week=game_time.elapsed_weeks,
                )
            ),
        )
        draw_pen_troughs(screen, buildings, animals)
        draw_animals(screen, animals)
        draw_animal_pen_fences(screen, buildings)
        draw_orchard_trees(screen, buildings)
        draw_orchard_fences(screen, buildings)
        vehicles.ensure_idle_positions(world, buildings)
        vehicles.draw(screen)
        draw_grid(
            screen, world, selected_tool, selected_building, mouse_row, mouse_col
        )
        draw_preview(
            screen, world, fields, buildings, animals, selected_tool,
            selected_building, selected_animal, selected_tree,
            mouse_row, mouse_col,
            road_preview_tiles=road_drag.tiles,
        )
        developer_console.draw(screen)
        draw_notification_bar(
            screen, font, notification_manager,
            developer_console.rect.top,
        )
        draw_ui(
            screen, font, buttons, selected_tool, buildings,
            game_time.elapsed_weeks, economy,
            game_time.current_time_speed, toolbar_icons,
            time_speed_icons, menu_button, menu_icon, menu_system_active,
            calendar_button, calendar_icon, calendar_panel.visible,
        )
        if selected_tool == TOOL_INSPECT and not camera.dragging_camera:
            trough_tooltip = get_trough_tooltip(
                (mouse_x, mouse_y), buildings, animals,
            )
            if trough_tooltip is not None:
                tooltip_text, tooltip_rect = trough_tooltip
                draw_tooltip(screen, font, tooltip_text, tooltip_rect)
            elif mouse_row >= 0 and mouse_col >= 0:
                progress_lines = find_timed_object_tooltip(
                    mouse_row, mouse_col, fields, animals, ANIMAL_TYPES,
                    game_time.elapsed_weeks, game_time.week,
                    harvest_availability=lambda field: (
                        vehicles.get_harvest_block_reason(
                            world, buildings, field,
                            current_week=game_time.week,
                            current_elapsed_week=game_time.elapsed_weeks,
                        )
                    ),
                    buildings=buildings,
                )
                if progress_lines is not None:
                    tile_x, tile_y = world_to_screen(
                        mouse_col * TILE_SIZE, mouse_row * TILE_SIZE,
                    )
                    draw_tooltip(
                        screen, font, progress_lines,
                        pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE),
                    )
        quest_panel.draw(screen, font, quest_manager)
        bank_panel.draw(screen, font, bank_system)
        info_panel.draw(screen, font, game_state)
        crop_selection_panel.draw(screen, font)
        building_selection_panel.draw(screen, font, game_state)
        animal_husbandry_panel.draw(screen, font)
        orchard_selection_panel.draw(screen, font)
        calendar_panel.draw(screen, font, game_time.elapsed_weeks)
        game_menu.draw(screen, font)
        save_slots_menu.draw(screen, font)
        load_slots_menu.draw(screen, font)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
