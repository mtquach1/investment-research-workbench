# One monthly stock contribution

November 7, 2026. The experimental decision workspace now previews one monthly
deposit against the existing ten-stock equal-weight research baseline, using
the contribution allocator. This is a dollar illustration, not a recommendation,
forecast, recurring schedule or broker integration. No paid data or AI call.

Enter a monthly amount, optionally enter holdings/restrictions, then open
**Preview one monthly contribution** and select **Preview this deposit**.
The three USD totals reconcile deposit = stock additions + cash left aside.
Each row shows before/add/after dollars, its target and why that amount applies.
Optional help explains blocked targets; dates and private JSON are available.

## Accounting and evidence boundaries

- Only entered holdings and this deposit form the denominator. Initial new cash
  and earlier paper proposals are excluded; execution is never assumed.
- The ten baseline stocks retain 10% targets. No exclusion replacement or target
  renormalization; no addition beyond a target. Existing over-target holdings are
  kept without adding; a user cap that cannot be met without selling withholds
  the entire plan. Unknown holdings remain in totals without becoming targets.
- Consent, current reference freshness and existing experimental decision rules
  apply. Horizon, exclusions, volatility and missing/failed company evidence can
  withhold additions. Strict verified-recommendation gates are unchanged.
- Reuses the existing integer-cent L1 allocator, with a zero-target cash asset.
  Account type is descriptive, not tax optimization. Only optimal results with
  independently checked permissions, account sums, integer cents and caps are
  exposed. Other solver states leave the full deposit unassigned. Multiple equally
  optimal solutions are possible; optimality says nothing about investment returns.
- Maximum 29 distinct stock/holding symbols plus cash; a union exceeding that
  limit is rejected without dropping holdings. Caps beyond six decimal places are
  rejected without rounding. Small budgets unable to form the baseline are withheld.
- No sales, transfers, fees, taxes, price/share-lot constraints, ETF look-through,
  forecast or guaranteed/outperformance claim. Fractional shares are assumed.

`POST /research/stock-monthly-contribution` accepts `DecisionContext` and loads
configured server evidence. Returns a typed no-store result with input context,
source fingerprints and strategy/policy versions. No client evidence, provider
calls, database storage or global private cache. UI results are session-only and
invalidate on any input/evidence edit. Private JSON is separate from the existing
decision snapshot/PDF format; it is not restorable through that panel.

## Verification and remaining work

TDD: nine initial engine checks failed on the absent module, then passed; extra
context/exclusion-explanation assertions failed before implementation. Final
focused run: **44 passed**, five dependency warnings, 7.33 seconds, UI/API enabled.
Includes cents/cash invariants, caps, exclusions, unknown/overweight holdings,
consent/staleness, solver rejection, API privacy and UI invalidation plus existing
decision UI/allocation regression tests. Log: `output/tests/monthly-contribution-focused.log`.
The Windows sandbox integration attempt stalled and was stopped; the focused run
completed outside it. No full-suite rerun, browser visual QA, novice study or
live-provider allocation claimed for this milestone.

Next: bounded holding-note portability and tax-lot boundaries, local stock
acceptance/evaluation and observed beginner tasks, then rental discovery. A useful
internship demo is a reproducible synthetic exclusion/cap scenario that shows
cash reconciliation and stale-data withholding, backed by these regression checks.
