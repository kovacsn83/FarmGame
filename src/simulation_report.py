"""A fejlesztői gazdasági szimuláció riportjainak előállítása."""

from __future__ import annotations

import json
from pathlib import Path

from buildings import BUILDING_TYPES
from inventory import get_inventory_item_name
from money_format import format_money
from vehicle_types import VEHICLE_TYPE_DEFINITIONS


INCOME_CATEGORY_NAMES = {
    "crop_sales": "Növényértékesítés",
    "fruit_sales": "Gyümölcsértékesítés",
    "milk_sales": "Tejértékesítés",
    "pork_sales": "Sertéshús-értékesítés",
    "other_animal_sales": "Egyéb állati termék",
    "processed_product_sales": "Feldolgozott termékek értékesítése",
    "other_income": "Egyéb bevétel",
}

EXPENSE_CATEGORY_NAMES = {
    "building_maintenance": "Épületek fenntartása",
    "field_maintenance": "Veteményesek fenntartása",
    "road_maintenance": "Utak fenntartása",
    "vehicle_maintenance": "Járművek fenntartása",
    "animal_purchase": "Állatvásárlás",
    "vehicle_purchase": "Járművásárlás",
    "building_construction": "Építkezés",
    "field_construction": "Veteményes-építés",
    "road_construction": "Útépítés",
    "feed_purchase": "Takarmányvásárlás",
    "seed_purchase": "Vetőmagvásárlás",
    "fruit_tree_purchase": "Gyümölcsfa-vásárlás",
    "bank_repayment": "Banki törlesztés",
    "other_expense": "Egyéb kiadás",
}

ANIMAL_NAMES = {
    "cattle": "Szarvasmarha",
    "pig": "Sertés",
    "chicken": "Csirke",
}


def _format_counts(counts, names=None):
    names = names or {}
    return ", ".join(
        f"{names.get(key, key)} ×{value}" for key, value in counts.items()
    ) or "–"


def _money_lines(values, names):
    if not values:
        return "- Nincs rögzített tétel."
    return "\n".join(
        f"- {names.get(key, key)}: {format_money(amount)}"
        for key, amount in values.items()
    )


def _largest(values):
    if not values:
        return {"category": None, "amount": 0.0}
    category, amount = max(values.items(), key=lambda item: item[1])
    return {"category": category, "amount": round(amount, 2)}


def build_economic_summary(snapshots):
    """Az éves főkönyvekből elkészíti az egész futás összesítését."""
    income = {}
    expenses = {}
    for snapshot in snapshots:
        for category, amount in snapshot["income_breakdown"].items():
            income[category] = income.get(category, 0.0) + amount
        for category, amount in snapshot["expense_breakdown"].items():
            expenses[category] = expenses.get(category, 0.0) + amount

    income = {key: round(value, 2) for key, value in sorted(income.items())}
    expenses = {key: round(value, 2) for key, value in sorted(expenses.items())}
    total_income = round(sum(item["income"] for item in snapshots), 2)
    total_expenses = round(sum(item["expenses"] for item in snapshots), 2)
    maintenance = sum(
        value for key, value in expenses.items() if key.endswith("_maintenance")
    )
    investments = sum(
        value for key, value in expenses.items()
        if key.endswith("_construction")
        or (key.endswith("_purchase") and key != "feed_purchase")
    )
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": round(total_income - total_expenses, 2),
        "income_breakdown": income,
        "expense_breakdown": expenses,
        "maintenance_expense_ratio": round(
            maintenance / total_expenses, 4,
        ) if total_expenses else 0.0,
        "feed_expense_ratio": round(
            expenses.get("feed_purchase", 0.0) / total_expenses, 4,
        ) if total_expenses else 0.0,
        "investment_expense_ratio": round(
            investments / total_expenses, 4,
        ) if total_expenses else 0.0,
        "largest_income_source": _largest(income),
        "largest_expense_category": _largest(expenses),
    }


