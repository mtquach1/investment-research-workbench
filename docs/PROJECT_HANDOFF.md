# Project handoff: Tax & Investment Strategy Optimizer

**Updated:** November 10, 2026
**Latest task:** [public-source preparation](publication-readiness.md).
User wants a public research-lab showcase. A clean source ZIP is prepared under
`output/public-release/investment-research-workbench-source.zip`; upload its
extracted contents to a NEW repository. Original Git retains checkpoint-history
personal paths/contact metadata; it was not rewritten or published. Snapshot
audit passes; whole-history audit retains four personal-path findings. No known
local credential/provider-token finding remains. Scanner output is redacted;
all history is omitted from the archive. Do not push/mirror the original checkout.
Expanded ignore rules, research-facing README (older notes retained in
`docs/development-history.md`), data/security/contribution docs, synthetic demo,
least-privilege CI and publication audit added. No license grant, remote, staging
or public deployment was created. Clean-source full tests: **642 passed**, zero
skipped, 55 dependency warnings, 68.75s; `output/tests/public-clean-source-final.log`.
Final audit-root guard: **18 focused checks passed**. Existing venv reused;
fresh install/remote CI/browser QA remain unconfirmed. Manifest hashes verified.

Previously unfinished [ranking/cost evaluation](ranking-cost-evaluation.md) now
passes UI/engine tests. November 10 installed-data run: 56 chosen yield scenarios,
three changed baskets, minimum nine original positions retained; row-order and
uniform-scale checks pass. No return-performance or probability claim. Earlier
November 7 integration execution was blocked by approval-review usage limits;
the November 10 verification succeeded. Original project pipeline resumes with
prospective paper follow-up and observed beginner/remaining stock acceptance,
then rentals. Both domains and strict evidence/free-data requirements remain.

**Latest milestone:** [listing calendar correction](listing-calendar-correction.md).
Audit found UTC receipt dates incorrectly compared with Los Angeles assessment
dates. A shared local-calendar age check now serves exact listings and complete
directory coverage, preserving 0–7 days and rejecting true future/undated/naive
receipts. Unsupported listing evidence no longer automatically becomes a filing
conflict. Actual same-source result: **501 listings corroborated / 4 not found**;
IT qualified peers rose from four to five, allowing a ten-stock experimental
basket without threshold changes. Actual workflow checks: **10 passed / 0
blocked / 0 failed**; `output/audits/stock-workflow-clock-corrected-2026-11-07.json`.
UI clarifies local assessment dates versus UTC receipts. TDD core: 70 passed,
four dependency warnings, 4.26s. Source/policy hashes and snapshot schemas stay
unchanged; preserve older decisions and recompute explicitly after the code fix.
Full UI/API regression: **618 passed, zero skipped**, 59 dependency warnings,
57.04s; `output/tests/listing-clock-full.log`. No browser or novice-study claim.
Strict verified gates remain disabled. Next: remaining local stock coverage/
ranking/cost evaluation, prospective paper follow-up and beginner acceptance,
with tax-lot boundaries retained; then rentals. No performance/readiness claim.

**Latest milestone:** [installed evidence refresh and diagnostics](stock-evidence-refresh-2026-11-07.md).
All four references published (listings Nov 6, IVV Nov 5), all 89 price series
published through Nov 6 in four batches, and all 88 SEC sources refreshed without
requested-source failures. 32 financial payloads / one annual period / 24 share
records changed. Final public release:
`0d080e7d913bb4d15eccb5f5dfb7c9bd4282c52f032cc2baa177c20a44277dda`;
market snapshot `8e593f26ae8494df137a01c1f1d9059abf423dcfbf4566e89c47bfb275c4e010`.
Actual workflow: **7 passed / 3 blocked / 0 failed**, candidate count zero.
Fresh data still cannot fill ten positions under unchanged peer/sector/financial
rules. Allocation/exclusion/cap examples remain blocked.
Current qualified peers: Industrials 9, Health Care 8, Consumer Staples 6,
Materials 4, Information Technology 4, Consumer Discretionary 1, Communication
Services 1. Only three sectors can score; three per sector supplies at most nine.
Notes now correctly run independently of market/candidate availability. UI/JSON diagnostics expose dates,
candidate counts and plain-language blockers. TDD: **44 focused tests passed**,
12 dependency warnings, 5.12s; `output/tests/stock-refresh-acceptance-focused.log`.
Compile/whitespace pass; prior full regression remains 609 passed. No browser or
novice-study claim. Next: audit sector-peer/financial-feature gaps across the
declared universe, improve justified coverage without score chasing or rule
relaxation, rerun actual acceptance, then remaining stock gates before rentals.

**Latest milestone:** [connected stock workflow evaluation](stock-workflow-evaluation.md).
Ten fixed-input behavior checks now connect decisions, portability, recomputation,
monthly/cap accounting, exclusion score invariance, notes and stale withholding.
Lazy Validation & evaluation panel provides clear pass/blocked/fail counts and
evidence-bound JSON; evidence edits invalidate it. Offline CLI added. Actual
November 7 installed-data run: **incomplete, 2 passed / 8 blocked / 0 failed**,
because references are stale. Synthetic fixtures pass all ten example paths;
this is not actual-data acceptance, performance evidence or production readiness.
Focused regression: **38 passed**, four dependency warnings, 5.95s. One earlier
fixture setup hit a Windows atomic-replace access denial; fresh rerun passed.
Full regression with UI/API enabled: **609 passed, zero skipped**, 59 dependency
warnings, 52.81s; `output/tests/stock-workflow-full.log`. The initial full run
exposed a monkeypatch/import leak in test setup; fixed and verified in the
previously failing sequence (two passed), then the full suite. No production
evidence gates changed. Browser visual review and observed beginner tasks remain.
Next: refresh actual evidence and repeat evaluation, remaining stock correctness/
coverage/cost and prospective evaluation, tax-lot boundaries and beginner tasks.
Stock gate stays open; no new rentals or strict-gate relaxation.

**Latest milestone:** [personal holding-note portability](personal-holding-notes.md).
Explicit bounded JSON restore reopens reason/notes for an exact entered holding;
sale assumptions reset, opinions/dates stay unverified and company conclusions
recompute. Drafts survive switching holdings; privacy clearing removes them.
Optional before-tax help explains unmodeled basis/lot boundaries. No provider,
database or API route added; snapshot/PDF formats stay compatible. TDD followed
by **29 focused tests passed**, four dependency warnings, 4.47s;
`output/tests/holding-notes-focused.log`. No full-suite/visual/novice claim.
Next: local stock acceptance/evaluation and outstanding tax/lot/evidence
boundaries, before new rental discovery. Strict verified gates remain intact.

