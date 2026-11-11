# Stock decision workflow, October 31, 2026

**November 6 update:** [decision snapshots](decision-snapshots.md) now provide
named private JSON save/restore and current-evidence change review. This supersedes
the earlier restore/change-review planned-only statements below. The older raw
assessment export is still not a restorable snapshot. Full suite: 569 tests pass;
private PDF summaries are now implemented; complete thesis/cost/tax-aware holding review remains unfinished.

This implements three bounded pieces of stock pipeline stages 1–3: an evidence
inventory, versioned user/decision contracts, and an experimental triage engine
with an investigation interface. It does **not** complete those stages or enable
verified recommendations.

## Find it

Stocks → Build portfolio → Decision workflow. Inspect the evidence chart/table,
explicitly opt in, enter constraints, filter assessments and investigate a
company. Open its existing financials, prices and events, or download a private
JSON assessment. This workflow only reads installed integrity-checked snapshots.

## Evidence inventory

`stock_evidence.py` separates pass, observed failure, missing and provisional
inputs. Counts cover installed issuers, not the full index. Requirements include
annual financials, missing financial checks, sector, quality features, dated
prices, risk history, estimated valuations, listing, identity and membership.
Stale prices and short history mean missing usable evidence, not adverse business
judgments. Checking today does not refresh observations. Automatic refresh is off.

Screen rows now preserve `financial_missing_reasons` separately. October 31's
installed inspection shows 43 records with missing financial checks: 31 classified
unavailable and 12 with both missing inputs and an observed failure. The existing
36 pass / 21 fail / 31 unavailable categories alone did not show that overlap.
Strict identity/index/valuation gates and public-display rights remain unresolved.

## Policy and context

`strategies/decision_policy_v1.json` is hashed canonically alongside strategy and
source release/market/universe/listing hashes. Its five-year horizon preference
is an explicit design choice, not an empirically validated suitability threshold.

Typed context accepts bounded exact-cent cash, monthly contribution intentions,
0–60 year horizon, direct-position cap, optional historical volatility ceiling,
unique exclusions and at most 25 unique holdings totaling at most $1 million.
Monthly contributions are recorded only, not allocated or forecast. No accounts.

Scores/sector peers use the unchanged baseline basket; personal restrictions
then affect fit without rewriting scores. This differs deliberately from the
older experimental-basket restrictions, which filter before scoring.

## Decision precedence

1. No consent or unavailable/integrity-failed sources/stale universe: no cards.
2. Missing usable evidence, ambiguous identity, contradictory listing or absent
   proxy membership: **insufficient evidence**. Known review flags remain visible.
3. Fully assessed holding failing financial/sector or personal fit rules:
   **review for trim/sell**, never an executable sell.
4. Unheld company failing those rules: **pass**, with reasons.
5. Missing qualified sector peers: **insufficient evidence**.
6. Existing holding still passing supported rules: **hold**, regardless of top-ten
   rank. This is a limited model result, not a complete investment thesis.
7. Unheld baseline selection passing fit: experimental **buy candidate**. Other
   qualified unheld company: **pass** for the opportunity limit, not a failed
   business. An infeasible basket cannot produce new buy candidates.

Current concentration uses entered holdings only, excluding new cash. Candidate
concentration uses holdings plus cash. Unknown holdings get insufficient-evidence
cards but remain in denominators. ETF look-through/class aggregation is unsupported.
Original equal-weight cent amounts apply only to unheld candidates. Held/blocked
amounts stay cash; no replacement or smaller allocation is invented. Additions
plus unassigned cash reconcile exactly. Zero funding still permits holding review.

## Engineering and boundaries

Pure `assess_decisions(screen, context)` sorts deterministically, preserves source
inputs and has no storage, provider, trade or clock side effects. API:

- `GET /research/stock-evidence`
- `POST /research/stock-decisions`

Server-loaded evidence and no-store responses prevent client certification and
response caching. Private context is not globally cached, persisted or sent to
providers. Downloads contain personal inputs: save privately. JSON is reproducible
export, not a signed attestation or implemented restore.

Tests exercise consent/failure states, missing-versus-fail precedence, rank
removal, concentration, exact cents, unchanged scores, duplicate/invalid inputs,
cross-request isolation and the interactive journey. No profitability claim.

Final verification: **419 passed, zero skipped, 55 dependency warnings**, with
`RUN_UI_TESTS=1` and `RUN_API_REQUEST_TESTS=1`; log:
`output/tests/decision-workflow-verified.log`. The browser inspection on October
31 used the real installed snapshot and showed ten experimental candidates with
the default constraints. No new source data was downloaded or certified.
The earlier full run found the expected API route list needed updating; the
final run includes that contract update and filing-vintage safeguards.

Still unfinished: strict data coverage; atomic daily refresh; broader news and
calendars; thesis changes and acquisition-lot/cost/tax review; recurring allocation;
decision restore/history/change review and stock PDFs. Finish stocks before new
Orange County discovery work. Interview priorities are refresh/recovery failure
tests, measured latency/concurrency, independently checked normalization and
prospective SPY evaluation. Architecture complexity needs a measured reason.
