# Project roadmap: investment discovery and decision workspace

November 10: [public source prepared](publication-readiness.md) for a new
research-portfolio repository, with redacted checks, excluded local Git/data,
documentation and clean-source verification (642 full tests; final audit guard
18 focused tests). [Ranking/cost diagnostics](ranking-cost-evaluation.md) are
verified. No publication/deployment, performance validation or full stock-gate
completion is claimed. Stock acceptance and rentals remain in scope.

November 7: [listing calendar correction](listing-calendar-correction.md) fixes
UTC/local date misclassification without changing the seven-day age policy.
Actual workflow now passes all ten example checks and forms an experimental
basket; verified recommendations and full stock acceptance remain gated.
Full UI/API regression: 618 passed, zero skipped, 59 dependency warnings.

November 7: [evidence refresh and diagnostics](stock-evidence-refresh-2026-11-07.md).
References, all 89 price series (through Nov 6) and all 88 SEC sources refreshed.
44 focused tests pass. Actual acceptance: 7 passed / 3 blocked, zero candidates
under unchanged ten-stock/sector/peer rules. Peer/financial coverage is next;
freshness alone does not close stock acceptance.

November 7: [connected workflow evaluation](stock-workflow-evaluation.md) adds
ten bounded software checks, source-change invalidation and downloadable results.
38 focused tests pass. Actual installed references are stale: 2 checks passed,
8 blocked; stock completion is not claimed. Refresh/re-evaluation comes next.
Final full UI/API regression: 609 passed, zero skipped, 59 dependency warnings.

November 7: [personal holding notes](personal-holding-notes.md) now reopen through
explicit validated JSON restore. Switching holdings preserves session drafts;
restoring clears sale assumptions and recomputes evidence. 29 focused tests pass.
Local stock acceptance/evaluation and full tax/lot analysis remain unfinished.

November 7: [monthly stock contribution preview](monthly-stock-contributions.md)
closes the bounded one-deposit integration with exact cents, fixed experimental
targets, hard caps, explanations and private JSON. 44 focused checks pass.
Historical recurring replay, scheduling, holding-note portability and local stock
acceptance remain separate unfinished work. Stocks still precede new rentals.

November 7: [guided holding review](guided-holding-review.md) adds personal-reason
review, clear evidence precedence and optional pre-tax cost illustrations, with
beginner-first stock navigation. Full tax/lot review and local acceptance remain.

**Approved first-release change, November 6:** local actual-data research plus a
public synthetic/individually cleared-data demo. This supersedes older mandatory
public/full-index-first-release and pending-choice wording below. Both stocks
and Orange County rentals remain required and stocks remain first. The strict
recommendation gates are unchanged; public real-data recommendations stay a
conditional later edition. Complete the local experimental stock workflow with
dated evidence, constrained selection, clear limitations, save/restore/recompute,
reports and evaluation; then rental discovery/analysis and aligned comparisons.
Public demo isolation, clean setup, privacy and usability still require acceptance.

November 3 historical class/statement milestone:
[historical-class-statement-matches.md](historical-class-statement-matches.md).
Two exact reviewed historical quantities can be linked to registered common
classes with source/date/precision guards. Current quantities, economic rights,
complete class coverage and verified valuation remain unfinished; no gate relaxed.

November 1 coordinated reference milestone: [coordinated-reference-refresh.md](coordinated-reference-refresh.md).
Four-source publication now fails closed as a cohort, with matching source-health
UI and actual October 30 references installed. A reproducible in-process latency
baseline is recorded. This closes a bounded refresh deliverable within stage 1;
security, membership and valuation acceptance remain unfinished.

November 1 quantity-evidence slice: [filing-share-evidence.md](filing-share-evidence.md).
Sixteen dated observations from two cached filings now retain precision and
dimensions; four same-filing manual references pass. Optional UI comparison keeps
these observations separate from latest issuer counts. Zero complete economic-class
reconciliations; stage 1 remains unfinished, with all strict gates preserved.

November 1 ledger slice: [class-share-ledger.md](class-share-ledger.md). Installed
class/share lineage is inspectable across 88 issuers / 125 directory securities.
Zero issuers have reconciled class quantities; complete economic-class evidence,
verified valuation and the remaining stage 1 gates are still unfinished. No gates
or experimental selection rules changed; existing rental functionality is preserved.

October 31 source-refresh milestone: [fundamental-refresh.md](fundamental-refresh.md).
88 installed SEC sources re-fetched; eight updated share references, valuation
estimates 59→64 and stale 15→10. Independent checks 662 pass / zero mismatch /
159 unavailable. Date timeline distinguishes observations from retrieval. Full
class coverage, verified selection, coordinated source refresh and rights stay open.

October 31 evidence milestone: [class-and-financial-evidence.md](class-and-financial-evidence.md).
Two dated filing-class corroborations, conservative liability recovery and
independent statement/math checks. 39 financial passes, 27 unavailable; 465 tests
pass. Full canonical security, membership, valuation and public rights stay open.

October 31 refresh milestone: [daily-stock-refresh.md](daily-stock-refresh.md)
implements complete installed-cohort staging/resume, atomic publication and
rollback, with 89 IEX series through October 30 and a freshness/recovery panel.
Full suite: 445 passed. Stage 1 remains partial: source verification, source
refresh coordination, SIP migration/full-index scale and scheduling remain open.