**Latest milestone:** [one monthly contribution](monthly-stock-contributions.md).
The decision workspace previews one deposit with before/add/after dollars,
per-holding explanations and exact cash reconciliation. Reuses the existing
allocator; ten targets stay fixed, blocked additions stay cash, holdings/caps
are preserved and stale/failed results are withheld. Initial cash is excluded;
no execution, forecasts or schedule. Private session JSON includes context and
provenance, separate from snapshot/PDF formats; edits clear results. New no-store
POST `/research/stock-monthly-contribution`. TDD engine red/green followed by
**44 passing focused tests**, five dependency warnings, 7.33s;
`output/tests/monthly-contribution-focused.log`. No full-suite repeat, browser QA
or novice-study claim. Next: holding-note portability/tax-lot boundaries and local
stock acceptance/evaluation, then rentals. Strict gates remain unchanged.

**Latest milestone:** [guided holding review](guided-holding-review.md). Decision
workflow is now the first stock-building tab; the main view uses plain labels,
short navigation guidance and optional data detail. Existing holdings have a
separate reason/concern review and optional whole-position pre-tax fee/purchase-
cost illustration. User notes never become company facts or change scores.
Missing evidence takes precedence; no sale is recommended. New no-store POST
`/research/stock-holding-review`; no LLM/provider calls or persistent storage.
Notes/illustrations have their own private JSON download and are explicitly
separate from existing snapshot/PDF formats. Focused checks: **21 passed**, five
warnings, 11.41s; `output/tests/holding-review-focused.log`. No unnecessary full
suite rerun or novice usability claim. Next: recurring-cash integration, remaining
holding persistence/tax-lot boundaries, then local stock acceptance before rentals.

**Latest milestone:** [private stock PDF summaries](stock-decision-pdf.md).
Snapshot review now prepares an in-memory PDF recomputed from current server
evidence. Includes settings/funding, every current card with primary reason,
changes, candidate/holding dates and provenance. Unverified recorded outcomes
stay labeled; stale evidence/absent consent withholds export. UI downloads clear
on edits. New no-store POST `/research/stock-decisions/report`; no provider or
database writes. Thirteen focused report/API/UI checks passed (five dependency
warnings); `output/tests/stock-pdf-focused.log`. Five-page synthetic sample
rendered/visually checked. Full core regression was not unnecessarily repeated.
Next: fuller holding review, recurring cash, local stock acceptance; then rentals.

**Latest local stock milestone:** [decision snapshots/change review](decision-snapshots.md).
Named session records now save/restore bounded validated JSON and recompute
against current server evidence with exact saved or current-editor settings.
Compare outcomes, cents, scores, coverage/symbols, reasons and evidence findings;
source/policy/settings changes are explicit. Originals remain separate and all
recorded/imported results/dates remain unverified. Current unavailable evidence
withholds assessment; edits invalidate comparisons. No-store POST
`/research/stock-decisions/snapshot-review` cannot accept client evidence or
bypass server mode. Max ten session records / 1 MiB each; no database, global
private cache, provider call or trade action. Actual 88-company check: 19 pass /
59 insufficient / ten experimental candidates; compact record 275,820 bytes;
same-evidence recomputation produced zero changes. Full suite: **569 passed,
zero skipped, 59 dependency warnings**, 91.65s, UI/API enabled;
`output/tests/decision-snapshots-verified.log`. Focused engine/decision/API-contract
checks: 54 passed; focused UI/API: four passed. Next: stock PDFs, fuller thesis/
cost/tax holding review and recurring-cash integration; finish local stock
acceptance before new rentals. Public-demo isolation/clean setup/deployment
remain unfinished. Fresh preview: http://127.0.0.1:8517/; old servers preserved.
Additional full-app save/compare navigation regression: one passed;
`output/tests/decision-snapshot-full-app.log`. Browser QA verified the same
component in an isolated local preview (8518) with an illustrative saved five-year
horizon and current one-year horizon: changed findings and unassigned cash were
visible and labeled. Earlier full-app browser navigation was inconclusive and
encountered a stale-tab error; automated full-app navigation passed. The isolated
preview is development QA, not a public synthetic-data edition.

**Approved first-release scope (November 6):** The user explicitly chose option 1:
local real-data research plus a public synthetic/individually cleared-data demo.
Both stocks and Orange County rentals remain required. Public full-index real-data
recommendations are a later conditional gate, not mandatory for this first release.
This supersedes older pending-choice and mandatory-public-first-release wording.
No data access/display permission, paid access or verification flag is changed.
Strict recommendations stay withheld until their evidence contracts pass; local
experimental assessments retain the existing opt-in policy and freshness checks.
Finish the local stock workflow (portability, reports, complete labeled review,
evaluation) before new rental discovery. Keep the remaining strict class/rights/
membership/valuation work explicit rather than inventing certificates or treating
it as already completed. Public-demo isolation, clean setup and deployment checks
remain unfinished. Subjective progress estimate for this approved scope: 40–45%,
not a measured milestone percentage or a claim that the scope choice wrote code.

**Latest stage 1 evidence milestone:** [historical class/statement matches](historical-class-statement-matches.md).
Exact reviewed statement/class links now match AAPL and NVDA historical common
share quantities. A versioned, hashed two-case registry records class titles,
source hashes, accessions, contexts, dates, quantity and precision. Review
availability is enforced as of November 3; missing/conflicting evidence cannot
select a convenient match. Actual audit: two historical matches / 123 unreviewed
directory securities; zero complete economic-class reconciliations. Existing
no-store stock-screen API and company ledger expose the typed result. UI keeps
current assignment unknown and provides an optional dated quantity/proof panel.
No provider download, published release change, current valuation certification
or experimental policy change occurred. Financial/valuation outcomes unchanged.
Next: complete current class quantities, all economic/nontraded class coverage,
economic/conversion rights and aligned corporate-action/price evidence for the
declared cohort; then broader source coverage and remaining strict gates.
Focused checks: 25 review/serialization cases and two UI/navigation checks pass.
Completed full regression: **546 passed, zero skipped, 59 dependency warnings**,
53.74s; `output/tests/historical-class-matches-verified.log` (UI/API enabled).
The navigation fixture clock is now fixed to its data date; November 3 exposed
its previously time-dependent sector-filter assertion. Production age policies
are unchanged. Fresh preview: http://127.0.0.1:8516/; older servers preserved.

