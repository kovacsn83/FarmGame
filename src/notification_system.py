"""A játékosnak szóló, ideiglenes Farm Hírközpont üzenetei."""

from collections import deque
from dataclasses import dataclass

from calendar_utils import get_year_and_week
from crops import CROPS, get_crop_week_intervals


NOTIFICATION_DURATION_MS = 10_000


@dataclass(frozen=True)
class Notification:
    """Egy később más játékrendszerekből is létrehozható nyilvános üzenet."""

    message: str
    event_id: object = None


class NotificationManager:
    """FIFO sorrendben, futó játékidő alapján jeleníti meg az üzeneteket."""

    def __init__(self, duration_ms=NOTIFICATION_DURATION_MS, start_ticks=0):
        self.duration_ms = max(1, int(duration_ms))
        self.queue = deque()
        self.current = None
        self.remaining_ms = 0
        self.last_update_ticks = int(start_ticks)
        self.processed_event_ids = set()

    @property
    def current_message(self):
        return self.current.message if self.current is not None else None

    def reset(self, current_ticks=0):
        """Új játék és betöltés után eldobja a nem mentett értesítéseket."""
        self.queue.clear()
        self.current = None
        self.remaining_ms = 0
        self.last_update_ticks = int(current_ticks)
        self.processed_event_ids.clear()

    def enqueue(self, message, event_id=None):
        """Új üzenetet ad a sorhoz; azonos eseményazonosítót csak egyszer fogad el."""
        if not message:
            return False
        if event_id is not None:
            if event_id in self.processed_event_ids:
                return False
            self.processed_event_ids.add(event_id)
        notification = Notification(str(message), event_id)
        if self.current is None:
            self.current = notification
            self.remaining_ms = self.duration_ms
        else:
            self.queue.append(notification)
        return True

    def update(self, current_ticks, time_running=True):
        """Valós időt fogyaszt, de szünetben nem csökkenti a láthatósági időt."""
        current_ticks = int(current_ticks)
        elapsed_ms = max(0, current_ticks - self.last_update_ticks)
        self.last_update_ticks = current_ticks
        if not time_running or self.current is None:
            return False

        self.remaining_ms -= elapsed_ms
        if self.remaining_ms > 0:
            return False
        self.current = self.queue.popleft() if self.queue else None
        self.remaining_ms = self.duration_ms if self.current is not None else 0
        return True

    def process_week(self, elapsed_weeks):
        """A növényadatokból létrehozza az adott héten kezdődő szezonüzeneteket."""
        year, week = get_year_and_week(elapsed_weeks)
        added = 0
        for crop_id, crop in CROPS.items():
            for event_type, interval_name in (
                ("planting", "planting_weeks"),
                ("harvest", "harvest_weeks"),
            ):
                intervals = get_crop_week_intervals(crop, interval_name) or ()
                for interval_index, (start_week, _end_week) in enumerate(intervals):
                    if week != start_week:
                        continue
                    event_id = (
                        year, crop_id, event_type, interval_index, start_week,
                    )
                    if self.enqueue(
                        _season_notification_message(crop_id, crop, event_type),
                        event_id,
                    ):
                        added += 1
        return added


def _season_notification_message(crop_id, crop, event_type):
    crop_name = crop["name"].lower()
    if event_type == "planting":
        return f"Elkezdődött a {crop_name} vetési időszaka."
    if crop_id == "tomato":
        return "Elkezdődött a paradicsom első szedési időszaka."
    return f"Elkezdődött a {crop_name} aratási időszaka."
