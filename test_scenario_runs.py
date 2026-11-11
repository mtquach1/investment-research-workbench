"""SQLite-backed saved-run and comparison checks without HTTP event loops."""

import pytest
from fastapi import HTTPException
from pathlib import Path
from uuid import uuid4

import main
from schemas import CompareGoalRiskRunsRequest, GoalRiskAnalysisRequest, SaveGoalRiskRunRequest


def _test_db_path() -> Path:
    return Path(__file__).with_name(f".scenario-test-{uuid4().hex}.sqlite3")


def _remove_test_db(path: Path) -> None:
    for suffix in ("", "-shm", "-wal"):
        Path(str(path) + suffix).unlink(missing_ok=True)


def _analysis(**overrides: object) -> GoalRiskAnalysisRequest:
    values: dict[str, object] = {
        "current_balance": 10_000,
        "monthly_contribution": 500,
        "years": 10,
        "annual_return_assumption": 0.05,
        "annual_volatility_assumption": 0.10,
        "annual_fee_assumption": 0.002,
        "annual_inflation_assumption": 0.03,
        "target_amount_today": 100_000,
        "simulation_count": 200,
        "random_seed": 42,
    }
    values.update(overrides)
    return GoalRiskAnalysisRequest(**values)  # type: ignore[arg-type]


def test_saved_run_can_be_reopened_listed_and_compared(monkeypatch) -> None:
    database_path = _test_db_path()
    monkeypatch.setattr(main, "settings", main.get_settings().model_copy(update={
        "scenario_db_path": database_path, "app_mode": "local",
    }))
    try:
        baseline = main.create_goal_risk_run(SaveGoalRiskRunRequest(label="Lower return", analysis=_analysis()))
        comparison = main.create_goal_risk_run(SaveGoalRiskRunRequest(
            label="Higher return", analysis=_analysis(annual_return_assumption=0.07, annual_volatility_assumption=0.18),
        ))

        reopened = main.saved_goal_risk_run(baseline.run_id)
        history = main.saved_goal_risk_runs(limit=10)
        delta = main.compare_saved_goal_risk_runs(CompareGoalRiskRunsRequest(
            baseline_run_id=baseline.run_id,
            comparison_run_id=comparison.run_id,
        ))

        assert reopened.inputs.annual_return_assumption == 0.05
        assert reopened.result == baseline.result
        assert len(history.runs) == 2
        assert delta.baseline.label == "Lower return"
        assert delta.comparison.label == "Higher return"
        assert delta.median_balance_delta_today_dollars == (
            comparison.result.ending_balance_median_in_today_dollars
            - baseline.result.ending_balance_median_in_today_dollars
        )
        assert delta.goal_probability_delta is not None
    finally:
        _remove_test_db(database_path)


def test_saved_runs_reject_comparison_with_different_goal_setup(monkeypatch) -> None:
    database_path = _test_db_path()
    monkeypatch.setattr(main, "settings", main.get_settings().model_copy(update={
        "scenario_db_path": database_path, "app_mode": "local",
    }))
    try:
        first = main.create_goal_risk_run(SaveGoalRiskRunRequest(label="One", analysis=_analysis()))
        second = main.create_goal_risk_run(SaveGoalRiskRunRequest(
            label="Different contribution", analysis=_analysis(monthly_contribution=750),
        ))

        with pytest.raises(HTTPException) as error:
            main.compare_saved_goal_risk_runs(CompareGoalRiskRunsRequest(
                baseline_run_id=first.run_id,
                comparison_run_id=second.run_id,
            ))
        assert error.value.status_code == 422
        assert "Align starting balance" in error.value.detail
    finally:
        _remove_test_db(database_path)
