"""Small, offline-safe HTTP client for FarmGame online services."""

import os
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Callable

import requests

from game_logger import log
from game_version import get_game_version


DEFAULT_API_BASE_URL = "https://farmgame-production.up.railway.app"
API_BASE_URL_ENV = "FARMGAME_API_BASE_URL"
DEFAULT_TIMEOUT = (3.0, 5.0)
TEN_YEAR_LEADERBOARD_PATH = "/api/v1/challenges/ten-year/leaderboard"
TEN_YEAR_SUBMIT_PATH = "/api/v1/challenges/ten-year/submit"
SUBMISSION_FIELDS = (
    "player_id",
    "player_name",
    "game_id",
    "game_version",
    "farm_value",
    "challenge_years",
    "completed_at",
)


@dataclass(frozen=True)
class ApiResult:
    success: bool
    status_code: int | None = None
    data: Any = None
    error_code: str | None = None
    error_message: str | None = None


def get_api_base_url():
    """Return the environment override or the public production endpoint."""
    value = os.environ.get(API_BASE_URL_ENV, DEFAULT_API_BASE_URL).strip()
    return (value or DEFAULT_API_BASE_URL).rstrip("/")


def _error_message(data, fallback):
    if isinstance(data, dict):
        detail = data.get("detail") or data.get("message") or data.get("error")
        if isinstance(detail, dict):
            detail = detail.get("message") or detail.get("detail")
        if isinstance(detail, str):
            return detail
        if detail is not None:
            return str(detail)
    return fallback


def _valid_leaderboard_entry(entry):
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("rank"), int)
        and not isinstance(entry.get("rank"), bool)
        and isinstance(entry.get("player_name"), str)
        and bool(entry["player_name"].strip())
        and isinstance(entry.get("farm_value"), (int, float))
        and not isinstance(entry.get("farm_value"), bool)
        and isinstance(entry.get("game_version"), str)
        and bool(entry["game_version"])
    )


class OnlineApiClient:
    """Stateless request wrapper suitable for synchronous or worker use."""

    def __init__(
        self,
        base_url=None,
        timeout=DEFAULT_TIMEOUT,
        request: Callable[..., Any] | None = None,
    ):
        self.base_url = (base_url or get_api_base_url()).rstrip("/")
        self.timeout = timeout
        self._request = request or requests.request

    @property
    def headers(self):
        return {
            "Accept": "application/json",
            "User-Agent": f"FarmGame/{get_game_version()}",
        }

    def _call(self, method, path, *, payload=None):
        try:
            response = self._request(
                method,
                f"{self.base_url}{path}",
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as error:
            log("Online API request timed out.", "OnlineAPI", level="ERROR")
            return ApiResult(False, error_code="timeout", error_message=str(error))
        except requests.exceptions.ConnectionError as error:
            log("Online API connection failed.", "OnlineAPI", level="ERROR")
            return ApiResult(
                False, error_code="connection_error", error_message=str(error)
            )
        except requests.exceptions.RequestException as error:
            log("Online API request failed.", "OnlineAPI", level="ERROR")
            return ApiResult(
                False, error_code="request_error", error_message=str(error)
            )

        try:
            data = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            log("Online API returned invalid JSON.", "OnlineAPI", level="ERROR")
            return ApiResult(
                False,
                status_code=response.status_code,
                error_code="invalid_response",
                error_message="The server returned invalid JSON.",
            )

        status = response.status_code
        if status == 409:
            return ApiResult(
                False,
                status_code=status,
                data=data,
                error_code="already_submitted",
                error_message=_error_message(data, "Result already submitted."),
            )
        if 400 <= status < 500:
            return ApiResult(
                False,
                status_code=status,
                data=data,
                error_code="validation_error",
                error_message=_error_message(data, "The request was rejected."),
            )
        if status >= 500:
            return ApiResult(
                False,
                status_code=status,
                data=data,
                error_code="server_error",
                error_message=_error_message(data, "The server failed."),
            )
        return ApiResult(True, status_code=status, data=data)

    def check_health(self):
        result = self._call("GET", "/health")
        if result.success and result.status_code == 200:
            log("Health check successful.", "OnlineAPI")
            return result
        if result.success:
            return ApiResult(
                False,
                status_code=result.status_code,
                data=result.data,
                error_code="unexpected_status",
                error_message="Unexpected health-check status.",
            )
        return result

    def get_ten_year_leaderboard(self):
        result = self._call("GET", TEN_YEAR_LEADERBOARD_PATH)
        if not result.success:
            return result
        if result.status_code != 200 or not isinstance(result.data, dict):
            return ApiResult(
                False,
                status_code=result.status_code,
                data=result.data,
                error_code="invalid_response",
                error_message="Invalid leaderboard response.",
            )
        entries = result.data.get("results")
        if not isinstance(entries, list):
            return ApiResult(
                False,
                status_code=result.status_code,
                data=result.data,
                error_code="invalid_response",
                error_message="Leaderboard results are missing.",
            )
        clean_data = dict(result.data)
        clean_data["results"] = [
            entry for entry in entries if _valid_leaderboard_entry(entry)
        ]
        log("Leaderboard loaded.", "OnlineAPI")
        return ApiResult(True, status_code=200, data=clean_data)

    def submit_ten_year_result(self, result):
        if is_dataclass(result) and not isinstance(result, type):
            source = asdict(result)
        elif isinstance(result, dict):
            source = result
        else:
            return ApiResult(
                False,
                error_code="invalid_request",
                error_message="Challenge result must be a record or mapping.",
            )
        try:
            payload = {field: source[field] for field in SUBMISSION_FIELDS}
        except KeyError as error:
            return ApiResult(
                False,
                error_code="invalid_request",
                error_message=f"Missing Challenge field: {error.args[0]}",
            )
        response = self._call("POST", TEN_YEAR_SUBMIT_PATH, payload=payload)
        if response.success and response.status_code == 201:
            log("Challenge result submitted.", "OnlineAPI")
            return response
        if response.success:
            return ApiResult(
                False,
                status_code=response.status_code,
                data=response.data,
                error_code="unexpected_status",
                error_message="Unexpected submission status.",
            )
        return response


def check_api_health():
    return OnlineApiClient().check_health()


def get_ten_year_leaderboard():
    return OnlineApiClient().get_ten_year_leaderboard()


def submit_ten_year_result(result):
    return OnlineApiClient().submit_ten_year_result(result)
