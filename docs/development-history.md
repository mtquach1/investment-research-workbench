# Retained implementation history

Historical notes retained during publication preparation. See the main README and current handoff for latest status; old test counts and next-step wording describe earlier milestones.

# Tax & Investment Strategy Optimizer

[Listing calendar correction](listing-calendar-correction.md) restores
correct UTC/local freshness classification. All ten installed-data workflow
checks now pass; verified recommendations remain unavailable.

[Installed evidence refreshed](stock-evidence-refresh-2026-11-07.md): all
references, 89 price series and 88 SEC sources updated. Checks initially reported
7 passed / 3 blocked; the subsequent calendar correction resolves that blocker.

[Connected stock workflow checks](stock-workflow-evaluation.md) now show
passed, blocked and failed example paths. These measure software behavior,
not investment performance; broader stock acceptance remains incomplete.
Latest full regression: **618 passed**, with UI/API checks enabled.

[Personal holding notes](personal-holding-notes.md) can now be downloaded
and reopened without importing company judgments or sale-cost assumptions.

[Monthly stock deposit preview](monthly-stock-contributions.md) shows one
experimental deposit across entered holdings, with exact stock/cash totals and
plain-language reasons. No automatic schedule, trades or return forecast.

[Guided holding review](guided-holding-review.md) adds simpler stock
navigation, personal-reason checks and optional pre-tax sale-cost illustrations.
Explanations use checked rules without paid AI calls; missing evidence stays clear.

[Private stock PDF reports](stock-decision-pdf.md) are available after
recomputing a saved decision. Settings, outcomes, primary reasons, changes and
provenance are exported in memory; edits or unavailable evidence withhold export.

[Private decision snapshots](decision-snapshots.md): save named research
assessments, restore validated JSON, and recompute against current evidence to
inspect changes. Originals are preserved; imported outcomes remain unverified.
Full regression: **569 passed**, with UI/API checks enabled.

**Approved release path (November 6):** a local real-data research edition and a
public synthetic/individually cleared-data demo, both covering stocks and Orange
County rentals. Verified recommendations remain gated. Public-demo isolation and
deployment are still planned; the scope choice does not grant provider rights.

[Historical class/statement links](historical-class-statement-matches.md),
November 3: two dated common-share quantities now match reviewed AAPL/NVDA filing
classes through exact source/context/precision checks. The inspector distinguishes
historical matches from unknown current class counts. Strict gates remain intact.

[Coordinated reference refresh](coordinated-reference-refresh.md): four
stock reference sources publish together only after all pass validation. The
Research screen adds a read-only source-health panel and before/after audit.
Actual October 30 listing/holdings references are installed. A reproducible
offline latency benchmark is included; verified recommendations remain blocked.

[Dated filing share quantities](filing-share-evidence.md): the Apple/NVIDIA
cohort now preserves source contexts, dimensions, scaling and reported precision.
Four same-filing reference checks pass. Optional UI comparison explains why
different share dates/counts cannot be added or assigned to classes automatically.

[Installed class/share ledger](class-share-ledger.md), November 1: research
now traces observed securities and issuer share counts across 88 installed issuers.
The inspector explains why a count cannot yet be assigned to each class. No issuer
has reconciled class quantities; verified valuations and recommendations remain
blocked. No source download or experimental policy change occurred.

[Beginner clarity standard](UI_CLARITY_GUIDELINES.md): the stock Research
screen adds optional term explanations with numerical examples, plain-language
evidence labels and compact status cards. Future milestones include the same
clarity review. Financial calculations and verification gates are unchanged.

[Financial/share-source refresh](fundamental-refresh.md), October 31: all 88
installed SEC sources re-fetched; eight share references changed. Usable valuation
estimates increased from 59 to 64, stale estimates fell from 15 to 10; financial
passes remain 39. Independent validation: 662 pass / zero mismatches / 159
unavailable. The company inspector adds an interactive evidence-date timeline.
Observation dates remain separate from new retrieval receipts; strict gates stay.
Full regression: **474 passed**, with UI/API checks enabled.

[Class and financial evidence](class-and-financial-evidence.md), October 31:
Apple/NVIDIA filing-class corroboration with source hashes and a new inspector
panel; conservative same-filing current/noncurrent liability sums with independent
checks. Financial passes: 39 (previously 36); unavailable: 27 (previously 31).
Independent validation: 648 pass, zero mismatches, 173 unavailable. Full suite:
**465 passed**, UI/API enabled. Strict verification and public-display gates remain.