**Latest stage 1 source milestone:** [coordinated reference refresh](coordinated-reference-refresh.md).
Exactly four installed references now refresh as one publication: SEC directory,
both listing directories and IVV proxy. Pre-publication validation under the
writer lock refuses any failed/stale source; the old serving pointer survives.
Full previous-release identity is checked before transport. Actual 4/4 refresh
published October 30 listing/proxy observations (proxy previously October 26).
Release `652a3b6d9d17e4ecb0c78e552b0039b99d9ba52cac50c0f7415879ea0e8cacff`.
Financial/valuation/listing outcomes unchanged; no strict gate relaxed. UI adds
a lazy source-health panel, separate observation/download dates, candidate-vs-
installed receipts and audit export. Offline stock-screen benchmark: three
same-snapshot runs, median 939.421 ms for 88 issuers/505 reference securities;
not an HTTP/load or guaranteed cold-start benchmark. Reference transaction and
UI failure/laziness checks pass. Stocks remain incomplete: class/rights mapping,
official membership, verified valuations and full decision/portable-report work
remain; rental discovery stays required after stock acceptance. Do not promote
the earlier subjective 40% estimate to 50% just because this milestone shipped.
Its interrupted full regression completed: **520 passed, zero skipped, 55
dependency warnings**, 74.31s; `output/tests/reference-refresh-verified.log`.

**Latest stock stage 1 slice:** [dated filing share quantities](filing-share-evidence.md).
The registered Apple/NVIDIA filing adapters now preserve 16 point-share
observations (10 dimensional), with exact context, units, scale, precision and
dates. Four manually read same-filing references match normalized values and
precision; this is not a second independent data source. Two cover tables were
rebuilt offline; all other data/market history retained. New release
`d7528d421a6a2cd61cbff4fd14ba01a223cebfb873d1fefa48223db9088ea8d4`.
Stock-screen API and ledger expose dated quantities without class assignment.
UI adds separate coverage/reconciliation cards and an optional count/rounding
comparison with older/dimensional observations opt-in. Strict gates and approved
experimental rules are unchanged. Actual financial, valuation and share-age
counts are unchanged; zero complete economic-class quantity reconciliations.
Next: complete reviewed class/rights/quantity mapping for a declared cohort;
do not equate an undimensioned common-share tag or registered listing with every
economic/nontraded class. Broader coverage, official membership, aligned corporate
actions/prices and public-display rights remain open. Stocks first; both domains
remain required. Existing rental functionality is preserved.
Full regression: **509 passed, zero skipped, 55 dependency warnings**, 54.41s;
`output/tests/filing-share-evidence-verified.log` (UI/API enabled). Focused parser,
ledger and screen checks: 50 passed; focused new UI comparison/navigation checks:
two passed. Reference audit: `output/audits/filing-share-references-2026-11-01.json`.
The import retains existing unrelated source-failure receipts; no new failure
was recorded for either cover table. Fresh preview is http://127.0.0.1:8514/; older servers remain.
Browser QA confirmed Apple's actual filing-count/precision comparison and optional
history control. The 8513 process retained an old UI module; use 8514 for this slice.

**Ongoing user preferences:** Improve UI appearance and beginner clarity with each
milestone. Give concise, candid internship-portfolio suggestions grounded in
demonstrated engineering (reproducibility, correctness, failure recovery and
measured performance); no invented hiring standard or outcomes. Keep reads and
updates targeted to conserve tokens, and avoid redundant test runs.

**Previous stock stage 1 slice:** [installed class/share ledger](class-share-ledger.md).
Typed per-issuer ledgers now join all observed directory securities, every installed
filing-class context and one unallocated issuer point count, preserving separate
source hashes and measurement/filing/retrieval clocks. Existing no-store stock-screen
API, evidence inventory and beginner inspector expose the ledger. Actual offline
audit: 88 issuers / 125 directory securities / two cover-class observations; 70
recent unallocated counts / 16 stale at check date / two unavailable; **zero class
quantities reconciled**. Valuations unchanged at 64 estimates / 10 stale / 12 multiple /
two unavailable (price-date aging and different precedence); financials 39/22/27.
No source downloads, data publication, gate relaxation or change to the authorized
experimental assessment policy. This completes the installed-evidence ledger slice,
not economic-class completeness or stock stage 1. Next: review a small declared
cohort's complete economic classes and class-specific quantities/rights, then
independently reconcile aligned prices/actions; broaden filing-class coverage and
coordinate reference refresh. Never infer completeness from one ticker. Both stock
and Orange County rental workflows remain required; new rentals stay deferred.
Full regression: **489 passed, zero skipped, 55 dependency warnings**, 167.62s,
UI/API enabled; `output/tests/class-share-ledger-verified.log`. Browser checked
the actual stale-count panel, accessible table and numerical example; dollar
signs were then escaped to prevent Markdown math formatting. No novice usability
study or investment performance validation is claimed. Current fresh preview:
**http://127.0.0.1:8513/** (`--server.fileWatcherType poll`); older previews remain.
Final focused UI check after that formatting fix: **one passed**, eight dependency
warnings; `output/tests/class-share-ledger-ui-final.log`.

