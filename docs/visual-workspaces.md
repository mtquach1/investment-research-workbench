# Visual investment workspaces

Updated October 28, 2026. This is an interaction milestone, not live discovery.

## Navigation

Four destinations: Real estate, Stocks, Goals and Tools. Real estate is the
landing workspace. Goals retains the existing explorer, comparisons, JSON and
PDF flow. Tools contains supporting calculators and earlier research forms.
Existing API contracts remain unchanged.

## Rentals

Capital, rent, mortgage rate, price and down-payment sliders recalculate
automatically. Other costs and requirements are collapsed but still enter the
model. The search ceiling is editable. All amounts are manual assumptions,
not Orange County listings, rent evidence or lender quotes.

- Cash-flow curve shows the debt/capital trade-off. Its shaded down-payment
  interval meets all entered requirements at the inspected price. A purchase
  outside the interval is flagged.
- Capital landscape checks 25 sampled prices plus the exact price limit and
  inspected price. Between-point shading is an interpolated guide. The inspected
  purchase and maximum price come from the cent-level constraint solver.
- Annual waterfall separates collected rent, operating costs, loan payments,
  capital replacement reserves and cash remaining. Rounded monthly outputs may
  introduce a few cents of annual reconciliation difference.
- One pinned baseline per session shows cash-flow and required-capital deltas.
  Its assumptions can be inspected directly.

Charts reuse the exact solver and shared underwriter. Rent and non-price costs
stay fixed across prices. No appreciation, sale, income tax, PMI or lender
qualification is inferred. This does not replace the owner-occupied tool.

## Stocks

A clickable quality/value map links to five weighted feature contributions.
A keyboard-accessible company selector provides an alternative. Each feature
contributes up to twenty points. Quality comprises three features; valuation
comprises two. Scores are sector-relative, not predictions or measured risk.

Balanced, missing-data and sector-bottleneck examples reveal eligibility and
diversification limits. A sector chart shows the thirty-percent cap. Infeasible
baskets leave cash unallocated. Budget affects sizing, not attractiveness.
The fabricated fixture now varies quality/value inputs to expose trade-offs
instead of overlapping identical sector points. Strategy weights are unchanged.
No real company or measured return is displayed.

## State and privacy

Pure helpers live in `investment_visuals.py`; rendering/private session state
live in `investment_workspace_ui.py`. No shared financial cache, database write,
AI call or new network request. Non-widget keys retain assumptions across
navigation. A single rental landscape is cached per session against the full
model-input signature; changing only inspected down payment reuses it. Sampling
is bounded to 41 points. Reset clears inputs/results/baselines and preserves
navigation. Processing remains server-side, not browser-only or secure erasure.

## Verification and next gates

Tests reconcile boundaries, selected purchase capital/cash flow, sensitivity,
empty bands, score contributions and portfolio constraints. Streamlit tests
cover reactive updates, navigation, pinning and clearing plus legacy workflows.
Browser checks exercise actual chart clicks, keyboard sliders and narrow layout.

Still required: verified live stock recommendations, Orange County coverage and
display rights, evidence-backed discovery, aligned comparison/report workflows,
and observed usability tasks. These views do not complete those release gates.

Verification: full suite with RUN_UI_TESTS=1 and RUN_API_REQUEST_TESTS=1: **238 passed, 0 skipped**, exit 0, 127.22 seconds; two dependency deprecation warnings. Final focused visual/interaction checks: **7 passed**. Desktop chart click changed the inspector to SYN_4_0 / 70.0; rent keyboard step changed 3000 to 3100 and cash flow from 3510.44 to 4559.24. A 390px viewport stacked content and had no document overflow. This is browser verification, not observed user testing. The historical intermittent Windows native diagnostic remains an unresolved release concern even though it did not recur in this run. Local preview: http://127.0.0.1:8508/ (API-backed legacy tools configured for port 8007).