Updated: October 29, 2026. This is the authoritative implementation order.

October 31 progress: evidence inventory, versioned context/policy and experimental
decision workspace now implement bounded portions of stock stages 1–3. See
[stock decision workflow](stock-decision-workflow.md). Verified recommendations,
automatic refresh and complete thesis/cost/tax-aware holding review remain open.
Older implementation descriptions below are the October 29 baseline.
Latest full regression: October 31, **419 passed**, with UI/API tests enabled.

**October 31 blocker audit:** [BLOCKER_RESOLUTION_PLAN.md](BLOCKER_RESOLUTION_PLAN.md)
is the current feasibility/release-scope reference. Historical SIP samples were
accessible with configured credentials, but public redistribution is not cleared.
The strict path is a readiness checker, not an implemented verified selector.
The user chose local research/public synthetic-or-cleared demo first on November
6. Public real-data recommendations remain conditional later work. Preserve
stocks-first execution, honest proxy/estimate labels and all strict evidence gates.

**Accepted decision-workflow expansion:** Stock selection must lead to explained
buy-candidate, hold, trim/sell-review, pass or insufficient-evidence assessments,
with versioned criteria, portfolio fit, supporting/contrary evidence and conditions
that change the conclusion. Complete hold/sell logic is not implemented; ranking
removal alone must not trigger a sell. This preserves strict gates and adds work
inside stock stages 2–5. Specific functions and current-versus-planned status are
saved in [DECISION_WORKFLOW_PIPELINE.md](DECISION_WORKFLOW_PIPELINE.md). This
capability reference does not change the stocks-first ten-stage order below.

## Product finish line and equal scope

One application with two equally important, complete research workflows:

- **Real estate:** Orange County long-term rental discovery -> specific-property
  underwriting -> stress testing -> candidate comparison.
- **Stocks:** dated S&P 500 universe -> strategy-based eligibility/scoring ->
  algorithm-selected stock basket and allocations -> explained purchase amounts ->
  company analysis and historical/scenario comparison. Users can inspect/override
  the proposal, but manually choosing every stock is not a prerequisite.

Both feed a shared decision workspace with explicit assumptions, source dates,
liquidity/workload/capital tradeoffs, session comparisons, and reproducible PDF
and JSON exports. The public v1 finish line requires both workflows. Stock
screening is not a deferred extension, and completing rentals alone does not
complete this product. Tax-budget trading is not the flagship.

The product produces model-based stock purchase recommendations under a defined
strategy and constraints, plus rental research matches and property scenarios. It does
not establish universally best investments, predict returns, execute trades, or
infer a property's achievable rent from a ZIP average. No-match and insufficient-
data outcomes are valid. No opaque combined stock/property investment score.

## Confirmed scope and working defaults

The user's stock research objective is to outperform the S&P 500 total-return
benchmark after modeled costs. Treat this as a falsifiable objective: matched
dates/cash flows, consistent tax basis, held-out evidence, and explicit losses
versus the benchmark. A high strategy score does not establish outperformance.
Property comparisons must also use consistent funding/horizon/exit assumptions
before claiming an advantage over a stock benchmark.

| Decision | State |
| --- | --- |
| Long-term rentals in Orange County, California | Confirmed by user |
| Strategy-based S&P 500 stock recommendations and portfolio construction, equally important to rentals | Confirmed by user; screening alone is insufficient |
| Standalone single-family rentals | Provisional housing type pending actual data coverage |
| Rental purchase financing | User-entered fixed-rate amortizing loan or cash purchase |
| Stock universe | Dated S&P 500 membership, retaining issuer/share-class distinctions; never infer membership from company size |
| Initial stock strategy | Working hypothesis: quality at a reasonable valuation; exact features, weights, sector rules and portfolio objective must be specified and evaluated before calling it implemented |
| Additional stock strategies | Growth/income/value filter exploration can be supported, but each additional recommendation strategy needs its own specification and evaluation; not required to launch multiple unvalidated algorithms |
| Price data cadence | End-of-day/delayed research data initially, with observation dates; no real-time requirement |
| Property listings | Manual specific-property inputs initially; automated listings optional after access/rights review |
| Spending and accounts | User authorizes free provider accounts/API keys, with zero paid data subscriptions or charges. Prefer public/free sources; free-tier coverage, quotas and public-display terms must be checked. No billing, paid upgrade or paid trial is authorized. |
| Privacy | Session-only user assumptions; no required names, bank credentials, brokerage connection, or cloud financial account |
| Comparison tax basis | Pre-tax initial comparisons; no after-tax conclusions unless both models implement consistent tax assumptions |

No personal finances are needed to begin either data audit. Later demo choices
(capital budget, rental bedroom range, management approach, and stock thresholds)
will be illustrative editable inputs. Source access/hosting decisions requiring
payment or user credentials will be resolved when concrete.

## Reusable implementation and limits

Existing foundations include typed FastAPI, Streamlit, shared calculation
modules, strict input contracts, goal projections, bounded simulations, session
comparisons, privacy defaults, versioned JSON, PDF generation, and test tooling.
The latest full verified suite had 391 passing tests; it does not validate unbuilt data
or screening features.

