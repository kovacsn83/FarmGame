"""A banki hitelajánlat és az egyetlen aktív hitel központi kezelése."""

from dataclasses import asdict, dataclass, field

from game_logger import log
from money_format import format_money
from financial_history import INCOME_LOAN, EXPENSE_LOAN_REPAYMENT


@dataclass(frozen=True)
class LoanTier:
    tier: int
    name: str
    principal_cents: int
    interest_percent: int
    total_repayment_cents: int
    duration_weeks: int
    weekly_payment_cents: int


LOAN_TIERS = {
    1: LoanTier(1, "Hitel I.", 1_000_000, 16, 1_160_000, 80, 14_500),
    2: LoanTier(2, "Hitel II.", 2_500_000, 18, 2_950_000, 100, 29_500),
    3: LoanTier(3, "Hitel III.", 5_000_000, 20, 6_000_000, 120, 50_000),
}

# Kompatibilitási aliasok a korábbi, egyetlen Hitel I.-et használó kódhoz.
LOAN_PRINCIPAL_CENTS = LOAN_TIERS[1].principal_cents
LOAN_INTEREST_PERCENT = LOAN_TIERS[1].interest_percent
LOAN_TERM_WEEKS = LOAN_TIERS[1].duration_weeks
LOAN_TOTAL_REPAYMENT_CENTS = LOAN_TIERS[1].total_repayment_cents
LOAN_WEEKLY_PAYMENT_CENTS = LOAN_TIERS[1].weekly_payment_cents


def cents_to_dollars(cents):
    return cents / 100


@dataclass
class LoanState:
    """Centpontosan tárolja az aktív hitel visszafizetési állapotát."""

    active_loan: bool = False
    active_loan_tier: int = 0
    principal_cents: int = LOAN_PRINCIPAL_CENTS
    interest_percent: int = LOAN_INTEREST_PERCENT
    total_repayment_cents: int = LOAN_TOTAL_REPAYMENT_CENTS
    weekly_payment_cents: int = LOAN_WEEKLY_PAYMENT_CENTS
    remaining_balance_cents: int = 0
    remaining_weeks: int = 0
    loan_offer_handled_for_current_negative_period: bool = False
    loans_taken: int = 0
    total_repaid_cents: int = 0
    completed_tiers: list = field(default_factory=list)


