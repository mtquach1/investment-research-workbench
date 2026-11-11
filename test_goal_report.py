"""PDF content, comparison, privacy, and hostile-label regression checks."""

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
import pytest

from goal_explorer import explore_goal
from goal_report import build_goal_report, money
from schemas import GoalExplorerRequest, GoalExplorerSnapshot


STAMP = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)


def snapshot(label="Example plan", **updates):
    values = dict(goal_name="Home down payment", current_balance=10_000, monthly_contribution=1000,
                  years=10, target_amount_today=150_000, annual_inflation_assumption=0.03,
                  annual_fee_assumption=0.002, return_assumptions={"low": 0.02, "base": 0.06, "high": 0.09})
    return GoalExplorerSnapshot(model_version="goal-explorer-v1", label=label,
                                created_at=STAMP.isoformat(), inputs=GoalExplorerRequest(**{**values, **updates}))


def text_of(data):
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(data)).pages)


def test_report_contains_verified_results_units_versions_and_privacy():
    data = build_goal_report(snapshot(), generated_at=STAMP)
    reader = PdfReader(BytesIO(data))
    text = text_of(data)
    assert data.startswith(b"%PDF-")
    assert len(reader.pages) == 2
    assert not reader.is_encrypted
    assert "$132,737.57" in text
    assert "$1,144.26" in text
    assert "-$17,262.43" in text
    assert "2026-10-27 12:00 UTC" in text
    assert "goal-explorer-v1" in text and "goal-report-pdf-v1" in text
    assert "not encrypted" in text
    assert "JSON export" in text
    assert "not probability bounds" in text
    assert "No stochastic simulation" in text
    assert "Home down payment" not in str(reader.metadata)
    assert reader.trailer["/Root"].get("/OpenAction") is None
    assert reader.trailer["/Root"].get("/Names") is None
    assert all(not page.get("/Annots") for page in reader.pages)


def test_nominal_report_uses_nominal_headline_and_chart_but_labels_real_funding_table():
    plan = snapshot()
    reader = PdfReader(BytesIO(build_goal_report(plan, basis="nominal", generated_at=STAMP)))
    first = reader.pages[0].extract_text()
    base = explore_goal(plan.inputs).scenarios[1].timeline[-1]
    assert money(base.balance_nominal) in first
    assert money(base.contributions_nominal) in first
    assert "Future dollars" in first
    assert "today's $" in reader.pages[1].extract_text()


def test_report_aligned_comparison_matches_common_checkpoint():
    baseline = snapshot(label="Earlier baseline")
    current = snapshot(label="Alternative", years=2, monthly_contribution=1200)
    data = build_goal_report(current, baseline=baseline, generated_at=STAMP)
    reader = PdfReader(BytesIO(data))
    assert len(reader.pages) == 3
    page = reader.pages[2].extract_text()
    assert "common elapsed year" in page
    assert "Earlier baseline" in page and "Alternative" in page
    assert "10 / 2" in page and "2 / 2" in page
    assert "Monthly Contribution" in page
    before = explore_goal(baseline.inputs).scenarios[1].timeline[2]
    after = explore_goal(current.inputs).scenarios[1].timeline[2]
    assert money(after.balance_today - before.balance_today) in page


def test_separate_deadlines_are_explicit_and_unaligned_goals_are_rejected():
    baseline = snapshot()
    current = snapshot(years=2)
    data = build_goal_report(current, baseline=baseline, comparison_mode="deadlines", generated_at=STAMP)
    text = text_of(data)
    assert "Separate deadlines" in text
    assert "10 / 10" in text and "2 / 2" in text
    with pytest.raises(ValueError, match="same goal"):
        build_goal_report(snapshot(target_amount_today=100_000), baseline=baseline)


def test_generator_writes_no_report_or_temporary_files(monkeypatch, tmp_path):
    import builtins
    import tempfile
    original_open = builtins.open

    def read_only(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            raise AssertionError("PDF generator attempted a filesystem write")
        return original_open(file, mode, *args, **kwargs)

    def fail(*_, **__):
        raise AssertionError("PDF generator attempted temporary storage")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(builtins, "open", read_only)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", fail)
    monkeypatch.setattr(tempfile, "mkstemp", fail)
    monkeypatch.setattr(Path, "write_bytes", fail)
    assert build_goal_report(snapshot(), generated_at=STAMP).startswith(b"%PDF-")
    assert list(tmp_path.iterdir()) == []


def test_labels_are_literal_text_and_font_fallback_is_explicit():
    plan = snapshot(label='<img src="https://example.invalid/leak"> & private', goal_name="Café goal 🏡")
    data = build_goal_report(plan, generated_at=STAMP)
    text = text_of(data)
    assert '<img src="https://example.invalid/leak"> & private' in text
    assert "Café goal [U+1F3E1]" in text
    assert "[U+XXXX]" in text
    assert all(not page.get("/Annots") for page in PdfReader(BytesIO(data)).pages)


@pytest.mark.parametrize("updates", [
    {"years": 60, "monthly_contribution": 0, "current_balance": 0, "target_amount_today": 0},
    {"years": 60, "return_assumptions": {"low": -0.5, "base": 0.5, "high": 1}},
    {"goal_name": "W" * 80, "current_balance": 100_000_000, "monthly_contribution": 1_000_000},
])
def test_supported_extremes_produce_readable_page_counts(updates):
    reader = PdfReader(BytesIO(build_goal_report(snapshot(**updates), generated_at=STAMP)))
    assert 2 <= len(reader.pages) <= 3
    assert all("Page " in page.extract_text() for page in reader.pages)


def test_reports_do_not_share_financial_labels_or_accept_invalid_copied_inputs():
    first = text_of(build_goal_report(snapshot(label="UNIQUE-PRIVATE-ONE"), generated_at=STAMP))
    second = text_of(build_goal_report(snapshot(label="UNIQUE-PRIVATE-TWO"), generated_at=STAMP))
    assert "UNIQUE-PRIVATE-TWO" not in first
    assert "UNIQUE-PRIVATE-ONE" not in second
    invalid = snapshot().model_copy(update={"inputs": snapshot().inputs.model_copy(update={"years": 0})})
    with pytest.raises(ValueError):
        build_goal_report(invalid)
    with pytest.raises(ValueError, match="timezone"):
        build_goal_report(snapshot(), generated_at=datetime(2026, 10, 27))


def test_subcent_report_estimate_is_not_presented_as_a_zero_deposit_solution():
    plan = snapshot(current_balance=0, monthly_contribution=0, years=60,
                    return_assumptions={"low": 0.02, "base": 1.0, "high": 1.0})
    text = text_of(build_goal_report(plan, generated_at=STAMP))
    assert "< $0.01 (model)" in text


def test_concurrent_reports_keep_plan_contents_separate():
    from concurrent.futures import ThreadPoolExecutor
    plans = [snapshot(label="CONCURRENT-PRIVATE-A"), snapshot(label="CONCURRENT-PRIVATE-B", monthly_contribution=2000)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda plan: build_goal_report(plan, generated_at=STAMP), plans))
    first, second = map(text_of, results)
    assert "CONCURRENT-PRIVATE-A" in first and "CONCURRENT-PRIVATE-B" not in first
    assert "CONCURRENT-PRIVATE-B" in second and "CONCURRENT-PRIVATE-A" not in second
