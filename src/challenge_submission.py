"""Shared, main-thread-safe controller for Challenge score submission."""

from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Lock, Thread

from challenge_results import SubmissionStatus
from game_logger import log
from online_api import OnlineApiClient


@dataclass(frozen=True)
class SubmissionFeedback:
    state: str
    message: str
    rank: int | None = None


class ChallengeSubmissionController:
    """Runs HTTP away from Pygame and applies results on the main thread."""

    def __init__(self, result_store, api_client=None):
        self.result_store = result_store
        self.api_client = api_client or OnlineApiClient()
        self.feedback = SubmissionFeedback("idle", "")
        self._results = Queue()
        self._lock = Lock()
        self._active_key = None

    @property
    def submitting(self):
        with self._lock:
            return self._active_key is not None

    def get_record(self, game_id, challenge_years=10):
        if not game_id:
            return None
        return self.result_store.find(game_id, challenge_years)

    def request_for_game(self, game_id, challenge_years=10):
        record = self.get_record(game_id, challenge_years)
        if record is None:
            log("No valid local Challenge result to submit.", "Challenge",
                level="ERROR")
            self.feedback = SubmissionFeedback(
                "failed", "Nincs beküldhető helyi Challenge-eredmény.",
            )
            return False
        return self.request(record)

    def request(self, record):
        key = (record.game_id, record.challenge_years)
        if record.submission_status == SubmissionStatus.SUBMITTED.value:
            self.feedback = SubmissionFeedback(
                "submitted", "Ez az eredmény már szerepel a ranglistán.",
            )
            return False
        with self._lock:
            if self._active_key is not None:
                return False
            self._active_key = key
        self.feedback = SubmissionFeedback("submitting", "Beküldés...")
        Thread(
            target=self._submit_worker, args=(key, record), daemon=True,
            name="FarmGameChallengeSubmit",
        ).start()
        return True

    def _submit_worker(self, key, record):
        result = self.api_client.submit_ten_year_result(record)
        self._results.put((key, result))

    def update(self):
        """Poll on the Pygame thread; never mutates UI from the worker."""
        try:
            key, result = self._results.get_nowait()
        except Empty:
            return False
        with self._lock:
            if key != self._active_key:
                return False
            self._active_key = None

        game_id, challenge_years = key
        if result.success and result.status_code == 201:
            data = result.data if isinstance(result.data, dict) else {}
            result_id = data.get("result_id")
            if isinstance(result_id, bool) or not isinstance(result_id, int):
                result_id = None
            rank = data.get("rank")
            if isinstance(rank, bool) or not isinstance(rank, int):
                rank = None
            saved = self.result_store.update_submission(
                game_id, challenge_years, SubmissionStatus.SUBMITTED,
                submitted_at=datetime.now(timezone.utc).astimezone().isoformat(
                    timespec="seconds"
                ),
                server_result_id=result_id,
            )
            if saved:
                message = "Az eredmény sikeresen felkerült a ranglistára!"
                if rank is not None:
                    message += f" Jelenlegi helyezés: {rank}."
                self.feedback = SubmissionFeedback("submitted", message, rank)
                return True
            self.feedback = SubmissionFeedback(
                "failed", "A beküldés sikerült, de a helyi állapot nem menthető.",
            )
            return True

        if result.error_code == "already_submitted":
            saved = self.result_store.update_submission(
                game_id, challenge_years, SubmissionStatus.SUBMITTED,
                submitted_at=datetime.now(timezone.utc).astimezone().isoformat(
                    timespec="seconds"
                ),
            )
            self.feedback = SubmissionFeedback(
                "submitted" if saved else "failed",
                ("Ez az eredmény már szerepel a ranglistán." if saved else
                 "A szerver ismeri az eredményt, de a helyi állapot nem menthető."),
            )
            return True

        self.result_store.update_submission(
            game_id, challenge_years, SubmissionStatus.FAILED,
        )
        if result.error_code in ("timeout", "connection_error"):
            message = (
                "A ranglista jelenleg nem érhető el. Később újra próbálhatod."
            )
        elif result.error_code == "server_error":
            message = "A ranglista szerverhibát jelzett. Próbáld újra később."
        else:
            message = "Az eredmény beküldése sikertelen. Később újra próbálhatod."
        self.feedback = SubmissionFeedback("failed", message)
        return True
