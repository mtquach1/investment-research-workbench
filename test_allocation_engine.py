"""Independent exhaustive oracles and accounting checks for allocation decisions."""

from decimal import Decimal
from itertools import product
from random import Random
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import allocation_engine
from allocation_engine import allocate_contributions
from allocation_models import AllocationRequest
from allocation_ui import example_allocation


def example():
    return AllocationRequest.model_validate(example_allocation())


def test_known_solution_respects_account_permissions_and_beats_baselines():
    result = allocate_contributions(example())
    assert result.status == "optimal"
    assert result.absolute_weight_drift == pytest.approx(0, abs=1e-12)
    assert result.cash_to_invest_cents == 400_000
    assert result.total_after_cents == 1_400_000
    assert {(trade.account_id, trade.asset_id): trade.amount_cents for trade in result.trades} == {
        ("taxable", "STOCKS"): 40_000, ("taxable", "BONDS"): 160_000, ("roth", "BONDS"): 200_000,
    }
    assert all(baseline.feasible and baseline.absolute_weight_drift > result.absolute_weight_drift
               for baseline in result.baselines[:2])
    assert result.solver_lower_bound_drift == pytest.approx(0, abs=1e-12)


def test_tiny_portfolios_match_independent_exhaustive_cent_oracle():
    rng = Random(280)
    for _ in range(32):
        budgets = [rng.randrange(5), rng.randrange(5)]
        initial = [rng.randrange(1, 6), rng.randrange(1, 6)]
        target = Decimal(rng.randrange(1, 10)) / 10
        permissions = [rng.choice([["A"], ["B"], ["A", "B"]]) for _ in range(2)]
        caps = [Decimal(rng.choice([6, 8, 10])) / 10 for _ in range(2)]
        request = AllocationRequest.model_validate({
            "assets": [{"asset_id": "A", "target_weight": target, "max_weight": caps[0]},
                       {"asset_id": "B", "target_weight": 1-target, "max_weight": caps[1]}],
            "accounts": [
                {"account_id": str(a), "account_type": "taxable", "available_cash": Decimal(budgets[a])/100,
                 "holdings": {"A" if a == 0 else "B": Decimal(initial[a])/100},
                 "allowed_assets": permissions[a]} for a in range(2)],
        })
        total = sum(initial) + sum(budgets)
        candidates = []
        for a_purchase, b_purchase in product(range(budgets[0]+1), range(budgets[1]+1)):
            plan = [[a_purchase, budgets[0]-a_purchase], [b_purchase, budgets[1]-b_purchase]]
            if any(plan[a][i] and asset not in permissions[a]
                   for a in range(2) for i, asset in enumerate(["A", "B"])):
                continue
            after = [initial[i] + sum(plan[a][i] for a in range(2)) for i in range(2)]
            if any(Decimal(after[i])/total > caps[i] for i in range(2)):
                continue
            candidates.append(sum(abs(Decimal(after[i])/total-weight)
                                  for i, weight in enumerate([target, 1-target])))
        result = allocate_contributions(request)
        if not candidates:
            assert result.status == "infeasible"
            assert not result.trades
        else:
            assert result.status == "optimal"
            assert result.absolute_weight_drift == pytest.approx(float(min(candidates)), abs=1e-9)
            assert sum(trade.amount_cents for trade in result.trades) == sum(budgets)
            assert all(result.absolute_weight_drift <= baseline.absolute_weight_drift + 1e-9
                       for baseline in result.baselines if baseline.feasible)


def test_joint_permissions_can_make_otherwise_sufficient_caps_infeasible():
    data = example_allocation()
    for account in data["accounts"]:
        account["allowed_assets"] = ["STOCKS"]
    data["assets"][0]["max_weight"] = ".6"
    result = allocate_contributions(AllocationRequest.model_validate(data))
    assert result.status == "infeasible"
    assert not result.trades


def test_cashless_account_and_legacy_prohibited_holdings_are_valid():
    data = example_allocation()
    data["accounts"][0]["available_cash"] = "0"
    data["accounts"][0]["allowed_assets"] = []
    assert allocate_contributions(AllocationRequest.model_validate(data)).status == "optimal"


def test_no_cash_returns_exposure_without_purchases():
    data = example_allocation()
    for account in data["accounts"]:
        account["available_cash"] = "0"
    result = allocate_contributions(AllocationRequest.model_validate(data))
    assert result.status == "optimal"
    assert not result.trades
    assert result.absolute_weight_drift == pytest.approx(.4)


