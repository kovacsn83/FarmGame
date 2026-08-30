from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quest_system import (
    QUEST_COMPLETED_DISPLAY_MS, QUEST_DEFAULT_REWARD,
    QUEST_NEXT_APPEAR_DELAY_MS,
    QUEST_EVENT_ALFALFA_HARVESTED, QUEST_EVENT_ALFALFA_PLANTED,
    QUEST_EVENT_ANIMAL_PEN_BUILT, QUEST_EVENT_CALENDAR_OPENED,
    QUEST_EVENT_CATTLE_COUNT_CHANGED, QUEST_EVENT_COMBINE_PURCHASED,
    QUEST_EVENT_FARMHOUSE_BUILT, QUEST_EVENT_FIELD_COUNT_CHANGED,
    QUEST_EVENT_FIELD_FERTILIZED, QUEST_EVENT_FIELD_SPRAYED,
    QUEST_EVENT_FIELD_WATERED,
    QUEST_EVENT_FOOD_TROUGH_FILLED, QUEST_EVENT_GARAGE_BUILT,
    QUEST_EVENT_MARKET_BUILT, QUEST_EVENT_MILK_SOLD,
    QUEST_EVENT_POND_BUILT, QUEST_EVENT_ROAD_BUILT,
    QUEST_EVENT_TIME_PAUSED_BY_KEY, QUEST_EVENT_TIME_STARTED_BY_KEY,
    QUEST_EVENT_TRAILER_PURCHASED, QUEST_EVENT_WAREHOUSE_BUILT,
    QUEST_EVENT_WATER_TANK_PURCHASED, QUEST_EVENT_WATER_TROUGH_FILLED,
    QuestManager, QuestState,
)
from financial_history import INCOME_QUEST_REWARD
from game_logger import get_logger
from constants import ROAD
from economy import Economy
from vehicle_manager import VehicleManager
from vehicle_types import VehicleType


EXPECTED_TITLES = [
    "Építs 5 utat",
    "Építsd meg a Farmházat",
    "Építs egy Garázst",
    "Vegyél 1 locsolótartályt a garázsban",
    "Vegyél 1 pótkocsit a garázsban",
    "Építs egy Raktárat",
    "Állítsd meg az időt a 0-ás billentyűvel",
    "Építs egy Karámot",
    "Vegyél 2 szarvasmarhát",
    "Építs egy Tavat",
    "Építsd meg a Piacot",
    "Indítsd újra az időt az 1-es billentyűvel",
    "Adj ivóvizet és eledelt a Karám vályúiba",
    "Add el a tejet a Piacon",
    "Legyen 3 Veteményesed",
    "Nyisd meg a Gazdálkodási naptárat",
    "Ültess 3 lucernát",
    "Locsolj meg 3 veteményest",
    "Trágyázz be 3 veteményest",
    "Permetezz be 3 veteményest",
    "Vegyél 1 kombájnt",
    "Arass 3 lucernát",
]


