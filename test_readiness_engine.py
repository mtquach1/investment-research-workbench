"""Regression checks for the deterministic financial-readiness guide."""

import pytest

from readiness_engine import review_financial_readiness


def example_inputs() -> dict[str, object]:
    return {
        "strategy_category": "rental_property",
        "emergency_savings": 8_000,
        "monthly_essential_expenses": 2_000,
        "emergency_fund_target_months": 6,
        "debt_balance_at_highest_apr": 5_000,
        "highest_debt_apr": 0.24,
        "user_debt_apr_comparison": 0.10,
        "liquidity_horizon_months": 36,
        "available_monthly_hours": 4,
        "estimated_strategy_monthly_hours": 6,
        "risk_tolerance_rating": 5,
        "risk_capacity_rating": 2,
    }


def test_readiness_review_exposes_each_dimension_without_a_total_score() -> None:
    result = review_financial_readiness(**example_inputs())

    assert result.emergency_savings_months == 4
    assert result.emergency_target_amount == 12_000
    assert result.emergency_target_gap == 4_000
    assert result.debt_apr_above_user_threshold is True
    assert result.fits_time_budget is False
    assert result.risk_rating_difference == 3
    assert "five years or less" in result.review_prompts[2]
    assert "exceeds" in result.review_prompts[3]
    assert "willingness-to-take-risk" in result.review_prompts[4]
    assert not hasattr(result, "readiness_score")


def test_readiness_review_does_not_invent_debt_threshold_or_time_estimate() -> None:
    inputs = example_inputs()
    inputs["debt_balance_at_highest_apr"] = 0
    inputs["highest_debt_apr"] = None
    inputs["user_debt_apr_comparison"] = None
    inputs["estimated_strategy_monthly_hours"] = None
    result = review_financial_readiness(**inputs)

    assert result.debt_apr_above_user_threshold is None
    assert result.fits_time_budget is None
    assert "No debt balance" in result.review_prompts[1]
    assert "Enter both available time and strategy workload" in result.review_prompts[3]


def test_readiness_review_uses_user_selected_reserve_target() -> None:
    inputs = example_inputs()
    inputs["emergency_savings"] = 20_000
    inputs["risk_tolerance_rating"] = 2
    inputs["risk_capacity_rating"] = 4
    result = review_financial_readiness(**inputs)

    assert result.emergency_target_gap == 0
    assert "self-selected 6-month target" in result.review_prompts[0]
    assert "capacity rating" in result.review_prompts[4]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("monthly_essential_expenses", 0, "monthly_essential_expenses"),
        ("emergency_fund_target_months", 121, "emergency_fund_target_months"),
        ("available_monthly_hours", -1, "available_monthly_hours"),
        ("highest_debt_apr", 1.1, "highest_debt_apr"),
        ("liquidity_horizon_months", 601, "liquidity_horizon_months"),
        ("risk_tolerance_rating", 6, "Risk ratings"),
    ],
)
def test_readiness_review_rejects_out_of_range_values(field: str, value: object, message: str) -> None:
    inputs = example_inputs()
    inputs[field] = value
    with pytest.raises(ValueError, match=message):
        review_financial_readiness(**inputs)
