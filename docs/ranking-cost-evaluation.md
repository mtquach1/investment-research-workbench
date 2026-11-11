# Ranking sensitivity and entry-cost evaluation

Verified November 10, 2026 after the November 7 integration attempt was
interrupted by an approval-review usage limit. **Stocks → Build portfolio →
Validation & evaluation → How sensitive are the rankings, and what could entry
cost?** provides an explicit opt-in evaluation using fixed $1,000.03 examples.

The model reuses the existing one-company sensitivity engine: move both annual
valuation yields by ±10%, one scored issuer at a time, keeping prices and quality
measures fixed. All scored issuers are included up to a 150-issuer limit; larger
cases are withheld rather than silently sampled. Changed-basket counts are
chosen scenarios, not probabilities. Input-order and uniform-yield-scale checks
are included. An alphabetical baseline uses the same eligibility/sector rules;
its 0–10 score total measures the ranking objective, not expected returns.

Entry-cost illustrations compare ten stock purchases with one SPY purchase,
using the same starting cash and fee policy. Percentage costs apply once to
starting cash, rounding half up to cents. Cases are 0%, 0.10%, 0.50% and $1 per
purchase. The last costs $10 versus $1, leaving $990.03 versus $999.03 before
market movement. Fees above cash withhold capital rather than making it negative.
Actual fees, spreads, taxes, sales and later deposits are unmodeled; original
proposals are preserved. These are assumptions, not broker quotes.

TDD uses a hand-calculable fictional universe (strategy score total 8,
alphabetical baseline 2.25), rounding/accounting invariants, unaffordable fees,
consent/staleness, unchanged inputs and UI invalidation/opt-out clearing. The
publication-focused run includes these checks: 23 passed, four dependency
warnings, 12.29 seconds.

The November 10 local installed-data run evaluated 56 yield scenarios; three
changed the basket, retaining at least nine original positions. Input-order and
uniform-scale checks passed. Local artifact:
`output/audits/ranking-cost-evaluation-2026-11-10.json` (excluded from upload).
This is not a strategy backtest, calibrated risk result or outperformance claim.

No provider/AI call, database write, API endpoint, trade or schedule is added.
Results stay in session and clear on evidence changes or withdrawn consent.
`tools/evaluate_ranking_costs.py` reproduces the offline diagnostic; real evidence
is obtained separately and is not bundled in the public source package.
