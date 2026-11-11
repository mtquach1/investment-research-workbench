"""Sensitivity-analysis ranking and invariant checks."""

import pytest

from scenario_engine import analyze_goal_sensitivity, project_goal


def _analysis():
    return analyze_goal_sensitivity(
        goal_name="Down payment",
        current_balance=10_000,
        monthly_contribution=500,
        years=15,
        annual_return=0.06,
        annual_fee=0.002,
        annual_inflation=0.03,
        target_amount_today=150_000,
        ranges={
            "annual_return": (0.04, 0.08),
            "monthly_contribution": (400, 600),
            "annual_fee": (0.001, 0.003),
            "annual_inflation": (0.02, 0.04),
        },
    )


def test_sensitivity_ranks_factors_by_projected_balance_span() -> None:
    result = _analysis()
    assert len(result.factors) == 4
    spans = [factor.balance_span_today_dollars for factor in result.factors]
    assert spans == sorted(spans, reverse=True)
    assert [factor.impact_rank for factor in result.factors] == [1, 2, 3, 4]


def test_base_output_matches_deterministic_goal_projection() -> None:
    result = _analysis()
    factor = next(item for item in result.factors if item.assumption == "annual_return")
    baseline = project_goal(
        current_balance=10_000,
        monthly_contribution=500,
        years=15,
        annual_return=0.06,
        annual_fee=0.002,
        annual_inflation=0.03,
        target_amount_today=150_000,
    )
    assert factor.balance_at_base_today_dollars == baseline.projected_balance_in_today_dollars


def test_fee_direction_and_return_direction_are_explained_by_outputs() -> None:
    result = _analysis()
    by_name = {factor.assumption: factor for factor in result.factors}
    assert by_name["annual_return"].balance_at_low_input_today_dollars < by_name["annual_return"].balance_at_high_input_today_dollars
    assert by_name["annual_fee"].balance_at_low_input_today_dollars > by_name["annual_fee"].balance_at_high_input_today_dollars


def test_baseline_must_be_inside_each_sensitivity_range() -> None:
    with pytest.raises(ValueError, match="contain its base assumption"):
        analyze_goal_sensitivity(
            goal_name="Goal", current_balance=0, monthly_contribution=500, years=10,
            annual_return=0.06, annual_fee=0, annual_inflation=0.03, target_amount_today=None,
            ranges={"annual_return": (0.01, 0.05), "monthly_contribution": (0, 1000),
                    "annual_fee": (0, 0.01), "annual_inflation": (0, 0.1)},
        )