[Complete-cohort daily price refresh](daily-stock-refresh.md), October 31:
operator-run staging/resume, full-window adjusted-history replacement, atomic
publication, concurrent-writer guards and explicit rollback now work. All 89
installed IEX series were refreshed through October 30 (89,444 observed rows).
Stocks → Build portfolio adds a lazy freshness/recovery panel. Five independent
latest-close diagnostics passed. Full suite: **445 passed**, UI/API enabled.
No automatic schedule, SIP adoption or verification/redistribution gate changes.

[Blocker audit and release decisions](BLOCKER_RESOLUTION_PLAN.md), October 31:
bounded older SIP samples are accessible using configured credentials, but the
production importer remains IEX. Public provider-data permissions, official
membership and the actual verified-selection adapter remain open. This audit
separates feasible local research from conditional public real-data release;
no verification gate or confirmed scope was silently changed.

[Experimental decision workflow](stock-decision-workflow.md), October 31:
Stocks → Build portfolio → Decision workflow now connects an evidence coverage
chart, versioned constraints/policy, and explained candidate/hold/review/pass/
insufficient-evidence assessments. Personal fit does not rewrite strategy scores;
rank removal alone never triggers selling. Private JSON export includes source
and policy hashes. Strict recommendations and automatic refresh remain blocked
or unfinished. Latest full suite: **419 passed**, UI/API enabled.

[Listing evidence and broader coverage](listing-evidence-and-coverage.md)
adds official directory cross-checks (501 corroborated reference securities),
dated listing coverage charts and 24 more issuer records. Installed scope is now
88 issuers / 89 market series. Strict recommendation gates remain in place.
Independent arithmetic reports 640 matching and 168 unavailable checks; five
latest-close diagnostics passed. Navigation now uses size-aware verified file
reads, selective company loading and a lazy source panel. Full suite: 391 passed.

[Decision review and validation](decision-review-and-validation.md) adds
feasible alternatives, basket stability checks, existing direct holdings exposure,
company evidence navigation and frozen prospective paper tracking versus SPY.
Calculation checks independently reconcile installed ratios/valuation/risk and
selected published annual-statement inputs: 500 pass, zero mismatches, 92 unavailable.
Private paper records support JSON download/restore. Historical strategy evaluation
remains withheld for missing point-in-time evidence. Full suite: 376 tests passed.

[Experimental paper-research basket](experimental-research-basket.md) now adds
an explicit opt-in tab under Stocks → Build portfolio. It selects ten equal-weight
research positions from the installed 64-company sample, with sector limits,
editable exclusions, volatility restrictions, score contribution charts and JSON
export. Verified recommendation gates remain in place. This experiment uses proxy
membership and estimated valuations; it is not evidence of beating the S&P 500.
Latest full verification: 366 tests passed with UI/API tests enabled.

The UI now opens into visual **Real estate / Stocks / Goals** workspaces, with
supporting calculators under **Tools**. Rental sliders drive financing bands,
cash-flow curves and a rent waterfall. The synthetic stock lab links company
selection to score contributions and sector weights. Read
[visual workspaces and limitations](visual-workspaces.md).

The public-data pipeline now publishes immutable, hash-verified normalized releases
with atomic publication, last-known-good recovery, selective/cadence-aware refresh,
and per-source failure states. The UI's collapsed coverage panel explains samples,
dates and remaining gaps. `GET /research/data-readiness` serves coverage metadata
without downloading or exposing quote values. Read the
[measured coverage, architecture and refresh commands](public-data-pipeline.md).

Stocks now includes [real company filing research](free-company-research.md)
and [strategy evidence](company-strategy-evidence.md)
for 44 financial research issuers, annual trend charts, period inspection and source
evidence. The SEC directory refresh works; prices and live recommendations remain
separate incomplete gates. Free accounts are allowed, with no paid data.

[News and event context](company-news-events.md) adds filterable SEC filing
timelines for 21 issuers and two manually reviewed official-announcement examples.
Schedules, source dates and coverage gaps stay explicit; headlines do not change
strategy scores. Broad news/calendar refresh remains incomplete.

[Local market history and portfolio dashboard](local-market-history.md)
adds authenticated free IEX research for five companies plus SPY, matched history
and risk charts, and an editable portfolio doughnut in a dark dashboard.
Licensed data stays separate from public releases and is withheld unless local
research is explicitly enabled. Live selection and public data rights remain open.

[Sector and valuation readiness](sector-valuation-readiness.md) adds a dated
sector reference, filing-based share/value estimates and real-company eligibility
inspection. Twenty issuers plus SPY have three adjustment modes; charts include
calendar range presets, area shading, paired hover and a dashed comparison.

