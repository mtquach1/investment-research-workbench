"""Deterministic financial-readiness prompts from user-selected assumptions."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal


StrategyCategory = Literal["portfolio", "rental_property", "property_flip", "other"]

WORKLOAD_EXAMPLES = {
    "portfolio": "account setup, contributions, monitoring, and any rebalancing you plan to do",
    "rental_property": "deal sourcing, tenant communication, repairs, vacancies, records, and management oversight",
    "property_flip": "deal sourcing, contractor coordination, permits, inspections, delays, and sale preparation",
    "other": "research, setup, ongoing administration, unexpected tasks, and outsourced oversight",
}


@dataclass(frozen=True)
class FinancialReadinessReview:
    strategy_category: StrategyCategory
    emergency_savings_months: float
    emergency_target_amount: float
    emergency_target_gap: float
    debt_balance_at_highest_apr: float
    highest_debt_apr: float | None
    user_debt_apr_comparison: float | None
    debt_apr_above_user_threshold: bool | None
    liquidity_horizon_months: int | None
    available_monthly_hours: float | None
    estimated_strategy_monthly_hours: float | None
    fits_time_budget: bool | None
    risk_tolerance_rating: int
    risk_capacity_rating: int
    risk_rating_difference: int
    review_prompts: tuple[str, ...]
    disclaimer: str = (
        "Educational self-check only. It does not score readiness, recommend an investment, "
        "model every risk, or replace individualized tax, legal, debt, or investment guidance."
    )


def _bounded_number(name: str, value: float, lower: float, upper: float) -> None:
    if not isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{name} must be between {lower} and {upper}")


def review_financial_readiness(
    *,
    strategy_category: StrategyCategory,
    emergency_savings: float,
    monthly_essential_expenses: float,
    emergency_fund_target_months: float,
    debt_balance_at_highest_apr: float = 0.0,
    highest_debt_apr: float | None = None,
    user_debt_apr_comparison: float | None = None,
    liquidity_horizon_months: int | None = None,
    available_monthly_hours: float | None = None,
    estimated_strategy_monthly_hours: float | None = None,
    risk_tolerance_rating: int,
    risk_capacity_rating: int,
) -> FinancialReadinessReview:
    """Return transparent checks and prompts without producing an overall score.

    The calculation performs a fixed number of checks and arithmetic operations:
    O(1) time and space, independent of balances or time horizon.
    """
    if strategy_category not in WORKLOAD_EXAMPLES:
        raise ValueError("strategy_category must be portfolio, rental_property, property_flip, or other")
    _bounded_number("emergency_savings", emergency_savings, 0, 100_000_000)
    _bounded_number("monthly_essential_expenses", monthly_essential_expenses, 0.01, 10_000_000)
    _bounded_number("emergency_fund_target_months", emergency_fund_target_months, 0.01, 120)
    _bounded_number("debt_balance_at_highest_apr", debt_balance_at_highest_apr, 0, 100_000_000)
    if available_monthly_hours is not None:
        _bounded_number("available_monthly_hours", available_monthly_hours, 0, 1000)
    if highest_debt_apr is not None:
        _bounded_number("highest_debt_apr", highest_debt_apr, 0, 1)
    if user_debt_apr_comparison is not None:
        _bounded_number("user_debt_apr_comparison", user_debt_apr_comparison, 0, 1)
    if estimated_strategy_monthly_hours is not None:
        _bounded_number("estimated_strategy_monthly_hours", estimated_strategy_monthly_hours, 0, 1000)
    if liquidity_horizon_months is not None and not 0 <= liquidity_horizon_months <= 600:
        raise ValueError("liquidity_horizon_months must be between 0 and 600")
    if not 1 <= risk_tolerance_rating <= 5 or not 1 <= risk_capacity_rating <= 5:
        raise ValueError("Risk ratings must be integers from 1 to 5")

    emergency_months = emergency_savings / monthly_essential_expenses
    target_amount = monthly_essential_expenses * emergency_fund_target_months
    target_gap = max(target_amount - emergency_savings, 0)

    debt_comparison: bool | None = None
    if (debt_balance_at_highest_apr > 0 and highest_debt_apr is not None
            and user_debt_apr_comparison is not None):
        debt_comparison = highest_debt_apr > user_debt_apr_comparison

    time_fit = None
    if estimated_strategy_monthly_hours is not None and available_monthly_hours is not None:
        time_fit = estimated_strategy_monthly_hours <= available_monthly_hours

    rating_difference = risk_tolerance_rating - risk_capacity_rating

    if target_gap > 0:
        reserve_prompt = (
            f"Your entered emergency savings cover about {emergency_months:.1f} months, versus your "
            f"self-selected {emergency_fund_target_months:g}-month target; the target gap is ${target_gap:,.2f}. "
            "The reserve amount that makes sense depends on personal circumstances; decide whether these funds "
            "need to remain separate from money exposed to investment loss or access limits."
        )
    else:
        reserve_prompt = (
            f"Your entered reserve meets your self-selected {emergency_fund_target_months:g}-month target. "
            "That target is a planning choice, not a guarantee that every emergency is covered."
        )

    if debt_balance_at_highest_apr <= 0:
        debt_prompt = "No debt balance at a highest APR was entered; this check does not rule out other debt."
    elif highest_debt_apr is None:
        debt_prompt = "Enter the APR on the balance being assessed to compare its interest cost with investment uncertainty."
    elif user_debt_apr_comparison is None:
        debt_prompt = (
            f"You entered a {highest_debt_apr:.1%} APR but no comparison rate. Set your own comparison threshold; "
            "the tool does not define a universal high-interest cutoff."
        )
    elif debt_comparison:
        debt_prompt = (
            f"The entered {highest_debt_apr:.1%} APR exceeds your chosen {user_debt_apr_comparison:.1%} comparison rate. "
            "Compare the debt's interest cost and payoff terms with an investment outcome that can be uncertain or negative."
        )
    else:
        debt_prompt = (
            f"The entered {highest_debt_apr:.1%} APR does not exceed your chosen "
            f"{user_debt_apr_comparison:.1%} comparison rate. This is only a threshold comparison, not a full debt analysis "
            "or a signal that investing is preferable."
        )

    if liquidity_horizon_months is None:
        liquidity_prompt = (
            "Set a date for when you may need these funds. Check how quickly the strategy can be exited, "
            "whether principal may fall, and whether sale or withdrawal costs apply."
        )
    elif liquidity_horizon_months <= 60:
        liquidity_prompt = (
            f"You may need these funds in {liquidity_horizon_months} months. Investor.gov cautions that money for goals "
            "five years or less should not be placed in risky investments because you may need to sell at a loss; "
            "also check access restrictions and exit costs."
        )
    else:
        liquidity_prompt = (
            f"You may need these funds in {liquidity_horizon_months} months. A longer horizon may allow more time to "
            "ride out volatility, but it does not remove loss risk; check access restrictions and exit costs."
        )

    if estimated_strategy_monthly_hours is None or available_monthly_hours is None:
        time_detail = (
            f"You entered {available_monthly_hours:g} available hours per month. "
            if available_monthly_hours is not None else ""
        )
        estimate_detail = (
            f"You estimated {estimated_strategy_monthly_hours:g} strategy hours per month. "
            if estimated_strategy_monthly_hours is not None else ""
        )
        time_prompt = (
            f"{time_detail}{estimate_detail}Enter both available time and strategy workload to compare them. "
            f"For this strategy, include {WORKLOAD_EXAMPLES[strategy_category]}."
        )
    elif time_fit:
        time_prompt = (
            f"Your estimate of {estimated_strategy_monthly_hours:g} hours per month fits within your "
            f"{available_monthly_hours:g}-hour budget. Revisit it for {WORKLOAD_EXAMPLES[strategy_category]}."
        )
    else:
        time_prompt = (
            f"Your estimate of {estimated_strategy_monthly_hours:g} hours per month exceeds your "
            f"{available_monthly_hours:g}-hour budget. Consider whether the workload can realistically fit "
            f"your schedule or be reduced. Include {WORKLOAD_EXAMPLES[strategy_category]} in your estimate."
        )

    if rating_difference > 0:
        risk_prompt = (
            f"Your willingness-to-take-risk rating ({risk_tolerance_rating}/5) is above your loss-capacity rating "
            f"({risk_capacity_rating}/5). Reflect on whether a loss could disrupt obligations or near-term goals."
        )
    elif rating_difference < 0:
        risk_prompt = (
            f"Your loss-capacity rating ({risk_capacity_rating}/5) is above your willingness-to-take-risk rating "
            f"({risk_tolerance_rating}/5). A loss you could financially absorb may still feel too uncomfortable to stay invested."
        )
    else:
        risk_prompt = (
            f"Your willingness-to-take-risk and loss-capacity ratings both equal {risk_tolerance_rating}/5. "
            "Matching self-ratings do not mean the strategy itself has low risk."
        )

    return FinancialReadinessReview(
        strategy_category=strategy_category,
        emergency_savings_months=round(emergency_months, 2),
        emergency_target_amount=round(target_amount, 2),
        emergency_target_gap=round(target_gap, 2),
        debt_balance_at_highest_apr=debt_balance_at_highest_apr,
        highest_debt_apr=highest_debt_apr,
        user_debt_apr_comparison=user_debt_apr_comparison,
        debt_apr_above_user_threshold=debt_comparison,
        liquidity_horizon_months=liquidity_horizon_months,
        available_monthly_hours=available_monthly_hours,
        estimated_strategy_monthly_hours=estimated_strategy_monthly_hours,
        fits_time_budget=time_fit,
        risk_tolerance_rating=risk_tolerance_rating,
        risk_capacity_rating=risk_capacity_rating,
        risk_rating_difference=rating_difference,
        review_prompts=(reserve_prompt, debt_prompt, liquidity_prompt, time_prompt, risk_prompt),
    )