**Current UI standard:** [beginner clarity](UI_CLARITY_GUIDELINES.md) applies to
each future milestone. Research screen adds optional term explanations/examples,
plain-language data states and separate business/price/history cards. Detailed
metadata remains optional; financial calculations and strict gates are unchanged.
Other workspaces still need this review; no novice usability study is claimed.
Regression: **474 passed, zero skipped, 55 dependency warnings** in 44.95s;
`output/tests/beginner-clarity-verified.log` (UI/API checks enabled).
**Latest source milestone:** [fundamental refresh](fundamental-refresh.md).
`fundamental_refresh.py` and `tools/refresh_installed_fundamentals.py` plan/refresh
installed issuers only, guard full public-release/directory identities, report
before/after clocks/quantities and retain visible last-good data on failures.
Actual 88/88 SEC sources re-fetched; 12 payloads changed, eight share references
advanced, no annual period changed. Valuations 64 estimated / 10 stale / 12 multiple /
two unavailable. Financial statuses unchanged at 39/22/27; validation 662 pass /
zero mismatches / 159 unavailable. New release
`3f3cebcf6eba188861924e00d13e9c2949c505c452da7b450b20217c35aa1fbf`.
Market snapshot/cutoff unchanged. UI adds an evidence-date timeline and retrieval
timestamp. Duration shares refused. No scheduler, paid access or gate relaxation.
Full regression: **474 passed, zero skipped, 55 warnings**, UI/API enabled;
`output/tests/fundamental-refresh-verified.log`.
Next: complete class/share ledger; broader dated security evidence and coordinated
reference refresh. Ten stale share observations cannot be repaired by download alone.
**Latest evidence milestone:** [class and financial evidence](class-and-financial-evidence.md).
`security_identity.py` imports/corroborates dated AAPL/NVDA registered classes;
new Research screen inspector panel. Narrow nested inline-DEI date parser, not a
general XBRL engine. `stock_financials.py` v2 sums same-accession/current-ending
current/noncurrent liabilities; independent rational sums plus GD statement
reference fixture. All 88 issuer tables rebuilt offline; only two filing-cover
documents downloaded. Financial states 39 pass / 22 fail / 27 unavailable;
40 issuers still have missing checks. Validation: 648 pass / 0 mismatch / 173 unavailable.
Release `98906539b176fc42dbd9e52ae6e2e2a406d8bfe404c7150688e19e34b58631a5`;
market snapshot/cutoff unchanged. **465 tests pass**, UI/API enabled, 55 warnings;
`output/tests/class-and-financial-evidence-verified.log`. No strict gate relaxed.
Next: freshness of filing/share observations, broader reviewed class coverage and
complete economic-class ledger; capex/custom-tag semantics remain unresolved.
Previous preview: **http://127.0.0.1:8512/**, launched with
`--server.fileWatcherType poll` for reliable updates on the Windows/OneDrive path.
Earlier servers were preserved; their imported source registries may be stale
and cannot necessarily read the new cover-table release. Use the current preview.
**Latest implementation:** [daily price refresh](daily-stock-refresh.md).
`daily_stock_refresh.py`, `tools/refresh_installed_history.py`, `stock_refresh_ui.py`
add complete-cohort staging/resume, full-window raw/split/all validation, atomic
CAS publication, explicit same-cohort rollback and a lazy read-only panel.
Actual 89-series refresh published through October 30: 89,444 rows; COR retains
August 30, 2023 gap. New snapshot `bd8ef356fe5633eb74e6c215b0bd3f3bbfc4728166b19fa2564d2b83dd6cd726`.
Full suite: **445 passed, zero skipped, 55 warnings**; log `output/tests/daily-refresh-verified.log`.
Five independent October 30 close diagnostics passed. No SIP migration, source
refresh, automatic scheduling, strict gate relaxation or public release occurred.
Windows MAX_PATH failure was fixed by short job locators plus full plan/hash
validation. Old artifacts remain. Fresh UI preview uses http://127.0.0.1:8511/;
the earlier 8510 server was preserved to avoid discarding existing sessions.
Next: security/class/share evidence, financial gaps and isolated SIP validation.
**Read first:** [blocker audit and release decisions](BLOCKER_RESOLUTION_PLAN.md).
Twelve bounded IEX/SIP historical probes succeeded with existing credentials;
no subscription or production feed was changed. Public Alpaca redistribution is
not cleared. Strict selection remains an unimplemented adapter/readiness checker.
Six diagnostic tests pass separately from the 419-test application baseline.
The October 31 packaging question was unresolved at that time. On November 6,
the user explicitly approved local actual-data research plus a public
synthetic/cleared demo first. Strict gates and source rights remain unchanged.
UCI Capital IQ and WRDS are optional academic-validation leads only; no user
entitlement, dataset access, exports or public/personal-investing use was verified.
**October 31 progress:** Evidence inventory, versioned decision policy/context and
opt-in experimental decision workspace are implemented. Read
[stock decision workflow](stock-decision-workflow.md) for precedence, limitations
and next priorities. These are bounded portions of stock stages 1–3; strict
verification, refresh and complete holding review remain unfinished.
Latest full regression: **419 passed, zero skipped, 55 warnings**, UI/API enabled;
`output/tests/decision-workflow-verified.log`. Local Streamlit is served at
http://127.0.0.1:8510/ for this session. UI proof is saved as
[Local workspace path omitted from public documentation.]
**Purpose:** Carry project goals, current code status, preferences, and next steps into a new Codex chat.

## Continue-from-here instructions

Continue in this repository and preserve the existing working tree. Do not reset, overwrite, or discard uncommitted work. Read this file and the README before making changes. Follow the next incomplete stage in the authoritative stocks-first execution order in PROJECT_ROADMAP.md, implement its concrete deliverable through the relevant model/API/UI/docs, and check the changes. Finish stock stages 1–5 before starting new rental milestones (stages 6–8), then shared comparisons and release (stages 9–10). Both stock screening and rental discovery are equal release requirements. Do not demote either to an optional extension or switch back to tax-aware portfolio trading as the flagship. Explain assumptions and report what tests could and could not run.

**Model preference:** Use GPT-6.1 Sol as the default for this multi-step coding project. Medium reasoning is suitable for routine feature work; use High for financial calculation design, architecture, or difficult multi-file debugging. Use Light for small, well-scoped edits.

## Project goal

**Accepted framing, October 29:** Complete an investment decision workflow, not
just a stock screener. Keep strategy-based purchase recommendations and add
separate hold/trim/sell review, pass and insufficient-evidence outcomes with
explanations and change conditions. Hold/sell policies and full personalization
remain planned work. Ranking removal alone is not a sell trigger. Read
[DECISION_WORKFLOW_PIPELINE.md](DECISION_WORKFLOW_PIPELINE.md) alongside the
authoritative ten-stage roadmap. Stocks first, rentals second, then integration
and release; strict evidence gates and the no-paid-data constraint persist.

**Data budget/access constraint:** The user authorizes free provider accounts and API keys, but no paid data, subscriptions, billing enrollment, paid trials or upgrades. Prefer documented free sources and verify actual free-tier limits and public-display permissions. Do not invent contact details or expose keys in chat, logs, URLs or artifacts. Provider signup requiring personal information or terms acceptance must be completed with the user. Broader daily price/benchmark coverage and index/property coverage remain measured feasibility gates.

Build a technically strong, in-depth educational tool for comparing tax and investment strategies. It should make assumptions, uncertainty, risk, time commitment, liquidity, fees, and tax limitations visible. Calculations should be deterministic or reproducible from recorded assumptions. The optional LLM may parse user language or explain completed results, but it must not own financial arithmetic, eligibility decisions, or unsupported claims.

This is an educational software project, not tax, legal, accounting, or investment advice. The current project has no user accounts and is intended to run locally.

## Current implementation

- **Listing evidence/coverage milestone (latest):** Added bounded official Nasdaq
  and other-exchange directory imports, exact ACT/CQS/NASDAQ alias matching and SEC
  exchange corroboration. 501/505 reference securities corroborate; BRK B, BF B,
  HOLX and SKYD WS remain unmatched. This does not verify official index membership,
  legal share-class identity or issuer-wide valuation. Listing flags/conflicts
  exclude observed experimental candidates; no strict gate changed. A coverage
  chart and source/date/type details are available in Research screen.
  Expanded a prespecified four-sector batch by 24 issuers: now 88 issuer records,
  89 market series, 89,266 daily rows through October 28. Financials: 36 pass,
  21 fail, 31 unavailable. Valuations: 63 estimates, seven stale, 12 multi-security,
  six unavailable. Independent arithmetic: 640 pass, zero mismatches, 168 unavailable.
  Five latest-close diagnostics passed against the new market snapshot. Fixed
  current-release/older-price-cutoff planning and old-symbol pricing. Resolved a
  repeatable navigation timeout with bounded size-aware file reads, selective
  company artifact verification and lazy source-panel loading. Integrity checks
  remain on all consumed artifacts. 391 tests passed, zero skipped, 55 warnings,
  126.96s; API and browser checked. Price data is not automatically refreshed or
  advanced to October 29. Read [listing-evidence-and-coverage.md](listing-evidence-and-coverage.md).

