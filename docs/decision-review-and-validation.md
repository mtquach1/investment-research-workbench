# Stock decision review, calculation validation and prospective evaluation

October 29, 2026. This extends the experimental stock workflow while preserving
the verified recommendation gates. It implements the initial useful slices of
alternatives, stability, existing exposure, research navigation and dated follow-up.
It does not finish historical strategy evaluation, full source verification,
personalized rebalancing, ETF look-through or the stock release milestone.

## Independent calculation checks

Stocks → Build portfolio → Validation & evaluation → Calculation checks runs a
second arithmetic implementation over installed inputs. Rational arithmetic
reconciles ROA, operating margin, cash FCF margin, liabilities/assets, split-aware
estimated capitalization and annual valuation yields. Decimal sample variance and
an independent running maximum reconcile all-adjusted volatility and drawdown.
It never calls the production ratio, valuation or risk calculation helpers.

The audit preserves missing/stale inputs and flags discrepancies at relative
tolerance 1e-10 (or absolute 1e-10 for values below one). A passing arithmetic
check is not verification of source tags, period choices or economic assumptions.
Year-over-year growth, all corporate actions and full-universe source correctness
are outside this initial audit. Cash capex excludes noncash additions and is not
a comprehensive economic measure of all reinvestment or dilution.

Two manually read primary-source annual statements are also checked against the
matching installed fiscal years: [Apple FY2025 10-K](https://s2.q4cdn.com/470004039/files/doc_financials/2025/ar/_10-K-2025-As-Filed.pdf)
and [Microsoft FY2025 annual report](https://www.microsoft.com/investor/reports/ar25/).
Eight inputs per issuer are recorded in `data/financial_reference_cases.json`:
revenue, operating income, net income, operating cash, cash capex, beginning and
ending assets, and ending liabilities. The sources report millions, so comparison
scales by 1,000,000 and requires matching issuer/fiscal year. It does not replace
a later revised filing with old values or fill a missing aligned input.

Measured installed result: **500 passes, zero mismatches, 92 unavailable checks**.
Of the 16 official-statement comparisons, 15 match and one is unavailable:
Microsoft FY2025 beginning assets are missing from the locally selected aligned
filing vintage. This is a limitation, not a passing check. The JSON audit includes
the public/market snapshot IDs, evaluation date, formula inputs and reference-file
hash. `GET /research/stock-validation` is no-store and respects local-market mode.

## Understand and investigate a choice

Under Experimental research, the Alternatives and recommendation stability panel
shows feasible one-for-one substitutes at frozen baseline scores. It preserves
sector limits, shows score gaps and the stronger/weaker feature contributions.
It is not a recomputed optimized portfolio or a personal suitability assessment.

The stress control changes both valuation-yield estimates for **one qualified
issuer at a time**, by ±1–50%, then reruns sector scoring and selection. It does
not alter the original screen/basket or present an inconsistent shocked price as
a quote. Input changes invalidate old sensitivity results. This covers valuation
feature uncertainty only, not quality-feature revisions, correlated shocks,
parameter fitting, return probabilities or broad strategy robustness.

Actual installed baseline at ±10%: 46 scenarios, 43 with no replacements and three
with one replacement. This is a deterministic sensitivity result, not a confidence
interval or performance forecast. Audit: `output/basket-sensitivity-audit.json`.

The existing-holdings editor accepts up to 25 unique direct ticker positions with
positive cent amounts and a bounded total. It shows combined entered holdings and
paper additions, duplicate exposure and direct concentration. The illustrative
Portfolio default is never treated as the user's real holdings. ETF constituents,
alternate share-class overlap and sector look-through remain unresolved. No
automatic rebalance or tax-aware trade is issued. Private entries survive
navigation within the session and clear with the workspace.

The company investigation panel opens the existing financial/source, valuation,
price and event workspace for a selected issuer. It does not add a broader news
feed: missing event coverage is explicitly not evidence that no event occurred.

## Dated paper follow-up

Freeze a complete basket assessed today, with a portfolio-level entry cost of
0–1,000 basis points (default 10 = 0.10%). The record captures the server clock,
source/specification hashes, exact issuer mapping, cash, selected companies,
weights and costs. Budget/selection changes leave the frozen record unchanged.
The earliest entry is the first NYSE session strictly after the New York decision
date, at that session's close. This conservative date convention never purchases
at an already-observed close on the decision day.

Track only subsequent installed sessions using matched all-adjusted provider
close ratios. Apply the identical portfolio-level entry-cost policy and initial
cash to SPY, preserve basket cash, and show gross/net values, gains **or losses**
and dollar difference. Missing dates, missing securities, issuer mismatches or
future evidence withhold the comparison. No silent date intersection, missing
security substitution or invented return path is allowed. No rebalancing,
recurring contributions, taxes, sale costs, calibrated risk model, brokerage
execution or exact consolidated reinvested total return is claimed.

Initially the actual record is pending because installed prices end October 28
and its entry must occur after the decision date. Showing no curve is correct.
Independent test prices explicitly exercise losses and cost accounting: a $1,000
basket declining 10% with a 1% entry cost ends at $891; a flat SPY comparator ends
at $990. These are fictional test inputs, never real strategy results.

Up to ten records are session-only, with JSON download/restore for user-controlled
persistence. Restore is limited to 512 KiB, rejects duplicate keys, invalid fields,
invalid funding/sector/issuer constraints, changed checksums, future creation
clocks and duplicate records. A restored timestamp is user-supplied, not attested;
its results are labeled accordingly. A SHA-256 checksum is not a signature or
proof that the record existed at its claimed time. No automatic server saving,
cloud upload, account connection or background refresh was added.

## Evaluation limits and next work

This adds a testable prospective evaluation path and an explicit historical
evaluation gate. It does **not** implement a historical walk-forward strategy
backtest. Current revised filings, today's selected companies and a recent ETF
reference cannot establish what the strategy would have selected years ago.
Contemporaneous filing/valuation vintages, dated membership including removals,
delisting treatment, benchmark conventions, costs, held-out periods and frozen
model versions must be sourced before that gate can open.

Next continue the stocks-first roadmap: independent security/valuation evidence,
coverage expansion and corporate-action validation; broaden point-in-time data
feasibility; finish stock reports and proposal/override comparisons; then user
acceptance. Orange County rentals remain equally required, after stock milestones.

## Verification

Full suite with UI and API request tests enabled: **376 passed, zero skipped,
55 dependency warnings, 42.61s**, log `output/tests/decision-review-final.log`.
Subsequent focused checks of restore UI, reference-file metadata and API privacy:
10 passed; final human-readable audit/API follow-up: two passed. The live local API
returned HTTP 200, no-store and all 592 dated checks. Browser review confirmed
the actual stability chart and froze an illustrative basket with earliest entry
October 30; the follow-up correctly remains pending rather than displaying a
historical performance curve. Tests cover hand-calculated independent ratios, deliberate corruption,
missing facts, fiscal identity/unit scaling, exact sector-feasible swaps, baseline
immutability, sensitivity invalidation, direct exposure, forward entry dates,
cent funding, frozen-record checksums, wrong issuer/date gaps, JSON restore and
benchmark losses after matched costs. Tests do not establish investment quality.
