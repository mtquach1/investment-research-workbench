# Stock strategy specification: quality at a reasonable valuation

Version: `quality-value-annual-v1`. Specified October 28, 2026. **Experimental
research hypothesis; scoring/selection are implemented on synthetic inputs only,
not live recommendations or validated benchmark outperformance.**
See [execution and feasibility notes](strategy-engine-and-feasibility.md).

The machine-readable [strategy definition](../strategies/quality_value_annual_v1.json)
freezes an initial design. These are chosen research defaults, not empirically
optimal constants. Changing them requires a recorded variant/version. The
[master roadmap](PROJECT_ROADMAP.md) remains the implementation order.

## What this strategy would decide

The user's research objective is to beat an S&P 500 **total-return** benchmark
after modeled costs. This is an objective to evaluate, not an achieved result or
guarantee. Use matched dates/external cash flows and a consistent pre-tax basis;
record any investable-proxy fees/tracking differences. Report losses versus the
benchmark alongside wins, drawdown, volatility, turnover, and cost assumptions.
The strategy score itself is not evidence of outperformance. Freeze the design
before held-out evaluation; do not repeatedly tune on the same test window.

Select ten eligible S&P 500 securities with the highest total strategy score,
subject to at most three per sector and one security per issuer. Propose equal
10% target weights, then size contribution-only purchases under actual account
cash/permissions and concentration constraints. The existing allocator can help
size purchases, but cannot replace the eligibility/scoring/selection stages.

Company evidence drives scores. Budget and existing holdings govern what can be
funded. Horizon/liquidity information is disclosed and can restrict proposals;
it is not evidence that one business is better than another. This version does
not infer a suitable equity allocation from age or a questionnaire.

## Eligible inputs and exclusions

- Dated independently verified index membership, stable issuer/security IDs,
  currency-consistent financials, and verified price/issuer market capitalization.
  An ETF holdings proxy cannot satisfy the membership gate.
- Latest complete aligned reported fiscal year whose filing was available at the
  analysis date, period end no older than 550 days. Annual-first is deliberate:
  it avoids premature mixing of quarterly/YTD records. It is not TTM valuation.
  A later TTM model requires its own normalization and validation.
- Positive revenue, net/operating income, operating/free cash flow, beginning/end
  total assets, and issuer equity market capitalization. Nonnegative cash capex.
  Liabilities must be nonnegative and at most 85% of assets. This last ratio
  includes all liabilities, not just interest-bearing debt.
- Initially exclude Financials and Real Estate because these industrial-company
  metrics do not establish comparable screening for those sectors. Keep those
  exclusions visible in full-universe coverage, not silently omitted.
- At least five eligible peers per sector for normalization; otherwise that
  sector is unsupported for this model snapshot. Missing core metrics produce
  an explicit exclusion, not a substituted zero.
- Prices at most seven calendar days old, with a recorded observation date. This
  is an initial audit gate, not a real-time quote guarantee. Three years/756 valid
  daily return observations are required for the proposed risk disclosure; shorter
  histories are insufficient for this version, not automatically low risk.

The initial gates intentionally exclude loss-making companies and some other
potentially successful investments. They define one narrow hypothesis, not a
universal stock selector. No sample company fetched during the data audit is a
recommendation.

## Metric definitions and score

All income/cash-flow metrics use the same fiscal start/end dates. Beginning
assets are the preceding fiscal year-end; ending assets match the income period.
Cash capex means nonnegative cash payments to acquire property, plant and
equipment. FCF is operating cash flow less this capex; it excludes acquisitions
and does not claim to measure owner earnings or adjust stock compensation.

| Feature | Formula | Weight |
| --- | --- | --- |
| Return on assets | Net income / average beginning and ending assets | 20% |
| Operating margin | Operating income / revenue | 20% |
| FCF margin | FCF / revenue | 20% |
| Earnings yield | Annual net income / current issuer equity market cap | 20% |
| FCF yield | Annual FCF / current issuer equity market cap | 20% |

This is 60% profitability/cash quality and 40% valuation. The features share
inputs and are correlated; five features are not five independent sources of
evidence. Market cap must represent the entire issuer's common equity on a
consistent date. Do not substitute diluted weighted-average annual shares times
one share-class price without checking class/share-count compatibility.

For each feature, rank eligible issuers within the same sector from low to high.
Use average ranks for ties, then `percentile = (rank - 1) / (n - 1)`. The score
is the weighted sum of percentiles in [0, 1]. With all peers tied, each receives
0.5. The score expresses relative fit, not return probability, fair value, or an
expected return. Sector-relative normalization does not prove an entire sector
is attractively valued.

## Selection and purchase sizing

Binary `y_i` selects a security. Maximize `sum(score_i * y_i)` subject to:

```text
sum(y_i) = 10
sum(y_i in each sector) <= 3
sum(y_i for each issuer) <= 1
y_i = 0 for prohibited or ineligible securities
```

This first selection problem can be solved by a suitable constrained algorithm;
a new solver is not required for prestige. Compare with independent exhaustive
small cases. Resolve equal-scoring feasible solutions lexicographically by
stable issuer/security IDs, without silently trading off non-tied scores.

Selected securities receive 10% target weights. Account-aware sizing is a
separate problem: use existing holdings, explicitly investable account cash,
permitted purchases, and final position/sector caps. Do not assume that a new
equal-weight target is achievable without selling legacy holdings. If the
existing allocator cannot enforce aggregate sector caps, add that constraint
before presenting the integrated output as compliant. Report actual resulting
weights and target drift; independently validate all final constraints. Never
silently drop restrictions to spend cash or make a recommendation.

For insufficient eligible sectors, data gaps, unverified membership/valuation,
or infeasible funding, return no compliant proposal with the blocking reasons.
Allow an explicitly labeled user override as a separate scenario, preserving
the original proposal. Dollar sizing assumes fractional-share availability;
whole-share execution would require another model. No trades are executed.

## Evidence and evaluation before release

1. Independently check every formula, date/period alignment, unit, tied percentile,
   exclusion reason, selection constraint and cent-level funded allocation.
2. Compare with equal-weight eligible stocks, quality-only, valuation-only and
   an identified broad-market total-return benchmark. Keep evaluation universe,
   dates and portfolio constraints consistent; describe differences explicitly.
3. Test liability thresholds 70/85/95%, quality weights 40/60/80%, sector peer
   minimums and analysis dates. Report membership/weight/ranking instability.
4. Freeze each version before testing. Historical strategy returns require dated
   membership, publication-date-aware fundamentals, delistings/corporate actions,
   cost/rebalance assumptions and held-out evaluation periods. Current members
   replayed backward cannot support that claim.
5. If point-in-time history is unavailable, evaluate correctness and stability and
   record prospective paper snapshots. State the strategy is unvalidated; do not
   replace historical evidence with invented performance.

Success for the first implementation means reproducible decisions, zero violated
hard constraints, explicit no-proposal behavior and understood sensitivity.
Outperformance is a separate empirical claim that may fail. If it fails, report
that outcome rather than tuning repeatedly on the same test period.
