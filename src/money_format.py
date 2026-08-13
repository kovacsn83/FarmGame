from decimal import Decimal, ROUND_HALF_UP


def format_money(value):
    """A pontos belső értéket egész dolláros, egységes UI-szöveggé alakítja."""
    rounded = int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    sign = "-" if rounded < 0 else ""
    grouped_amount = f"{abs(rounded):,}".replace(",", " ")
    return f"{sign}${grouped_amount}"