- **Decision review/validation milestone (latest):** Added independent arithmetic
  reconciliation plus two official annual-report reference cases. Actual audit:
  500 pass / 0 mismatches / 92 unavailable; 15/16 source inputs match, one unavailable.
  GET /research/stock-validation is no-store and respects local-market mode.
  Experimental research now explains feasible alternatives and contribution gaps,
  offers one-company yield sensitivity (actual ±10%: 46 scenarios, three replacing
  one stock), checks manually entered direct holdings exposure, and links selected
  companies to financial/event research. Freeze a dated prospective paper basket;
  track subsequent complete sessions versus SPY after matched entry costs, export/
  restore bounded validated JSON. Private records stay in session; imported clocks
  are explicitly unverified. Actual tracking is pending future installed sessions.
  Full historical strategy backtest remains withheld for missing point-in-time
  membership/filing/valuation/delisting evidence. 376 tests passed, zero skipped,
  55 warnings; final restore/metadata/API focused checks: 10 passed. Read
  [decision-review-and-validation.md](decision-review-and-validation.md).

- **Experimental basket milestone (latest):** User explicitly approved a separate
  proxy/estimate paper-research section while preserving strict recommendation
  gates. Stocks → Build portfolio now has Verified recommendations / Experimental
  research tabs. Explicit opt-in selects ten equal-weight real-company research
  positions using five exact within-sector percentile features and sector quotas;
  exclusions/risk limits can make the request infeasible. No relaxed constraints,
  broker orders or performance claim. Session-only budget sizing, contribution
  chart, exclusions, source hashes and JSON snapshot are available. Coverage is now
  64 financial issuers / 65 market series / 65,194 daily records. Full suite:
  366 passed, zero skipped, 39 warnings, 99.07s. UI and API tests enabled.
  Strict recommendations remain blocked; this does not complete stock stage 3.
  See [experimental-research-basket.md](experimental-research-basket.md).

- **Split price/replay/readiness milestone:** Share price defaults to split-only
  adjusted closes, with original prices opt-in; missing split evidence withholds
  that view. Actual NVDA June 2024 split values were checked against the installed
  snapshot. New Historical replay uses matched company/SPY dates and deposits,
  explicit price-only or all-adjusted proxy basis, fees and a deposit/value ledger.
  Three-company financial comparison preserves fiscal-period/availability labels.
  Build portfolio is a server-owned READINESS CHECKER, not real stock selection:
  no basket is issued from unverified membership/security/valuation inputs. Real
  selection integration is still unfinished, alongside source gates. An experimental
  estimate/proxy basket was subsequently explicitly approved and implemented as
  documented in the latest milestone above. New no-store endpoints: /research/stock-replay
  and /research/stock-proposal. 360 tests passed, zero skipped, 39 warnings, 53.08s.
  See [split-prices-and-investment-replay.md](split-prices-and-investment-replay.md).

- **Stocks-first stages 1–2 milestone (October 29):** Financial coverage expanded
  from 20 to 44 issuers across eight sectors; 24/25 requested new SEC imports
  normalized, with the unresolved XOM current-directory dataset kept unavailable.
  Private IEX history now has 44 issuer series plus SPY, 1,003 dates each, with
  per-series retrieval clocks and compatible atomic merge protection. The screen
  adds annual profitability/leverage/growth and full-window risk metrics,
  fail-closed editable filters, exact exclusion reasons, sortable metric results,
  a profitability scatterplot and all 505 proxy securities in Coverage & evidence.
  New no-store POST /research/stock-screen/filter uses the same pure engine.
  Financial rules: 23 pass, 6 fail, 15 unavailable. Valuation: 35 estimates,
  3 stale, 4 multiple-security cases, 2 unavailable. All 44 histories pass the
  count/gap gate; none establishes exact consolidated reinvested total return.
  AAPL/MSFT/NVDA latest-close diagnostics were within the stated tolerance.
  Full suite: 353 passed, zero skipped, 34 dependency warnings, 37.49s; final
  filter/API/UI focused checks: 6 passed. Source verification is still PARTIAL:
  official dated membership/security identity, verified current valuations,
  full-universe inputs and public quote rights remain open. Stage 3 is blocked.
  Next continue these stock verification/coverage gates; do not start new rental
  work. Offline audit: tools/audit_stock_research.py. Read
  [stock-verification-and-metrics.md](stock-verification-and-metrics.md).

- **Rental holding-period milestone:** Added Purchase & cash flow / Holding period
  & stress tabs. A Decimal monthly ledger reconciles fixed-loan payoff, yearly
  rent/expense growth, equity, separate operating/replacement reserves, repair
  shocks, distributions, bounded outside funding and sale costs. Both operating
  insolvency and an unaffordable underwater sale withhold exit profit. Base and
  adverse timelines, month inspection and full ledger table explain assumptions.
  Typed POST /real-estate/rental-projection shares the engine; no private cache,
  database or provider calls. Inputs survive navigation and reset explicitly.
  Full verification: 347 passed, zero skipped, 30 dependency warnings, 40.59s.
  Preview UI8510 / API8009. This is manual property research, not ZIP discovery.
  See [rental-holding-period.md](rental-holding-period.md). Next: finish the stocks-first stages in the authoritative execution order;
  rental discovery resumes after stock workflow acceptance. Do not claim release done.

- **Chart clarity and second-source diagnostic:** Value of $100 / Share price ($)
  / Drawdown views explain their units and date-window behavior. Dollar view uses
  original raw closes and hides SPY; return/risk cards stay adjusted. Donut radii
  now respond to plot dimensions with a separate wrapping legend and padding.
  Freshness distinguishes completed trading session, download timestamp and live
  quote. A bounded operator Yahoo Finance diagnostic checks exact-date latest
  closes without replacing primary data. Apple was within the visible tolerance
  (about 0.067% difference); full history remains unverified. Reports are bound to
  snapshot hash/date, local-only, with explicit unavailable/discrepancy states.
  Full suite: 338 passed, zero skipped, 30 dependency warnings, 69.31 seconds.
  See [chart-clarity-and-price-checks.md](chart-clarity-and-price-checks.md).

- **Latest sector/valuation/readiness milestone:** Research screen joins the dated
  505-security fund proxy to 501 unique SEC matches; no official membership is
  inferred. Real split-only history now covers 20 issuers plus SPY (1,003 dates
  each). Normalized reported point-share evidence supports 16 filing-based
  valuation estimates, explicitly separate from verified current market caps.
  Financial rules: 12 pass, three fail, five unavailable. Local-only typed screen
  exposes eligibility reasons and source hashes with no partial scores or live
  selections. Charts now have area shading, dashed comparison, paired hover and
  calendar range presets. See [sector-valuation-readiness.md](sector-valuation-readiness.md).
  Verification: 334 tests passed (zero skipped, 22 dependency warnings, 45.98s).
  Browser checked the 20-to-12 financial filter, inspector-to-company navigation
  and one-year matched-date chart. A tooltip layering fix then passed both chart
  tests. Preview remains UI8510 / API8009. The earlier Windows native diagnostic
  remains unresolved; it did not recur in this full run.

