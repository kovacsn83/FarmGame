from dataclasses import dataclass
from enum import Enum

import pygame

from calendar_utils import WEEKS_PER_YEAR, get_year_and_week


TIME_PAUSED = 0
TIME_SLOW = 1
TIME_NORMAL = 2
TIME_FAST = 3

class Season(Enum):
    """A későbbi szezonális rendszerek közös évszakazonosítói."""

    WINTER = "Tél"
    SPRING = "Tavasz"
    SUMMER = "Nyár"
    AUTUMN = "Ősz"


@dataclass(frozen=True)
class SeasonPeriod:
    """Egy évszak egybefüggő, mindkét szélen zárt heti tartománya."""

    season: Season
    start_week: int
    end_week: int

    @property
    def duration_weeks(self):
        return self.end_week - self.start_week + 1


# A Tél két naptári szakasza ugyanahhoz a logikai évszakhoz tartozik.
SEASON_PERIODS = (
    SeasonPeriod(Season.WINTER, 1, 8),
    SeasonPeriod(Season.SPRING, 9, 21),
    SeasonPeriod(Season.SUMMER, 22, 34),
    SeasonPeriod(Season.AUTUMN, 35, 47),
    SeasonPeriod(Season.WINTER, 48, 52),
)

# Az aktuális hét előrehaladása mindig 1×-es játékidőben mérődik.
# A sebességfokozat csak azt szabja meg, hogy valós idő alatt mennyi ilyen
# játékidő kerül az akkumulátorba.
BASE_WEEK_DURATION_MS = 10000

TIME_WEEK_LENGTHS_MS = {
    TIME_PAUSED: None,
    TIME_SLOW: BASE_WEEK_DURATION_MS,
    TIME_NORMAL: BASE_WEEK_DURATION_MS // 2,
    # Mentési kompatibilitás: a 3× fokozat már nem kapcsolható be.
    TIME_FAST: BASE_WEEK_DURATION_MS // 2,
}

AVAILABLE_TIME_SPEEDS = (TIME_PAUSED, TIME_SLOW, TIME_NORMAL)

# Kompatibilitási alias régebbi modulok és kiegészítések számára.
TIME_DAY_LENGTHS_MS = TIME_WEEK_LENGTHS_MS

# Ezt a központi szorzót használja minden valós idejű, játéksebességhez kötött
# animáció. Az időfokozat azonosítója nem kerül közvetlenül szorzóként
# értelmezésre más modulokban.
TIME_SPEED_MULTIPLIERS = {
    TIME_PAUSED: 0.0,
    TIME_SLOW: 1.0,
    TIME_NORMAL: 2.0,
    TIME_FAST: 2.0,
}

TIME_SPEED_INDICATORS = {
    TIME_PAUSED: "[||]",
    TIME_SLOW: "[>]",
    TIME_NORMAL: "[>>]",
    TIME_FAST: "[>>>]",
}


def get_season_for_week(week):
    """Az 1–52 közötti hétből a központi konfiguráció alapján ad évszakot."""
    if isinstance(week, bool) or not isinstance(week, int):
        raise ValueError("A hétnek 1 és 52 közötti egész számnak kell lennie.")
    for period in SEASON_PERIODS:
        if period.start_week <= week <= period.end_week:
            return period.season
    raise ValueError("A hétnek 1 és 52 között kell lennie.")


def format_game_time(elapsed_weeks):
    """A HUD és a mentési lista közös év–hét formátumát adja vissza."""
    year, week = get_year_and_week(elapsed_weeks)
    return f"{year}. év • {week}. hét"


def legacy_day_to_elapsed_weeks(legacy_day_value):
    """A régi, 1-től induló mentési számlálót 0-tól induló hétté alakítja."""
    return max(0, int(legacy_day_value) - 1)


def get_time_speed_indicator(time_speed):
    return TIME_SPEED_INDICATORS.get(
        time_speed, TIME_SPEED_INDICATORS[TIME_NORMAL],
    )


def get_time_speed_multiplier(time_speed):
    """Visszaadja az időfokozathoz tartozó központi sebességszorzót."""
    return TIME_SPEED_MULTIPLIERS.get(
        time_speed, TIME_SPEED_MULTIPLIERS[TIME_NORMAL],
    )


