"""Reproducible synthetic evaluation. No market/user data, API calls, or DB access.

Run from the repository root: python tools/evaluate_allocation.py
Outputs only aggregate metrics to stdout; redirect explicitly to save a run.
"""

import json
import platform
from pathlib import Path
from random import Random
from statistics import median
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scipy

from allocation_engine import allocate_contributions
from allocation_models import AllocationRequest


def evaluate(count=100, seed=2802026):
    rng = Random(seed)
    timings = []
    statuses = {}
    comparisons = {name: {"feasible": 0, "improved": 0, "tied": 0, "worse": 0, "drift_reduction": []}
                   for name in ("target_weight_contributions", "equal_weight_contributions", "sequential_deficit_first")}
    cold_start_ms = None
    for case in range(count):
        size = 2 + case % 9
        cuts = [0, *sorted(rng.sample(range(1, 1_000_000), size-1)), 1_000_000]
        weights = [cuts[i+1]-cuts[i] for i in range(size)]
        assets = [{"asset_id": f"A{i}", "target_weight": f"{weight / 1_000_000:.6f}",
                   "max_weight": ".5" if case % 4 == 0 else "1"}
                  for i, weight in enumerate(weights)]
        accounts = []
        for a in range(1 + case % 4):
            allowed = [asset["asset_id"] for asset in assets if rng.random() > .3]
            if not allowed:
                allowed = [assets[0]["asset_id"]]
            accounts.append({"account_id": f"account{a}", "account_type": "taxable",
                             "available_cash": f"{rng.randrange(1, 10_001)}.00",
                             "holdings": {asset["asset_id"]: f"{rng.randrange(20_001)}.00" for asset in assets},
                             "allowed_assets": allowed})
        request = AllocationRequest.model_validate({"assets": assets, "accounts": accounts})
        started = perf_counter()
        result = allocate_contributions(request)
        measured = (perf_counter()-started)*1000
        if cold_start_ms is None:
            cold_start_ms = measured
        timings.append(measured)
        statuses[result.status] = statuses.get(result.status, 0) + 1
        if result.status != "optimal":
            continue
        for baseline in result.baselines:
            if not baseline.feasible:
                continue
            row = comparisons[baseline.name]
            row["feasible"] += 1
            reduction = baseline.absolute_weight_drift - result.absolute_weight_drift
            row["drift_reduction"].append(reduction)
            row["improved" if reduction > 1e-9 else "worse" if reduction < -1e-9 else "tied"] += 1
    for row in comparisons.values():
        reductions = row.pop("drift_reduction")
        row["median_drift_reduction_percentage_points"] = round(median(reductions)*100, 6) if reductions else None
    # Separately exercise the supported variable-count bound, including permissions.
    largest = AllocationRequest.model_validate({
        "assets": [{"asset_id": f"A{i}", "target_weight": ".04" if i < 10 else ".03"} for i in range(30)],
        "accounts": [{"account_id": f"a{a}", "account_type": "roth", "available_cash": "10000",
                      "holdings": {f"A{i}": "1000" for i in range(30)},
                      "allowed_assets": [f"A{i}" for i in range(30) if (i+a) % 3 != 0]}
                     for a in range(8)],
    })
    started = perf_counter()
    large_result = allocate_contributions(largest)
    maximum_ms = (perf_counter()-started)*1000
    return {"seed": seed, "synthetic_cases": count, "python": platform.python_version(),
            "scipy": scipy.__version__, "platform": platform.system(), "statuses": statuses,
            "timing_ms": {"first_case": round(cold_start_ms, 3), "median": round(median(timings), 3),
                          "p95_nearest_rank": round(sorted(timings)[int(.95*len(timings)+.999999)-1], 3),
                          "maximum": round(max(timings), 3)},
            "baselines": comparisons,
            "maximum_dimensions": {"accounts": 8, "assets": 30, "integer_trade_variables": 240,
                                   "status": large_result.status, "elapsed_ms": round(maximum_ms, 3)},
            "limits": "Synthetic allocation-drift evaluation, not investment performance or concurrent-load evidence. Timings exclude process/import startup and vary by hardware."}


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
