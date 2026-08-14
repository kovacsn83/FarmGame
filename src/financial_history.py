"""A játék pénzmozgásainak stabil, menthető kategóriái."""

import math

INCOME = "income"
EXPENSE = "expense"

INCOME_CROP_SALES = "crop_sales"
INCOME_LIVESTOCK_SALES = "livestock_sales"
INCOME_ORCHARD_SALES = "orchard_sales"
INCOME_LOAN = "loan_income"

EXPENSE_MAINTENANCE = "maintenance"
EXPENSE_SHIPPING = "shipping"
EXPENSE_PLANTING = "planting"
EXPENSE_ANIMAL_FEED = "animal_feed"
EXPENSE_ANIMAL_PURCHASE = "animal_purchase"
EXPENSE_FRUIT_TREE = "fruit_tree_purchase"
EXPENSE_CONSTRUCTION = "construction"
EXPENSE_VEHICLE = "vehicle_purchase"
EXPENSE_UPGRADE = "upgrade"
EXPENSE_LOAN_REPAYMENT = "loan_repayment"

FINANCIAL_HISTORY_RETENTION_WEEKS = 156
FINANCIAL_SUMMARY_WEEKS = 52


def is_valid_transaction(record):
    """A mentésből érkező tranzakció minimális sémáját ellenőrzi."""
    if not isinstance(record, dict):
        return False
    return (
        record.get("type") in (INCOME, EXPENSE)
        and isinstance(record.get("category"), str)
        and (record.get("id") is None
             or (isinstance(record.get("id"), int)
                 and not isinstance(record.get("id"), bool)
                 and record.get("id") >= 0))
        and isinstance(record.get("week"), int)
        and not isinstance(record.get("week"), bool)
        and record.get("week") >= 0
        and isinstance(record.get("amount"), (int, float))
        and not isinstance(record.get("amount"), bool)
        and record.get("amount") >= 0
        and math.isfinite(record.get("amount"))
        and (record.get("subcategory") is None
             or isinstance(record.get("subcategory"), str))
        and (record.get("description") is None
             or isinstance(record.get("description"), str))
    )
