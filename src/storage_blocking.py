from game_logger import log
from time_system import TIME_PAUSED


class StorageBlockManager:
    """A konkrétan blokkolt automatikus raktári eseményeket kezeli.

    Az eseményazonosító szerinti deduplikáció miatt ugyanaz a fennálló probléma
    csak egyszer jelez és csak egyszer állítja meg a játékot. A mechanizmus nem
    állat-specifikus, ezért későbbi automatikus termelők is használhatják.
    """

    def __init__(self, notification_manager=None, game_time=None):
        self.notification_manager = notification_manager
        self.game_time = game_time
        self.active_events = set()
        self.previous_time_speed = None

    def report(self, event_id, message, log_message=None):
        if event_id in self.active_events:
            return False
        self.active_events.add(event_id)
        if log_message:
            log(log_message, "Storage")
        if self.notification_manager is not None:
            # A fennálló eseményt ez az osztály deduplikálja. Így feloldás után
            # egy későbbi, új blokkolás ismét jogosan megjelenhet.
            self.notification_manager.enqueue_priority(message)
        if (
            self.game_time is not None
            and self.game_time.current_time_speed != TIME_PAUSED
        ):
            self.previous_time_speed = self.game_time.current_time_speed
            self.game_time.set_time_speed(TIME_PAUSED)
        return True

    def resolve(self, event_id, log_message=None):
        if event_id not in self.active_events:
            return False
        self.active_events.remove(event_id)
        if log_message:
            log(log_message, "Storage")
        return True

    def reset(self):
        self.active_events.clear()
        self.previous_time_speed = None