[Chart explanations and independent price checks](chart-clarity-and-price-checks.md)
adds share-price / value-of-$100 views, completed-session freshness, a separate
responsive donut legend and a local Yahoo Finance diagnostic.

[Rental holding-period analysis](rental-holding-period.md) adds a monthly cash
ledger, reserve-aware funding failures, loan payoff, selling costs and interactive
base/adverse stress timelines. These remain user-entered forward scenarios.

[Stock verification and metrics](stock-verification-and-metrics.md) expands
research to 44 financial issuers and 45 IEX series including SPY, adds editable
metric/risk filters and visual comparisons, and exposes all 505 reference securities
with explicit coverage gaps. Official membership and current-valuation verification
remain open; the sample does not enable real buy recommendations.

[Split-adjusted prices and historical investment replay](split-prices-and-investment-replay.md)
adds continuous split-price charts, matched recurring-deposit/fee comparisons with
SPY and three-company financial comparisons. Build portfolio currently checks
readiness and constraints; it does not yet generate real stock recommendations.

**Implementation order:** finish the stock workflow first, then Orange County
rental discovery and analysis, then shared comparisons/reports and public release.
This replaces the earlier alternating development order; both pillars remain
required. The current next gate is stock data/security/valuation verification.

**Active product direction (October 28, 2026): two equally important workflows**:
**S&P 500 strategy-based stock selection -> recommended portfolio/purchases -> analysis**, and
**Orange County long-term rental discovery -> property underwriting -> stress
comparison**. Both are required for the final product, with shared scenario
comparisons, reporting, evaluation and deployment. Standalone single-family
rentals remain a provisional housing type pending coverage verification.
Neither live screening/recommendation pipeline is implemented yet. The
[first stock strategy](stock-strategy-v1.md) is specified but unvalidated;
[actual source coverage](data-feasibility-2026-10-28.md) is partially audited.
The public-data download/offline audit foundation now exists alongside the
existing tax, goal, allocation and rental tools. Follow the
[authoritative combined roadmap](PROJECT_ROADMAP.md). Track remaining
coverage and access gates for both [stocks](stock-data-audit.md) and
[Orange County rentals](orange-county-data-audit.md).

A Python 3.11+ FastAPI portfolio project that pairs a deterministic tax engine with an optional language-model interface. The engine owns every tax calculation, contribution cap, and strategy threshold. The LLM can extract facts from natural language into a validated schema and write a narrative around completed calculations; it is not an arithmetic or eligibility authority.

## Scope and tax-year basis

The initial engine supports **single W-2 filers** and the three target gross-income tiers of **$100,000, $250,000, and $500,000**. It uses 2026 federal ordinary income brackets and the 2026 $16,100 single standard deduction. The handoff listed a $15,000 standard deduction and $23,500 401(k) cap, which are not the 2026 amounts: those correspond to 2025-era assumptions. This project uses the published 2026 values: the $24,500 base employee 401(k) deferral limit, $7,500 IRA limit, and Roth IRA direct contribution phase-out for single filers from $153,000 to $168,000 MAGI. The 401(k) model currently excludes age-based catch-up contributions and the special Roth catch-up requirement. The state tax estimate defaults to the requested flat 8%, configurable per request.

The source ledger for the modeled 2026 parameters and their scope is in [docs/tax-rules-2026.md](tax-rules-2026.md).

The **Contribution allocator** adds a defined optimization problem: choose
cent-sized purchases that minimize aggregate allocation drift while respecting
account cash, permitted assets, and final concentration caps. It uses a bounded
mixed-integer solver, checks returned money constraints independently, and
compares three baseline policies. This is contribution-only allocation, not
tax-aware asset location, security selection, or return optimization. Read the
[formulation, evaluation, and limitations](contribution-allocation.md).

The Roth phase-out applies to **direct Roth IRA contributions**. It does not create a legal “backdoor Roth requirement.” A backdoor Roth is a conversion strategy, and pre-tax traditional, SEP, or SIMPLE IRA assets can trigger taxable pro-rata treatment. The calculator surfaces this caveat and does not claim an individualized conversion outcome.

The estimate includes federal ordinary income tax, the flat state estimate, employee Social Security tax up to the 2026 wage base, Medicare tax, and Additional Medicare Tax for single wages above the threshold. The estimate excludes credits, qualified dividends and capital gains, AMT, NIIT, local taxes, detailed itemized-deduction limitations, 2026 special deductions, multiple-employer payroll coordination, and refund/withholding calculations. W-2 401(k) deferrals lower modeled income-tax AGI but do not lower FICA wages. Treat results as educational planning estimates, not a filed return or professional tax advice.

