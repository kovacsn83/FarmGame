from dataclasses import dataclass
from enum import Enum

import pygame

from game_logger import log
from financial_history import INCOME_QUEST_REWARD
from money_format import format_money


QUEST_APPEAR_DELAY_MS = 2000
QUEST_COMPLETED_DISPLAY_MS = 2000
QUEST_NEXT_APPEAR_DELAY_MS = 2000
QUEST_DEFAULT_REWARD = 100

QUEST_EVENT_ROAD_BUILT = "road_built"
QUEST_EVENT_FARMHOUSE_BUILT = "farmhouse_built"
QUEST_EVENT_WAREHOUSE_BUILT = "warehouse_built"
QUEST_EVENT_ANIMAL_PEN_BUILT = "animal_pen_built"
QUEST_EVENT_CATTLE_COUNT_CHANGED = "cattle_count_changed"
QUEST_EVENT_FIELD_COUNT_CHANGED = "field_count_changed"
QUEST_EVENT_WHEAT_PLANTED = "wheat_planted"
QUEST_EVENT_ALFALFA_PLANTED = "alfalfa_planted"
QUEST_EVENT_WHEAT_HARVESTED = "wheat_harvested"
QUEST_EVENT_TOMATO_HARVESTED = "tomato_harvested"
QUEST_EVENT_ALFALFA_HARVESTED = "alfalfa_harvested"
QUEST_EVENT_CROP_HARVESTED = "crop_harvested"
QUEST_EVENT_MARKET_BUILT = "market_built"
QUEST_EVENT_PRODUCT_SOLD = "product_sold"
QUEST_EVENT_MILK_SOLD = "milk_sold"
QUEST_EVENT_TIME_PAUSED_BY_KEY = "time_paused_by_key"
QUEST_EVENT_TIME_STARTED_BY_KEY = "time_started_by_key"
QUEST_EVENT_CALENDAR_OPENED = "calendar_opened"
QUEST_EVENT_GARAGE_BUILT = "garage_built"
QUEST_EVENT_COMBINE_PURCHASED = "combine_purchased"
QUEST_EVENT_WATER_TANK_PURCHASED = "water_tank_purchased"
QUEST_EVENT_TRAILER_PURCHASED = "trailer_purchased"
QUEST_EVENT_POND_BUILT = "pond_built"
QUEST_EVENT_FOOD_TROUGH_FILLED = "food_trough_filled"
QUEST_EVENT_WATER_TROUGH_FILLED = "water_trough_filled"
QUEST_EVENT_FIELD_DEMOLISHED = "field_demolished"
QUEST_EVENT_FIELD_WATERED = "field_watered"
QUEST_EVENT_FIELD_FERTILIZED = "field_fertilized"
QUEST_EVENT_FIELD_SPRAYED = "field_sprayed"


class QuestState(Enum):
    """A küldetések megjelenítési és teljesítési állapotai."""

    ACTIVE = "active"
    COMPLETED = "completed"
    HIDDEN = "hidden"


@dataclass
class Quest:
    """Egy adatvezérelt, később jutalommal is bővíthető küldetés."""

    quest_id: str
    title: str
    event_id: str | None = None
    target: int | None = None
    active_only: bool = False
    required_events: tuple[str, ...] = ()
    progress: int = 0
    state: QuestState = QuestState.HIDDEN
    completed: bool = False
    completed_at: int | None = None
    unique_progress: bool = False
    reward: float = QUEST_DEFAULT_REWARD
    reward_granted: bool = False

    def reset(self):
        self.progress = 0
        self.state = QuestState.HIDDEN
        self.completed = False
        self.completed_at = None
        self.reward_granted = False


