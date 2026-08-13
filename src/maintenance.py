"""Az építhető objektumok egységes fenntartási szabályai."""


ANNUAL_MAINTENANCE_RATE = 0.10
MAINTENANCE_WEEKS_PER_YEAR = 52


def calculate_annual_maintenance(price):
    """A vételárból kiszámítja az egy teljes évre jutó fenntartást."""
    return float(price) * ANNUAL_MAINTENANCE_RATE


def calculate_weekly_maintenance(price):
    """Az éves fenntartás 52 egyenlő heti részének egyikét adja vissza."""
    return calculate_annual_maintenance(price) / MAINTENANCE_WEEKS_PER_YEAR


def format_annual_maintenance_rate():
    """A felhasználói felület egységes százalékos feliratát adja vissza."""
    return f"{ANNUAL_MAINTENANCE_RATE:.0%}"