## Architecture

```text
Natural language ──> AI parser ──> Pydantic profile ──> pure Python tax engine ──> metrics
                                                              │                   │
                                                              └──────────────────> AI narrative
Structured inputs ────────────────────────────────────────────┘
```

- `config.py` — Pydantic tax-year tables, limits, environment-backed settings.
- `schemas.py` — strict request, profile, calculation, and response contracts.
- `tax_engine.py` — deterministic functions with no third-party imports; uses progressive brackets and explicit contribution phase-outs.
- `ai_service.py` — OpenAI Responses API structured parsing and narrative formatting. Errors are translated into clear API responses.
- `scenario_engine.py` — standard-library, assumption-driven comparisons for retirement accounts, savings growth, rental/house-hack underwriting, and flips.
- `readiness_engine.py` — self-selected reserve, debt, liquidity, time, and risk prompts without a readiness score or strategy recommendation.
- `debt_engine.py` — avalanche and snowball payoff simulations with a constant total monthly payment budget.
- `simulation_engine.py` — seeded Monte Carlo goal analysis using user-entered return and volatility assumptions, with inflation-adjusted empirical percentiles.
- `scenario_store.py` — explicit local SQLite persistence for goal-risk runs, including exact input/output snapshots and model version.
- `goal_explorer.py` and `goal_explorer_ui.py` — interactive goal workspace with annual trajectories, contribution/deadline controls, optional terminal uncertainty simulation, session comparisons, and validated JSON plan export/import. See [docs/goal-explorer.md](goal-explorer.md).
- `privacy.py` — default session-only policy, explicit local storage/AI gates, and session reset. See [docs/privacy-boundaries.md](privacy-boundaries.md) for the data-flow inventory, retention boundaries, PDF design, and public-release gates.
- `goal_report.py` — in-memory PDF reports recomputed from validated plans, including vector charts and an optional baseline comparison. See [docs/goal-pdf-reports.md](goal-pdf-reports.md).
- `main.py` — FastAPI endpoints, CORS, validation, and orchestration.
- `allocation_models.py`, `allocation_engine.py`, `allocation_ui.py` — cent-sized constrained purchase allocation, independent accounting checks, three baseline comparisons, and a session-only editor. API: `POST /portfolio/contribution-allocation`.
- `streamlit_app.py` — local Python UI for tax estimates, portfolio scenarios, goal risk and sensitivity analysis, saved-run comparisons, rentals, flips, financial readiness, and debt payoff comparisons.
- `api_client.py` — bounded-timeout JSON HTTP client used by the UI to call the FastAPI backend.
- `test_tax_engine.py` — regression coverage of the income tiers, tax calculations, limits, phase-out, and strategy pivots.
- `test_simulation_engine.py` — simulation repeatability, zero-volatility parity with the deterministic goal planner, percentile ordering, and input bounds.
- `test_goal_sensitivity.py` — sensitivity rank ordering, directionality, baseline parity, and range validation.
- `test_scenario_runs.py` — SQLite persistence, run retrieval, aligned comparisons, and dollar-delta checks.
- `test_api_requests.py` and `test_streamlit_app.py` — endpoint and UI-render checks, plus goal-risk save/history/comparison workflows through a temporary localhost API and isolated SQLite database; enabled in CI on Linux.
- `docs/financial-readiness-guide.md` — definitions, calculation method, limitations, and official source ledger for the readiness guide.
- `docs/debt-payoff-model.md` — payoff-order formulas, simplified amortization assumptions, and CFPB source notes.
- `docs/goal-risk-analysis.md` — return-generation formulas, repeatability contract, compute bounds, and simulation limitations.
- `docs/goal-sensitivity.md` — one-variable-at-a-time method, ranking definition, and limitations.
- `docs/saved-scenario-runs.md` — stored fields, model-version behavior, comparison rules, and local-only privacy scope.

## Research workbench

Choose **Research workbench** for the synthetic stock strategy and manual rental
purchase-constraint solver. Stock eligibility, tied feature ranks, sector-constrained
selection, explanations and equal-weight dollar sizing are implemented, but all
company IDs/data are synthetic and no live recommendations can be enabled.
The rental solver finds a bounded maximum price and candidate down-payment range
under explicit cash-flow/return and financing assumptions. It uses exact internal
constraint arithmetic. See [execution and model limits](strategy-engine-and-feasibility.md).

## Latest financial model work

