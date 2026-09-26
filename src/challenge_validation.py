"""Small validation helpers for untrusted client Challenge data."""

import math


def is_finite_farm_value(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def has_name_control_characters(name):
    return any(ord(character) < 32 or 127 <= ord(character) <= 159
               for character in name)