The contribution allocator already minimizes allocation drift with account cash,
purchase permissions, and concentration caps. Reuse it for user-chosen stock
weights; it does not select suitable securities or optimize returns/taxes.
It is a downstream sizing component, not the planned recommendation algorithm.
Rental underwriting v2 and exact fixed-loan/cash purchase feasibility are now
implemented. Multi-year stress and discovery integration remain. Existing PDF reports cover goals, not
stock research or rentals. Existing Monte Carlo assumptions are not calibrated
stock forecasts or property risk models.

Preserve supporting tax, debt, goal, and flip tools. Scope additions must help
complete the two core workflows before expanding the product further.

## Authoritative execution order: stocks, then real estate, then integration

**User decision, October 28, 2026:** finish the stock workflow before resuming
new real-estate feature work. Both remain equally required for the final product;
equal importance does not mean alternating implementation. Preserve and maintain
existing rental features. Fix shared regressions as needed, but do not start new
rental milestones while stock acceptance gates remain unfinished. This order
supersedes the earlier interleaved phase order and older next-step notes.

### 1. Finish stock data and security verification — CURRENT

October 29 latest milestone: 88 issuer records and 89 IEX series including SPY;
all 505 reference securities have explicit issuer/financial/price coverage states.
Five independent latest-close diagnostics passed their disclosed tolerance for
the new merged snapshot. Official listing references corroborate 501 exact
symbols/exchanges, with four unresolved; this is not legal share-class or index
verification. Independent arithmetic now has 640 passes and 168 unavailable
checks, with zero mismatches. See [listing evidence and coverage](listing-evidence-and-coverage.md).
Verification is still partial; official membership/security identity, verified
current valuations and full-universe coverage remain open. See
[stock verification and metrics](stock-verification-and-metrics.md).

- [ ] Establish dated S&P 500 membership and exact issuer/security/share-class
  identity, sector references and explicit unresolved mappings.
- [ ] Verify usable current valuations and annual financial inputs, expand beyond
  the installed 20 issuers, and expose supported coverage and missing features.
- [ ] Check price/benchmark adjustment conventions, free access/quotas, permitted
  use and display, source dates, refresh commands and independent diagnostics.

Exit: a documented, reproducible data scope can supply the defined stock strategy.
Proxy holdings and filing-based estimates alone do not satisfy verified-input gates.
If no-cost access prevents the intended scope, report the concrete gap and obtain
an explicit scope decision rather than silently redefining completion.

### 2. Complete the real-company stock metrics and screen

Core implemented for the installed sample: typed annual profitability/leverage/
growth and full-window risk metrics, optional fail-closed thresholds, sortable
results, visual comparisons, evidence/availability and per-company exclusions.
Missing financial inputs and verified valuation coverage still prevent declaring
this stage complete for the intended full universe.

- [ ] Independently reconcile strategy financial/valuation/risk features, period
  alignment, negative earnings, missing inputs and sector exceptions.
  Partial milestone: a second arithmetic implementation reconciles 500 available
  checks with zero mismatches; 92 remain unavailable. Two published annual-report
  reference cases compare 16 inputs (15 match, one unavailable). This is limited
  validation, not full source/tag/period/valuation verification. See
  [decision review and validation](decision-review-and-validation.md).
- [x] Provide reproducible filtering, sector-aware comparisons and explanations
  for passing, failing and unavailable results with dated evidence.

Exit: every strategy input used for selection has a defined, tested calculation
and source; unavailable inputs cannot quietly pass or receive invented scores.

### 3. Enable explained real stock portfolio recommendations

Readiness UI/API now reports per-company data failures and portfolio/peer
constraints while keeping all cash uncommitted. This is not a basket generator;
verified selection integration and source acceptance still remain. The user approved
a separate opt-in experimental proxy/estimate basket, now implemented and tested
with ten paper positions, exact scoring, sector limits, budget sizing and exclusions.
It does not satisfy verified stage-3 acceptance or establish outperformance. See
[experimental basket notes](experimental-research-basket.md).

- [ ] Connect verified evidence to the versioned strategy and portfolio selection.
- [ ] Enforce position/sector limits, issuer overlap, permitted purchases, budget,
  minimum diversification and explicit no-basket outcomes.
- [ ] Explain stock choices, exclusions, scores, weights and cent-reconciled dollar
  purchases; disclose fractional-share assumptions and preserve original proposals
  separately from user overrides. No brokerage transactions.

Exit: users receive a reproducible algorithm-selected real basket, not merely a
budget filter, synthetic demo or basket they must select entirely themselves.

### 4. Finish stock analysis, context and interactive exploration

Implemented slice: split-adjusted default share-price charts, matched-deposit
single-security/SPY replay with fees and explicit return basis, and up to three
company financial comparisons with fiscal-period differences disclosed. Full
basket comparison, broader news coverage/refresh and remaining workflow details
are still incomplete. Replay is not a historical strategy evaluation.