The [annual normalization engine](annual-financial-normalization.md) now
reconciles same-period/same-accession SEC facts into traced financial metrics;
valuation and live stock selection remain blocked on further data work. Run
`python tools/normalize_stock_samples.py --as-of 2026-10-28` on cached samples.
The research objective is S&P 500 total-return outperformance after modeled costs,
not an established outcome.

[Rental model v2](rental-underwriting-v2.md) corrects NOI/capex accounting,
adds held operating reserves, repairs, HOA/utilities, break-even rent and annual
loan accounting. The rental API/UI expose these results and undefined ratios.
It remains manual, pre-tax property underwriting, not automated ZIP rent sourcing.

## Public data coverage audit

Use `python tools/audit_market_data.py --as-of 2026-10-28 --download` to explicitly
fetch missing registered public sources; omit `--download` to reproduce from
local checksum-verified snapshots. Add `--download --refresh` to fetch updates.
Provider bytes live under ignored `data_cache/`, and audit JSON under ignored
`output/audits/`. No user financial inputs or AI are used. The report labels ETF
holdings as a proxy and mixed/metro rent as incompatible with automated single-
family ZIP cash-flow claims. Access is not redistribution approval. See the
[joint feasibility report](data-feasibility-2026-10-28.md) for measured gaps.

## Installation

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
# Default: APP_MODE=ephemeral, ENABLE_AI=false. /calculate needs no API key.
python run_api.py
```

Open the interactive API documentation at `http://127.0.0.1:8000/docs`.

In a second terminal with the same virtual environment active, start the local UI:

```powershell
streamlit run streamlit_app.py
```

The default **Goal Explorer** page runs the shared calculation engines in the Streamlit server process and works without a separate API server or AI key. Its chart-first layout keeps the results full width; a side-by-side layout is also available. Adjust contributions and deadlines, use the calculated monthly estimate, inspect year-by-year outcomes in future or today's dollars, and compare a session baseline at the same elapsed year. Its inputs remain in the session unless explicitly exported; this is server-side processing, not browser-only processing. Imported plan files are uploaded to the Streamlit host and validated before outputs are recomputed.

Use **Prepare PDF report**, then **Download PDF report**, for a readable copy with charts, funding scenarios, assumptions, and an optional selected baseline comparison. Reports are generated in memory without AI, database access, or application-created report files. Changed inputs invalidate the old download. PDFs are not encrypted; keep a JSON export as well to reopen/edit the plan. See [PDF reports](goal-pdf-reports.md) for scope, privacy limits, and verification.

Contribution allocator also runs directly in the Streamlit process without an API server. The remaining calculator pages call FastAPI at `API_BASE_URL` from `.env` (default `http://127.0.0.1:8000`) when submitted. Keep API and UI running in separate terminals for those pages. In default `APP_MODE=ephemeral`, SQLite history and `/optimize` are blocked before request parsing, history navigation is hidden, and database saving is disabled. Merely setting an API key does not enable AI. Existing local databases are preserved but not exposed through these routes.

For **trusted local use only**, set `APP_MODE=local` in `.env` and restart both services to enable unauthenticated SQLite history. AI additionally requires `ENABLE_AI=true` and `OPENAI_API_KEY`; this explicitly enables external processing of submitted financial text and completed metrics. Never use local mode as a multi-user deployment. Explorer never uses AI or database persistence. Keep API/UI settings consistent; a separately hosted API must enforce its own policy.

The sidebar explains these boundaries and provides **Clear session workspace**. Reset removes current session references and returns to defaults; it does not delete downloaded files, local databases, or guarantee secure memory erasure. Repository Streamlit settings disable telemetry, bind to loopback, preserve XSRF/CORS protections, and limit uploads. The API launcher disables URL access logs. Review [privacy boundaries](privacy-boundaries.md) before any public deployment; session-only mode alone is not a release approval.

Run the deterministic regression and contract suite with `python -m pytest -q`. The HTTP request tests use FastAPI's `TestClient`, and Streamlit's `AppTest` renders each page; both are enabled in GitHub Actions on Linux. The UI workflow tests also start a temporary localhost Uvicorn server and use the real HTTP client and an isolated SQLite database. They cover named saves, retrieval, history refresh, displayed comparison deltas, incompatible comparisons, unsaved simulations, and blank save labels. These exercise Streamlit widgets and backend persistence; they do not automate a browser or verify visual layout. GitHub Actions runs compilation and the test suite on Python 3.11 and 3.12 for pushes and pull requests, with a ten-minute job timeout.

To include all integration checks locally, run in a shell that supports threads, event loops, localhost sockets, and temporary files (the restricted Windows sandbox may hang on these checks):