- **Latest market/dashboard milestone:** User-configured ignored Alpaca paper
  credentials were verified by actual data-only requests. Private IEX history now
  covers AAPL, MSFT, AMD, NVDA, AMZN and SPY: 1,003 observations each, no missing
  calendar sessions in the imported interval. Added bounded raw/all-adjusted
  ingestion, atomic local snapshots, gap-aware risk math and matched-date charts.
  Market display is explicitly local research; public redistribution is not allowed.
  Stocks now opens an editable portfolio doughnut matching the user's six-weight
  example, with exact cent reconciliation, cash and index/ETF overlap caveats.
  A dark slate/mint/lavender interface groups research into five focused tabs.
  See [local-market-history.md](local-market-history.md). Do not expose, print or
  copy keys; no trading/account/paid endpoints or automatic jobs were used.
  Full regression suite: 324 passed, zero skipped, 22 dependency warnings,
  115.39 seconds; final layout checks: two passed. No native diagnostic in this
  run, but the earlier allocation/API Windows issue remains unresolved.
  Local preview: UI8510 / API8009. Price/risk coverage is research-only; current
  issuer market caps, full universe/sector validation and live selection remain open.

- **Latest news/events slice:** 21 issuers have verified SEC filing metadata
  (2,251 nested filings), a filterable timeline and source links. AMD/Meta and
  Sandisk earnings examples are manually reviewed official-source facts with
  review dates and no sentiment score. There are 20 financial research issuers;
  Sandisk is Events only because its financial import failed validation. Browsing
  stays offline; operator refresh is explicit and not scheduled. See
  [company-news-events.md](company-news-events.md). Preview UI8510 / API8009.
  Full suite: 300 passed, zero skipped, two warnings, 31.51 seconds. The first
  run caught an outdated expected OpenAPI route list; final full rerun passed.
  Existing Windows native diagnostic concern is still unresolved.

- **Latest strategy evidence milestone:** Company research now opens Strategy fit:
  raw five-feature evidence, shared financial rules, missing versus failed checks,
  and explicit recommendation blockers. Latest assessment is included in the typed
  company API; fiscal-year inspection updates the UI assessment. No partial score
  or live recommendation is fabricated. Full suite: 285 passed, zero skipped,
  two warnings, 24.75 seconds. Preview remains UI8510 / API8009. See
  [company-strategy-evidence.md](company-strategy-evidence.md).

- **Latest issuer expansion:** 19 supported cached issuers (previously 4), through
  bounded operator import plans from a verified SEC directory. Exact CIK joins,
  share-class deduplication, fixed SEC URL templates and publication-time mapping
  guards are implemented. Fifteen new issuers succeeded; XOM's current issuer
  response failed normalization and remains unavailable. Full suite: 281 passed,
  zero skipped, two warnings, 64.54 seconds. Current preview UI8510 / API8009.
  See [sec-issuer-imports.md](sec-issuer-imports.md). Price/benchmark coverage,
  index membership and single-family ZIP rent evidence remain incomplete.

- **Public-data release pipeline:** verified normalized releases now separate transport, semantic adapters, immutable artifacts, publication and read-only serving. Ten datasets contain 35,544 records; per-area/security/source audit matrices expose missing joins and incompatible categories. Source locks, per-provider spacing, bounded retries, atomic publication, idempotent offline builds, selective refresh and last-known-good recovery are tested. `GET /research/data-readiness` and collapsed three-tab UI panels expose coverage without quote values or private financial inputs. See [public-data-pipeline.md](public-data-pipeline.md).

- **Visual workspaces:** Real estate / Stocks / Goals / Tools navigation. Real estate is the landing view with reactive financing/cash-flow charts, annual waterfall and pinned comparison. Stocks has a clickable synthetic quality/value map, feature inspector, constraint examples and sector weights. Manual rental assumptions and synthetic data are prominent. No live discovery is implied. See [visual-workspaces.md](visual-workspaces.md).

- **Tax:** deterministic 2026 federal and payroll estimates for single W-2 profiles; optional LLM profile parsing and narrative output.
- **IRA corrections:** compensation-limited eligibility, phaseout rounding/minimum treatment, and separate prior traditional/Roth capacity effects. Legacy total-only prior contributions are treated as Roth unless the traditional portion is supplied. See the tax rule ledger.
- **Contribution allocator:** bounded mixed-integer L1 allocation model with cent-sized purchases, per-account cash/permissions, aggregate concentration limits, explicit infeasibility, independent output checks, three baselines, API and session-only Streamlit page. Account types are descriptive: no tax-aware allocation, sales, or return optimization yet. Exhaustive tiny-case oracle and seeded synthetic evaluation are documented in [contribution-allocation.md](contribution-allocation.md).
- **Scenarios:** monthly portfolio growth, low/base/high savings goal plans, equal-current-cost Roth/traditional comparison, rental/house-hack underwriting, and flip underwriting.
- **Planning constraints:** financial readiness prompts covering self-selected reserves, debt APR comparisons, liquidity horizon, time availability, and separate risk willingness/loss capacity.
- **Debt:** avalanche versus snowball payoff model with fixed minimum-payment assumptions.
- **Uncertainty and sensitivity:** seeded lognormal Monte Carlo goal analysis; deterministic one-variable-at-a-time sensitivity for return, contributions, fees, and inflation.
- **Saved runs:** explicit SQLite save/list/retrieve/compare flow for goal-risk runs. Comparisons require aligned goal setup, contribution, horizon, inflation, path count, and seed. Other assumptions such as return, volatility, and fee may differ.
- **Interfaces:** FastAPI with typed Pydantic contracts and a Streamlit UI.
- **Goal Explorer:** interactive planning workspace with contribution/deadline sliders, annual low/base/high charts, purchasing-power toggle, required deposits, optional terminal simulation, and session baseline comparison/restore/delete. Validated JSON export/import records model version and inputs; no Explorer database persistence or shared financial cache. Calculations run in the Streamlit process, not the browser. See [goal-explorer.md](goal-explorer.md).
- **Privacy boundaries:** default `APP_MODE=ephemeral` blocks saved-run and AI endpoints before request parsing; a key alone cannot enable AI. Explicit trusted local mode enables history, and AI also requires `ENABLE_AI=true`. Validation failures do not echo financial inputs. API responses discourage caching; the local launcher omits URL access logs. Streamlit telemetry is off, local binding and XSRF/CORS protections remain on, and the sidebar discloses processing and can reset the session. See [privacy-boundaries.md](privacy-boundaries.md).
- **Goal Explorer polish:** chart-first/side-by-side layouts, stacked funding and comparison cards, keyboard timeline controls, readable changed assumptions, same-elapsed-year comparisons by default, rounded/sub-cent estimate safeguards, static table alternatives, and applying the base contribution estimate.
- **PDF reports:** explicit in-memory preparation/download, vector charts, required deposits, yearly checkpoints, model/report versions, privacy notices, and an optional compatible baseline comparison. Financial outputs are recomputed from revalidated inputs; stale downloads are invalidated. JSON remains the format for reopening a plan. See [goal-pdf-reports.md](goal-pdf-reports.md). Developer-only sample PDFs under ignored `output/pdf/` are synthetic and separate from the production path.
- **Documentation:** source/method notes for tax assumptions, readiness, debt payoff, goal-risk simulation, sensitivity, and saved-run privacy.

