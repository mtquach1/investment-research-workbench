"""Tests for reproducible goal-risk simulations and model invariants."""

import pytest

from scenario_engine import project_goal
from simulation_engine import analyze_goal_risk


def _run(**overrides: object):
    values: dict[str, object] = {
        "current_balance": 10_000,
        "monthly_contribution": 500,
        "years": 10,
        "annual_return": 0.06,
        "annual_volatility": 0.15,
        "annual_fee": 0.002,
        "annual_inflation": 0.03,
        "target_amount_today": 100_000,
        "simulation_count": 1000,
        "random_seed": 42,
    }
    values.update(overrides)
    return analyze_goal_risk(**values)  # type: ignore[arg-type]


def test_fixed_seed_produces_identical_distribution() -> None:
    assert _run() == _run()


def test_zero_volatility_produces_identical_paths_and_percentiles() -> None:
    result = _run(annual_volatility=0, simulation_count=100)
    deterministic = project_goal(
        current_balance=10_000, monthly_contribution=500, years=10,
        annual_return=0.06, annual_fee=0.002, annual_inflation=0.03,
        target_amount_today=100_000,
    )
    assert result.ending_balance_p10_in_today_dollars == result.ending_balance_median_in_today_dollars
    assert result.ending_balance_median_in_today_dollars == result.ending_balance_p90_in_today_dollars
    assert result.ending_balance_median_in_today_dollars == deterministic.projected_balance_in_today_dollars


def test_higher_volatility_widens_empirical_distribution_with_same_seed() -> None:
    low_vol = _run(annual_volatility=0.05)
    high_vol = _run(annual_volatility=0.30)
    low_width = low_vol.ending_balance_p90_in_today_dollars - low_vol.ending_balance_p10_in_today_dollars
    high_width = high_vol.ending_balance_p90_in_today_dollars - high_vol.ending_balance_p10_in_today_dollars
    assert high_width > low_width


def test_goal_probability_is_omitted_when_target_is_omitted() -> None:
    result = _run(target_amount_today=None)
    assert result.probability_of_reaching_goal is None
    assert result.target_amount_future_dollars is None


def test_target_beyond_maximum_possible_is_never_reached() -> None:
    result = _run(target_amount_today=100_000_000)
    assert result.probability_of_reaching_goal == 0


@pytest.mark.parametrize("bad", [-0.01, 1.51, float("nan")])
def test_invalid_volatility_is_rejected(bad: float) -> None:
    with pytest.raises(ValueError, match="annual_volatility"):
        _run(annual_volatility=bad)


def test_simulation_bounds_are_enforced() -> None:
    with pytest.raises(ValueError, match="simulation_count"):
        _run(simulation_count=5_001)
    with pytest.raises(ValueError, match="random_seed"):
        _run(random_seed=-1)
