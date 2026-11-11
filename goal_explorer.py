"""Shared Goal Explorer orchestration; no network, database, or global user cache."""

from dataclasses import asdict
from typing import Literal

from scenario_engine import project_goal
from schemas import (GoalExplorerRequest, GoalExplorerResponse, GoalExplorerScenario,
                     GoalExplorerSnapshot, GoalScenarioResponse, GoalTimelinePoint)


def explore_goal(request: GoalExplorerRequest) -> GoalExplorerResponse:
    """Build annual checkpoints using the same month-end model as goal planning."""
    scenarios = []
    for label in ("low", "base", "high"):
        annual_return = getattr(request.return_assumptions, label)
        monthly_factor = (1 + annual_return - request.annual_fee_assumption) ** (1 / 12)
        balance = request.current_balance
        timeline = []
        for month in range(request.years * 12 + 1):
            if month:
                balance = balance * monthly_factor + request.monthly_contribution
            if month % 12:
                continue
            year = month // 12
            inflation = (1 + request.annual_inflation_assumption) ** year
            contributions = request.current_balance + request.monthly_contribution * month
            timeline.append(GoalTimelinePoint(
                year=year, balance_nominal=round(balance, 2), balance_today=round(balance / inflation, 2),
                contributions_nominal=round(contributions, 2),
                contributions_today=round(contributions / inflation, 2),
                growth_nominal=round(balance - contributions, 2),
                growth_today=round((balance - contributions) / inflation, 2),
                target_nominal=round(request.target_amount_today * inflation, 2),
                target_today=request.target_amount_today,
            ))
        summary = project_goal(
            current_balance=request.current_balance, monthly_contribution=request.monthly_contribution,
            years=request.years, annual_return=annual_return,
            annual_fee=request.annual_fee_assumption, annual_inflation=request.annual_inflation_assumption,
            target_amount_today=request.target_amount_today,
        )
        scenarios.append(GoalExplorerScenario(
            summary=GoalScenarioResponse(scenario=label, **asdict(summary)), timeline=timeline,
        ))
    return GoalExplorerResponse(inputs=request, scenarios=scenarios)


def import_goal_plan(raw: bytes) -> GoalExplorerSnapshot:
    """Import only validated inputs, never executable content or trusted outputs."""
    if len(raw) > 32_000:
        raise ValueError("Plan files must be no larger than 32 KB")
    return GoalExplorerSnapshot.model_validate_json(raw)


def export_goal_plan(snapshot: GoalExplorerSnapshot) -> str:
    return snapshot.model_dump_json(indent=2)


def changed_assumptions(baseline: GoalExplorerRequest, comparison: GoalExplorerRequest) -> list[dict]:
    """Reject a different goal setup; identify all remaining changed inputs."""
    for name in ("goal_name", "current_balance", "target_amount_today", "annual_inflation_assumption"):
        if getattr(baseline, name) != getattr(comparison, name):
            raise ValueError("Compare plans for the same goal, starting balance, target, and inflation assumption.")
    rows = []
    for name, label, fmt in (
        ("monthly_contribution", "Monthly Contribution", lambda value: f"${value:,.2f}"),
        ("years", "Years", lambda value: str(value)),
        ("annual_fee_assumption", "Annual fee", lambda value: f"{value:.2%}"),
    ):
        before, after = getattr(baseline, name), getattr(comparison, name)
        if before != after:
            rows.append({"Assumption": label, "Baseline": fmt(before), "Current": fmt(after)})
    for scenario in ("low", "base", "high"):
        before = getattr(baseline.return_assumptions, scenario)
        after = getattr(comparison.return_assumptions, scenario)
        if before != after:
            rows.append({"Assumption": f"{scenario.title()} annual return",
                         "Baseline": f"{before:.2%}", "Current": f"{after:.2%}"})
    return rows


def comparison_checkpoints(baseline: GoalExplorerRequest, current: GoalExplorerRequest,
                          mode: Literal["aligned", "deadlines"] = "aligned") -> tuple[GoalTimelinePoint, GoalTimelinePoint]:
    """Shared UI/report semantics: aligned setup, disclosed evaluation horizons."""
    changed_assumptions(baseline, current)
    if mode not in ("aligned", "deadlines"):
        raise ValueError("Unsupported comparison mode")
    years = (min(baseline.years, current.years),) * 2 if mode == "aligned" else (baseline.years, current.years)
    return tuple(explore_goal(value).scenarios[1].timeline[year]
                 for value, year in zip((baseline, current), years))
