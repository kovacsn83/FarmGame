"""Helyi Challenge-eredmények, online kommunikáció nélkül."""

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum

from calendar_utils import get_year_and_week
from game_logger import log
from game_identity import is_valid_game_id, restore_or_generate_game_id
from game_version import get_game_version
from money_format import format_money
from player_profile import get_player_id, get_player_name


TEN_YEAR_CHALLENGE = "ten_year"


class ChallengeStatus(Enum):
    NOT_COMPLETED = "not_completed"
    COMPLETED = "completed"
    LEGACY_INELIGIBLE = "legacy_ineligible"


@dataclass(frozen=True)
class ChallengeResult:
    challenge_type: str
    game_id: str
    farm_value: float
    completed_year: int
    completed_week: int
    game_version: str
    player_id: str
    player_name: str
    completed_at: str


def is_valid_challenge_save_record(record):
    """A hiányzó/None rekord legacy mentésként, nem sérülésként érvényes."""
    if record is None:
        return True
    if not isinstance(record, dict):
        return False
    try:
        status = ChallengeStatus(record.get("status"))
    except (ValueError, TypeError):
        return False
    result = record.get("result")
    if status is not ChallengeStatus.COMPLETED:
        return result is None
    if not isinstance(result, dict):
        return False
    required_types = {
        "challenge_type": str,
        "farm_value": (int, float),
        "completed_year": int,
        "completed_week": int,
        "game_version": str,
        "player_id": str,
        "player_name": str,
        "completed_at": str,
    }
    game_id = result.get("game_id")
    if game_id is not None and not is_valid_game_id(game_id):
        return False
    fields_valid = all(
        isinstance(result.get(key), expected)
        and not isinstance(result.get(key), bool)
        for key, expected in required_types.items()
    ) and (
        result["challenge_type"] == TEN_YEAR_CHALLENGE
        and result["completed_year"] == 10
        and result["completed_week"] == 52
        and math.isfinite(result["farm_value"])
        and bool(result["game_version"])
        and bool(result["player_id"])
        and bool(result["player_name"])
    )
    if not fields_valid:
        return False
    try:
        datetime.fromisoformat(result["completed_at"])
    except ValueError:
        return False
    return True


class ChallengeManager:
    """A konkrét farm egyszeri Challenge-snapshotját kezeli."""

    def __init__(
            self, player_profile, notification_manager=None,
            result_store=None):
        self.player_profile = player_profile
        self.notification_manager = notification_manager
        self.result_store = result_store
        self.status = ChallengeStatus.NOT_COMPLETED
        self.result = None

    def handle_week_transition(
            self, previous_elapsed_week, new_elapsed_week, game_state):
        """A 10/52 -> 11/1 határon, az új hét eseményei előtt rögzít."""
        if self.status is not ChallengeStatus.NOT_COMPLETED:
            return None
        if (
            get_year_and_week(previous_elapsed_week) != (10, 52)
            or get_year_and_week(new_elapsed_week) != (11, 1)
        ):
            return None
        game_state.game_id, generated = restore_or_generate_game_id(
            getattr(game_state, "game_id", None),
        )
        if generated:
            log("GameState assigned a new game_id at Challenge completion.",
                "Game", level="WARNING")
        farm_value = game_state.economy.calculate_net_farm_value(game_state)
        self.result = ChallengeResult(
            challenge_type=TEN_YEAR_CHALLENGE,
            game_id=game_state.game_id,
            farm_value=farm_value,
            completed_year=10,
            completed_week=52,
            game_version=get_game_version(),
            player_id=get_player_id(self.player_profile),
            player_name=get_player_name(self.player_profile),
            completed_at=datetime.now(timezone.utc).astimezone().isoformat(
                timespec="seconds"
            ),
        )
        self.status = ChallengeStatus.COMPLETED
        if self.result_store is not None:
            self.result_store.save_snapshot(self.result)
        message = (
            "10 éves Challenge teljesítve! Gazdaság értéke: "
            f"{format_money(farm_value)}"
        )
        if self.notification_manager is not None:
            self.notification_manager.enqueue(
                message, event_id=(TEN_YEAR_CHALLENGE, "completed"),
            )
        log(
            f"10-year challenge completed. Farm Value: {format_money(farm_value)}",
            "Challenge",
        )
        return self.result

    def to_save_record(self):
        return {
            "status": self.status.value,
            "result": asdict(self.result) if self.result is not None else None,
        }

    def load_save_record(self, record, elapsed_weeks, game_id=None):
        """Régi 11. év feletti farmhoz nem talál ki utólagos eredményt."""
        if record is None:
            if get_year_and_week(elapsed_weeks) >= (11, 1):
                self.status = ChallengeStatus.LEGACY_INELIGIBLE
                self.result = None
                log(
                    "Legacy save is already past the 10-year snapshot point; "
                    "challenge result unavailable.",
                    "Challenge",
                )
            else:
                self.status = ChallengeStatus.NOT_COMPLETED
                self.result = None
            return
        if not is_valid_challenge_save_record(record):
            raise ValueError("Érvénytelen Challenge mentési rekord.")
        self.status = ChallengeStatus(record["status"])
        result = record.get("result")
        if result is not None:
            result = dict(result)
            # A game_id előtti Challenge-mentések ugyanazt a migrált farm-ID-t kapják.
            result["game_id"] = game_id
            self.result = ChallengeResult(**result)
            # Egy korábbi, hiteles snapshotból biztonságosan pótolható a
            # hiányzó helyi rekord. Aktuális Farm Value újraszámítás nincs.
            if self.result_store is not None:
                self.result_store.save_snapshot(self.result)
        else:
            self.result = None
