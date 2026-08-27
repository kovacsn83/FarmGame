"""A játékosnak szóló, ideiglenes Farm Hírközpont üzenetei."""

from collections import deque
from dataclasses import dataclass

from calendar_utils import get_year_and_week
from crops import CROPS, get_crop_week_intervals


NOTIFICATION_DURATION_MS = 10_000
MAX_ACTIVE_NOTIFICATIONS = 3


@dataclass(frozen=True)
class Notification:
    """Egy később más játékrendszerekből is létrehozható nyilvános üzenet."""

    message: str
    event_id: object = None


@dataclass
class ActiveNotification:
    """Egy látható értesítés saját, egymástól független időzítővel."""

    notification: Notification
    remaining_ms: int


class NotificationManager:
    """Legfeljebb három üzenetet jelenít meg, mindet saját időzítővel."""

    def __init__(self, duration_ms=NOTIFICATION_DURATION_MS, start_ticks=0):
        self.duration_ms = max(1, int(duration_ms))
        self.active_notifications = []
        self.pending_notifications = deque()
        self.last_update_ticks = int(start_ticks)
        self.processed_event_ids = set()

    @property
    def current_message(self):
        current = self.current
        return current.message if current is not None else None

    @property
    def current(self):
        """Kompatibilitási nézet: a legalsó, legrégebbi aktív üzenet."""
        if not self.active_notifications:
            return None
        return self.active_notifications[0].notification

    @property
    def remaining_ms(self):
        """Kompatibilitási nézet az első aktív üzenet időzítőjéhez."""
        if not self.active_notifications:
            return 0
        return self.active_notifications[0].remaining_ms

    @property
    def queue(self):
        """A korábbi API szerinti, első üzenet utáni teljes várakozó sor."""
        active_tail = (
            entry.notification for entry in self.active_notifications[1:]
        )
        return deque((*active_tail, *self.pending_notifications))

    @property
    def active_messages(self):
        """A rajzoláshoz sorrendhelyesen visszaadja az aktív szövegeket."""
        return tuple(
            entry.notification.message for entry in self.active_notifications
        )

    def reset(self, current_ticks=0):
        """Új játék és betöltés után eldobja a nem mentett értesítéseket."""
        self.active_notifications.clear()
        self.pending_notifications.clear()
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
        if len(self.active_notifications) < MAX_ACTIVE_NOTIFICATIONS:
            self._activate(notification)
        else:
            self.pending_notifications.append(notification)
        return True

    def enqueue_priority(self, message):
        """Kritikus üzenetet azonnal láthatóvá tesz, a jelenlegit megőrzi."""
        if not message:
            return False
        notification = Notification(str(message))
        self.active_notifications.insert(
            0, ActiveNotification(notification, self.duration_ms),
        )
        if len(self.active_notifications) > MAX_ACTIVE_NOTIFICATIONS:
            displaced = self.active_notifications.pop()
            self.pending_notifications.appendleft(displaced.notification)
        return True

    def _activate(self, notification):
        self.active_notifications.append(
            ActiveNotification(notification, self.duration_ms),
        )

    def _fill_available_slots(self):
        while (len(self.active_notifications) < MAX_ACTIVE_NOTIFICATIONS
                and self.pending_notifications):
            self._activate(self.pending_notifications.popleft())

    def update(self, current_ticks, time_running=True):
        """Valós időt fogyaszt, de szünetben nem csökkenti a láthatósági időt."""
        current_ticks = int(current_ticks)
        elapsed_ms = max(0, current_ticks - self.last_update_ticks)
        self.last_update_ticks = current_ticks
        if not time_running or not self.active_notifications:
            return False

        for entry in self.active_notifications:
            entry.remaining_ms -= elapsed_ms
        surviving = [
            entry for entry in self.active_notifications
            if entry.remaining_ms > 0
        ]
        changed = len(surviving) != len(self.active_notifications)
        self.active_notifications = surviving
        if changed:
            self._fill_available_slots()
        return changed

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
