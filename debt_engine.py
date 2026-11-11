"""Debt payoff order comparisons using fixed user-entered assumptions."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal, Sequence


PayoffMethod = Literal["avalanche", "snowball"]


@dataclass(frozen=True)
class DebtAccount:
    name: str
    balance: float
    annual_apr: float
    minimum_monthly_payment: float


@dataclass(frozen=True)
class DebtLineResult:
    name: str
    payoff_month: int | None
    interest_paid: float
    remaining_balance: float


@dataclass(frozen=True)
class DebtPayoffResult:
    method: PayoffMethod
    payoff_months: int | None
    total_interest: float
    total_paid: float
    remaining_balance_after_horizon: float
    debt_results: tuple[DebtLineResult, ...]


@dataclass(frozen=True)
class DebtPayoffComparison:
    monthly_payment_budget: float
    simulation_horizon_months: int
    avalanche: DebtPayoffResult
    snowball: DebtPayoffResult
    avalanche_interest_minus_snowball: float | None
    avalanche_months_minus_snowball: int | None
    disclaimer: str = (
        "Illustrative comparison from fixed user-entered balances, APRs, and minimums. "
        "It excludes new charges, fees, variable rates, changing minimums, promotional terms, and creditor rules."
    )


def _validate_accounts(debts: Sequence[DebtAccount]) -> None:
    if not 1 <= len(debts) <= 10:
        raise ValueError("Provide between 1 and 10 debts")
    for debt in debts:
        if not debt.name.strip():
            raise ValueError("Each debt needs a name")
        for field, amount in (("balance", debt.balance), ("annual_apr", debt.annual_apr),
                              ("minimum_monthly_payment", debt.minimum_monthly_payment)):
            if not isfinite(amount) or amount < 0:
                raise ValueError(f"{field} for {debt.name} must be finite and non-negative")
        if debt.balance <= 0:
            raise ValueError(f"balance for {debt.name} must be greater than zero")
        if debt.annual_apr > 5:
            raise ValueError(f"annual_apr for {debt.name} must be at most 5.0 (500%)")
        if debt.minimum_monthly_payment <= 0:
            raise ValueError(f"minimum_monthly_payment for {debt.name} must be greater than zero")


def _simulate(debts: Sequence[DebtAccount], extra_monthly_payment: float,
              max_months: int, method: PayoffMethod) -> DebtPayoffResult:
    balances = [round(debt.balance, 2) for debt in debts]
    interest_paid = [0.0 for _ in debts]
    payoff_months: list[int | None] = [None for _ in debts]
    total_paid = 0.0
    monthly_budget = sum(debt.minimum_monthly_payment for debt in debts) + extra_monthly_payment

    if method == "avalanche":
        order = sorted(range(len(debts)), key=lambda i: (-debts[i].annual_apr, balances[i], i))
    else:
        order = sorted(range(len(debts)), key=lambda i: (balances[i], -debts[i].annual_apr, i))

    completed_month = 0
    for month in range(1, max_months + 1):
        for index, debt in enumerate(debts):
            if balances[index] > 0:
                interest = round(balances[index] * debt.annual_apr / 12, 2)
                balances[index] = round(balances[index] + interest, 2)
                interest_paid[index] = round(interest_paid[index] + interest, 2)

        budget_remaining = monthly_budget
        for index, debt in enumerate(debts):
            if balances[index] <= 0:
                continue
            payment = min(balances[index], debt.minimum_monthly_payment, budget_remaining)
            balances[index] = round(balances[index] - payment, 2)
            budget_remaining = round(budget_remaining - payment, 2)
            total_paid = round(total_paid + payment, 2)

        for index in order:
            if budget_remaining <= 0:
                break
            if balances[index] <= 0:
                continue
            payment = min(balances[index], budget_remaining)
            balances[index] = round(balances[index] - payment, 2)
            budget_remaining = round(budget_remaining - payment, 2)
            total_paid = round(total_paid + payment, 2)

        for index, balance in enumerate(balances):
            if balance <= 0:
                balances[index] = 0.0
                if payoff_months[index] is None:
                    payoff_months[index] = month

        completed_month = month
        if all(balance == 0 for balance in balances):
            break

    total_interest = round(sum(interest_paid), 2)
    remaining = round(sum(balances), 2)
    payoff_time = completed_month if remaining == 0 else None
    debt_results = tuple(
        DebtLineResult(debt.name, payoff_months[index], round(interest_paid[index], 2), balances[index])
        for index, debt in enumerate(debts)
    )
    return DebtPayoffResult(method, payoff_time, total_interest, total_paid, remaining, debt_results)


def compare_debt_payoff(debts: Sequence[DebtAccount], extra_monthly_payment: float,
                        max_months: int = 600) -> DebtPayoffComparison:
    """Compare avalanche and snowball with a constant total monthly payment budget.

    Each month applies nominal APR/12 interest, pays every debt's fixed minimum,
    then sends remaining budget to the selected priority order. Previously freed
    minimum payments stay in the total budget and roll to the next balance.
    Complexity is O(M * D + D log D) time and O(D) space, where M is months and
    D is number of debts (limited to 10 accounts and 1,200 months by API schema).
    """
    _validate_accounts(debts)
    if not isfinite(extra_monthly_payment) or extra_monthly_payment < 0 or extra_monthly_payment > 1_000_000:
        raise ValueError("extra_monthly_payment must be between 0 and 1000000")
    if not isinstance(max_months, int) or not 1 <= max_months <= 1200:
        raise ValueError("max_months must be between 1 and 1200")

    avalanche = _simulate(debts, extra_monthly_payment, max_months, "avalanche")
    snowball = _simulate(debts, extra_monthly_payment, max_months, "snowball")
    both_paid = avalanche.payoff_months is not None and snowball.payoff_months is not None
    return DebtPayoffComparison(
        monthly_payment_budget=round(sum(debt.minimum_monthly_payment for debt in debts) + extra_monthly_payment, 2),
        simulation_horizon_months=max_months,
        avalanche=avalanche,
        snowball=snowball,
        avalanche_interest_minus_snowball=(
            round(avalanche.total_interest - snowball.total_interest, 2) if both_paid else None
        ),
        avalanche_months_minus_snowball=(
            avalanche.payoff_months - snowball.payoff_months if both_paid else None
        ),
    )
