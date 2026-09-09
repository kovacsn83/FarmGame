"""Background controller for the online Challenge leaderboard."""

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Lock, Thread

from online_api import OnlineApiClient


@dataclass(frozen=True)
class LeaderboardState:
    status: str = "idle"
    entries: tuple = ()
    message: str = ""


class ChallengeLeaderboardController:
    """Fetches one leaderboard at a time without touching Pygame in workers."""

    def __init__(self, api_client=None):
        self.api_client = api_client or OnlineApiClient()
        self.state = LeaderboardState()
        self._results = Queue()
        self._lock = Lock()
        self._request_id = 0
        self._active_request_id = None

    @property
    def loading(self):
        with self._lock:
            return self._active_request_id is not None

    def request(self):
        with self._lock:
            if self._active_request_id is not None:
                return False
            self._request_id += 1
            request_id = self._request_id
            self._active_request_id = request_id
        self.state = LeaderboardState(
            status="loading", message="Ranglista betöltése...",
        )
        Thread(
            target=self._worker, args=(request_id,), daemon=True,
            name="FarmGameLeaderboard",
        ).start()
        return True

    def _worker(self, request_id):
        self._results.put((
            request_id, self.api_client.get_ten_year_leaderboard(),
        ))

    def update(self):
        try:
            request_id, result = self._results.get_nowait()
        except Empty:
            return False
        with self._lock:
            if request_id != self._active_request_id:
                return False
            self._active_request_id = None

        if result.success and result.status_code == 200:
            entries = tuple(result.data.get("results", ()))
            self.state = LeaderboardState(
                status="success" if entries else "empty",
                entries=entries,
                message=("" if entries else "Még nincs beküldött eredmény."),
            )
            return True

        messages = {
            "connection_error": (
                "A ranglista jelenleg nem érhető el.\n"
                "Ellenőrizd az internetkapcsolatot, majd próbáld újra."
            ),
            "timeout": "A ranglista lekérése túllépte az időkorlátot.",
            "server_error": "A ranglistaszerver jelenleg nem érhető el.",
            "invalid_response": "A ranglistaszerver hibás választ küldött.",
        }
        self.state = LeaderboardState(
            status="error",
            message=messages.get(
                result.error_code,
                "A ranglista betöltése sikertelen. Próbáld újra később.",
            ),
        )
        return True
