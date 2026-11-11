"""Reproducible return-path simulation for educational goal analysis.

The model uses independent, identically distributed monthly log returns calibrated
to a user-entered annual arithmetic return and annualized volatility. It is a
scenario generator, not a forecast or a model of actual market regimes.
"""

from dataclasses import dataclass
from math import exp, isfinite, log, sqrt
from random import Random


@dataclass(frozen=True)
class GoalRiskAnalysis:
    simulation_count: int
    random_seed: int
    annual_return_assumption: float
    annual_volatility_assumption: float
    annual_fee_assumption: float
    target_amount_future_dollars: float | None
    probability_of_reaching_goal: float | None
    ending_balance_p10_in_today_dollars: float
    ending_balance_median_in_today_dollars: float
    ending_balance_p90_in_today_dollars: float
    total_contributions: float
    disclaimer: str = (
        "Illustrative Monte Carlo scenarios from user-entered assumptions. "
        "Returns are modeled as independent lognormal monthly outcomes; real markets can have "
        "regime changes, fat tails, correlations, taxes, and costs beyond the entered fee assumption. "
        "Percentiles and goal probabilities are not forecasts or guarantees."
    )


def _percentile(sorted_values: list[float], quantile: float) -> float:
    """Linearly interpolate an empirical percentile (inclusive endpoints)."""
    position = (len(sorted_values) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def analyze_goal_risk(*, current_balance: float, monthly_contribution: float, years: int,
                      annual_return: float, annual_volatility: float, annual_fee: float,
                      annual_inflation: float, target_amount_today: float | None,
                      simulation_count: int = 2000, random_seed: int = 42) -> GoalRiskAnalysis:
    """Simulate end-of-month contributions across seeded return paths."""
    for name, value in (("current_balance", current_balance), ("monthly_contribution", monthly_contribution),
                        ("annual_fee", annual_fee), ("annual_inflation", annual_inflation)):
        if not isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and non-negative")
    if target_amount_today is not None and (not isfinite(target_amount_today) or target_amount_today < 0):
        raise ValueError("target_amount_today must be finite and non-negative")
    if not isfinite(annual_return) or not -0.95 <= annual_return <= 1.0:
        raise ValueError("annual_return must be between -0.95 and 1.0")
    if not isfinite(annual_volatility) or not 0 <= annual_volatility <= 1.5:
        raise ValueError("annual_volatility must be between 0 and 1.5")
    if annual_fee > 0.1 or annual_inflation > 0.2:
        raise ValueError("annual_fee must be at most 0.1 and annual_inflation at most 0.2")
    if annual_return - annual_fee <= -1:
        raise ValueError("annual return less fees must be greater than -100%")
    if not 1 <= years <= 60:
        raise ValueError("years must be between 1 and 60")
    if not 100 <= simulation_count <= 5000:
        raise ValueError("simulation_count must be between 100 and 5000")
    if not 0 <= random_seed <= 2_147_483_647:
        raise ValueError("random_seed must be between 0 and 2147483647")

    months = years * 12
    monthly_volatility = annual_volatility / sqrt(12)
    expected_net_annual_return = 1 + annual_return - annual_fee
    monthly_log_mean = log(expected_net_annual_return) / 12 - 0.5 * monthly_volatility**2
    inflation_factor = (1 + annual_inflation) ** years
    target_future = None if target_amount_today is None else target_amount_today * inflation_factor
    rng = Random(random_seed)
    ending_balances: list[float] = []
    goals_reached = 0

    for _ in range(simulation_count):
        balance = current_balance
        for _ in range(months):
            # exp(log return) is the gross monthly return; deposits occur at month end.
            balance *= exp(monthly_log_mean + monthly_volatility * rng.gauss(0, 1))
            balance += monthly_contribution
        ending_balances.append(balance)
        if target_future is not None and balance >= target_future:
            goals_reached += 1

    ending_balances.sort()
    real_balances = [value / inflation_factor for value in ending_balances]
    return GoalRiskAnalysis(
        simulation_count=simulation_count,
        random_seed=random_seed,
        annual_return_assumption=annual_return,
        annual_volatility_assumption=annual_volatility,
        annual_fee_assumption=annual_fee,
        target_amount_future_dollars=None if target_future is None else round(target_future, 2),
        probability_of_reaching_goal=None if target_future is None else round(goals_reached / simulation_count, 4),
        ending_balance_p10_in_today_dollars=round(_percentile(real_balances, 0.10), 2),
        ending_balance_median_in_today_dollars=round(_percentile(real_balances, 0.50), 2),
        ending_balance_p90_in_today_dollars=round(_percentile(real_balances, 0.90), 2),
        total_contributions=round(current_balance + monthly_contribution * months, 2),
    )
