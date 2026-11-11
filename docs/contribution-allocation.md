# Contribution allocation engine

Implemented October 28, 2026. Model version: `contribution-allocation-l1-v1`.

## Purpose and boundary

Given user-selected portfolio targets, existing holdings, account cash, permitted
purchases, and concentration caps, compute contribution-only purchases minimizing
absolute allocation drift. This is an allocation optimizer, not a return, tax,
Sharpe-ratio, or asset-location optimizer. Account types are descriptive metadata.
Cash must already be available in each account; tax eligibility and affordability
are not inferred. No sales, account transfers, execution, share prices, lots,
commissions, or fractional-share availability checks are included.

The UI's illustrative STOCKS/BONDS labels are user-defined asset buckets. They do
not identify actual securities or prescribe an allocation. The model cannot see
overlapping fund holdings or aggregate exposure across correlated assets.

## Mathematical formulation

All amounts below are in cents. Let `h_i` be total existing asset holdings,
`b_a` account cash, `w_i` target weights, `u_i` maximum weights, and
`V = sum(h_i) + sum(b_a)` the fixed value after investing all cash.

```text
Decision variables: x_ai >= 0, integer cents; d_i >= 0, continuous cents
Objective: minimize sum_i d_i

sum_i x_ai = b_a                         for every account
x_ai = 0                                for prohibited purchases
h_i + sum_a x_ai <= floor(u_i * V)       for every asset
d_i >=  h_i + sum_a x_ai - w_i * V
d_i >= -h_i - sum_a x_ai + w_i * V
```

The output divides the objective by `V` to give the sum of absolute weight
differences. A 10-percentage-point excess paired with a 10-point deficit has
20 points of absolute drift. This differs from half-L1 allocation distance or
risk-based tracking error. L1 can have several equally optimal purchase plans;
there is no implicit tax or account preference to break those ties.

Targets must sum to exactly one, with at most six decimal places. Inputs support
up to 30 assets and eight accounts (240 integer purchase variables plus 30
continuous slacks). Monetary inputs are nonnegative Decimals with at most two
places and a $10 million bound per value. Outputs use integer cents. Existing
holdings may remain in an account where new purchases of that asset are banned.

Maximum weights constrain final aggregate exposures. An overweight existing
position that cannot be diluted by all available cash makes the problem
infeasible because sales are prohibited. Other account/cap interactions can also
make a request infeasible. Targets may exceed caps: the optimizer then finds the
closest feasible allocation, rather than promising an exact target match.

## Solver and correctness evidence

`allocation_engine.py` uses SciPy `milp` with HiGHS. Solver time is bounded at
three seconds and 10,000 nodes with requested relative MIP gap zero. This is a
mixed-integer optimization model; worst-case runtime is not promised polynomial.
Input preparation builds at most 98 dense constraint rows and 270 columns.

Only a solver optimal status can produce purchases. Infeasible, limited, and
failed solves return typed statuses with no partial purchase plan. Original
cent-level budgets, permissions, and cap constraints are independently checked
after solver output is rounded. The computed objective must match the solver
objective within 0.001 cent. Output includes a solver bound and gap when supplied.
Optimality is subject to solver numerical tolerances, not an exact-arithmetic
certificate. The time option bounds solver work, not end-to-end network latency.

Tests independently enumerate every feasible purchase split in 32 seeded tiny
two-asset/two-account portfolios and compare the best objective, including cases
with no solution. Additional tests cover the known worked example, fractional-cent
targets, large values, cashless accounts, legacy prohibited holdings, infeasible
baselines, solver limits, corrupt solver output, and input revalidation.

## Reproducible evaluation

Run `python tools/evaluate_allocation.py` from the repository root. It uses 100
synthetic cases, seed 2802026, varying targets/holdings/account permissions and
periodic concentration caps. Two simple baselines split each account's cash by
permitted target weights or equally, using largest-remainder cent accounting.
A third sequential heuristic purchases the largest remaining deficits account
by account without looking ahead to later accounts' restrictions.
Baselines violating caps are marked infeasible and excluded from comparisons.

An October 28 local run (Python 3.12.14, SciPy 1.18.1, Windows) found 97 optimal
cases and three infeasible cases. Against proportional contributions, it improved
87 of 95 valid comparisons and tied eight, with median absolute-drift reduction
2.639973 percentage points. Against equal contributions, it improved 89 of 96,
tied seven, with median reduction 6.388379 points. No valid comparison was worse.
Against the stronger deficit-first heuristic it improved only two of 97 valid
comparisons and tied 95; median improvement was zero. This is a material limit
on claims of benefit: a good heuristic already matches the optimum in most of
this fixture distribution. An adversarial test demonstrates why joint account
constraints still matter: with two $100 accounts, one unrestricted and one
permitting only A, 50/50 A/B targets require allocating the flexible account to B.
The sequential greedy tie-break buys A first, yielding 100% A; the joint model
finds an exact 50/50 allocation. That example proves a possible failure, not its
frequency in real portfolios.
The maximum-dimension example (eight accounts, 30 assets) also solved optimally.
Observed median latency was about 1.1 ms and p95 about 7.5 ms in that run; those
measurements exclude process/import startup and are hardware-dependent.

This is evidence of allocation-drift performance on this fixture distribution.
It is not historical investment performance, return improvement, calibrated
risk, real user validation, or concurrent-load capacity. The baselines are
transparent, not an exhaustive comparison with allocation algorithms. Broader
constraint distributions and real usage remain untested.

## Interfaces and privacy

- Streamlit: choose **Contribution allocator**, edit three tables, submit
  **Optimize purchases**. Results are explicitly the last submitted snapshot.
- API: `POST /portfolio/contribution-allocation`, typed `AllocationRequest` and
  `AllocationResponse`. HTTP 200 can contain an `infeasible` or `limit` model
  outcome; malformed input returns the API's generic 422.
- Both interfaces call the same engine. The UI works without the API server.
- No AI calls, price feeds, caching, database writes, or trades occur. UI inputs
  and results remain server-side session references until cleared or cleaned up.
- No authentication or public concurrency guarantees have been added. The solver
  runs synchronously in Streamlit and in FastAPI's normal sync-handler thread
  pool; it is not a durable background job service. Concurrent resource limits
  and isolation/load checks remain release gates.

## Worked example

Existing STOCKS $8,000 and BONDS $2,000. Targets 60%/40%, maxima 80%/80%.
Taxable account cash $2,000 permits either asset. Roth account cash $2,000 permits
only BONDS. Final value is $14,000, so target holdings are $8,400/$5,600.

Optimal purchases: taxable STOCKS $400, taxable BONDS $1,600, Roth BONDS $2,000.
Final allocation exactly matches targets. Account labels do not create a tax
benefit; the restriction is explicitly provided by the user.

## Next engineering milestones

The project now requires equally important stock-screening and Orange County
rental-discovery workflows. Reusing this allocator for user-selected stock baskets
is in scope; tax-aware trading extensions below remain deferred;
[PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) is the authoritative product order.

1. Expand solver sensitivity/adversarial evaluations and measure concurrent load.
2. Design tax-lot and account-rule inputs before implementing a separately
   versioned tax-aware sale/location objective; compare it with tax-unaware rules
   under identical assumptions. Never infer future tax rates as facts.
3. Add dated holdings look-through and coverage reporting before claiming actual
   security-level diversification analysis.
4. Demonstrate clean installation, remote CI, and bounded concurrent deployment.

References: [SciPy MILP API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html).