See [README.md](../README.md) for architecture, setup, endpoints, interview demo path, and the full feature backlog.

## Ordered remaining pipeline

**Authoritative direction:** [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md).
The user requires **algorithm-generated S&P 500 stock purchase recommendations
and Orange County long-term rental discovery as equally important parts of the
final investment product**. A screener alone or an exclusively user-selected
basket does not satisfy the stock requirement.
Standalone single-family rentals remain a provisional housing type. Stock work
must not be deferred until after a rental-only release is called complete.

**Finish line:** stock strategy -> selected securities/weights/purchase amounts
-> explained company/basket analysis, and rental discovery
-> property underwriting, connected by stress/history exploration, aligned
scenario comparisons, reproducible exports, evaluation and verified deployment.

The authoritative execution order is now **stocks first, real estate second,
shared integration third**. This user decision supersedes earlier alternating
milestones, including the older next-step notes below historical milestones.

1. Verify stock membership/security identity, valuations, coverage and source access.
2. Finish real-company stock metrics, filters and evidence.
3. Enable explained real stock baskets, weights and purchase amounts.
4. Complete company/basket analysis, news context and investment replay.
5. Close stock shortlists, reports, portability and evaluation; meet stock acceptance.
6. Complete Orange County geography, rental data coverage and area discovery.
7. Connect area candidates to property analysis, existing feasibility/stress and comparisons.
8. Close rental shortlists, reports, portability and evaluation; meet rental acceptance.
9. Align stock/property funding, horizons, cash flows and combined comparison/reports.
10. Verify packaging, public data permissions, deployment, privacy and production behavior.

**Current task selection: finish local stock acceptance under the November 6
approved scope.** Decision portability/review/reports/evaluation can proceed
under the existing explicit experimental policy. Strict stage 1 source gates
remain open and must never be presented as satisfied.
Do not switch back to new rental feature work until the stock workflow is complete.
Fix shared regressions and preserve all existing rental behavior. No paid feeds,
real-time quotes, brokerage execution or cloud financial accounts are assumed.

Preserve supporting calculators. Defer tax-aware trading, broker execution,
additional universes/geographies/property types and cloud financial accounts.
Stock attractiveness must come from the defined strategy and company/market
evidence; user budgets/goals constrain feasibility and sizing. The first strategy
hypothesis is quality at a reasonable valuation; features, weights and objective
are now specified in stock-strategy-v1.md but remain unimplemented and unvalidated. Current-universe recommendations and selected-
stock historical replay are in scope; a historical screening backtest requires separate point-in-time evidence.
Neither missing-data matches nor universal stock/property winners may be invented.

## October 28 strategy/data milestone

Read [data-feasibility-2026-10-28.md](data-feasibility-2026-10-28.md) and
[stock-strategy-v1.md](stock-strategy-v1.md). Strategy design is frozen in
`strategies/quality_value_annual_v1.json`: annual quality/value scoring and a
sector-constrained ten-stock target basket, specified and unvalidated, not a
live selector. The existing allocator is only the downstream sizing component.

`market_sources.py`, `market_data.py`, `data_audit.py` and
`tools/audit_market_data.py` implement fixed public-source downloads, hashes,
atomic snapshot pointers, basic schema gates and repeatable offline coverage.
Nine snapshots were downloaded. Census 2020 land-overlap candidates number 92;
89 have SFR value rows and 81 mixed-rent rows. Audited SFR rents are metro-only,
so automated SFR ZIP yield screening is unsupported by these sources. IVV has
505 equity proxy rows with snapshot prices; this is not verified membership or
price history. SEC company facts work for four samples; ticker/exchange mapping
returned HTTP 403. Public display rights and several data gates remain open.

Proceed with coherent annual financial normalization/reference tests and rental
accounting while resolving data gates. Do not claim Phase 1 or Phase 2 entirely
complete, silently substitute mixed rents, or generate real recommendations from
unverified membership/valuation. No paid data subscription was authorized or
purchased. Raw provider data is ignored under `data_cache/`.

## October 28 annual metrics/rental v2 milestone

The user's research objective is to outperform S&P 500 total return after modeled
costs, with aligned dates/cash flows and honest held-out evidence. This is not an
achieved result or promise. It is recorded in the strategy JSON and roadmap.

`stock_financials.py` normalizes same-accession/same-period annual USD facts with
source evidence. It computes ROA, operating/FCF margins and liabilities/assets,
including a checked total-equity liabilities fallback. Offline command:
`python tools/normalize_stock_samples.py --as-of 2026-10-28`. AAPL/MSFT/KO normalize;
JPM remains incomplete. Valuation inputs and stock selection remain unavailable.
See [annual-financial-normalization.md](annual-financial-normalization.md).

`scenario_engine.py` rental model v2 now excludes capex reserves from operating
NOI, includes repairs/held operating reserves/HOA/utilities, returns break-even
rent and first-year loan accounting, and uses null for undefined ratios.
`cash_invested_estimate` excludes held reserves; `initial_cash_required` includes
them and is the cash-on-cash denominator. API/UI are updated, with a single-rental
UI default. See [rental-underwriting-v2.md](rental-underwriting-v2.md). This changes
v1 NOI/ratio semantics deliberately. No price optimization or automatic rent
sourcing is implemented. Local preview: UI8506, API8006, no access logs.

## October 28 strategy execution/feasibility milestone

`stock_strategy.py` executes eligibility, exact sector-relative tied percentiles,
score contributions, canonical issuer classes and optimal sector-quota selection
on synthetic IDs only. Public `/research/stock-strategy-demo` accepts fixed cases
and budget cents; it cannot be switched to live data. `rental_feasibility.py`
solves a cent-level bounded maximum purchase price and down-payment intervals
under capital, financing, cash-flow and optional return constraints using exact
rational arithmetic. `/real-estate/rental-feasibility` exposes typed results.
Both run directly in the new session-only Research workbench. Preview UI8507
and matching API8007 use the new code; older previews were preserved. No live provider permissions were added.

