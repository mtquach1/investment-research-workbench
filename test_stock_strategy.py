"""Exact ranking, exhaustive constrained-selection oracles and demo boundaries."""

from collections import Counter
from fractions import Fraction
from itertools import combinations
from random import Random

import pytest
from pydantic import ValidationError

from stock_strategy import (StrategyDemoRequest, StrategyDemoResponse, SyntheticStock, SyntheticUniverse,
                            evaluate_synthetic_strategy, select_sector_constrained, strategy_demo, tied_percentiles)


def test_tied_ranks_and_all_equal_scores_are_exact():
    assert tied_percentiles({"A": 10, "B": 20, "C": 20, "D": 40}) == {
        "A": Fraction(0), "B": Fraction(1, 2), "C": Fraction(1, 2), "D": Fraction(1)}
    assert set(tied_percentiles({"A": 5, "B": 5, "C": 5}).values()) == {Fraction(1, 2)}


def test_selection_matches_independent_exhaustive_optima_and_tie_policy():
    rng = Random(2810)
    for _ in range(40):
        rows = [{"issuer_id": f"I{i}", "security_id": f"S{i}", "sector": rng.choice(["A", "B", "C"]),
                 "score": Fraction(rng.randrange(5), 4)} for i in range(9)]
        feasible = [group for group in combinations(rows, 4) if max(Counter(row["sector"] for row in group).values()) <= 2]
        chosen = select_sector_constrained(rows, count=4, sector_limit=2)
        if not feasible:
            assert not chosen
        else:
            best_score = max(sum(row["score"] for row in group) for group in feasible)
            best_ids = min(tuple(sorted(row["issuer_id"] for row in group)) for group in feasible
                           if sum(row["score"] for row in group) == best_score)
            assert sum(row["score"] for row in chosen) == best_score
            assert tuple(sorted(row["issuer_id"] for row in chosen)) == best_ids


def test_balanced_demo_selects_ten_with_caps_and_dollar_accounting():
    result = strategy_demo(StrategyDemoRequest(available_cash_cents=100_003))
    StrategyDemoResponse.model_validate(result)
    assert result["status"] == "synthetic_proposal"
    assert len(result["selected"]) == 10
    assert len({row["issuer_id"] for row in result["selected"]}) == 10
    assert max(Counter(row["sector"] for row in result["selected"]).values()) <= 3
    assert all(row["purchase_cents"] == 10_000 for row in result["selected"])
    assert result["cash_unallocated_cents"] == 3
    assert not result["live_recommendations_enabled"]
    for row in result["findings"]:
        assert row["score"] == pytest.approx(sum(row["score_contributions"].values()))


@pytest.mark.parametrize("scenario", ["sector_bottleneck", "missing_data"])
def test_insufficient_data_or_sector_capacity_returns_no_basket(scenario):
    result = strategy_demo(StrategyDemoRequest(scenario=scenario))
    assert result["status"] == "infeasible"
    assert not result["selected"] and result["objective_score_sum"] is None


def test_budget_does_not_change_scores_or_selection_except_unfundable_cases():
    low = strategy_demo(StrategyDemoRequest(available_cash_cents=1000))
    high = strategy_demo(StrategyDemoRequest(available_cash_cents=100000))
    assert low["findings"] == high["findings"]
    assert strategy_demo(StrategyDemoRequest(available_cash_cents=9))["status"] == "infeasible"


def test_public_demo_schema_does_not_accept_live_inputs_or_verification_flags():
    with pytest.raises(ValidationError):
        StrategyDemoRequest.model_validate({"scenario": "balanced", "verified": True})
    with pytest.raises(ValidationError):
        SyntheticUniverse.model_validate({"data_kind": "live", "as_of": "2026-10-28", "stocks": [], "available_cash_cents": 100})


def observations():
    return [SyntheticStock(security_id=f"SYN_{sector.upper()}_{i}", issuer_id=f"SYN_{sector.upper()}_{i}", sector=sector,
        period_end="2025-12-31", filed="2026-02-01", price_date="2026-10-27", return_observations=756,
        revenue=1000, operating_income=200, net_income=100, operating_cashflow=180, cash_capex=60,
        assets_start=900, assets_end=1100, liabilities=550, issuer_market_cap=2000, price=20)
        for sector in ("Energy", "Materials", "Industrials", "Utilities") for i in range(5)]


def test_share_classes_do_not_inflate_peer_counts_and_input_order_is_irrelevant():
    rows = observations()
    rows.append(rows[0].model_copy(update={"security_id": "SYN_ENERGY_0_ALT"}))
    request = SyntheticUniverse(as_of="2026-10-28", stocks=rows, available_cash_cents=10000)
    first = evaluate_synthetic_strategy(request)
    second = evaluate_synthetic_strategy(request.model_copy(update={"stocks": list(reversed(rows))}))
    assert first == second and first["eligible_issuer_count"] == 20
    alternate = next(row for row in first["findings"] if row["security_id"].endswith("_ALT"))
    assert alternate["reasons"] == ["alternate_share_class"]


def test_missing_future_and_unsupported_data_get_explicit_exclusions():
    from datetime import date
    rows = observations()
    rows[0] = rows[0].model_copy(update={"price_date": date(2026, 10, 29)})
    rows[1] = rows[1].model_copy(update={"issuer_market_cap": None})
    rows[2] = rows[2].model_copy(update={"sector": "Financials"})
    result = evaluate_synthetic_strategy(SyntheticUniverse(as_of="2026-10-28", stocks=rows, available_cash_cents=10000))
    by_id = {row["security_id"]: row for row in result["findings"]}
    assert "stale_or_future_price" in by_id[rows[0].security_id]["reasons"]
    assert "missing_or_nonpositive:issuer_market_cap" in by_id[rows[1].security_id]["reasons"]
    assert "unsupported_sector" in by_id[rows[2].security_id]["reasons"]