The experimental workflow now adds feasible alternatives, valuation-yield
sensitivity, existing direct holdings exposure and company research navigation.
Frozen prospective paper baskets can be evaluated against matched SPY sessions
after entry costs; actual records await future installed prices. Historical
selection evaluation remains blocked; no backward application of today's basket.

- [ ] Complete company/basket comparisons and sourced financial/news/event context,
  with coverage/freshness and important missing context visible.
- [ ] Add historical recurring-investment replay with explicit timing, adjustments,
  fees and matched benchmark cash flows; keep hypothetical forecasts separate.
- [ ] Preserve clear chart units, educational explanations and accessible tables.

Exit: users can investigate why a proposal was made, its risks and historical
behavior without mistaking a single-stock replay for a strategy backtest.

### 5. Close the stock workflow and evaluation — STOCK COMPLETION GATE

- [x] Recomputed private decision PDF summary with settings, all card outcomes,
  primary reasons, changes, dates and provenance; [details](stock-decision-pdf.md).
  Full evidence remains in JSON; this does not complete the entire stock gate.

November 6: [decision snapshots](decision-snapshots.md) add named session decisions,
private JSON save/restore, source/settings change review and current-evidence
recomputation. Stock PDFs, fuller holding review and local acceptance remain.

- [ ] Session shortlists, proposal/override comparison, validated JSON portability
  and stock PDF reports with reproducible assumptions and source/model versions.
- [ ] Evaluate calculation/selection correctness, coverage, ranking sensitivity,
  costs and transparent baselines. Use prospective paper snapshots if historical
  point-in-time evidence is unavailable; do not claim proven outperformance.
- [ ] Verify refresh failure/staleness, privacy, navigation, user task completion,
  and stock-specific access/display gates. Record remaining external blockers.

Exit: discovery -> real proposal -> explanation -> sizing -> exploration -> export
works end-to-end and is evaluated honestly. Freeze nonessential stock additions
and move to real estate. Shared public deployment is still stage 10.

### 6. Finish Orange County rental geography, data and area discovery

- [ ] Establish dated ZIP/ZCTA/county treatment and cross-county membership rules.
- [ ] Verify single-family value/rent coverage, units, dates and source permissions;
  distinguish regional/mixed-property context from property-specific achievable rent.
- [ ] Build map plus accessible sortable results, transparent criteria, source
  coverage, exclusions and no-match/insufficient-data outcomes.

Exit: users can find supported areas to investigate without fabricated rent or
claims of complete current ZIP coverage. Manual rent fallback stays labeled.

### 7. Connect rental candidates to property decisions

- [ ] Carry selected area context into specific-property inputs and editable rent
  ranges, expenses, financing, reserves and due-diligence assumptions.
- [ ] Connect existing underwriting, exact financing feasibility and holding-period
  stress; identify criterion failures and conditions that exhaust funding.
- [ ] Add named session shortlists and consistent property comparisons.

Exit: discovery -> property underwriting -> financing -> stress -> comparison is
connected. Existing calculation engines are reused, not rebuilt.

### 8. Close the rental workflow and evaluation — RENTAL COMPLETION GATE

- [ ] Rental PDF/validated JSON portability with context, inputs, source/model
  references, missing data and due-diligence limitations.
- [ ] Independently validate discovery and property comparisons, observe user tasks,
  and finish rental-specific data rights, refresh and privacy acceptance.

Exit: rental discovery and analysis are usable end-to-end; hypothetical model
returns remain distinct from evidence about an actual property.

### 9. Connect stocks and real estate through fair comparisons

- [ ] Common starting capital, contribution schedule, horizon, currency basis and
  consistent pre-tax treatment, funding of deficits and treatment of distributions.
- [ ] Account for residual cash, leverage, liquidity, workload, sale costs and
  uncertainty without an unsupported universal winner or combined investment score.
- [ ] Complete aligned comparison UI and combined PDF/JSON reports.

Exit: users can reproduce and explain both alternatives under aligned assumptions.

### 10. Package and verify the complete public release

- [ ] Clean installation/offline demo, confirmed CI, reproducible packaging,
  hosting, source display permissions, HTTPS/secrets and dependency review.
- [ ] Verify privacy/session isolation, bounded workloads, logs/download retention,
  concurrent performance, provider failures, rollback and recovery.
- [ ] Complete the two-domain usability/interview demo and deployment acceptance.

Exit: both finished workflows and their integration work in the deployed product.
No paid data, subscriptions, billing enrollment or cloud financial accounts are
introduced without an explicit user decision.

## Detailed capability acceptance reference (legacy phase identifiers)

The following original phase checklists preserve existing acceptance details and
progress. Their numeric headings are historical references, **not execution order**.
Use stages 1–10 above to choose the next task; use these checklists to ensure no
financial, data, evaluation or privacy requirement is lost. Apply tests and clear
UI explanations within each stock or rental milestone, not only at release.

### Legacy reference 0: Record the combined direction — complete

- [x] Confirm both pillars are required for v1 and save the ordered gates.
- [x] Link this roadmap from README/handoff and remove the stock-deferral language.
- [x] Identify candidate official sources, without claiming raw coverage or rights.

### Legacy reference 1: Specify the stock strategy and audit both data domains — in progress

