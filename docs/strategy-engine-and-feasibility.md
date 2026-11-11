# Strategy execution and rental feasibility milestone

Implemented October 28, 2026. The Research workbench contains a **synthetic-only
stock example** and a **manual-assumption rental constraint solver**. Neither
pulls market data, calls AI, saves financial history, or executes trades.

## Stock strategy engine

`stock_strategy.py` executes the [quality/value strategy](stock-strategy-v1.md)
on bounded `SyntheticUniverse` inputs (maximum 600 securities, finite bounded
amounts). Public `POST /research/stock-strategy-demo` accepts only a scenario
enum and cash budget in integer cents. The server generates fixed synthetic IDs
and inputs. No flag enables live recommendations, and there is no public raw
company-data ingestion endpoint disguised as verified inputs.

Eligibility checks financial positivity, capex sign, liability/assets threshold,
financial/filing/price dates, declared history count, sector support and minimum
peer population. The history counts are synthetic inputs, not calculated market
risk. Missing fields are exclusions rather than favorable zeroes. Financials and
Real Estate remain explicitly unsupported by this initial stock model.

Issuer financials and sector must agree across share classes. Pick one eligible
canonical security per issuer by stable ID before calculating sector peer ranks;
alternate classes cannot inflate the peer population. Five feature ratios and
weighted average-tied-rank percentiles use exact Fractions. Tied peers share the
average percentile; all equal peers receive 0.5. Outputs explain exclusions,
percentiles, feature contributions, score, selected identities and targets.

Selection sorts exact scores descending, then stable issuer/security IDs, and
takes ten securities while enforcing at most three per sector. With one
canonical security per issuer and one sector per issuer, this is a partition
quota/cardinality problem: the greedy rule maximizes the stated sum of scores.
A generic optimizer is unnecessary for these particular constraints. More
complex future constraints can invalidate that guarantee and require a new
algorithm. Complexity is O(F*N*log N), F=5, with O(F*N) working storage, excluding
bounded rational-number arithmetic.

Equal target weights are 10% of the funded synthetic basket. Each gets
`floor(budget_cents / 10)`; the residual 0-9 cents remains cash. Budgets below ten
cents cannot fund ten positive purchases. Scores/selection do not depend on
budget. Existing holdings, account restrictions, fees, whole shares and actual
stock selection still require the integrated funding/data stage. The contribution
allocator is a separate component. This demonstration is not a complete live
recommendation pipeline and provides no S&P 500 performance evidence.

The response records the strategy ID and canonical JSON hash. Synthetic-only
status is always visible. Frozen scenarios include balanced coverage, a sector
capacity bottleneck, and missing valuation inputs. Infeasible examples return no
basket rather than weakening diversification or data rules.

Tests compare selection to exhaustive optima in 40 seeded nine-name cases,
including exact tie behavior. They check tied normalization, money conservation,
issuer/share-class handling, input-order invariance, data exclusions, budget
independence and public demo restrictions.

## Rental feasibility engine

`rental_feasibility.py` exposes `POST /real-estate/rental-feasibility` and the
workbench form. Inputs cover capital, rent, bounded price search, optional
candidate price, minimum down-payment fraction, fixed-rate loan assumptions,
fixed/price-based closing costs, initial repairs/held reserves, price-based
property tax, special assessments, insurance, maintenance, HOA, owner utilities,
capex reserves, vacancy/management, minimum annual cash flow and optional minimum
cash-on-cash return.

This version models one fully rented property. Rent and non-price-linked expenses
are fixed across prices. It does not estimate achievable rent, appraisal value,
PMI, lender approval or tax outcomes. The output maximum is conditional on all
entered assumptions. A search-ceiling hit means higher prices were not tested.
Negative cash-flow tolerance does not establish funding for future deficits.

Let P and D be price/down payment in cents, C(P) initial non-down-payment cash
(including held reserves), k annual debt service per cent borrowed, and A(P)
retained rent less all modeled annual non-debt costs, including capex reserves.
Then:

```text
Annual cash flow = A(P) - k*(P-D)
Initial capital = D + C(P)
D >= minimum_down_rate * P
0 <= D <= P
D + C(P) <= available capital
Annual cash flow >= selected dollar target
Annual cash flow >= selected return target * (D + C(P)), if specified
```

At a fixed price these constraints define an integer-cent interval for D.
The return condition's coefficient is `(k - target_return)`: it can impose a
lower bound, an upper bound, or a feasibility condition independent of D. Thus
"more down always improves the return constraint" would be incorrect. An
explicit return target excludes an undefined zero-capital ratio.

All constraint calculations, including loan factors, use exact rational
arithmetic. Price-based tax/closing costs round upward to cents. Reported
cash flow rounds downward to cents; details give a 40-significant-digit decimal
view of the unrounded result, while actual checks remain exact. Both ends of
each reported interval are checked against the original constraints.

With nonnegative price-based costs, lower prices cannot destroy feasibility:
keep the same down payment capped at the lower price, and borrowing/capital
requirements cannot increase. Binary search finds the highest feasible price
cent in O(log(price-range-cents)) interval checks. The supported dollar range
bounds this search; rational arithmetic cost also depends on loan term/rates.
Outputs include maximum-price down-payment range, optional candidate range,
minimum-down cash requirements, remaining cash, cash flow and return, plus a
bound-hit flag and evaluation count. No solution is a normal typed outcome.

Tests independently enumerate every price/down-payment cent in 35 seeded small
cases. They cover closing/tax rounding, zero-interest and equal-factor/return
cases, a return-imposed upper down-payment bound, zero-income all-cash numerical
boundaries, and an independent 70-digit Decimal reference proving the realistic
maximum is feasible while one cent higher is not.

## UI, privacy and remaining release gates

Choose **Research workbench**. Both tabs call the same engines as their typed API
routes directly in Streamlit. Results are explicitly the last submitted snapshot;
invalid inputs clear the previous result and show a fixed error. Clear session
removes both results. There is no private shared cache or persistence added.
Existing data rights, live source coverage, benchmark evaluation, and public
deployment/concurrency/security gates remain open in [the roadmap](PROJECT_ROADMAP.md).

The full local suite passed 231 tests at this milestone. An intermittent Windows
native access-violation diagnostic recurred during the existing allocation/API
test path even though pytest finished with exit 0. An isolated 22-test
allocation/API run passed without it; root cause remains unresolved. Do not
describe local test success as a clean production/runtime certification or hide
the diagnostic by disabling error reporting. Remote Linux CI remains unconfirmed.

Browser QA verified the balanced synthetic basket and default rental scenario in
Research workbench. Under the illustrative rental inputs, the bounded maximum
was $349,535.96 with $78,009.28 down; the $300,000 candidate allowed $60,000-$79,000
down. These are model examples, not Orange County quotes or lender approvals.
The matching local preview is UI8507/API8007.
