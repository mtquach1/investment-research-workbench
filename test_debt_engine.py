"""Regression checks for avalanche and snowball debt payoff scenarios."""

import pytest

from debt_engine import DebtAccount, compare_debt_payoff


def sample_debts() -> list[DebtAccount]:
    return [
        DebtAccount("Card", 5_000, 0.24, 200),
        DebtAccount("Personal loan", 1_500, 0.08, 75),
        DebtAccount("Auto loan", 3_000, 0.12, 100),
    ]


def test_avalanche_and_snowball_share_budget_and_report_different_outcomes() -> None:
    result = compare_debt_payoff(sample_debts(), extra_monthly_payment=500)

    assert result.monthly_payment_budget == 875
    assert result.avalanche.payoff_months == 12
    assert result.snowball.payoff_months == 13
    assert result.avalanche.total_interest == pytest.approx(805.11)
    assert result.snowball.total_interest == pytest.approx(1_087.72)
    assert result.avalanche_interest_minus_snowball == pytest.approx(-282.61)
    assert result.avalanche_months_minus_snowball == -1
    assert result.avalanche.remaining_balance_after_horizon == 0


def test_zero_apr_debt_pays_off_with_exact_fixed_payment_budget() -> None:
    result = compare_debt_payoff([DebtAccount("No interest", 1_200, 0, 100)], extra_monthly_payment=100)

    assert result.avalanche.payoff_months == 6
    assert result.snowball.payoff_months == 6
    assert result.avalanche.total_interest == 0
    assert result.avalanche.total_paid == 1_200
    assert result.avalanche.debt_results[0].payoff_month == 6


def test_minimum_payment_released_by_paid_debt_rolls_into_constant_budget() -> None:
    result = compare_debt_payoff(
        [DebtAccount("Small", 100, 0, 50), DebtAccount("Large", 1_000, 0, 50)],
        extra_monthly_payment=0,
    )

    assert result.monthly_payment_budget == 100
    assert result.avalanche.payoff_months == 11
    assert result.snowball.payoff_months == 11
    assert result.avalanche.total_paid == 1_100


def test_unaffordable_minimum_is_reported_as_unpaid_with_remaining_balance() -> None:
    result = compare_debt_payoff(
        [DebtAccount("Growing balance", 1_000, 1.0, 0.1)],
        extra_monthly_payment=0,
        max_months=12,
    )

    assert result.avalanche.payoff_months is None
    assert result.avalanche.remaining_balance_after_horizon > 1_000
    assert result.avalanche_interest_minus_snowball is None


@pytest.mark.parametrize(
    ("debts", "extra", "months", "message"),
    [
        ([], 0, 12, "between 1 and 10"),
        ([DebtAccount("Invalid", 0, 0.1, 10)], 0, 12, "balance for Invalid"),
        ([DebtAccount("Invalid", 100, 0.1, 0)], 0, 12, "minimum_monthly_payment"),
        (sample_debts(), -1, 12, "extra_monthly_payment"),
        (sample_debts(), 0, 0, "max_months"),
    ],
)
def test_debt_payoff_rejects_invalid_assumptions(
    debts: list[DebtAccount], extra: float, months: int, message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        compare_debt_payoff(debts, extra, months)
