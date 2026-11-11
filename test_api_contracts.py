"""Synchronous API contract checks that do not need an async HTTP test client."""

import pytest
from pydantic import ValidationError

from main import app
from schemas import (CalculateRequest, DebtPayoffRequest, FinancialReadinessRequest, GoalPlanRequest,
                     GoalRiskAnalysisRequest, GoalSensitivityRequest, PortfolioProjectionRequest)


def test_openapi_publishes_supported_routes_and_models() -> None:
    document = app.openapi()
    paths = document["paths"]

    assert set(paths) == {
        "/health",
        "/calculate",
        "/optimize",
        "/scenarios/portfolio",
        "/portfolio/contribution-allocation",
        "/research/stock-strategy-demo",
        "/research/data-readiness",
        "/research/companies",
        "/research/companies/{issuer_key}",
        "/research/companies/{issuer_key}/events",
        "/research/companies/{issuer_key}/market",
        "/research/stock-screen",
        "/research/stock-screen/filter",
        "/research/stock-proposal",
        "/research/experimental-basket",
        "/research/stock-validation",
        "/research/stock-evidence",
        "/research/stock-decisions",
        "/research/stock-decisions/snapshot-review",
        "/research/stock-decisions/report",
        "/research/stock-holding-review",
        "/research/stock-monthly-contribution",
        "/research/stock-replay",
        "/real-estate/rental-feasibility",
        "/real-estate/rental-projection",
        "/scenarios/goal-plan",
        "/scenarios/goal-explorer",
        "/scenarios/goal-risk-analysis",
        "/scenarios/goal-sensitivity",
        "/scenario-runs/goal-risk",
        "/scenario-runs/goal-risk/{run_id}",
        "/scenario-runs/goal-risk/compare",
        "/scenarios/retirement-accounts",
        "/real-estate/rental-underwriting",
        "/real-estate/flip-underwriting",
        "/scenarios/readiness-check",
        "/scenarios/debt-payoff",
    }
    assert paths["/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/HealthResponse")
    assert paths["/calculate"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/TaxMetrics")
    assert paths["/scenarios/goal-plan"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/GoalPlanResponse")
    assert paths["/scenarios/goal-risk-analysis"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/GoalRiskAnalysisResponse")
    assert paths["/scenarios/goal-sensitivity"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/GoalSensitivityResponse")
    assert paths["/scenario-runs/goal-risk"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/SavedGoalRiskRun")
    assert paths["/scenario-runs/goal-risk"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/SavedGoalRiskRunsResponse")
    assert paths["/scenarios/readiness-check"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/FinancialReadinessResponse")
    assert paths["/scenarios/debt-payoff"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/DebtPayoffComparisonResponse")


def test_calculate_request_rejects_invalid_or_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        CalculateRequest(gross_income=-1)
    with pytest.raises(ValidationError):
        CalculateRequest(gross_income=100_000, unexpected_financial_field=123)


def test_goal_plan_request_validates_scenario_rates_and_duration() -> None:
    with pytest.raises(ValidationError):
        GoalPlanRequest(
            goal_name="Down payment",
            monthly_contribution=500,
            years=8,
            return_assumptions={"low": -1.2, "base": 0.05, "high": 0.08},
        )
    with pytest.raises(ValidationError):
        GoalPlanRequest(
            goal_name="Down payment",
            monthly_contribution=500,
            years=61,
            return_assumptions={"low": 0.02, "base": 0.05, "high": 0.08},
        )


def test_goal_risk_request_bounds_simulation_and_risk_parameters() -> None:
    request = GoalRiskAnalysisRequest(
        monthly_contribution=500, years=8, annual_return_assumption=0.06,
        annual_volatility_assumption=0.15,
    )
    assert request.simulation_count == 2000
    assert request.random_seed == 42
    with pytest.raises(ValidationError):
        GoalRiskAnalysisRequest(
            monthly_contribution=500, years=8, annual_return_assumption=0.06,
            annual_volatility_assumption=1.6,
        )
    with pytest.raises(ValidationError):
        GoalRiskAnalysisRequest(
            monthly_contribution=500, years=8, annual_return_assumption=0.06,
            annual_volatility_assumption=0.15, simulation_count=99,
        )


def test_goal_sensitivity_requires_ordered_ranges_containing_base_values() -> None:
    request = GoalSensitivityRequest(
        goal_name="Down payment",
        monthly_contribution=500,
        years=15,
        annual_return_assumption=0.06,
        annual_fee_assumption=0.002,
        annual_inflation_assumption=0.03,
        sensitivity_ranges={
            "monthly_contribution": {"low": 400, "high": 600},
            "annual_return": {"low": 0.04, "high": 0.08},
            "annual_fee": {"low": 0.001, "high": 0.003},
            "annual_inflation": {"low": 0.02, "high": 0.04},
        },
    )
    assert request.sensitivity_ranges.monthly_contribution.low == 400
    with pytest.raises(ValidationError, match="contain the base assumption"):
        GoalSensitivityRequest(
            goal_name="Down payment",
            monthly_contribution=700,
            years=15,
            annual_return_assumption=0.06,
            sensitivity_ranges={
                "monthly_contribution": {"low": 400, "high": 600},
                "annual_return": {"low": 0.04, "high": 0.08},
                "annual_fee": {"low": 0, "high": 0.01},
                "annual_inflation": {"low": 0.02, "high": 0.04},
            },
        )
def test_portfolio_request_accepts_optional_time_budget_and_bounds_hours() -> None:
    request = PortfolioProjectionRequest(
        monthly_contribution=500,
        years=10,
        annual_return_assumption=0.06,
        estimated_monthly_hours=3,
        available_monthly_hours=5,
    )
    assert request.estimated_monthly_hours == 3
    with pytest.raises(ValidationError):
        PortfolioProjectionRequest(
            monthly_contribution=500,
            years=10,
            annual_return_assumption=0.06,
            estimated_monthly_hours=-1,
        )


def test_readiness_request_requires_valid_user_selected_targets() -> None:
    request = FinancialReadinessRequest(
        strategy_category="rental_property",
        emergency_savings=5_000,
        monthly_essential_expenses=2_000,
        emergency_fund_target_months=6,
        available_monthly_hours=5,
        risk_tolerance_rating=3,
        risk_capacity_rating=2,
    )
    assert request.emergency_fund_target_months == 6
    with pytest.raises(ValidationError):
        FinancialReadinessRequest(
            strategy_category="rental_property",
            emergency_savings=5_000,
            monthly_essential_expenses=2_000,
            emergency_fund_target_months=0,
            available_monthly_hours=5,
            risk_tolerance_rating=3,
            risk_capacity_rating=2,
        )


def test_debt_payoff_request_validates_debt_list_and_payment_assumptions() -> None:
    request = DebtPayoffRequest(
        debts=[{"name": "Card", "balance": 1_000, "annual_apr": 0.24, "minimum_monthly_payment": 50}],
        extra_monthly_payment=100,
    )
    assert request.max_months == 600
    with pytest.raises(ValidationError):
        DebtPayoffRequest(
            debts=[{"name": "Card", "balance": 1_000, "annual_apr": 0.24, "minimum_monthly_payment": 0}],
            extra_monthly_payment=100,
        )