class GameTime:
    """Egyetlen eltelt-hét számlálóval kezeli a játék idejét."""

    def __init__(self, current_time_speed=TIME_NORMAL, start_ticks=None):
        self.elapsed_weeks = 0
        self.elapsed_time_in_week_ms = 0.0
        self.current_time_speed = TIME_NORMAL
        self.last_week_change = (
            pygame.time.get_ticks() if start_ticks is None else start_ticks
        )
        self.set_time_speed(current_time_speed, self.last_week_change)

    @property
    def year(self):
        return get_year_and_week(self.elapsed_weeks)[0]

    @property
    def week(self):
        return get_year_and_week(self.elapsed_weeks)[1]

    @property
    def current_season(self):
        return get_season_for_week(self.week)

    def get_current_season(self):
        """A hétből számolt aktuális évszak központi lekérdezése."""
        return self.current_season

    @property
    def week_length_ms(self):
        return TIME_WEEK_LENGTHS_MS[self.current_time_speed]

    @property
    def day(self):
        """Régi mentési formátumhoz megtartott, 1-től induló kompatibilitási nézet."""
        return self.elapsed_weeks + 1

    @day.setter
    def day(self, value):
        self.elapsed_weeks = legacy_day_to_elapsed_weeks(value)

    @property
    def day_length_ms(self):
        """Régi külső hívók kompatibilitási aliasa."""
        return self.week_length_ms

    @property
    def time_speed_multiplier(self):
        return get_time_speed_multiplier(self.current_time_speed)

    @property
    def week_progress(self):
        """Az aktuális hét 0 és 1 közötti, menthető előrehaladása."""
        return self.elapsed_time_in_week_ms / BASE_WEEK_DURATION_MS

    def restore_week_progress(self, progress):
        """Ellenőrzött, normalizált heti progresszt állít vissza."""
        if (isinstance(progress, bool)
                or not isinstance(progress, (int, float))
                or not 0 <= progress < 1):
            progress = 0.0
        self.elapsed_time_in_week_ms = float(progress) * BASE_WEEK_DURATION_MS

    def _accumulate_until(self, current_ticks):
        """Az utolsó mintavétel óta eltelt időt az aktuális skálával gyűjti."""
        elapsed_time = max(0, current_ticks - self.last_week_change)
        self.elapsed_time_in_week_ms += (
            elapsed_time * self.time_speed_multiplier
        )
        self.last_week_change = current_ticks

    def set_time_speed(self, time_speed, current_ticks=None):
        """Beállítja a sebességet a heti progressz megőrzése mellett."""
        if isinstance(time_speed, bool) or time_speed not in AVAILABLE_TIME_SPEEDS:
            return False
        now = (
            pygame.time.get_ticks() if current_ticks is None else current_ticks
        )
        # Előbb a régi szorzóval számoljuk el a sebességváltásig eltelt
        # időt. Emiatt még minden frame-ben végrehajtott kapcsolgatással sem
        # lehet megállítani vagy visszatekerni az aktuális hetet.
        self._accumulate_until(now)
        self.current_time_speed = time_speed
        return True

    def update(self, current_ticks=None):
        """Visszaadja az előző frissítés óta eltelt hetek 0-alapú indexeit."""
        now = pygame.time.get_ticks() if current_ticks is None else current_ticks

        self._accumulate_until(now)
        passed_weeks = int(
            self.elapsed_time_in_week_ms // BASE_WEEK_DURATION_MS
        )
        if passed_weeks <= 0:
            return []

        first_week_index = self.elapsed_weeks + 1
        self.elapsed_weeks += passed_weeks
        self.elapsed_time_in_week_ms -= passed_weeks * BASE_WEEK_DURATION_MS
        return list(range(first_week_index, self.elapsed_weeks + 1))

    def synchronize(self, current_ticks=None):
        """Külső, ideiglenes szünet alatt eldobja az eltelt valós időt."""
        self.last_week_change = (
            pygame.time.get_ticks() if current_ticks is None else current_ticks
        )
