# Installed stock evidence refresh — November 7, 2026

Operator-run refresh of the existing free-data cohort, without selecting sources
to improve a score. Current serving data remains available during staging;
verification gates, cohorts and paid-feed restrictions are unchanged. No
scheduler, account/billing change, provider-response logging or credential export.

## Published references and prices

All four required reference sources published together:

| Source | Observation date | Records |
| --- | --- | ---: |
| SEC issuer directory | Not provided by source | 10,419 |
| Nasdaq listings | November 6 | 5,610 |
| Other exchange listings | November 6 | 7,666 |
| IVV fund holdings reference | November 5 | 505 |

Reference release:
`369ef1b924154c1531f820df8241489e7d1734731ecffbdd1e93a87292a2c439`.
Retrieval was November 8 UTC / November 7 Los Angeles. This does not verify
official S&P membership, economic share classes or public redistribution rights.

All **89 installed price series** published in four batches through the latest
completed session, **November 6**, replacing the October 30 cutoff. Snapshot:
`8e593f26ae8494df137a01c1f1d9059abf423dcfbf4566e89c47bfb275c4e010`.
No newly required sessions are missing. The known COR August 30, 2023 gap remains
disclosed. This is local IEX data, not a consolidated feed or certified total return.

References, prices and SEC financial refreshes are separate transactions; this
run does not imply one atomic transaction across all stores. The price plan binds
the reference release used during its download. A later financial-only release
can advance the public manifest while preserving those reference tables.

## Clearer acceptance diagnostics

All **88 SEC company-facts sources** subsequently refreshed without requested-
source failures or budget exhaustion. Thirty-two source payload hashes changed,
one selected annual period changed and 24 share-evidence records changed.
Final public release:
`0d080e7d913bb4d15eccb5f5dfb7c9bd4282c52f032cc2baa177c20a44277dda`.
This does not refresh old fiscal/share measurement dates merely by downloading.

Final installed-data evaluation: **incomplete — 7 passed, 3 blocked, 0 failed**.
References satisfy the age policy and all available company price observations
are November 6. Candidate count remains zero because the covered sample cannot
fill the ten-stock basket under unchanged financial/peer/sector rules. Monthly
allocation, exclusion sensitivity and cap examples remain blocked on actual
data. The independent-note correction accounts for one additional exercised
check; seven passes are not all a consequence of better source coverage.

Before the financial refresh, qualified sector counts were Industrials 8,
Consumer Staples 6, Health Care 7, Materials 4, Information Technology 4,
Consumer Discretionary 1 and Communication Services 1. Only three sectors met
the five-peer minimum, allowing at most nine stocks at three per sector.
After refresh, Industrials rose to 9 and Health Care to 8; the other counts
were unchanged. There are still only three qualifying sectors.
Next audit the current peer/financial-feature gaps under the declared universe;
do not relax rules or pick extra companies merely to force a basket.

The workflow evaluation now records reference freshness, observed fund-reference
date, company count, candidate count, available price-date range and counted
blocking reasons. The UI uses plain labels and explains the ten-stock, three-per-
sector and five-qualified-peer rules. Counts can overlap and are not probabilities.
Blocked example checks identify the actual candidate count instead of suggesting
that every failure is stale data. Price ranges do not establish complete coverage.

TDD also exposed an unnecessary candidate dependency: personal notes need neither
current prices nor a ten-stock basket. Their roundtrip now uses a fixed fictitious
holding, so it remains exercised when market-dependent paths are blocked.

Focused regression: **44 passed**, 12 dependency warnings, 5.12 seconds,
`output/tests/stock-refresh-acceptance-focused.log`. Includes all three refresh
workflows, diagnostics, the independent-note correction and UI invalidation.
Earlier red logs retain the initial diagnostic and note-independence failures.
Compile and whitespace checks pass. The prior milestone's complete UI/API run
passed 609 tests; it was not unnecessarily repeated for this bounded change.

## Audit files

All paths below are ignored local artifacts under `output/audits/`:

- `reference-plan-2026-11-07.json`, `reference-refresh-2026-11-07.json`
- `history-plan-2026-11-07.json`, `history-refresh-2026-11-07.log`
- `fundamental-plan-2026-11-07.json`, `fundamental-refresh-2026-11-07.json`
- `stock-workflow-refreshed-2026-11-07.json`

No investment-performance, full stock completion, public deployment or observed
beginner-usability claim follows from refreshed inputs or passing software tests.
Both stocks and rentals remain required; new rental discovery follows stock acceptance.