October 28 evidence: [strategy specification](stock-strategy-v1.md),
[machine-readable design](../strategies/quality_value_annual_v1.json), and
[joint feasibility report](data-feasibility-2026-10-28.md). Nine source snapshots
were downloaded. The 92-area Census 2020 land-overlap candidate set has 89
single-family value rows and 81 mixed-rent rows, but audited single-family rent
is metro-only. IVV proxy holdings cover 505 equity rows, not verified index
membership. Four SEC annual fact samples are accessible; ticker mapping returned
403 initially; the operator-contact refresh now supplies 10,430 issuer mapping
records and 501 exact matches to 505 fund-proxy rows. Phase 1 remains incomplete:
current geography/membership, price history,
full-universe fundamentals, single-family rent and public display rights still
need resolution. The strategy core runs on synthetic data; live selection and
investment performance remain unvalidated. The normalized-release milestone and
coverage matrices are documented in [public-data-pipeline.md](public-data-pipeline.md).

- [x] Write the first strategy specification: eligible universe, metric definitions,
  sector exceptions, thresholds, score normalization/weights, objective, portfolio
  constraints, intended use, baseline methods and falsifiable evaluation criteria.
- [x] Define input roles explicitly: company/market evidence drives eligibility
  and ranking; budget, existing holdings, horizon, liquidity and user-selected
  risk constraints govern admissibility/sizing. Budget alone does not make a
  company attractive. No guaranteed outperformance or inferred suitable stock mix.

- [ ] Rentals: establish a dated Orange County ZIP universe, membership rule for
  cross-county ZIPs, and ZIP versus Census ZCTA mapping/geometry treatment.
- [x] Rentals: inspect actual ZIP/category price and rent rows, history, units,
  observation dates, gaps, and benchmark-only series. Do not silently substitute
  multifamily/all-home rent for single-family rent.
- [ ] Stocks: verify a dated constituent source, issuer/CIK/security identifiers,
  share classes, ticker changes, and membership effective dates. Do not require
  exactly 500 tradable ticker rows as a completeness test.
- [ ] Stocks: audit end-of-day prices, dividend/split events and adjustment method,
  financial statements, sector classifications, and an appropriate benchmark.
- [ ] Both: review API/download access, rate limits, credentials, permitted use,
  display/redistribution, attribution, refresh cadence, and costs.
- [x] Publish separate coverage matrices and blockers, including actual missing
  ZIPs/securities/metrics, stale records, and incompatible units/categories.

Done when: the initial strategy has a reviewable specification and actual source
rows support a documented launch scope in both domains.
Official documentation alone is insufficient. If coverage is incomplete, expose
supported subsets and unknowns; do not claim county/universe completeness.
Insufficient rental coverage can lead to regional context plus manual rent
inputs, explicitly labeled. Changing housing scope requires a documented user
choice. See [rental source inventory](orange-county-data-audit.md) and
[stock source inventory](stock-data-audit.md).

### Legacy reference 2: Build a shared, versioned data foundation

Normalized-release foundation implemented: provider-aware bounded transport,
semantic adapters, immutable public artifacts, atomic publication, verified
last-known-good recovery, selective refresh, structured failure records and a
read-only coverage API/UI. Eleven datasets produce 45,974 normalized observations
and metadata records. Detailed per-area/security/source matrices are exportable.
Full feed coverage, display review, deployment scheduling, multi-host coordination
and production load/recovery verification remain incomplete. See
[public-data-pipeline.md](public-data-pipeline.md).

- [x] Separate provider adapters, raw snapshots, identifier mapping, normalization,
  validated metrics, and serving. Reuse infrastructure, not incompatible formulas.
- [x] Preserve source URI, series/security ID, category, currency/units, observation
  period, publication/filing time, retrieval time, and calculation/model version.
- [x] Add bounded downloads, provider-aware rate limiting, retries/backoff,
  schema/duplicate checks, cache policy, and explicit missing-value handling.
- [x] Validate snapshots before atomic publication; retain last-known-good public
  data with visible stale status if refresh fails. Do not cache private user inputs
  alongside public provider snapshots.
- [ ] Provide repeatable refresh commands and offline fixtures, then schedule
  deployment refreshes according to each source's actual update cadence.
  Repeatable offline/cadence-aware CLI and independent test fixtures now exist;
  deployment scheduling is pending. An unavailable mapping stays unverified,
  and unsupported providers do not become ready because an adapter exists.

Done when: either domain can reproduce outputs from recorded snapshots and
survive partial provider failures without silent data corruption. A clean setup
can run a fixture demo without credentials. Tests include mapping ambiguity,
changed schemas, date alignment, and refresh interruption.

### Legacy reference 3: Implement and independently verify the stock metrics engine

Annual normalization slice implemented October 28: same-period/same-accession
USD financials, beginning/end assets, traceable liabilities fallback, ROA,
operating/FCF margins and liabilities/assets with missing-data states. Three
cached nonfinancial samples normalize; the bank sample remains incomplete.
Verified live valuation yields, full-universe coverage and TTM/growth/dividend/
risk features remain incomplete. Synthetic scoring/selection is implemented
(Phase 6); live recommendations remain disabled. See [normalization notes](annual-financial-normalization.md).