def test_infeasible_baseline_is_identified_instead_of_ranked_as_valid():
    data = example_allocation()
    data["assets"][0]["max_weight"] = ".6"
    result = allocate_contributions(AllocationRequest.model_validate(data))
    assert result.status == "optimal"
    assert any(not baseline.feasible for baseline in result.baselines)


@pytest.mark.parametrize("alter", [
    lambda d: d["assets"][0].update(target_weight=".61"),
    lambda d: d["accounts"][0].update(available_cash="1.001"),
    lambda d: d["accounts"][0].update(available_cash="NaN"),
    lambda d: d["accounts"][0].update(allowed_assets=["UNKNOWN"]),
    lambda d: d["accounts"][0].update(allowed_assets=["STOCKS", "STOCKS"]),
    lambda d: d["accounts"][0].update(holdings={"STOCKS": "-1"}),
    lambda d: d["accounts"][1].update(account_id="taxable"),
])
def test_invalid_financial_inputs_rejected(alter):
    data = example_allocation()
    alter(data)
    with pytest.raises(ValidationError):
        AllocationRequest.model_validate(data)


@pytest.mark.parametrize("status,expected", [(1, "limit"), (2, "infeasible"), (4, "error")])
def test_solver_failure_never_returns_partial_purchase_plan(monkeypatch, status, expected):
    monkeypatch.setattr(allocation_engine, "milp", lambda *a, **k: SimpleNamespace(status=status))
    result = allocate_contributions(example())
    assert result.status == expected
    assert not result.trades
    assert result.absolute_weight_drift is None


def test_independent_accounting_rejects_corrupt_solver_output(monkeypatch):
    monkeypatch.setattr(allocation_engine, "milp", lambda *a, **k: SimpleNamespace(
        status=0, x=allocation_engine.np.zeros(6), fun=0))
    assert allocate_contributions(example()).status == "error"


def test_account_types_do_not_pretend_to_change_tax_objective():
    data = example_allocation()
    first = allocate_contributions(AllocationRequest.model_validate(data))
    data["accounts"][0]["account_type"] = "traditional"
    second = allocate_contributions(AllocationRequest.model_validate(data))
    assert first.absolute_weight_drift == second.absolute_weight_drift
    assert first.trades == second.trades
    assert any("does not optimize taxes" in text for text in second.limitations)


def test_fractional_cent_targets_keep_exact_cash_accounting():
    request = AllocationRequest.model_validate({
        "assets": [{"asset_id": "A", "target_weight": ".333333"},
                   {"asset_id": "B", "target_weight": ".333333"},
                   {"asset_id": "C", "target_weight": ".333334"}],
        "accounts": [{"account_id": "a", "account_type": "taxable", "available_cash": ".01",
                      "allowed_assets": ["A", "B", "C"]}],
    })
    result = allocate_contributions(request)
    assert result.status == "optimal"
    assert sum(row.amount_cents for row in result.trades) == 1
    assert result.trades[0].asset_id == "C"


def test_global_permissions_beat_a_feasible_sequential_greedy_allocation():
    request = AllocationRequest.model_validate({
        "assets": [{"asset_id": "A", "target_weight": ".5"},
                   {"asset_id": "B", "target_weight": ".5"}],
        "accounts": [{"account_id": "flexible", "account_type": "taxable", "available_cash": "100",
                      "allowed_assets": ["A", "B"]},
                     {"account_id": "restricted", "account_type": "roth", "available_cash": "100",
                      "allowed_assets": ["A"]}],
    })
    result = allocate_contributions(request)
    assert result.status == "optimal"
    assert result.absolute_weight_drift == 0
    greedy = next(b for b in result.baselines if b.name == "sequential_deficit_first")
    assert greedy.feasible
    assert greedy.absolute_weight_drift == 1


def test_large_supported_values_and_model_copy_boundary():
    data = example_allocation()
    for account in data["accounts"]:
        account["available_cash"] = "10000000"
        account["holdings"] = {"STOCKS": "10000000", "BONDS": "10000000"}
    request = AllocationRequest.model_validate(data)
    assert allocate_contributions(request).status == "optimal"
    with pytest.raises(ValidationError):
        allocate_contributions(request.model_copy(update={"accounts": []}))
