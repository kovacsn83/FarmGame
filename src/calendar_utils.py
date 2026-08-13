"""Pygame-től független naptári alapértékek és átváltások."""

WEEKS_PER_YEAR = 52


def get_year_and_week(elapsed_weeks):
    """A belső hétszámlálóból kiszámítja az 1-től induló évet és hetet."""
    normalized_weeks = max(0, int(elapsed_weeks))
    return (
        normalized_weeks // WEEKS_PER_YEAR + 1,
        normalized_weeks % WEEKS_PER_YEAR + 1,
    )