- [ ] Calculate documented profitability, revenue/earnings growth, free-cash-flow,
  leverage, valuation, and dividend measures where source coverage permits.
- [ ] Reconcile annual versus quarterly/YTD/TTM periods, fiscal calendars, units,
  restatements, filing availability, and share-class/issuer aggregation.
- [ ] Treat negative earnings, zero denominators, missing history, non-dividend
  payers, and unavailable data explicitly. Do not report invalid P/E as cheap.
- [ ] Use sector-appropriate metrics/comparisons; do not force industrial-company
  leverage/cash-flow rules onto banks or other incompatible businesses.
- [ ] Compute historical total-return measures, annualized volatility and maximum
  drawdown with stated windows, sampling cadence, adjustment methods, and coverage.
  Distinguish price return from total return; avoid double-counting dividends.

Done when: independent statement and price fixtures reproduce displayed metrics;
users can trace each metric to its period, inputs, and formula. Missing or
inapplicable metrics are not favorable zeroes. Return history is not a forecast.

### Legacy reference 4: Strengthen and verify the rental underwriting engine — core complete

Rental model v2 is implemented through engine/API/UI: corrected NOI/reserve
accounting, held initial reserves/repairs/HOA/utilities, break-even rent,
first-year principal/interest and explicit undefined ratios. Maximum purchase
price/down-payment solving is now implemented in a separate exact-constraint
engine and Research workbench; additional financing options remain incomplete.
See [execution and feasibility notes](strategy-engine-and-feasibility.md).
See [rental model v2](rental-underwriting-v2.md).

- [x] Model down payment, closing costs, initial repairs, and separately held
  reserves without counting reserves twice as spent expenses or distributable cash.
- [x] Include amortization/cash purchases, vacancy, property tax, insurance,
  maintenance, management, HOA, owner-paid utilities, and capex reserves.
- [x] Distinguish operating NOI from cash flow after debt service and replacement
  reserves. Deliberately revise the current capex-in-NOI convention and fixtures.
- [x] Calculate break-even rent, capital required, cash flow, cash-on-cash return,
  and defined coverage ratios; no-debt/zero-capital undefined ratios are not zero.
- [x] Solve maximum purchase price and feasible down-payment ranges under explicit
  capital/financing/return constraints. Interest alone does not determine down payment.
- [x] Independently validate amortization and accounting, including negative
  outcomes, loan boundaries, and purchase-related tax/insurance assumptions.

Done when: shared API/UI calculations reconcile capital, debt, operating income,
reserves, and cash flow. Outputs remain pre-tax unless a separate validated tax
model is added. Area indices are not parcel assessments or insurance quotes.

### Legacy reference 5: Build both explainable discovery interfaces

- [ ] Stocks: editable sector, profitability, leverage, growth, valuation,
  dividend and historical-risk filters; illustrative strategy presets disclose
  exact thresholds, eligible sectors, and missing-data policy.
- [ ] Stocks: sortable result table, sector-aware comparisons, source/filing dates,
  reasons each company matches/fails, and user-selected sorting or explicit
  weighted ranking. Expose weights/normalization rather than a secret score.
- [ ] Rentals: budget/financing/reserve/cash-flow criteria, map plus accessible
  sortable ZIP results, geographic boundaries, dates/categories, and coverage states.
- [ ] Rentals: distinguish market descriptors from illustrative underwriting;
  index rent/price ratios are not property returns or appraisals.
- [ ] Both: hard constraints precede ranking; show exclusions, unknown criteria,
  and no-match results. Explain sensitivity to changed thresholds or ranking weights.

Done when: users can find candidates in either domain and explain why they appear.
Changing criteria reproducibly changes matches; stale/unknown data cannot silently
pass filters. No area or security is labeled universally good or safe.

### Legacy reference 6: Build stock recommendations and connect property analysis

The scoring/selection core is implemented on synthetic inputs with exact tied
percentiles, one canonical class per issuer, sector quotas, deterministic ties,
cent-level equal sizing, explanations and explicit no-basket cases. The workbench
and typed demo endpoint cannot enable live recommendations. Verified market cap,
index membership, historical risk, provider integration and account-aware funding
remain gates; this phase is not complete. Live valuation remains unavailable.

- [ ] Stocks: company detail with business/sector context, sourced financial trends,
  valuation context, dividend/risk history, missing-data warnings, and comparison
  of up to three selected companies under the same periods and definitions.
- [ ] Stocks: algorithm selects eligible securities and proposes portfolio weights
  according to the versioned strategy, instead of requiring a user-selected basket.
  Define decision variables/objective and enforce position/sector concentration,
  holdings overlap, permitted purchases, cash and any minimum-diversification rules.
- [ ] Stocks: explain selection, exclusion, score contributions, binding constraints,
  proposed allocation and data age. Strategy score is not an expected-return estimate.
- [ ] Stocks: use the existing allocator where appropriate for executing proposed
  targets in integer cents. Expose the difference between strategy selection and
  allocation-drift minimization; do not imply the existing solver implements both.
- [ ] Stocks: support user overrides as a separate labeled alternative, preserve
  the original proposal, and return no recommendation/explicit infeasibility when
  data or constraints prevent a defensible plan.