```powershell
$env:RUN_API_REQUEST_TESTS = "1"
$env:RUN_UI_TESTS = "1"
.venv\Scripts\python.exe -m pytest -q
```

The integration suite can run locally outside the Windows sandbox with both flags enabled. A successful GitHub Actions run has not yet been confirmed; this checkout has no Git remote configured. Goal Explorer reference and workflow coverage is described in [docs/goal-explorer.md](goal-explorer.md).

## API

### `POST /calculate`

Deterministic and does not call an LLM. Example:

```json
{
  "gross_income": 250000,
  "filing_status": "single",
  "income_type": "w2",
  "age": 35,
  "traditional_401k_contribution": 24500,
  "other_pretax_adjustments": 0,
  "roth_magi_adjustments": 0,
  "itemized_deductions": null,
  "other_ira_assets": 0,
  "annual_ira_contributions_already_made": 0,
  "state_tax_rate": 0.08
}
```

The response includes the income-tax calculation, payroll taxes, total modeled tax, take-home estimate, IRA eligibility, contribution priorities, and assumptions.

### `POST /optimize`

Requires explicitly configured trusted local mode, `ENABLE_AI=true`, and `OPENAI_API_KEY`. Otherwise returns 404. Both AI requests set `store=False`; this does not promise zero provider retention. Example request:

```json
{"text":"I make $250,000 as a W-2 engineer, age 35, and have no traditional IRA balances. I want to save for retirement."}
```

The parser returns the same strict profile shape used by `/calculate`; Python then calculates the metrics. The formatter is only given completed metrics and is instructed not to state or modify financial figures. The response's `metrics` object is the source of truth.

### `GET /health`

Returns health, configured tax year, and whether AI parsing is enabled.

### Scenario and real-estate calculators

All of these use user-entered assumptions. They do not pull security prices, forecast returns, provide appraisals, or fetch ZIP-code rent and home-price data yet.

- `POST /scenarios/portfolio` compounds monthly contributions under a stated annual return and fee assumption, separating deposits from hypothetical growth. Optional time inputs report estimated monthly hours, the user's available monthly hours, budget utilization, and whether the estimate fits.
- `POST /scenarios/goal-plan` estimates how much a savings or investment account could hold after a chosen number of years for a named goal, such as a down payment, car, or retirement. It returns low/base/high scenarios using the returns you provide, includes current savings and monthly contributions, adjusts the future target for inflation, and calculates both the target gap and the monthly contribution needed to reach it under each scenario.
- `POST /scenarios/goal-explorer` uses the goal-plan inputs with a required target and ordered low/base/high returns. It returns model-versioned inputs, annual trajectories including year zero, nominal and today's-dollar accounting, and each scenario's contribution requirement. This endpoint does not persist inputs. The default UI uses the same shared implementation directly.
- `POST /scenarios/goal-risk-analysis` simulates 100–5,000 seeded return paths using user-entered expected return, volatility, fees, and inflation. It reports the empirical chance of reaching an optional inflation-adjusted goal and p10/median/p90 ending balances in today's dollars. The mathematical assumptions and limitations are documented in [docs/goal-risk-analysis.md](goal-risk-analysis.md); this is not a market forecast.
- `POST /scenarios/goal-sensitivity` changes the user-selected low and high ranges for expected return, monthly contributions, annual fees, and inflation one at a time. It ranks assumptions by the resulting span in projected balance in today's dollars. The analysis is deterministic and does not assign probabilities to the ranges; see [docs/goal-sensitivity.md](goal-sensitivity.md).
- `POST /scenario-runs/goal-risk` explicitly calculates and saves a named goal-risk run to the local SQLite database. `GET /scenario-runs/goal-risk` lists recent runs; `GET /scenario-runs/goal-risk/{run_id}` retrieves an exact input/output snapshot; `POST /scenario-runs/goal-risk/compare` compares two runs with aligned goal, contribution, horizon, inflation, path-count, and random-seed assumptions, reporting dollar changes in p10/median/p90 and the goal-reaching share.
- `POST /scenarios/retirement-accounts` compares traditional and Roth account balances at an equal current cash cost, using explicit current and retirement tax-rate assumptions.
- `POST /scenarios/readiness-check` compares emergency savings with the user's own target, optionally checks a debt APR against a user-chosen threshold, records a goal liquidity horizon, compares optional strategy hours with available time, and surfaces separate risk-willingness and loss-capacity reflections. It produces no total readiness score or recommended strategy.
- `POST /scenarios/debt-payoff` compares highest-APR-first with smallest-balance-first using each entered debt's balance, APR, and fixed minimum payment, plus an extra monthly budget. It reports interest and payoff time under both payment orders without claiming that either approach is universally best.
- `POST /real-estate/rental-underwriting` calculates rent after vacancy, operating expenses, mortgage payment, NOI, cap rate, cash flow, cash-on-cash return, DSCR, and owner-occupied rent comparable for a house hack. Optional time inputs compare the user's estimated monthly workload with their available investing hours.
- `POST /real-estate/flip-underwriting` estimates contingency, holding costs, sale costs, all-in cost, break-even resale, and pre-tax profit for a flip. Optional time inputs compare the user's estimated active monthly workload with their available investing hours.

