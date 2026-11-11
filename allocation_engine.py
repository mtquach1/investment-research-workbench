"""Cent-sized contribution allocation using a bounded HiGHS mixed-integer model.

Minimize sum_i |(h_i + sum_a x_ai) / V - w_i|. Each account
must invest exactly its available cash, x_ai >= 0 is integer cents,
prohibited purchases are zero, and asset exposure cannot exceed its cap.
No financial inputs, solver messages, or reports are logged or persisted.
"""

from decimal import Decimal, ROUND_FLOOR
from math import ceil
from time import perf_counter

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from allocation_models import (AllocationBaseline, AllocationExposure, AllocationRequest,
                               AllocationResponse, AllocationTrade)


def cents(amount: Decimal) -> int:
    return int(amount * 100)


def _largest_remainder(budget, weights):
    """Deterministic cent allocation, with uniform fallback for zero target mass."""
    if not weights:
        return []
    mass = sum(weights)
    weights = weights if mass else [Decimal(1)] * len(weights)
    mass = sum(weights)
    exact = [Decimal(budget) * weight / mass for weight in weights]
    allocated = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact]
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - allocated[i]), i))
    for index in order[:budget - sum(allocated)]:
        allocated[index] += 1
    return allocated


def allocate_contributions(request: AllocationRequest) -> AllocationResponse:
    # Revalidate even model_copy/model_construct inputs at the calculation boundary.
    request = AllocationRequest.model_validate(request.model_dump())
    started = perf_counter()
    assets, accounts = request.assets, request.accounts
    n, m = len(assets), len(accounts)
    holdings = [sum(cents(account.holdings.get(asset.asset_id, Decimal(0))) for account in accounts)
                for asset in assets]
    budgets = [cents(account.available_cash) for account in accounts]
    total = sum(holdings) + sum(budgets)
    caps = [int((asset.max_weight * total).to_integral_value(rounding=ROUND_FLOOR)) for asset in assets]
    targets = [float(asset.target_weight * total) for asset in assets]
    permitted = [[asset.asset_id in account.allowed_assets for asset in assets] for account in accounts]

    def response(status, explanation, **kwargs):
        return AllocationResponse(status=status, explanation=explanation, total_after_cents=total,
                                  cash_to_invest_cents=sum(budgets),
                                  elapsed_ms=round((perf_counter() - started) * 1000, 3), **kwargs)

    if any(h > cap for h, cap in zip(holdings, caps)):
        return response("infeasible", "Existing holdings exceed a maximum weight even after adding all cash. Sales or revised constraints are required.")
    if any(budget and not any(allowed) for budget, allowed in zip(budgets, permitted)):
        return response("infeasible", "An account has cash but no permitted purchase. Revise permissions or the amount to invest.")
    if sum(caps) < total:
        return response("infeasible", "Maximum weights cannot accommodate the portfolio in whole cents.")

    # x_ai occupies m*n integer variables; n continuous slacks measure absolute drift.
    size = m * n + n
    rows, lower, upper = [], [], []
    variable_upper = np.full(size, np.inf)
    for a in range(m):
        row = np.zeros(size)
        row[a*n:(a+1)*n] = 1
        rows.append(row)
        lower.append(budgets[a])
        upper.append(budgets[a])
        for i in range(n):
            variable_upper[a*n+i] = budgets[a] if permitted[a][i] else 0
    for i in range(n):
        exposure = np.zeros(size)
        exposure[i:m*n:n] = 1
        rows.append(exposure)
        lower.append(-np.inf)
        upper.append(caps[i] - holdings[i])
        positive = exposure.copy()
        positive[m*n+i] = -1
        rows.append(positive)
        lower.append(-np.inf)
        upper.append(targets[i] - holdings[i])
        negative = -exposure
        negative[m*n+i] = -1
        rows.append(negative)
        lower.append(-np.inf)
        upper.append(holdings[i] - targets[i])
    objective = np.zeros(size)
    objective[m*n:] = 1
    try:
        solved = milp(objective, integrality=np.r_[np.ones(m*n), np.zeros(n)],
                      bounds=Bounds(np.zeros(size), variable_upper),
                      constraints=LinearConstraint(np.array(rows), lower, upper),
                      options={"time_limit": 3.0, "node_limit": 10_000, "mip_rel_gap": 0.0})
    except Exception:
        return response("error", "The allocation solver could not complete. No purchase plan was produced.")
    if solved.status == 2:
        return response("infeasible", "Account permissions, cash budgets, and concentration limits cannot all be satisfied. Revise the constraints; no purchases are proposed.")
    if solved.status == 1:
        return response("limit", "The solver reached its work limit. No optimal purchase plan is claimed or returned.")
    if solved.status != 0 or solved.x is None or not np.all(np.isfinite(solved.x)):
        return response("error", "The solver did not establish an optimal allocation. No purchases are proposed.")
    raw = solved.x[:m*n]
    trades = [[int(round(raw[a*n+i])) for i in range(n)] for a in range(m)]

    def feasible(plan):
        return (all(sum(plan[a]) == budgets[a] for a in range(m)) and
                all(plan[a][i] >= 0 and (permitted[a][i] or plan[a][i] == 0)
                    for a in range(m) for i in range(n)) and
                all(holdings[i] + sum(plan[a][i] for a in range(m)) <= caps[i] for i in range(n)))

    def drift(plan):
        return sum(abs(holdings[i] + sum(plan[a][i] for a in range(m)) - targets[i])
                   for i in range(n)) / total

    # Independently check rounded output against original integer-money constraints.
    if (np.max(np.abs(raw - np.rint(raw))) > 1e-4 or not feasible(trades) or
            abs(drift(trades) * total - solved.fun) > 0.001):
        return response("error", "The solver output failed independent accounting checks. No purchases are proposed.")

    def trade_rows(plan):
        return [AllocationTrade(account_id=accounts[a].account_id, asset_id=assets[i].asset_id,
                                amount_cents=plan[a][i]) for a in range(m) for i in range(n) if plan[a][i]]

    baselines = []
    for name, equal in (("target_weight_contributions", False), ("equal_weight_contributions", True)):
        plan = [[0] * n for _ in range(m)]
        for a in range(m):
            indices = [i for i in range(n) if permitted[a][i]]
            weights = [Decimal(1) if equal else assets[i].target_weight for i in indices]
            for i, amount in zip(indices, _largest_remainder(budgets[a], weights)):
                plan[a][i] = amount
        baselines.append(AllocationBaseline(name=name, feasible=feasible(plan),
                                           absolute_weight_drift=drift(plan), trades=trade_rows(plan)))
    # Stronger heuristic: fill largest deficits sequentially, without looking
    # ahead to restrictions on later accounts. Report failure if caps block cash.
    plan = [[0] * n for _ in range(m)]
    running = holdings.copy()
    for a in range(m):
        remaining = budgets[a]
        while remaining:
            candidates = [i for i in range(n) if permitted[a][i] and running[i] < caps[i]]
            if not candidates:
                break
            i = min(candidates, key=lambda i: (-(targets[i] - running[i]), i))
            deficit = targets[i] - running[i]
            amount = min(remaining, caps[i]-running[i], max(1, ceil(deficit)) if deficit > 0 else remaining)
            plan[a][i] += amount
            running[i] += amount
            remaining -= amount
    baselines.append(AllocationBaseline(name="sequential_deficit_first", feasible=feasible(plan),
                                       absolute_weight_drift=drift(plan), trades=trade_rows(plan)))
    purchases = [sum(trades[a][i] for a in range(m)) for i in range(n)]
    exposures = [AllocationExposure(asset_id=asset.asset_id, before_cents=holdings[i],
                                   purchase_cents=purchases[i], after_cents=holdings[i]+purchases[i],
                                   target_weight=float(asset.target_weight),
                                   after_weight=(holdings[i]+purchases[i])/total,
                                   max_weight=float(asset.max_weight)) for i, asset in enumerate(assets)]
    bound = getattr(solved, "mip_dual_bound", None)
    gap = getattr(solved, "mip_gap", None)
    return response("optimal", "Minimum absolute allocation drift found within solver numerical tolerances. All account cash is allocated and original cent-level constraints were checked.",
                    trades=trade_rows(trades), exposures=exposures, absolute_weight_drift=drift(trades),
                    solver_lower_bound_drift=None if bound is None else float(bound)/total,
                    solver_gap=None if gap is None else float(gap), baselines=baselines)
