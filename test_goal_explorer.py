"""Independent reference calculations, invariants, and plan-file validation."""

from decimal import Decimal, localcontext
import json

from pydantic import ValidationError
import pytest

from goal_explorer import changed_assumptions, explore_goal, export_goal_plan, import_goal_plan
from schemas import GoalExplorerRequest, GoalExplorerSnapshot


def inputs(**updates):
    values = dict(goal_name="Down payment", current_balance=10_000, monthly_contribution=1000,
                  years=1, target_amount_today=30_000, annual_inflation_assumption=0,
                  annual_fee_assumption=0, return_assumptions={"low": 0, "base": 0, "high": 0})
    return GoalExplorerRequest(**{**values, **updates})


def test_zero_return_reference_and_initial_checkpoint():
    result = explore_goal(inputs())
    base = result.scenarios[1]
    assert base.timeline[0].balance_nominal == 10_000
    assert base.timeline[0].growth_nominal == 0
    assert base.timeline[-1].contributions_nominal == 22_000
    assert base.timeline[-1].balance_nominal == 22_000
    assert base.summary.required_monthly_contribution == 1666.67
    assert base.summary.goal_surplus_or_shortfall == -8000


def test_independent_decimal_deposit_reference():
    # Exactly 1% monthly growth. Independently sum each deposit's remaining months.
    with localcontext() as ctx:
        ctx.prec = 40
        monthly = Decimal("1.01")
        annual_return = float(monthly ** 12 - 1)
        expected = Decimal(1000) * sum(monthly ** n for n in range(12))
    request = inputs(current_balance=0, return_assumptions=dict.fromkeys(("low", "base", "high"), annual_return))
    base = explore_goal(request).scenarios[1]
    assert base.timeline[-1].balance_nominal == pytest.approx(float(expected), abs=0.005)
    assert base.summary.projected_balance_nominal == base.timeline[-1].balance_nominal


def test_ten_percent_reference_is_not_twelve_months_return_on_all_deposits():
    result = explore_goal(inputs(current_balance=0, return_assumptions={"low": 0.1, "base": 0.1, "high": 0.1}))
    assert result.scenarios[1].timeline[-1].balance_nominal == 12_540.54
    assert result.scenarios[1].timeline[-1].growth_nominal == 540.54


@pytest.mark.parametrize("years", [1, 15, 60])
def test_timeline_endpoint_matches_existing_model_and_real_accounting(years):
    result = explore_goal(inputs(years=years, annual_inflation_assumption=0.03,
                                 annual_fee_assumption=0.002,
                                 return_assumptions={"low": -0.1, "base": 0.06, "high": 0.09}))
    for scenario in result.scenarios:
        last = scenario.timeline[-1]
        assert len(scenario.timeline) == years + 1
        assert last.balance_nominal == scenario.summary.projected_balance_nominal
        assert last.balance_today == scenario.summary.projected_balance_in_today_dollars
        assert last.balance_nominal == pytest.approx(last.balance_today * 1.03 ** years, abs=1)
        for point in scenario.timeline:
            assert point.balance_nominal == pytest.approx(point.contributions_nominal + point.growth_nominal, abs=0.011)
            assert point.target_today == 30_000
    assert result.scenarios[0].timeline[-1].growth_nominal < 0


def test_ordering_and_contribution_monotonicity():
    request = inputs(return_assumptions={"low": -0.1, "base": 0.03, "high": 0.09})
    result = explore_goal(request)
    assert [s.summary.projected_balance_nominal for s in result.scenarios] == sorted(s.summary.projected_balance_nominal for s in result.scenarios)
    required = [s.summary.required_monthly_contribution for s in result.scenarios]
    assert required == sorted(required, reverse=True)
    more = explore_goal(inputs(monthly_contribution=1100, return_assumptions=request.return_assumptions))
    assert more.scenarios[1].summary.projected_balance_nominal > result.scenarios[1].summary.projected_balance_nominal


def test_already_funded_goal_requires_no_further_deposit():
    result = explore_goal(inputs(current_balance=50_000, monthly_contribution=0))
    assert result.scenarios[1].summary.required_monthly_contribution == 0


@pytest.mark.parametrize("annual_return", [-0.2, 0, 0.07])
def test_solved_deposit_funds_inflated_goal_within_cent_rounding(annual_return):
    request = inputs(years=10, annual_inflation_assumption=0.03,
                     return_assumptions=dict.fromkeys(("low", "base", "high"), annual_return))
    required = explore_goal(request).scenarios[1].summary.required_monthly_contribution
    funded = explore_goal(request.model_copy(update={"monthly_contribution": required})).scenarios[1]
    assert abs(funded.timeline[-1].balance_nominal - funded.timeline[-1].target_nominal) < 2.5


def test_fees_and_inflation_do_not_improve_outcomes():
    baseline = explore_goal(inputs()).scenarios[1].summary
    fee = explore_goal(inputs(annual_fee_assumption=0.01)).scenarios[1].summary
    inflation = explore_goal(inputs(annual_inflation_assumption=0.05)).scenarios[1].summary
    assert fee.projected_balance_nominal < baseline.projected_balance_nominal
    assert inflation.projected_balance_nominal == baseline.projected_balance_nominal
    assert inflation.projected_balance_in_today_dollars < baseline.projected_balance_in_today_dollars
    assert inflation.required_monthly_contribution > baseline.required_monthly_contribution


@pytest.mark.parametrize("updates", [
    {"years": 0}, {"monthly_contribution": -1}, {"current_balance": float("nan")},
    {"target_amount_today": float("inf")}, {"goal_name": " "},
    {"return_assumptions": {"low": 0.1, "base": 0, "high": 0.2}},
    {"return_assumptions": {"low": -0.95, "base": 0, "high": 0.1}, "annual_fee_assumption": 0.1},
])
def test_invalid_explorer_inputs_are_rejected(updates):
    with pytest.raises(ValidationError):
        inputs(**updates)


def test_plan_export_import_roundtrip_and_untrusted_results_rejected():
    snapshot = GoalExplorerSnapshot(model_version="goal-explorer-v1", label="Baseline",
                                    created_at="2026-10-25T00:00:00+00:00", inputs=inputs())
    encoded = export_goal_plan(snapshot)
    assert import_goal_plan(encoded.encode()) == snapshot
    assert explore_goal(import_goal_plan(encoded.encode()).inputs) == explore_goal(snapshot.inputs)
    raw = json.loads(encoded)
    raw["result"] = {"balance": 1_000_000}
    with pytest.raises(ValidationError):
        import_goal_plan(json.dumps(raw).encode())
    raw.pop("result")
    raw.pop("model_version")
    with pytest.raises(ValidationError):
        import_goal_plan(json.dumps(raw).encode())
    raw["model_version"] = "future-version"
    with pytest.raises(ValidationError):
        import_goal_plan(json.dumps(raw).encode())
    with pytest.raises(ValueError, match="32 KB"):
        import_goal_plan(b" " * 32_001)


def test_comparison_explains_changes_and_rejects_different_goal_setup():
    baseline = inputs()
    assert changed_assumptions(baseline, baseline) == []
    changed = changed_assumptions(baseline, inputs(monthly_contribution=1200, years=2))
    assert {row["Assumption"] for row in changed} == {"Monthly Contribution", "Years"}
    with pytest.raises(ValueError, match="same goal"):
        changed_assumptions(baseline, inputs(target_amount_today=100_000))
