"""Persistent, upload-ready local Challenge results without networking."""

import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime

from game_identity import is_valid_game_id
from game_logger import log
from user_data import get_challenge_results_path


RESULTS_FORMAT_VERSION = 1
TEN_YEAR_CHALLENGE_YEARS = 10


@dataclass(frozen=True)
class LocalChallengeResult:
    player_id: str
    player_name: str
    game_id: str
    game_version: str
    farm_value: float
    challenge_years: int
    completed_at: str


def _is_valid_result(record):
    if not isinstance(record, dict):
        return False
    required_types = {
        "player_id": str,
        "player_name": str,
        "game_id": str,
        "game_version": str,
        "farm_value": (int, float),
        "challenge_years": int,
        "completed_at": str,
    }
    if not all(
        isinstance(record.get(key), expected)
        and not isinstance(record.get(key), bool)
        for key, expected in required_types.items()
    ):
        return False
    if not (
        record["player_id"] and record["player_name"]
        and is_valid_game_id(record["game_id"])
        and record["game_version"] and record["challenge_years"] > 0
        and math.isfinite(record["farm_value"])
    ):
        return False
    try:
        datetime.fromisoformat(record["completed_at"])
    except ValueError:
        return False
    return True


class ChallengeResultStore:
    """Atomically stores one result per game and Challenge duration."""

    def __init__(self, path=None):
        self.path = path

    def _path(self):
        return self.path or get_challenge_results_path()

    def load(self):
        path = self._path()
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as result_file:
                document = json.load(result_file)
            if not isinstance(document, dict):
                raise ValueError("the root is not an object")
            if document.get("format_version") != RESULTS_FORMAT_VERSION:
                raise ValueError("unsupported format version")
            records = document.get("results")
            if not isinstance(records, list) or not all(
                    _is_valid_result(record) for record in records):
                raise ValueError("invalid result record")
            keys = {
                (record["game_id"], record["challenge_years"])
                for record in records
            }
            if len(keys) != len(records):
                raise ValueError("duplicate result key")
            return [LocalChallengeResult(**record) for record in records]
        except (OSError, json.JSONDecodeError, ValueError) as error:
            log(
                f"Local Challenge results could not be loaded: {error}",
                "Challenge", level="ERROR",
            )
            return None

    def _write(self, results):
        path = self._path()
        temporary_path = path.with_name(f".{path.name}.tmp")
        document = {
            "format_version": RESULTS_FORMAT_VERSION,
            "results": [asdict(result) for result in results],
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with temporary_path.open(
                    "w", encoding="utf-8", newline="\n") as result_file:
                json.dump(document, result_file, ensure_ascii=False, indent=4)
                result_file.write("\n")
                result_file.flush()
                os.fsync(result_file.fileno())
            os.replace(temporary_path, path)
            return True
        except OSError as error:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            log(
                f"Local Challenge result could not be saved: {error}",
                "Challenge", level="ERROR",
            )
            return False

    def save_snapshot(self, snapshot):
        """Persist a trusted completed snapshot; never recompute its value."""
        if snapshot is None:
            return False
        result = LocalChallengeResult(
            player_id=snapshot.player_id,
            player_name=snapshot.player_name,
            game_id=snapshot.game_id,
            game_version=snapshot.game_version,
            farm_value=snapshot.farm_value,
            challenge_years=TEN_YEAR_CHALLENGE_YEARS,
            completed_at=snapshot.completed_at,
        )
        if not _is_valid_result(asdict(result)):
            log("Invalid Challenge snapshot was not persisted.", "Challenge",
                level="ERROR")
            return False
        results = self.load()
        if results is None:
            return False
        key = (result.game_id, result.challenge_years)
        if any((item.game_id, item.challenge_years) == key for item in results):
            return True
        if not self._write([*results, result]):
            return False
        log(
            f"Local Challenge result saved for game_id={result.game_id}.",
            "Challenge",
        )
        return True

    def find(self, game_id, challenge_years=TEN_YEAR_CHALLENGE_YEARS):
        results = self.load()
        if results is None:
            return None
        return next((
            result for result in results
            if result.game_id == game_id
            and result.challenge_years == challenge_years
        ), None)