- [ ] Stocks: prices support share estimates only when fractional-share and
  rounding assumptions are explicit. No transactions or broker connections.
- [ ] Rentals: specific-property editor carries labeled market context, then accepts
  property price, supported rent assumptions, expenses, financing, and overrides.
- [ ] Rentals: compare required rent with the user's achievable-rent range, capital
  needs, reserve coverage, and criterion failures. Flag property-specific condition,
  rental restrictions, and parcel costs as due-diligence inputs, not ZIP facts.

Done when: the app independently proposes a reproducible stock basket, weights
and dollar purchases with explanations; user-selected goals/cash alone do not
drive security attractiveness. A rental match becomes an inspectable property
scenario. Neither modeled optimality nor a strategy score promises real-world
optimality, and property facts are not replaced with unlabeled area averages.

### Legacy reference 7: Add interactive history, scenarios, and stress tests to both

Holding-period slice implemented: `rental-hold-v1` reconciles monthly debt,
distributed cash, separate reserve accounts, bounded external funding, repairs,
growth and exit costs. The visual base/adverse comparison stops at funding failure
and withholds exit profit. See [rental holding-period analysis](rental-holding-period.md).
Discovery, broader financing surfaces and the full cross-domain comparison remain.

- [ ] Stocks: historical "what if I invested" replay with starting amount, recurring
  deposits, dates, dividends/splits, fees, and a benchmark under identical cash
  flows. State trading-day, purchase-timing, and fractional-share assumptions.
- [ ] Stocks: separate hypothetical forward contribution scenarios from historical
  replay. Show deposits versus growth, losses/drawdowns, and concentration; do
  not treat a current constituent replay as a historical screening backtest.
- [ ] Rentals: rent/vacancy/repair scenarios, prospective financing comparisons,
  purchase-price/down-payment tradeoffs, and joint adverse break-even surfaces.
- [x] Rentals: for multi-year outputs, reconcile loan amortization, cash deficits,
  reserve use, rent/expense growth, appreciation assumptions and exit costs.
  Do not double-count principal reduction/equity or change a fixed loan's rate mid-hold.
- [ ] Both: consistent candidate comparisons and source/model snapshots. Use
  deterministic stress ranges initially; introduce simulations only with justified
  distribution/dependence assumptions and sampling-error evidence.

Done when: historical observations and forward assumptions are unmistakably
separate, timelines reconcile, and users can identify conditions under which
candidates fail. Selected-stock history does not establish a successful strategy.

### Legacy reference 8: Connect the pillars through a fair decision comparison

- [ ] Accept a common starting capital, contribution schedule, horizon, and
  nominal/today-dollar basis; expose financing and cash-flow timing differences.
- [ ] Compare a user-selected stock basket or supported benchmark scenario with
  a user-entered property scenario, both under explicit forward assumptions.
- [ ] Account for property down payment/closing/repair costs, separately held
  reserves, residual cash, operating deficits, mortgage balances, and sale costs.
- [ ] Treat stock distributions and property cash flows consistently (withdrawn,
  reinvested, or retained) and require funding for deficits without assuming
  unlimited cash. Do not force every available dollar into either investment.
- [ ] Show modeled ending net value, external cash required, income, downside
  scenarios, liquidity, leverage/concentration, and user-estimated workload.
- [ ] Keep tax basis consistent. Do not compare an after-tax stock result to a
  pre-tax property result, or historical stock results to assumed property returns.
  Unsmoothed stock volatility is not comparable to sparse property value estimates.

Done when: users can inspect tradeoffs without an unsupported winner. This is a
scenario comparison, not automatic suitability advice or a promise of returns.
A universal "best investment" recommendation is outside v1.

### Legacy reference 9: Complete the shared workflow and portable reports

- [ ] Clear navigation: shared goal/criteria -> Stocks or Real Estate -> detailed
  analysis -> sizing/stress tests -> same-domain or cross-domain comparison.
- [ ] Session-only shortlists, assumptions and named comparisons for both domains;
  explicit reset, no global cache of private holdings/budgets.
- [ ] Validated JSON import/export with recomputation, model versions and source
  snapshot references; identify expired/unavailable source snapshots on import.
- [ ] In-memory stock, rental and combined PDF reports with filters, match reasons,
  inputs, dates, metric definitions, comparisons and limitations. Existing goal PDFs
  do not satisfy this requirement.
- [ ] Invalidate stale outputs/downloads after edits. Verify keyboard/table
  alternatives to charts/maps and usable desktop/phone layouts.

Done when: both complete workflows can be saved, reopened and explained without
losing provenance. Downloads are not described as encrypted or secure vaults.

### Legacy reference 10: Evaluate both pillars and validate real use

- [ ] Independent financial/accounting fixtures, invariants, malformed/missing-data
  tests, source-refresh tests, and API/UI/report workflows for both domains.
- [ ] Stocks: evaluate metric correctness, coverage, filter reproducibility,
  ranking sensitivity and concentration constraints. Compare with transparent
  simple screens; do not call passing more filters investment outperformance.
- [ ] Stocks: independently test selection/sizing constraints and compare the
  complete recommendation policy with equal-weight eligible baskets, the existing
  deficit-first approach where applicable, and an identified broad-market baseline.
  Separate allocation/score improvements from historical or future return claims.
