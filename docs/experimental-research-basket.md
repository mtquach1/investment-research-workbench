# Experimental paper-research basket

October 29, 2026. The user approved keeping verified recommendation gates and
adding a separate opt-in experiment. Open Stocks → Build portfolio → Experimental
research. Acknowledgement is unchecked by default. This feature does not enable
verified recommendations or claim suitability, proven performance or outperformance.

## Selection and funding

The installed real-company sample is filtered for fresh proxy membership,
financial eligibility, supported sectors, a unique directory ticker, fresh prices,
756 complete historical returns and usable estimated valuation inputs. Ambiguous
securities, duplicate issuer evidence and missing inputs are excluded. User stock
exclusions and an optional historical volatility ceiling apply before peer scoring.

Five features receive 20% each: annual return on assets, operating margin, free
cash flow margin, estimated earnings yield and estimated free cash flow yield.
Exact rational tied-rank percentiles are computed within qualified sectors with
at least five peers. The existing deterministic selector maximizes total score
under sector quotas. Ten equal-weight positions are required, with at most three
per sector (editable downward). Infeasible requests produce no basket; rules are
never relaxed. Scores are ranks, not expected returns. Sample and restriction
changes can change ranks and selections.

Budget changes purchase sizes, not attractiveness scores. Integer-cent allocations
divide cash equally; rounding residue remains cash. Indicative fractional shares
use the disclosed dated raw reference price. These are paper purchases with no
fees, existing holdings, execution guarantees, tax optimization or brokerage orders.

## Interface, API and privacy

The separate tab shows stock choices, scores, weights, paper amounts, price dates,
feature contribution bars, exclusions and source/specification hashes. JSON export
is generated in memory. Private budgets are session-only, are not globally cached,
and are not sent to market providers. Removing acknowledgement clears the result.
POST `/research/experimental-basket` uses server-loaded evidence and no-store
responses; callers cannot certify membership or valuation through request fields.
The strict `/research/stock-proposal` path remains a readiness checker with no
selected positions. No acceptance gate or public redistribution restriction changed.

## Measured coverage and limits

Offline audit `output/experimental-stock-audit.json`, October 29:

- 64 financial issuers, 65 installed market series including SPY, 65,194 daily rows.
- 30 financial passes, 11 failures, 23 unavailable; 53 valuation estimates, five
  stale, four multiple-security cases and two unavailable.
- ETF reference dated October 26 contains 505 securities; this sample is not full
  S&P 500 coverage or verified official membership.
- Actual default request filled ten positions in four sectors. This is a current
  paper basket, not a point-in-time historical strategy simulation.

Public release: `4105c67a54a40540088198cd32753694fb1e66094f2169fd1e46e1d0e31e4e9f`.
Market snapshot: `3af0a18d240abb2a2d72e559c982fae486ed6b71a569bd79ccda50b244f1ceb3`.
Previous independent price diagnostics tied to older snapshots are not evidence
for this new snapshot. No missing observation is silently invented.

## Verification and next work

Full suite with RUN_UI_TESTS=1 and RUN_API_REQUEST_TESTS=1: **366 passed, zero
skipped, 39 warnings, 99.07 seconds**. Log:
`output/tests/experimental-basket-full.log`. New tests cover opt-in, independently
known rank/selection results, deterministic ordering, issuer/sector constraints,
cent conservation, infeasible requests, missing evidence, strict-path separation,
HTTP privacy contracts and UI result removal after restriction/acknowledgement changes.
Final chart color, ordering and label changes also passed the focused UI test.
The actual local page was checked for basket construction and contribution chart
rendering. These checks validate software behavior, not investment performance.

Next: reconcile financial and valuation calculations against independent examples,
resolve dated security/index evidence, expand measured coverage and evaluate a
point-in-time strategy with contemporaneously available filings and membership,
transaction costs and held-out benchmark comparisons. Applying today's selected
stocks to past prices would introduce selection/look-ahead bias and is not a
valid strategy backtest. Continue stock stages before new rental milestones.