The time comparison uses user-supplied estimates; it does not assume that a rental, flip, or portfolio has a universal workload. Provide both `estimated_monthly_hours` and `available_monthly_hours` to receive `fits_time_budget` and (when the budget is above zero) `time_budget_utilization`. If either value is omitted, fit is unknown. Workload can vary with property count, repairs, tenant turnover, project stage, outsourcing, and investing style, so time fit is a planning constraint alongside the financial scenarios, not a measure of return or a recommendation.

All return projections are scenarios, not forecasts. Rental and flip outputs are only as useful as the rent, price, condition, financing, and cost assumptions entered. The calculators do not yet calculate deal-level tax depreciation, capital-gains tax, or financing qualification.

Example goal plan request:

```json
{
  "goal_name": "Fourplex down payment",
  "current_balance": 20000,
  "monthly_contribution": 1200,
  "years": 8,
  "target_amount_today": 150000,
  "annual_inflation_assumption": 0.03,
  "annual_fee_assumption": 0.002,
  "return_assumptions": {"low": 0.02, "base": 0.05, "high": 0.08}
}
```

`target_amount_today` is expressed in today's dollars; the API inflates that goal to its estimated future cost. The projected balance is also returned in today's purchasing power. A return assumption is not a prediction: the scenario values are deterministic compound-growth calculations and do not model volatility, taxes on investment gains, changing contributions, or sequence-of-returns risk. For retirement planning, treat this as an accumulation estimate rather than a withdrawal or lifetime-income plan.

Example retirement account comparison request:

```json
{
  "annual_gross_contribution": 10000,
  "current_marginal_tax_rate": 0.30,
  "retirement_tax_rate_assumption": 0.20,
  "years": 20,
  "annual_return_assumption": 0.07,
  "annual_fee_assumption": 0.002
}
```

Rates are decimal fractions, so `0.07` means a 7% assumption. The comparison holds current cash cost equal; it does not infer a future tax bracket.

## Historical data-integration ideas

The combined roadmap above supersedes provider/universe suggestions in this historical section. S&P 500 screening and Orange County rental discovery are both required for v1; provider choices remain subject to the coverage/rights audit.

Live stock screening and ZIP-level market discovery are a separate data-integration stage. A suitable stock feed needs historical adjusted prices and financial statements; an analysis should report source timestamps, performance periods, volatility/drawdowns, and balance-sheet risks without labeling a stock safe or predicting its price. The current data source candidate is FMP, which requires an API key and may limit endpoints by subscription. Fortune 500 membership must be checked against a dated Fortune list rather than inferred from company size.

For housing, HUD publishes Small Area Fair Market Rents by ZIP and Zillow publishes market trend datasets; those can help screen local rent and price trends but do not replace property-level comparable sales, inspection, crime, insurance, tax, zoning, or rental-license research. A ZIP score should expose the metrics and data dates behind it instead of describing an area as objectively “good.”

## Interview demo path

Start with **Goal Explorer**: open the goal editor, adjust monthly deposits, inspect a year on the chart, toggle purchasing power, keep a session baseline, then change the contribution or deadline and explain the comparison. The default comparison uses the earlier deadline for both plans; separate-deadline comparisons explicitly warn about different horizons. Export a JSON plan and demonstrate its validated import. Run the optional seeded uncertainty simulation and explain why its terminal percentiles differ from the constant-return lines. Use the privacy disclosure and clear the session workspace. No FastAPI server is needed for this page.