- [ ] Stocks: freeze strategy versions before evaluation; check sensitivity to
  weights, thresholds, sectors and dates. Use prospective paper snapshots when
  historical point-in-time data is unavailable; disclose that limitation and
  label the strategy experimental rather than implying validated outperformance.
- [ ] Rentals: compare discovery against price-only and rent/price sorting with
  identical data coverage and criteria; independently check underwriting/stress cases.
- [ ] Publish reproducible latency/completeness/refresh metrics and adversarial
  fixtures; include no-match, stale-data, and infeasible-budget examples.
- [ ] Historical screening performance claims require point-in-time constituents,
  publication-date-aware fundamentals, corporate actions/delistings, transaction
  assumptions, and out-of-sample methodology. Without these, omit the claim;
  do not block current research screening on unsupported historical assertions.
- [ ] Observe 3-5 potential users completing tasks in each workflow, document
  confusion and task outcomes, fix problems, and rehearse a two-domain interview demo.

Done when: reviewers can reproduce substantive claims for both pillars and users
can complete both workflows. Do not fabricate usability or performance evidence.

### Legacy reference 11: Package, deploy, and verify the complete release

- [ ] Clean install/offline demo, reproducible service packaging, user-owned Git
  remote and confirmed CI on supported runtimes. Containers where useful.
- [ ] HTTPS, secrets management, provider refresh controls, reviewed download/log
  behavior, dependency/security review, rollback and recovery instructions.
- [ ] Measure concurrent latency/resource use and session isolation for both data
  browsing and private calculations; enforce request/job limits and safe failures.
  Add workers or a queue only when workload measurements justify them.
- [ ] Verify clearing, stale-data disclosures, failure recovery, host retention and
  no financial payloads in telemetry. No public use of unauthenticated local history.
- [ ] Release demo exercises stock discovery -> basket/history, rental discovery
  -> property stress, and an aligned comparison/export. Both pillars are required.

Done when: deployed behavior, privacy, source permissions, evidence and clean setup
are verified. Hosting/paid-provider decisions need user input when concrete.

## Deferred beyond this finish line

More stock universes/countries, additional counties/property types, automatic
property listings, real-time quotes, broker execution, automatic tax-loss
harvesting, detailed rental tax-return preparation, tax-aware portfolio sales,
and user accounts/cloud financial storage. If accounts are later added, require
authentication, ownership, retention/deletion and isolation tests first.

## Continuity and progress rules

- Dated sector/universe reference, split-aware filing valuation estimates and
  real-company eligibility inspection now exist. Strict live selection remains
  blocked; ETF proxy membership and estimates have not been promoted to verified
  strategy inputs. See [sector-valuation-readiness.md](sector-valuation-readiness.md).

- Real local IEX price/risk research now exists for five issuers plus SPY, with
  exact-date comparisons, source/basis limitations and explicit redistribution
  withholding. Portfolio composition has a user-editable doughnut and cent-exact
  allocation; it does not complete live portfolio selection. See
  [local-market-history.md](local-market-history.md).

- News/event context is a required part of explained recommendations alongside
  financial evidence. The first slice has filing timelines for 21 issuers and two
  manually reviewed announcement examples; broad news coverage and reliable
  calendar refresh remain incomplete. Do not turn headlines into ranking weights
  without a separate defined and evaluated strategy. See
  [company-news-events.md](company-news-events.md).

- Company-to-strategy evidence now exposes financial rule outcomes, five feature
  definitions and remaining gates with no partial score. Shared financial checks
  keep the synthetic engine and research explanations aligned. See
  [company-strategy-evidence.md](company-strategy-evidence.md).

- Issuer expansion milestone: 19 supported cached issuers, bounded verified-SEC
  import plans and 281 passing full-suite tests. See
  [sec-issuer-imports.md](sec-issuer-imports.md). This does not complete current
  index membership, price/benchmark coverage or rental discovery gates.

- Both pillars are equal release requirements, not an optional add-on relationship.
- Update completed checkboxes and handoff after each milestone, with actual evidence.
- Report completed gates and remaining work, not a precise completion percentage.
- New ideas enter the deferred backlog unless needed for one of these gates.
- Annual metric reference cases, rental v2/constraint solving and the versioned
  normalized-release pipeline now exist. Next finish stock stages 1–5: identity/membership, verified valuation, coverage,
  real portfolio selection, exploration and export/evaluation. Rental discovery
  resumes at stage 6. Both discovery workflows remain incomplete; preserve all
  existing rental functionality while stocks are completed first.
- Screening alone or a manually selected basket does not meet the stock finish line.

## Visual interaction milestone · October 28, 2026

- [x] Organize Real estate, Stocks, Goals and supporting Tools.
- [x] Reactive rental financing/cash-flow charts, rent waterfall and pinned comparison.
- [x] Synthetic stock quality/value selection linked to score and sector charts.
- [x] Session-only state, reset, accessible table/selector alternatives and model reconciliation tests.

See [visual-workspaces.md](visual-workspaces.md). Live stock/ZIP discovery, data
rights and observed usability remain separate incomplete gates above.