def render_markdown_report(result):
    """Olvasható Markdown gazdasági riportot készít a begyűjtött adatokból."""
    building_names = {key: value["name"] for key, value in BUILDING_TYPES.items()}
    vehicle_names = {
        key.value: value["name"] for key, value in VEHICLE_TYPE_DEFINITIONS.items()
    }
    field_names = {"field_4x4": "4×4", "field_6x6": "6×6", "field_8x8": "8×8"}
    investment_names = {
        "road": "Út",
        **building_names,
        **{key: f"{value} Veteményes" for key, value in field_names.items()},
        **{
            f"vehicle:{key}": value for key, value in vehicle_names.items()
        },
        **{
            f"animal:{key}": value for key, value in ANIMAL_NAMES.items()
        },
    }

    rows = [
        f"| {item['year']}. év | {format_money(item['money'])} | "
        f"{format_money(item['income'])} | {format_money(item['expenses'])} | "
        f"{format_money(item['net_profit'])} |"
        for item in result["snapshots"]
    ]
    details = []
    for item in result["snapshots"]:
        largest_income = item["largest_income_source"]
        largest_expense = item["largest_expense_category"]
        inventory = {
            get_inventory_item_name(key): value
            for key, value in item["inventory"].items()
        }
        details.append(
            f"### {item['year']}. év\n\n"
            f"- Év végi egyenleg: {format_money(item['money'])}\n"
            f"- Bevétel: {format_money(item['income'])}\n"
            f"- Kiadás: {format_money(item['expenses'])}\n"
            f"- Nyereség/veszteség: {format_money(item['net_profit'])}\n\n"
            "#### Bevételi bontás\n\n"
            f"{_money_lines(item['income_breakdown'], INCOME_CATEGORY_NAMES)}\n\n"
            "#### Kiadási bontás\n\n"
            f"{_money_lines(item['expense_breakdown'], EXPENSE_CATEGORY_NAMES)}\n\n"
            "#### Mutatók\n\n"
            f"- Fenntartás aránya: {item['maintenance_expense_ratio']:.1%}\n"
            f"- Takarmány aránya: {item['feed_expense_ratio']:.1%}\n"
            f"- Beruházások aránya: {item['investment_expense_ratio']:.1%}\n"
            f"- Legnagyobb bevétel: {INCOME_CATEGORY_NAMES.get(largest_income['category'], '–')} "
            f"({format_money(largest_income['amount'])})\n"
            f"- Legnagyobb kiadás: {EXPENSE_CATEGORY_NAMES.get(largest_expense['category'], '–')} "
            f"({format_money(largest_expense['amount'])})\n\n"
            "#### Éves beruházások és év végi állapot\n\n"
            f"- Létrehozott/vásárolt objektumok: "
            f"{_format_counts(item['investments'], investment_names)}\n"
            f"- Épületek: {_format_counts(item['buildings'], building_names)}\n"
            f"- Veteményesek: {_format_counts(item['fields'], field_names)}\n"
            f"- Járművek: {_format_counts(item['vehicles'], vehicle_names)}\n"
            f"- Állatok: {_format_counts(item['animals'], ANIMAL_NAMES)}\n"
            f"- Raktár: {item['warehouse_used']} / {item['warehouse_capacity']} "
            f"({item['warehouse_utilization']:.1%})\n"
            f"- Készlet: {_format_counts(inventory)}\n"
            f"- Feladatok: {item['completed_tasks']} sikeres, "
            f"{item['failed_tasks']} sikertelen\n"
            f"- Banki törlesztés: {format_money(item['bank_repayments'])}; "
            f"év végi tartozás: {format_money(item['outstanding_loan_balance'])}\n"
        )

    summary = result["economic_summary"]
    largest_income = summary["largest_income_source"]
    largest_expense = summary["largest_expense_category"]
    decisions = "\n".join(f"- {entry}" for entry in result["decisions"]) or "- Nincs."
    return (
        "# FarmGame – részletes gazdasági szimuláció\n\n"
        f"- Seed: `{result['seed']}`\n"
        f"- Feldolgozott hetek: {result['weeks_processed']}\n"
        f"- Futási idő: {result['runtime_seconds']:.3f} másodperc\n"
        f"- Invariánshibák: {len(result['invariant_errors'])}\n\n"
        "## Ötéves összesítő\n\n"
        "| Év vége | Egyenleg | Bevétel | Kiadás | Nyereség/veszteség |\n"
        "|---|---:|---:|---:|---:|\n" + "\n".join(rows) + "\n\n"
        f"- Teljes bevétel: {format_money(summary['total_income'])}\n"
        f"- Teljes kiadás: {format_money(summary['total_expenses'])}\n"
        f"- Összesített eredmény: {format_money(summary['net_profit'])}\n"
        f"- Fenntartási kiadások aránya: {summary['maintenance_expense_ratio']:.1%}\n"
        f"- Takarmánykiadások aránya: {summary['feed_expense_ratio']:.1%}\n"
        f"- Beruházások aránya: {summary['investment_expense_ratio']:.1%}\n\n"
        f"- Legnagyobb bevételi forrás: "
        f"{INCOME_CATEGORY_NAMES.get(largest_income['category'], '–')} "
        f"({format_money(largest_income['amount'])})\n"
        f"- Legnagyobb kiadási kategória: "
        f"{EXPENSE_CATEGORY_NAMES.get(largest_expense['category'], '–')} "
        f"({format_money(largest_expense['amount'])})\n\n"
        "## Stratégiai döntések\n\n" + decisions + "\n\n"
        "## Éves részletek\n\n" + "\n".join(details) + "\n"
    )


def render_console_summary(result):
    summary = result["economic_summary"]
    return (
        "Gazdasági szimuláció elkészült: "
        f"bevétel {format_money(summary['total_income'])}, "
        f"kiadás {format_money(summary['total_expenses'])}, "
        f"eredmény {format_money(summary['net_profit'])}."
    )


def write_simulation_reports(result, report_dir):
    """A gyűjtött adatokat JSON és Markdown fejlesztői riportként menti."""
    result["economic_summary"] = build_economic_summary(result["snapshots"])
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = f"five_year_simulation_seed_{result['seed']}"
    json_path = report_dir / f"{stem}.json"
    md_path = report_dir / f"{stem}.md"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    md_path.write_text(render_markdown_report(result), encoding="utf-8")
    return md_path, json_path