1. Start the API and show `/docs` to demonstrate its typed contracts.
2. Run the $100k, $250k, and $500k profiles through `/calculate` and compare marginal versus effective rates.
3. Compare a traditional contribution with a Roth contribution using `/scenarios/retirement-accounts`; change the retirement tax-rate assumption and explain why the result flips.
4. Show an owner-occupied fourplex through `/real-estate/rental-underwriting`, then stress-test rent, vacancy, repairs, and rates.
5. Use `/scenarios/goal-plan` to see how different return assumptions affect the time and monthly savings needed for a down-payment goal.
6. Use `/scenarios/goal-risk-analysis` with a fixed seed, then change volatility and explain how the simulated distribution changes while the return assumption remains fixed.
7. In explicitly configured trusted local mode, save two goal-risk runs with the same goal setup but different return and volatility assumptions, then compare their median and downside balance deltas in Scenario history.
8. Use `/scenarios/goal-sensitivity` to explain which selected assumption range produces the largest modeled balance span.
9. Run `python -m pytest -q` and show CI checks on a pull request.

This demo highlights the separation between validated inputs, deterministic calculations, and optional LLM prose. The README and response fields name the assumptions so an interviewer can see what the estimate does and does not claim.

## Historical backlog (not implementation order)

- Build an educational stock/ETF allocation planner: let users specify target percentages and dollar amounts across broad-market ETFs, sector/factor ETFs, and individual stocks; validate totals; show exposure, overlap, and concentration using dated holdings data. Any example allocations (including S&P 500, QQQ, NVIDIA, or Apple combinations) must be labeled illustrative and user-adjustable, never represented as universally optimal or personalized recommendations.
- Compare user-selected investment strategies on the same starting capital, contribution schedule, time horizon, fee and tax assumptions; report ending-value differences in dollars and percent, as well as downside and time/liquidity tradeoffs, so users can inspect modeled gains or losses without implying which strategy will win.
- Add a dated, source-attributed Fortune 500 stock research endpoint with total-return periods, volatility, maximum drawdown, valuation, earnings/cash-flow trends, debt measures, and a transparent risk rubric. Keep “risk indicators” separate from buy/sell recommendations. FMP is one candidate source, but API access and redistribution rights should be verified before committing to it.
- Add a ZIP-code market screener combining dated home-value and rent trends with HUD Small Area Fair Market Rents. Show affordability, rent-to-price, trend, data coverage, and uncertainty as separate measures; rank by a user's criteria rather than calling a ZIP universally “good.”
- Add bear/base/bull scenario comparisons and sensitivity charts for return, vacancy, interest rates, renovation overruns, and resale price.
- Extend saved-run history to the remaining calculators and store tax-rule years and external data timestamps where applicable. Before supporting shared or hosted accounts, decide on authentication, per-user data isolation, encryption, retention, and deletion.
- Compare strategy options across outcome, downside, liquidity, time requirements, and taxes; expose tradeoffs instead of reducing them to an unexplained single score.
- Compare historical-resampling and alternative return models with the current lognormal simulation, documenting calibration sources and how model choice changes outcomes.
- Stress-test property underwriting across joint ranges for vacancy, rates, maintenance, rehab overrun, holding period, and resale value; show break-even surfaces and loss cases.
- Add property-based invariants, independent reference cases, and reliable end-to-end API/UI checks in continuous integration.
- Extend goal planning to compare named strategies and account types, model contribution changes over time, and show goal progress alongside the tax and real-estate scenarios. Add an optional range-based simulation only with clear assumptions and a distinction from deterministic scenarios.
- Compare debt avalanche versus snowball, emergency-fund targets, and HSA/IRA/401(k) contribution order using user-entered APRs, employer match, and liquidity needs.
- Add portfolio-level after-tax asset allocation, diversification/concentration measures, and rebalancing scenarios before attempting personalized stock selection.
- Add versioned tax-year rule sets and explicit filing-status support only after the single-filer engine is fully validated against official examples.
- Add property-level expense categories, depreciation schedules, closing-cost detail, loan options, and exit scenarios; keep tax depreciation separate until its rules are implemented and reviewed.
- Add API-level tests for status codes, request validation, and response schemas once the runtime dependencies are installed in the development environment.

## Configuration

Copy `.env.example` to `.env`. `APP_MODE` defaults to `ephemeral`; only the explicit value `local` enables unauthenticated SQLite history. `ENABLE_AI` defaults to false and additionally requires local mode and an API key. `OPENAI_MODEL` defaults to `gpt-4.1-mini`. `CORS_ORIGINS` accepts comma-separated origins. `SCENARIO_DB_PATH` defaults to `scenario_runs.sqlite3`; the file is local and ignored by Git. Avoid committing `.env` or secrets. Full data-processing and public-hosting boundaries are documented in [docs/privacy-boundaries.md](privacy-boundaries.md).

## Disclaimer

This is an educational software project, not tax, legal, investment, or accounting advice. Tax law and contribution rules change, and individual facts can materially change outcomes. Verify current rules with the IRS and a qualified tax professional before taking action or filing.