See [strategy-engine-and-feasibility.md](strategy-engine-and-feasibility.md).
Tests include 40 exhaustive-selection comparisons and 35 brute-force rental
cent-grid cases, independent maximum-price boundaries, issuer/data gates, typed
API workflows and UI submission/clear/invalid-budget behavior. Live selection,
full portfolio/account integration and benchmark evidence remain incomplete.

## Earlier verification snapshot (superseded by latest milestones below)

October 28, 2026: **231 passed, 0 skipped**, exit code 0, with both integration
flags enabled outside the Windows sandbox, exit 0 in 24.48 seconds. A Windows
native access-violation diagnostic recurred during an existing allocation/API
path despite all tests completing. An isolated 22-test check passed without it;
root cause is unresolved and remains a runtime/release concern. Do not describe
this as a clean production certification or suppress diagnostics. The final UI
precision validation change also passed its targeted workflow test.
Eighteen additional tests cover normalized annual metrics/filing coherence and
rental v2 accounting, Decimal amortization, break-even, API and live UI behavior.
Sixteen prior offline tests cover
transport/cache integrity, geographic overlap, missing/future observations,
proxy non-claims, publication/period alignment and offline execution.
Two dependency warnings remain
(Starlette/AnyIO and Streamlit/Pandas). Compilation and `git diff --check` passed.
Allocation tests include exhaustive tiny-case references, restriction conflicts,
cent accounting, solver failure handling, API validation, and UI submission/reset.
The previous October 27 PDF milestone had 151 passing tests; its Poppler render
checks covered normal and 60-year extreme-value/long-label reports. Browser
checks use synthetic defaults, not real user financial data. Remote CI is still
unconfirmed because this checkout has no Git remote configured.

Goal Explorer adds independent reference cases, accounting/contribution/return invariants, validated plan-file tests, an API trajectory endpoint, and AppTest interaction checks. Run the complete suite using the flags below outside the Windows sandbox. The legacy API/UI workflows also use a temporary localhost Uvicorn server, the real HTTP client, and an isolated SQLite database. Browser spot-checking used synthetic defaults in the in-app browser at a narrow viewport, including contribution-slider keyboard input and synchronized balance changes. This is not a full mobile, cross-browser, or accessibility review. These checks are enabled in GitHub Actions, but no remote is configured and no successful CI run has been confirmed. The restricted Windows sandbox can hang on integration tests.

Run locally from PowerShell:

```powershell
$env:RUN_API_REQUEST_TESTS = "1"
$env:RUN_UI_TESTS = "1"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q .
git diff --check
```

For local app usage, start these in separate terminals:

```powershell
.venv\Scripts\Activate.ps1
python run_api.py
```

```powershell
.venv\Scripts\Activate.ps1
streamlit run streamlit_app.py
```

`/calculate` works without an OpenAI API key. `/optimize` requires `APP_MODE=local`, `ENABLE_AI=true`, and `OPENAI_API_KEY`; otherwise it returns 404. Restart both services after configuration changes.

## Git and workspace state

[Local workspace path omitted from public documentation.]
- Current branch at handoff: `master`
- Initial baseline commit: `1492071 Initial project baseline`
- The readiness guide, debt payoff, Streamlit/API work, Monte Carlo analysis, sensitivity, saved-run storage, and documentation are part of the current working tree and remain uncommitted. Keep them intact.
- The default SQLite file `scenario_runs.sqlite3` and sidecars are Git-ignored. Saved-run routes are local/single-user only; the app does not yet authenticate users.

## Progress reporting

Report completed acceptance gates and remaining work from PROJECT_ROADMAP.md,
not a precise percentage. Existing calculators and the first contribution
allocator and initial public-data audit foundation are implemented. Actual
source coverage is partially measured and the stock strategy is specified; live
discovery/recommendations and full data approval remain incomplete. The user's priority is a useful, defensible investment project with equal
stock and rental workflows, substantive data engineering, transparent modeling,
and measured results. Neither scanner's coverage, real user validation nor
public deployment is complete yet.

## Latest visual milestone verification

238 full-suite tests passed (0 skipped, exit 0); final targeted visual/interaction checks 7 passed. Browser confirmed chart-to-inspector selection and live rent sensitivity; 390px layout checked. Preview port 8508, backend 8007. New UI source: investment_workspace_ui.py; pure chart helpers: investment_visuals.py. Read docs/visual-workspaces.md. Live data/rights/discovery and observed usability remain next gates; previous intermittent Windows native diagnostic is still a release concern.

## Latest data engineering milestone (October 28, 2026)

262 full-suite tests passed (0 skipped, exit 0, 27.53 seconds); two dependency warnings. Ten public datasets normalize into 35,544 records. Coverage matrices contain 92 rental candidate rows, 505 fund-proxy security rows, four issuer summaries and source provenance. No verified current USPS/index universe, ZIP single-family rent or matched benchmark is claimed. HUD download returned HTTP 202/empty; SEC mapping refresh requires SEC_USER_AGENT operator contact (the earlier endpoint returned 403). Paid accounts/subscriptions and recurring jobs were not created.

Current preview UI8509 / API8008. Start through the existing Streamlit app and configured API URL. Public refresh: tools/refresh_market_data.py --as-of 2026-10-28; network requires --download and only missing/due sources are fetched. --source refresh retains other tables. Developer-only audit export: --coverage-report output/audits/source-coverage-matrices-2026-10-28.json. Read docs/public-data-pipeline.md before continuing. Data verification remains partial. Next resolve the explicit source/mapping/rights gaps before enabling live discovery; deployment scheduling and load/recovery verification remain release gates. Historical Windows native diagnostic remains unresolved even though it did not recur in this run.

## Latest free-data company research milestone

User authorizes free accounts and API keys but no paid data, billing, subscriptions, paid trials or upgrades. Authorized SEC operator contact is configured in Git-ignored .env; never copy it into docs, logs or artifacts. Actual SEC refresh now succeeds: 10,430 directory records and four filing snapshots. SEC numeric filing data/directory reuse is reviewed against the official FAQ. Exact joins resolve 501/505 fund-proxy tickers; BRK B, BF B, HOLX and SKYD WS remain unresolved. This is not verified S&P membership or historical identity.

Stocks now defaults to Company research with five fiscal years for Apple, Microsoft, Coca-Cola and JPMorgan. Strategy lab remains explicitly synthetic. Added offline typed company endpoints, filing evidence, linked period inspection and revenue/cash-flow/margin charts. Source histories may include later restatements; no price/valuation/purchase advice is inferred. See docs/free-company-research.md. Full suite: 270 passed, exit 0, 54.33 seconds, 0 native diagnostics in the final run; an earlier 269-pass run did reproduce existing Windows diagnostics. Root cause remains unresolved. Final log: ignored output/tests/company-research-full-suite.log. Current preview UI8510 / API8009.
