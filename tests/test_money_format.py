import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from money_format import format_money


class MoneyFormatTests(unittest.TestCase):
    def test_whole_amount_has_no_decimal_places(self):
        self.assertEqual("$10 000", format_money(10000.0))

    def test_thousands_are_grouped_with_spaces(self):
        self.assertEqual("$999", format_money(999))
        self.assertEqual("$1 000", format_money(1000))
        self.assertEqual("$10 000", format_money(10000))
        self.assertEqual("$1 000 000", format_money(1000000))

    def test_fractional_amount_is_rounded_to_nearest_dollar(self):
        self.assertEqual("$146", format_money(145.5))
        self.assertEqual("$145", format_money(145.49))

    def test_negative_sign_precedes_currency_symbol(self):
        self.assertEqual("-$125", format_money(-125.0))
        self.assertEqual("-$1 250", format_money(-1250.0))

    def test_grouping_is_applied_after_display_rounding(self):
        self.assertEqual("$12 451", format_money(12450.73))

    def test_formatting_does_not_change_source_value(self):
        value = 40 / 52
        format_money(value)
        self.assertEqual(40 / 52, value)


if __name__ == "__main__":
    unittest.main()