class QuestManager:
    """A küldetések sorrendjét, állapotát és időzített váltását kezeli."""

    def __init__(self, economy=None, appear_delay_ms=QUEST_APPEAR_DELAY_MS):
        self.economy = economy
        self.appear_delay_ms = appear_delay_ms
        self.quests = [
            Quest(
                "build_5_roads", "Építs 5 utat",
                QUEST_EVENT_ROAD_BUILT, 5,
            ),
            Quest(
                "build_farmhouse",
                "Építsd meg a Farmházat",
                QUEST_EVENT_FARMHOUSE_BUILT,
                1,
            ),
            Quest(
                "build_garage",
                "Építs egy Garázst",
                QUEST_EVENT_GARAGE_BUILT,
                1,
            ),
            Quest(
                "buy_water_tank",
                "Vegyél 1 locsolótartályt a garázsban",
                QUEST_EVENT_WATER_TANK_PURCHASED,
                1,
            ),
            Quest(
                "buy_trailer",
                "Vegyél 1 pótkocsit a garázsban",
                QUEST_EVENT_TRAILER_PURCHASED,
                1,
            ),
            Quest(
                "build_warehouse",
                "Építs egy Raktárat",
                QUEST_EVENT_WAREHOUSE_BUILT,
                1,
            ),
            Quest(
                "pause_time",
                "Állítsd meg az időt a 0-ás billentyűvel",
                QUEST_EVENT_TIME_PAUSED_BY_KEY,
                1,
                active_only=True,
            ),
            Quest(
                "build_animal_pen",
                "Építs egy Karámot",
                QUEST_EVENT_ANIMAL_PEN_BUILT,
                1,
            ),
            Quest(
                "own_2_cattle",
                "Vegyél 2 szarvasmarhát",
                QUEST_EVENT_CATTLE_COUNT_CHANGED,
                2,
            ),
            Quest(
                "build_pond",
                "Építs egy Tavat",
                QUEST_EVENT_POND_BUILT,
                1,
            ),
            Quest(
                "build_market",
                "Építsd meg a Piacot",
                QUEST_EVENT_MARKET_BUILT,
                1,
            ),
            Quest(
                "start_time",
                "Indítsd újra az időt az 1-es billentyűvel",
                QUEST_EVENT_TIME_STARTED_BY_KEY,
                1,
                active_only=True,
            ),
            Quest(
                "fill_animal_troughs",
                "Adj ivóvizet és eledelt a Karám vályúiba",
                target=2,
                required_events=(
                    QUEST_EVENT_FOOD_TROUGH_FILLED,
                    QUEST_EVENT_WATER_TROUGH_FILLED,
                ),
            ),
            Quest(
                "sell_milk",
                "Add el a tejet a Piacon",
                QUEST_EVENT_MILK_SOLD,
                1,
            ),
            Quest(
                "own_3_fields",
                "Legyen 3 Veteményesed",
                QUEST_EVENT_FIELD_COUNT_CHANGED,
                3,
            ),
            Quest(
                "open_calendar",
                "Nyisd meg a Gazdálkodási naptárat",
                QUEST_EVENT_CALENDAR_OPENED,
                1,
            ),
            Quest(
                "plant_3_alfalfa",
                "Ültess 3 lucernát",
                QUEST_EVENT_ALFALFA_PLANTED,
                3,
                unique_progress=True,
            ),
            Quest(
                "water_3_fields",
                "Locsolj meg 3 veteményest",
                QUEST_EVENT_FIELD_WATERED,
                3,
                unique_progress=True,
            ),
            Quest(
                "fertilize_3_fields",
                "Trágyázz be 3 veteményest",
                QUEST_EVENT_FIELD_FERTILIZED,
                3,
                unique_progress=True,
            ),
            Quest(
                "spray_3_fields",
                "Permetezz be 3 veteményest",
                QUEST_EVENT_FIELD_SPRAYED,
                3,
                unique_progress=True,
            ),
            Quest(
                "buy_combine",
                "Vegyél 1 kombájnt",
                QUEST_EVENT_COMBINE_PURCHASED,
                1,
            ),
            Quest(
                "harvest_3_alfalfa",
                "Arass 3 lucernát",
                QUEST_EVENT_ALFALFA_HARVESTED,
                3,
                unique_progress=True,
            ),
        ]
        self.statistics = {}
        self.unique_statistics = {}
        self.current_quest_index = 0
        self.next_appearance_at = None
        self.enabled = False

    @property
    def current_quest(self):
        if not self.enabled or self.current_quest_index >= len(self.quests):
            return None
        return self.quests[self.current_quest_index]

    @property
    def visible(self):
        quest = self.current_quest
        return quest is not None and quest.state in (
            QuestState.ACTIVE, QuestState.COMPLETED,
        )

    def start_new_game(self, current_ticks=None):
        """Új játékhoz alaphelyzetbe állítja a teljes küldetéssort."""
        now = self._get_ticks(current_ticks)
        for quest in self.quests:
            quest.reset()
        self.statistics.clear()
        self.unique_statistics.clear()
        self.current_quest_index = 0
        self.next_appearance_at = now + self.appear_delay_ms
        self.enabled = True

    def hide(self):
        """Betöltött játékban elrejti a még nem mentett Quest rendszert."""
        self.next_appearance_at = None
        self.enabled = False

    def to_save_record(self):
        """Stabil Quest ID-k alapján JSON-kompatibilis állapotot készít."""
        return {
            "enabled": self.enabled,
            "current_quest_id": (
                self.current_quest.quest_id if self.current_quest else None
            ),
            "quests": {
                quest.quest_id: {
                    "progress": quest.progress,
                    "completed": quest.completed,
                }
                for quest in self.quests
            },
            "statistics": dict(self.statistics),
            "unique_statistics": {
                event_id: [list(key) if isinstance(key, tuple) else key
                           for key in keys]
                for event_id, keys in self.unique_statistics.items()
            },
        }

    def load_save_record(self, record, current_ticks=None):
        """ID alapján tölt, a korábban teljesített Questeket nem játssza vissza."""
        if not isinstance(record, dict) or not record.get("enabled", False):
            self.hide()
            return False
        saved_quests = record.get("quests", {})
        if not isinstance(saved_quests, dict):
            self.hide()
            return False
        for quest in self.quests:
            quest.reset()
            saved = saved_quests.get(quest.quest_id, {})
            if not isinstance(saved, dict):
                continue
            progress = saved.get("progress", 0)
            if isinstance(progress, int) and not isinstance(progress, bool):
                quest.progress = min(max(0, progress), quest.target or 0)
            quest.completed = saved.get("completed") is True

        # A sorrend változhat két verzió között (például új Quest kerülhet egy
        # régi aktuális feladat elé). Ezért nem a mentett aktuális azonosítót
        # jelenítjük meg újra, hanem mindig az első befejezetlen Questet.
        self.current_quest_index = self._first_incomplete_index()
        self.statistics = {
            key: value for key, value in record.get("statistics", {}).items()
            if isinstance(key, str) and isinstance(value, int)
            and not isinstance(value, bool) and value >= 0
        } if isinstance(record.get("statistics"), dict) else {}
        self.unique_statistics = {}
        unique_record = record.get("unique_statistics", {})
        if isinstance(unique_record, dict):
            for event_id, values in unique_record.items():
                if isinstance(event_id, str) and isinstance(values, list):
                    self.unique_statistics[event_id] = {
                        tuple(value) if isinstance(value, list) else value
                        for value in values
                    }
        self.enabled = True
        self.next_appearance_at = None
        quest = self.current_quest
        if quest is not None:
            quest.state = QuestState.ACTIVE
        return True

    def record_event(
            self, event_id, amount=1, current_ticks=None, current_value=None,
            unique_key=None):
        """Az eseményhez tartozó, még nem teljesített küldetések haladását rögzíti."""
        if not self.enabled:
            return False

        matching_quests = [
            quest for quest in self.quests
            if (
                not quest.completed
                and (
                    quest.event_id == event_id
                    or event_id in quest.required_events
                )
                and quest.target is not None
                and (
                    not quest.active_only
                    or (
                        quest is self.current_quest
                        and quest.state == QuestState.ACTIVE
                    )
                )
            )
        ]
        # A statisztikai események Quest nélkül is gyűlnek, így egy későbbi
        # küldetés ugyanazt az eseményfolyamot használhatja.
        statistic_only = event_id in {
            QUEST_EVENT_CROP_HARVESTED,
            QUEST_EVENT_TOMATO_HARVESTED,
            QUEST_EVENT_ALFALFA_HARVESTED,
        }
        if not matching_quests and not statistic_only:
            return False

        unique_events = self.unique_statistics.setdefault(event_id, set())
        if unique_key is not None:
            unique_events.add(unique_key)

        if current_value is None:
            self.statistics[event_id] = (
                self.statistics.get(event_id, 0) + amount
            )
        else:
            self.statistics[event_id] = max(0, current_value)

        event_recorded = statistic_only
        for quest in matching_quests:
            if quest.required_events:
                quest.progress = sum(
                    self.statistics.get(required_event, 0) > 0
                    for required_event in quest.required_events
                )
            else:
                quest.progress = min(
                    quest.target,
                    len(unique_events)
                    if quest.unique_progress else self.statistics[event_id],
                )
            event_recorded = True
            if (
                quest is self.current_quest
                and quest.progress >= quest.target
                and quest.state == QuestState.ACTIVE
            ):
                self._complete_current_quest(self._get_ticks(current_ticks))

        return event_recorded

    def update(self, current_ticks=None):
        """Frissíti az aktív küldetés időzített állapotváltásait."""
        if not self.enabled:
            return False

        now = self._get_ticks(current_ticks)
        quest = self.current_quest
        if quest is None:
            return False

        if (
            quest.state == QuestState.HIDDEN
            and not quest.completed
            and self.next_appearance_at is not None
            and now >= self.next_appearance_at
        ):
            quest.state = QuestState.ACTIVE
            self.next_appearance_at = None
            if quest.target is not None and quest.progress >= quest.target:
                self._complete_current_quest(now)

        elif (
            quest.state == QuestState.COMPLETED
            and quest.completed_at is not None
            and now - quest.completed_at >= QUEST_COMPLETED_DISPLAY_MS
        ):
            quest.state = QuestState.HIDDEN
            self.current_quest_index = self._first_incomplete_index(
                self.current_quest_index + 1,
            )
            self.next_appearance_at = now + QUEST_NEXT_APPEAR_DELAY_MS

        return self.visible

    def _first_incomplete_index(self, start=0):
        """Visszaadja a sorrend következő, még nem teljesített Questjét."""
        return next(
            (index for index in range(start, len(self.quests))
             if not self.quests[index].completed),
            len(self.quests),
        )

    def _complete_current_quest(self, current_ticks):
        quest = self.current_quest
        if quest is None or quest.completed:
            return
        quest.completed = True
        quest.state = QuestState.COMPLETED
        quest.completed_at = current_ticks
        if self.economy is not None and quest.reward > 0:
            quest.reward_granted = self.economy.credit_income(
                INCOME_QUEST_REWARD,
                quest.reward,
                description=quest.title,
            )
        reward_text = (
            f". Jutalom: {format_money(quest.reward)}"
            if quest.reward_granted else ""
        )
        log(f"Quest teljesítve: {quest.title}{reward_text}", "Quest")

    @staticmethod
    def _get_ticks(current_ticks):
        return pygame.time.get_ticks() if current_ticks is None else current_ticks
