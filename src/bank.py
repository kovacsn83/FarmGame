"""A banki hitelajánlat és az egyetlen aktív hitel központi kezelése."""

from dataclasses import asdict, dataclass

from game_logger import log
from money_format import format_money


LOAN_PRINCIPAL_CENTS = 1_000_000
LOAN_INTEREST_PERCENT = 16
LOAN_TERM_WEEKS = 80
LOAN_TOTAL_REPAYMENT_CENTS = (
    LOAN_PRINCIPAL_CENTS * (100 + LOAN_INTEREST_PERCENT) // 100
)
LOAN_WEEKLY_PAYMENT_CENTS = (
    LOAN_TOTAL_REPAYMENT_CENTS // LOAN_TERM_WEEKS
)


def cents_to_dollars(cents):
    return cents / 100


@dataclass
class LoanState:
    """Centpontosan tárolja az aktív hitel visszafizetési állapotát."""

    active_loan: bool = False
    principal_cents: int = LOAN_PRINCIPAL_CENTS
    interest_percent: int = LOAN_INTEREST_PERCENT
    total_repayment_cents: int = LOAN_TOTAL_REPAYMENT_CENTS
    weekly_payment_cents: int = LOAN_WEEKLY_PAYMENT_CENTS
    remaining_balance_cents: int = 0
    remaining_weeks: int = 0
    loan_offer_handled_for_current_negative_period: bool = False
    loans_taken: int = 0
    total_repaid_cents: int = 0


class BankSystem:
    """Érzékeli a negatív átmenetet, folyósít és hetente törleszt."""

    def __init__(self, economy):
        self.economy = economy
        self.loan = LoanState()
        self.offer_pending = False
        self.last_observed_money = float(economy.money)

    @property
    def active_loan(self):
        return self.loan.active_loan

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

    def accept_offer(self):
        if self.loan.active_loan or not self.offer_pending:
            return False
        self.economy.earn(cents_to_dollars(LOAN_PRINCIPAL_CENTS))
        self.loan.active_loan = True
        self.loan.remaining_balance_cents = LOAN_TOTAL_REPAYMENT_CENTS
        self.loan.remaining_weeks = LOAN_TERM_WEEKS
        self.loan.loans_taken += 1
        self.offer_pending = False
        self.last_observed_money = float(self.economy.money)
        log(f"Hitel felvéve: {format_money(cents_to_dollars(LOAN_PRINCIPAL_CENTS))}.", "Bank")
        return True

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
            self.loan.active_loan = False
            self.loan.remaining_balance_cents = 0
            self.loan.remaining_weeks = 0
            log(
                "A bankhitel teljes egészében visszafizetésre került.",
                "Bank",
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
    if record["active_loan"]:
        return (
            0 < record["remaining_weeks"] <= LOAN_TERM_WEEKS
            and 0 < record["remaining_balance_cents"]
            <= record["total_repayment_cents"]
        )
    return record["remaining_weeks"] == 0 and record["remaining_balance_cents"] == 0