class BankSystem:
    """Érzékeli a negatív átmenetet, folyósít és hetente törleszt."""

    def __init__(self, economy, notification_manager=None):
        self.economy = economy
        self.notification_manager = notification_manager
        self.loan = LoanState()
        self.offer_pending = False
        self.last_observed_money = float(economy.money)

    @property
    def active_loan(self):
        return self.loan.active_loan

    def is_tier_unlocked(self, tier):
        if tier not in LOAN_TIERS:
            return False
        return tier == 1 or tier - 1 in self.loan.completed_tiers

    def reset_for_new_game(self):
        self.loan = LoanState()
        self.offer_pending = False
        self.synchronize_balance()

    def synchronize_balance(self):
        """Betöltéskor új ajánlat kiváltása nélkül igazodik az egyenleghez."""
        self.last_observed_money = float(self.economy.money)
        self.offer_pending = False

    def observe_balance(self):
        """Pontosan a nemnegatívból negatívba forduló átmenetet jelzi egyszer."""
        current_money = float(self.economy.money)
        if current_money >= 0:
            self.loan.loan_offer_handled_for_current_negative_period = False
        crossed_below_zero = self.last_observed_money >= 0 > current_money
        should_offer = (
            crossed_below_zero
            and not self.loan.active_loan
            and not self.loan.loan_offer_handled_for_current_negative_period
        )
        self.last_observed_money = current_money
        if should_offer:
            self.loan.loan_offer_handled_for_current_negative_period = True
            self.offer_pending = True
            log(
                "A pénzegyenleg negatívba fordult. Hitelajánlat megnyitva.",
                "Bank",
            )
        return should_offer

    def take_loan(self, tier=1):
        """Folyósítja a közös hitelkonstrukciót, ha nincs aktív hitel."""
        definition = LOAN_TIERS.get(tier)
        if (
            definition is None
            or self.loan.active_loan
            or not self.is_tier_unlocked(tier)
        ):
            return False
        self.economy.earn(cents_to_dollars(definition.principal_cents))
        self.economy.record_income(
            INCOME_LOAN, cents_to_dollars(definition.principal_cents),
            description=definition.name,
        )
        self.loan.active_loan = True
        self.loan.active_loan_tier = tier
        self.loan.principal_cents = definition.principal_cents
        self.loan.interest_percent = definition.interest_percent
        self.loan.total_repayment_cents = definition.total_repayment_cents
        self.loan.weekly_payment_cents = definition.weekly_payment_cents
        self.loan.remaining_balance_cents = definition.total_repayment_cents
        self.loan.remaining_weeks = definition.duration_weeks
        self.loan.loans_taken += 1
        self.offer_pending = False
        self.last_observed_money = float(self.economy.money)
        log(
            f"{definition.name} felvéve: "
            f"{format_money(cents_to_dollars(definition.principal_cents))}. "
            "Teljes visszafizetés: "
            f"{format_money(cents_to_dollars(definition.total_repayment_cents))} "
            f"/ {definition.duration_weeks} hét.",
            "Bank",
        )
        return True

    def accept_offer(self, tier=1):
        """A negatív egyenleg miatt létrejött ajánlatot fogadja el."""
        if not self.offer_pending:
            return False
        return self.take_loan(tier)

    def decline_offer(self):
        if not self.offer_pending:
            return False
        self.offer_pending = False
        self.last_observed_money = float(self.economy.money)
        log("A hitelajánlat elutasítva.", "Bank")
        return True

    def resolve_offer_after_market(self):
        """Pozitív egyenlegnél hitel nélkül lezárja a függő banki ajánlatot."""
        if not self.offer_pending or self.economy.money < 0:
            return False
        self.offer_pending = False
        self.last_observed_money = float(self.economy.money)
        self.loan.loan_offer_handled_for_current_negative_period = False
        log(
            "A Piaci értékesítés rendezte a negatív egyenleget; "
            "nincs szükség hitelre.",
            "Bank",
        )
        return True

    def apply_weekly_repayment(self):
        """Fedezettől függetlenül levonja az aktuális, legfeljebb hátralévő részt."""
        if not self.loan.active_loan:
            return 0.0
        payment_cents = min(
            self.loan.weekly_payment_cents,
            self.loan.remaining_balance_cents,
        )
        payment = cents_to_dollars(payment_cents)
        self.economy.charge(payment)
        self.economy.record_expense(
            EXPENSE_LOAN_REPAYMENT, payment, description="Heti hiteltörlesztés",
        )
        self.loan.remaining_balance_cents -= payment_cents
        self.loan.remaining_weeks = max(0, self.loan.remaining_weeks - 1)
        self.loan.total_repaid_cents += payment_cents
        log(f"Heti törlesztőrészlet levonva: {format_money(payment)}.", "Bank")
        log(
            "Hátralévő tartozás: "
            f"{format_money(cents_to_dollars(self.loan.remaining_balance_cents))}, "
            f"hátralévő idő: {self.loan.remaining_weeks} hét.",
            "Bank",
        )
        if self.loan.remaining_balance_cents == 0 or self.loan.remaining_weeks == 0:
            completed_tier = self.loan.active_loan_tier or 1
            newly_completed = completed_tier not in self.loan.completed_tiers
            if newly_completed:
                self.loan.completed_tiers.append(completed_tier)
                self.loan.completed_tiers.sort()
            self.loan.active_loan = False
            self.loan.active_loan_tier = 0
            self.loan.remaining_balance_cents = 0
            self.loan.remaining_weeks = 0
            completed_name = LOAN_TIERS[completed_tier].name
            next_tier = completed_tier + 1
            message = f"{completed_name} teljesen visszafizetve!"
            log(f"{completed_name} teljesen visszafizetve.", "Bank")
            if newly_completed and next_tier in LOAN_TIERS:
                next_name = LOAN_TIERS[next_tier].name
                message += f"\nA {next_name} mostantól elérhető."
                log(f"{next_name} feloldva.", "Bank")
            if self.notification_manager is not None:
                self.notification_manager.enqueue(
                    message,
                    event_id=(
                        "loan_repaid", self.loan.loans_taken, completed_tier,
                    ),
                )
        return payment

    def to_save_record(self):
        return asdict(self.loan)

    def load_save_record(self, record):
        """Régi mentésnél alapállapotot, új rekordnál ellenőrzött értékeket tölt."""
        if not isinstance(record, dict):
            self.loan = LoanState()
            self.synchronize_balance()
            return
        defaults = asdict(LoanState())
        values = {key: record.get(key, default) for key, default in defaults.items()}
        if values["active_loan"] and "active_loan_tier" not in record:
            values["active_loan_tier"] = 1
        completed_tiers = values["completed_tiers"]
        values["completed_tiers"] = (
            sorted(set(completed_tiers))
            if isinstance(completed_tiers, list)
            else []
        )
        self.loan = LoanState(**values)
        self.synchronize_balance()


def is_valid_loan_record(record):
    if record is None:
        return True
    if not isinstance(record, dict):
        return False
    boolean_keys = (
        "active_loan", "loan_offer_handled_for_current_negative_period",
    )
    integer_keys = (
        "principal_cents", "interest_percent", "total_repayment_cents",
        "weekly_payment_cents", "remaining_balance_cents", "remaining_weeks",
        "loans_taken", "total_repaid_cents",
    )
    if any(not isinstance(record.get(key), bool) for key in boolean_keys):
        return False
    if any(
            not isinstance(record.get(key), int)
            or isinstance(record.get(key), bool)
            or record.get(key) < 0
            for key in integer_keys):
        return False
    active_tier = record.get("active_loan_tier", 1 if record["active_loan"] else 0)
    if (
        not isinstance(active_tier, int)
        or isinstance(active_tier, bool)
        or active_tier not in ({0} | set(LOAN_TIERS))
    ):
        return False
    completed_tiers = record.get("completed_tiers", [])
    if (
        not isinstance(completed_tiers, list)
        or any(
            not isinstance(tier, int)
            or isinstance(tier, bool)
            or tier not in LOAN_TIERS
            for tier in completed_tiers
        )
    ):
        return False
    if completed_tiers:
        expected_completed = list(range(1, max(completed_tiers) + 1))
        if (
            len(set(completed_tiers)) != len(completed_tiers)
            or sorted(completed_tiers) != expected_completed
        ):
            return False
    if record["active_loan"]:
        if active_tier == 0:
            return False
        duration = LOAN_TIERS[active_tier].duration_weeks
        return (
            0 < record["remaining_weeks"] <= duration
            and 0 < record["remaining_balance_cents"]
            <= record["total_repayment_cents"]
        )
    return (
        active_tier == 0
        and record["remaining_weeks"] == 0
        and record["remaining_balance_cents"] == 0
    )