class QuestSystemTests(unittest.TestCase):
    def test_quest_order_and_titles_are_exact(self):
        manager = QuestManager()
        self.assertEqual([quest.title for quest in manager.quests], EXPECTED_TITLES)

    def test_completion_grants_and_records_the_central_reward_once(self):
        economy = Economy(starting_money=1000)
        manager = QuestManager(economy, appear_delay_ms=0)
        manager.start_new_game(current_ticks=0)
        manager.update(current_ticks=0)
        get_logger().reset()

        manager.record_event(QUEST_EVENT_ROAD_BUILT, amount=5, current_ticks=0)
        manager.record_event(QUEST_EVENT_ROAD_BUILT, amount=5, current_ticks=0)

        self.assertEqual(QUEST_DEFAULT_REWARD, 100)
        self.assertEqual(economy.money, 1100)
        summary = economy.get_financial_summary()
        self.assertEqual(
            summary["income"][INCOME_QUEST_REWARD]["total"], 100,
        )
        self.assertTrue(manager.current_quest.reward_granted)
        self.assertIn("Jutalom: $100", get_logger().entries[-1].message)

    def test_rewards_from_multiple_quests_are_aggregated(self):
        economy = Economy(starting_money=0)
        manager = QuestManager(economy, appear_delay_ms=0)
        manager.start_new_game(current_ticks=0)
        manager.update(current_ticks=0)
        manager.record_event(QUEST_EVENT_ROAD_BUILT, amount=5, current_ticks=0)
        manager.update(current_ticks=QUEST_COMPLETED_DISPLAY_MS)
        manager.update(
            current_ticks=(
                QUEST_COMPLETED_DISPLAY_MS + QUEST_NEXT_APPEAR_DELAY_MS
            ),
        )
        manager.record_event(
            QUEST_EVENT_FARMHOUSE_BUILT,
            current_ticks=(
                QUEST_COMPLETED_DISPLAY_MS + QUEST_NEXT_APPEAR_DELAY_MS
            ),
        )

        self.assertEqual(economy.money, 200)
        self.assertEqual(
            economy.get_financial_summary()["income"]
            [INCOME_QUEST_REWARD]["total"],
            200,
        )

    def test_loaded_completed_quest_does_not_receive_a_retroactive_reward(self):
        source = QuestManager(appear_delay_ms=0)
        source.start_new_game(current_ticks=0)
        source.update(current_ticks=0)
        source.record_event(QUEST_EVENT_ROAD_BUILT, amount=5, current_ticks=0)
        record = source.to_save_record()

        economy = Economy(starting_money=500)
        restored = QuestManager(economy, appear_delay_ms=0)
        self.assertTrue(restored.load_save_record(record, current_ticks=10))
        restored.record_event(
            QUEST_EVENT_ROAD_BUILT, amount=5, current_ticks=10,
        )

        self.assertEqual(economy.money, 500)
        self.assertEqual(economy.get_financial_summary()["income_total"], 0)
        self.assertFalse(restored.current_quest.reward_granted)

    def test_all_twenty_two_conditions_advance_in_order(self):
        manager = QuestManager(appear_delay_ms=0)
        tick = 0
        manager.start_new_game(current_ticks=tick)
        manager.update(current_ticks=tick)
        events = [
            (QUEST_EVENT_ROAD_BUILT, 5, None),
            (QUEST_EVENT_FARMHOUSE_BUILT, 1, None),
            (QUEST_EVENT_GARAGE_BUILT, 1, None),
            (QUEST_EVENT_WATER_TANK_PURCHASED, 1, None),
            (QUEST_EVENT_TRAILER_PURCHASED, 1, None),
            (QUEST_EVENT_WAREHOUSE_BUILT, 1, None),
            (QUEST_EVENT_TIME_PAUSED_BY_KEY, 1, None),
            (QUEST_EVENT_ANIMAL_PEN_BUILT, 1, None),
            (QUEST_EVENT_CATTLE_COUNT_CHANGED, 1, 2),
            (QUEST_EVENT_POND_BUILT, 1, None),
            (QUEST_EVENT_MARKET_BUILT, 1, None),
            (QUEST_EVENT_TIME_STARTED_BY_KEY, 1, None),
            (None, 1, None),
            (QUEST_EVENT_MILK_SOLD, 1, None),
            (QUEST_EVENT_FIELD_COUNT_CHANGED, 1, 3),
            (QUEST_EVENT_CALENDAR_OPENED, 1, None),
            (QUEST_EVENT_ALFALFA_PLANTED, 3, None),
            (QUEST_EVENT_FIELD_WATERED, 3, None),
            (QUEST_EVENT_FIELD_FERTILIZED, 3, None),
            (QUEST_EVENT_FIELD_SPRAYED, 3, None),
            (QUEST_EVENT_COMBINE_PURCHASED, 1, None),
            (QUEST_EVENT_ALFALFA_HARVESTED, 3, None),
        ]

        for index, (event_id, amount, current_value) in enumerate(events):
            self.assertEqual(manager.current_quest.title, EXPECTED_TITLES[index])
            self.assertEqual(manager.current_quest.state, QuestState.ACTIVE)
            if event_id is None:
                manager.record_event(
                    QUEST_EVENT_FOOD_TROUGH_FILLED, current_ticks=tick,
                )
                self.assertFalse(manager.current_quest.completed)
                manager.record_event(
                    QUEST_EVENT_WATER_TROUGH_FILLED, current_ticks=tick,
                )
            else:
                if manager.current_quest.unique_progress:
                    for field_number in range(amount):
                        manager.record_event(
                            event_id, current_ticks=tick,
                            unique_key=(index, field_number),
                        )
                else:
                    manager.record_event(
                        event_id, amount=amount, current_ticks=tick,
                        current_value=current_value,
                    )
            self.assertTrue(manager.current_quest.completed)
            self.assertEqual(manager.current_quest.state, QuestState.COMPLETED)

            if index == len(events) - 1:
                break
            tick += QUEST_COMPLETED_DISPLAY_MS
            manager.update(current_ticks=tick)
            tick += QUEST_NEXT_APPEAR_DELAY_MS
            manager.update(current_ticks=tick)

    def test_future_condition_is_retained_until_quest_becomes_active(self):
        manager = QuestManager(appear_delay_ms=0)
        manager.start_new_game(current_ticks=0)
        manager.update(current_ticks=0)
        manager.record_event(QUEST_EVENT_WATER_TANK_PURCHASED, current_ticks=0)
        water_tank_quest = next(
            quest for quest in manager.quests if quest.quest_id == "buy_water_tank"
        )
        self.assertEqual(water_tank_quest.progress, 1)
        self.assertFalse(water_tank_quest.completed)

    def test_field_work_quests_count_distinct_completed_fields(self):
        manager = QuestManager(appear_delay_ms=0)
        manager.start_new_game(current_ticks=0)
        for event_id, quest_id in (
                (QUEST_EVENT_FIELD_WATERED, "water_3_fields"),
                (QUEST_EVENT_FIELD_FERTILIZED, "fertilize_3_fields"),
                (QUEST_EVENT_FIELD_SPRAYED, "spray_3_fields")):
            manager.record_event(event_id, unique_key=(2, 3))
            manager.record_event(event_id, unique_key=(2, 3))
            manager.record_event(event_id, unique_key=(4, 5))
            quest = next(q for q in manager.quests if q.quest_id == quest_id)
            self.assertEqual(quest.progress, 2)
            manager.record_event(event_id, unique_key=(6, 7))
            self.assertEqual(quest.progress, 3)

    def test_alfalfa_progress_counts_distinct_fields(self):
        manager = QuestManager(appear_delay_ms=0)
        manager.start_new_game(current_ticks=0)
        for event_id, quest_id in (
                (QUEST_EVENT_ALFALFA_PLANTED, "plant_3_alfalfa"),
                (QUEST_EVENT_ALFALFA_HARVESTED, "harvest_3_alfalfa")):
            manager.record_event(event_id, unique_key=(1, 1))
            manager.record_event(event_id, unique_key=(1, 1))
            quest = next(q for q in manager.quests if q.quest_id == quest_id)
            self.assertEqual(quest.progress, 1)

    def test_progress_round_trips_by_stable_quest_id(self):
        manager = QuestManager(appear_delay_ms=0)
        manager.start_new_game(current_ticks=0)
        manager.record_event(
            QUEST_EVENT_FIELD_WATERED, unique_key=(2, 3),
        )
        manager.record_event(
            QUEST_EVENT_FIELD_WATERED, unique_key=(4, 5),
        )

        restored = QuestManager(appear_delay_ms=0)
        self.assertTrue(restored.load_save_record(manager.to_save_record(), 10))
        quest = next(
            q for q in restored.quests if q.quest_id == "water_3_fields"
        )
        self.assertEqual(quest.progress, 2)
        self.assertEqual(
            restored.unique_statistics[QUEST_EVENT_FIELD_WATERED],
            {(2, 3), (4, 5)},
        )

    def test_legacy_save_without_quest_record_stays_compatible(self):
        manager = QuestManager(appear_delay_ms=0)
        self.assertFalse(manager.load_save_record(None))
        self.assertFalse(manager.enabled)

    def test_vehicle_purchases_emit_their_specific_quest_events(self):
        world = [[ROAD for _ in range(20)] for _ in range(20)]
        garage = {
            "type": "garage", "row": 5, "col": 5,
            "width": 4, "height": 4,
        }
        manager = VehicleManager()
        events = []
        manager.quest_event_handler = events.append
        economy = Economy(starting_money=100000)
        for vehicle_type in (
                VehicleType.WATER_TANK, VehicleType.TRAILER,
                VehicleType.COMBINE):
            self.assertTrue(manager.purchase_vehicle(
                world, [garage], economy, garage, vehicle_type,
            ))
        self.assertEqual(events, [
            QUEST_EVENT_WATER_TANK_PURCHASED,
            QUEST_EVENT_TRAILER_PURCHASED,
            QUEST_EVENT_COMBINE_PURCHASED,
        ])


if __name__ == "__main__":
    unittest.main()
