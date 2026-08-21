from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bank import (
    BankSystem, LOAN_PRINCIPAL_CENTS, LOAN_TERM_WEEKS, LOAN_TIERS,
    LOAN_TOTAL_REPAYMENT_CENTS, LOAN_WEEKLY_PAYMENT_CENTS,
    is_valid_loan_record,
)
from economy import Economy
from financial_history import INCOME_LOAN, EXPENSE_LOAN_REPAYMENT
from game_logger import GameLogger
from notification_system import NotificationManager
from save_system import load_game, save_game
from simulation import SimulationBot, run_simulation


class BankSystemTests(unittest.TestCase):
    def test_each_tier_emits_one_completion_notification(self):
        expected_messages = {
            1: "Hitel I. teljesen visszafizetve!\nA Hitel II. mostantól elérhető.",
            2: "Hitel II. teljesen visszafizetve!\nA Hitel III. mostantól elérhető.",
            3: "Hitel III. teljesen visszafizetve!",
        }
        for tier, expected in expected_messages.items():
            with self.subTest(tier=tier):
                notifications = NotificationManager(start_ticks=0)
                bank = BankSystem(Economy(100000), notifications)
                bank.loan.completed_tiers = list(range(1, tier))
                self.assertTrue(bank.take_loan(tier))
                bank.loan.remaining_balance_cents = (
                    bank.loan.weekly_payment_cents
                )
                bank.loan.remaining_weeks = 1

                bank.apply_weekly_repayment()

                self.assertEqual(notifications.current_message, expected)
                self.assertFalse(bank.active_loan)
                self.assertIn(tier, bank.loan.completed_tiers)
                self.assertEqual(bank.apply_weekly_repayment(), 0.0)
                self.assertEqual(len(notifications.queue), 0)

    def test_loaded_completed_loan_does_not_replay_notification(self):
        original_notifications = NotificationManager(start_ticks=0)
        original = BankSystem(Economy(100000), original_notifications)
        self.assertTrue(original.take_loan(1))
        original.loan.remaining_balance_cents = (
            original.loan.weekly_payment_cents
        )
        original.loan.remaining_weeks = 1
        original.apply_weekly_repayment()
        record = original.to_save_record()

        restored_notifications = NotificationManager(start_ticks=0)
        restored = BankSystem(Economy(100000), restored_notifications)
        restored.load_save_record(record)
        self.assertEqual(restored.apply_weekly_repayment(), 0.0)
        self.assertIsNone(restored_notifications.current_message)

    def test_central_loan_calculation(self):
        self.assertEqual(LOAN_PRINCIPAL_CENTS, 1_000_000)
        self.assertEqual(LOAN_TOTAL_REPAYMENT_CENTS, 1_160_000)
        self.assertEqual(LOAN_TERM_WEEKS, 80)
        self.assertEqual(LOAN_WEEKLY_PAYMENT_CENTS, 14_500)
        self.assertEqual(
            [
                (tier.principal_cents, tier.total_repayment_cents,
                 tier.duration_weeks, tier.weekly_payment_cents)
                for tier in LOAN_TIERS.values()
            ],
            [
                (1_000_000, 1_160_000, 80, 14_500),
                (2_500_000, 2_950_000, 100, 29_500),
                (5_000_000, 6_000_000, 120, 50_000),
            ],
        )

    def test_offer_appears_only_on_new_negative_transition(self):
        economy = Economy(100)
        bank = BankSystem(economy)
        self.assertFalse(bank.observe_balance())
        economy.charge(101)
        self.assertTrue(bank.observe_balance())
        self.assertTrue(bank.decline_offer())
        self.assertFalse(bank.observe_balance())
        economy.earn(1)
        self.assertFalse(bank.observe_balance())
        economy.charge(1)
        self.assertTrue(bank.observe_balance())

    def test_acceptance_credits_once_and_blocks_second_loan(self):
        economy = Economy(0)
        bank = BankSystem(economy)
        economy.charge(1)
        self.assertTrue(bank.observe_balance())
        self.assertTrue(bank.accept_offer())
        self.assertEqual(economy.money, 9999.0)
        self.assertEqual(bank.loan.remaining_balance_cents, 1_160_000)
        self.assertFalse(bank.accept_offer())

    def test_manual_loan_works_with_positive_balance_and_is_atomic(self):
        economy = Economy(8500)
        bank = BankSystem(economy)
        self.assertTrue(bank.take_loan())
        self.assertEqual(economy.money, 18500)
        self.assertTrue(bank.active_loan)
        self.assertEqual(bank.loan.remaining_balance_cents, 1_160_000)
        self.assertEqual(bank.loan.remaining_weeks, 80)
        self.assertFalse(bank.take_loan())
        self.assertEqual(economy.money, 18500)

    def test_manual_loan_can_be_taken_again_after_full_repayment(self):
        economy = Economy(15000)
        bank = BankSystem(economy)
        self.assertTrue(bank.take_loan())
        for _ in range(80):
            bank.apply_weekly_repayment()
        self.assertFalse(bank.active_loan)
        self.assertTrue(bank.take_loan())
        self.assertTrue(bank.active_loan)
        self.assertEqual(bank.loan.loans_taken, 2)

    def test_manual_loan_uses_financial_history_categories(self):
        economy = Economy(15000)
        bank = BankSystem(economy)
        bank.take_loan()
        bank.apply_weekly_repayment()
        summary = economy.get_financial_summary(52)
        self.assertEqual(summary["income"][INCOME_LOAN]["total"], 10000)
        self.assertEqual(
            summary["expense"][EXPENSE_LOAN_REPAYMENT]["total"], 145,
        )

    def test_tiers_unlock_in_order_and_lower_tiers_remain_available(self):
        economy = Economy(100000)
        bank = BankSystem(economy)
        self.assertTrue(bank.is_tier_unlocked(1))
        self.assertFalse(bank.is_tier_unlocked(2))
        self.assertFalse(bank.is_tier_unlocked(3))
        self.assertFalse(bank.take_loan(2))

        self.assertTrue(bank.take_loan(1))
        for _ in range(80):
            bank.apply_weekly_repayment()
        self.assertTrue(bank.is_tier_unlocked(1))
        self.assertTrue(bank.is_tier_unlocked(2))
        self.assertFalse(bank.is_tier_unlocked(3))

        self.assertTrue(bank.take_loan(2))
        self.assertEqual(bank.loan.active_loan_tier, 2)
        self.assertEqual(bank.loan.weekly_payment_cents, 29_500)
        self.assertFalse(bank.take_loan(1))
        for _ in range(100):
            bank.apply_weekly_repayment()
        self.assertTrue(bank.is_tier_unlocked(3))
        self.assertTrue(bank.take_loan(3))
        self.assertEqual(bank.loan.active_loan_tier, 3)
        self.assertEqual(bank.loan.weekly_payment_cents, 50_000)
        repaid_before = bank.loan.total_repaid_cents
        for _ in range(120):
            self.assertEqual(bank.apply_weekly_repayment(), 500.0)
        self.assertEqual(
            bank.loan.total_repaid_cents - repaid_before, 6_000_000,
        )
        self.assertFalse(bank.active_loan)
        self.assertEqual(bank.loan.completed_tiers, [1, 2, 3])

    def test_progression_save_load_round_trip(self):
        original = SimulationBot(21)
        original.economy.money = 100000
        original.bank_system.take_loan(1)
        for _ in range(80):
            original.bank_system.apply_weekly_repayment()
        original.bank_system.take_loan(2)
        original.bank_system.apply_weekly_repayment()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiered_bank_save.json"
            self.assertTrue(save_game(original.state, path))
            loaded = SimulationBot(22)
            self.assertTrue(load_game(loaded.state, path))
        self.assertEqual(loaded.bank_system.loan.completed_tiers, [1])
        self.assertEqual(loaded.bank_system.loan.active_loan_tier, 2)
        self.assertEqual(loaded.bank_system.loan.remaining_weeks, 99)
        self.assertEqual(
            loaded.bank_system.loan.remaining_balance_cents, 2_920_500,
        )

    def test_legacy_active_loan_migrates_to_tier_one_without_unlock(self):
        economy = Economy(0)
        bank = BankSystem(economy)
        bank.take_loan(1)
        legacy = bank.to_save_record()
        legacy.pop("active_loan_tier")
        legacy.pop("completed_tiers")
        self.assertTrue(is_valid_loan_record(legacy))

        restored = BankSystem(Economy(0))
        restored.load_save_record(legacy)
        self.assertEqual(restored.loan.active_loan_tier, 1)
        self.assertEqual(restored.loan.completed_tiers, [])
        self.assertFalse(restored.is_tier_unlocked(2))

    def test_eighty_installments_repay_exactly_even_with_insufficient_money(self):
        economy = Economy(0)
        bank = BankSystem(economy)
        economy.charge(1)
        bank.observe_balance()
        bank.accept_offer()
        for _ in range(80):
            self.assertEqual(bank.apply_weekly_repayment(), 145.0)
        self.assertEqual(bank.loan.total_repaid_cents, 1_160_000)
        self.assertEqual(bank.loan.remaining_balance_cents, 0)
        self.assertEqual(bank.loan.remaining_weeks, 0)
        self.assertFalse(bank.active_loan)
        self.assertEqual(economy.money, -1601.0)

    def test_bank_logger_keeps_bank_category(self):
        logger = GameLogger(echo_to_terminal=False)
        entry = logger.log("Hitelteszt", "Bank")
        self.assertEqual(entry.category, "Bank")

    def test_final_installment_can_trigger_a_new_negative_transition(self):
        economy = Economy(0)
        bank = BankSystem(economy)
        economy.charge(1)
        bank.observe_balance()
        bank.accept_offer()
        for _ in range(79):
            bank.apply_weekly_repayment()

        # Az utolsó részlet előtt helyreálló nemnegatív egyenleg lezárja
        # az előző negatív időszakot.
        economy.money = 144.0
        self.assertFalse(bank.observe_balance())
        self.assertEqual(bank.apply_weekly_repayment(), 145.0)

        self.assertFalse(bank.active_loan)
        self.assertEqual(economy.money, -1.0)
        self.assertTrue(bank.observe_balance())
        self.assertTrue(bank.offer_pending)

    def test_save_load_continues_without_second_credit(self):
        original = SimulationBot(10)
        original.economy.charge(10001)
        original.bank_system.observe_balance()
        original.bank_system.accept_offer()
        for _ in range(3):
            original.bank_system.apply_weekly_repayment()
        money_before_save = original.economy.money
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bank_save.json"
            self.assertTrue(save_game(original.state, path))
            loaded = SimulationBot(11)
            self.assertTrue(load_game(loaded.state, path))
        self.assertEqual(loaded.economy.money, money_before_save)
        self.assertTrue(loaded.bank_system.active_loan)
        self.assertEqual(loaded.bank_system.loan.remaining_weeks, 77)
        self.assertEqual(loaded.bank_system.loan.remaining_balance_cents, 1_116_500)

    def test_market_can_resolve_pending_offer_without_a_loan(self):
        economy = Economy(0)
        bank = BankSystem(economy)
        economy.charge(25)
        self.assertTrue(bank.observe_balance())

        economy.earn(25)
        self.assertTrue(bank.resolve_offer_after_market())
        self.assertFalse(bank.offer_pending)
        self.assertFalse(bank.active_loan)
        self.assertEqual(economy.money, 0)

    def test_market_keeps_offer_pending_while_balance_is_negative(self):
        economy = Economy(0)
        bank = BankSystem(economy)
        economy.charge(25)
        self.assertTrue(bank.observe_balance())

        economy.earn(10)
        self.assertFalse(bank.resolve_offer_after_market())
        self.assertTrue(bank.offer_pending)
        self.assertEqual(economy.money, -15)

    def test_old_save_default_has_no_loan(self):
        bank = BankSystem(Economy())
        bank.load_save_record(None)
        self.assertFalse(bank.active_loan)
        self.assertEqual(bank.loan.remaining_balance_cents, 0)

    def test_simulation_reports_bank_state_without_forcing_a_loan(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_simulation(5, 12345, directory)
        # Az egységes, alacsonyabb fenntartás mellett a mintagazdaság nem
        # kerül mínuszba, ezért nincs szüksége mesterségesen kikényszerített hitelre.
        self.assertEqual(result["loans_taken"], 0)
        self.assertEqual(result["total_bank_repaid"], 0.0)
        self.assertFalse(result["active_loan"])
        self.assertIn("bank_repayments", result["snapshots"][0])


if __name__ == "__main__":
    unittest.main()
