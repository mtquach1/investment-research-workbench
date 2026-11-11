"""Developer-only synthetic PDF fixtures for layout QA; not a production save path."""

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from goal_report import build_goal_report
from schemas import GoalExplorerRequest, GoalExplorerSnapshot


def example(monthly=1000, label="Baseline contribution plan"):
    return GoalExplorerSnapshot(
        model_version="goal-explorer-v1", label=label,
        created_at="2026-10-27T12:00:00+00:00",
        inputs=GoalExplorerRequest(
            goal_name="Home down payment", current_balance=10_000, monthly_contribution=monthly,
            years=10, target_amount_today=150_000, annual_inflation_assumption=0.03,
            annual_fee_assumption=0.002, return_assumptions={"low": 0.02, "base": 0.06, "high": 0.09},
        ),
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    output = root / "output" / "pdf"
    temporary = root / "tmp" / "pdfs"
    output.mkdir(parents=True, exist_ok=True)
    temporary.mkdir(parents=True, exist_ok=True)
    stamp = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
    (output / "illustrative-goal-report.pdf").write_bytes(
        build_goal_report(example(1200, "Higher contribution illustration"), baseline=example(), generated_at=stamp),
    )
    (temporary / "current-plan.pdf").write_bytes(build_goal_report(example(), generated_at=stamp))
    stress_values = example().inputs.model_dump()
    stress_values.update(goal_name="W" * 80, current_balance=100_000_000,
                         monthly_contribution=1_000_000, years=60, target_amount_today=100_000_000,
                         return_assumptions={"low": -0.5, "base": 0.5, "high": 1.0})
    stress = example().model_copy(update={"label": "W" * 80, "inputs": GoalExplorerRequest(**stress_values)})
    (temporary / "stress-case.pdf").write_bytes(build_goal_report(stress, generated_at=stamp))
    print("Synthetic report fixtures generated. No user session data was read.")
