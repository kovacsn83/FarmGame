from collections import deque
from dataclasses import dataclass
from datetime import datetime


MAX_LOG_ENTRIES = 100
LOG_CATEGORIES = frozenset({
    "General", "System", "Vehicle", "Dispatcher", "Planting",
    "Fertilizing", "Harvest", "Economy", "Inventory", "Animals",
    "Quest", "Save", "Load", "Time", "Building", "Watering", "Supply",
    "Market", "Bank", "Road", "Automation", "Orchard", "Processing",
})


@dataclass(frozen=True)
class LogEntry:
    """Egyetlen, UI-tól független játékbeli naplóbejegyzés."""

    timestamp: str
    category: str
    message: str
    level: str = "INFO"

    def format(self):
        return f"[{self.timestamp}] [{self.category}] {self.message}"


class GameLogger:
    """Központi, korlátozott előzményű játéklogger."""

    def __init__(self, max_entries=MAX_LOG_ENTRIES, echo_to_terminal=True):
        self.entries = deque(maxlen=max_entries)
        self.echo_to_terminal = echo_to_terminal
        self.timestamp_provider = None
        self.revision = 0

    def set_timestamp_provider(self, provider):
        """Függőség nélkül kapcsolható hozzá a játékbeli idő formázója."""
        self.timestamp_provider = provider

    def reset(self):
        self.entries.clear()
        self.revision += 1

    def log(self, message, category="General", timestamp=None, level="INFO"):
        normalized_category = (
            category if category in LOG_CATEGORIES else "General"
        )
        if timestamp is None and self.timestamp_provider is not None:
            timestamp = self.timestamp_provider()
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        entry = LogEntry(
            str(timestamp), normalized_category, str(message), str(level),
        )
        self.entries.append(entry)
        self.revision += 1
        if self.echo_to_terminal:
            print(entry.format())
        return entry


_LOGGER = GameLogger()


def get_logger():
    return _LOGGER


def log(message, category="General", timestamp=None, level="INFO"):
    """Kényelmi belépési pont a közös loggerhez."""
    return _LOGGER.log(message, category, timestamp, level)
