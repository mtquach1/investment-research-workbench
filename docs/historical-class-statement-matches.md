# Reviewed historical class/statement links

November 3, 2026. A bounded stock stage 1 milestone: two dated statement quantities
can now be linked to their reviewed registered common-stock classes. These are
historical matches, not verified current quantities or complete economic-class
reconciliations. No paid source, provider download or data-release mutation occurred.

## Evidence and scope

The versioned review registry, `data/reviewed_class_quantities.json`, records exact
issuer/ticker/class title, cover and share contexts, accession, source hash,
measurement/filing/review dates, quantity, scaling, precision and review rationale.
Both reviews are available only on or after November 3; historical assessments
cannot see them before that date. The registry hash accompanies every assessment.

The [Apple filing](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm)
maps AAPL to common stock with a $0.00001 par value. Its balance-sheet common-stock
caption uses the same par value; the year-end count and Note 10 ending count agree.
The [NVIDIA filing](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)
similarly connects NVDA's $0.001-par common-stock title with the balance-sheet and
equity-rollforward count. These links rely on a documented manual reading of the
same filings, not a second independent source or ticker-count inference.

| Reviewed class | Historical measurement | Shares | Filing date |
| --- | --- | ---: | --- |
| AAPL common stock | 2025-09-27 | 14,773,260,000 | 2025-10-31 |
| NVDA common stock | 2026-01-25 | 24,304,000,000 | 2026-02-25 |

DEI cover counts remain unallocated issuer observations. Other dates, weighted
averages and dimensional facts are not silently substituted. No class market
capitalization or yield is calculated from these historical quantities.

## Match contract

`class_quantity_review.py` requires a fresh unique directory association,
corroborated listing and unique corroborated filing class. Every exact reviewed
title, cover context, period and source must match. Exactly one undimensioned
outstanding-share observation must match issuer, accession, date, context,
quantity, precision and scale; its complete source receipt must agree with the
cover. Missing evidence and conflicting evidence have different statuses.
Duplicate facts/reviews fail closed; no newest, largest or convenient match is
selected. Explicit dimensions stay separate and do not become ticker assignments.

The per-security ledger adds `historical_quantity`, including registry hash,
review record and reason. Existing `assigned_shares` remains null and all current
class/economic-rights/issuer-valuation verification flags remain literal false.
The existing no-store stock-screen API serializes this additive typed evidence.
Malformed review registries fail closed rather than enabling a match.

## UI

Stocks → Research screen → company → share-class ledger now separates **current
shares assigned** (unknown) from the **historical statement link**. An optional
panel gives the full historical quantity, measurement/filing/review dates, age at
the check date and primary filing link. Another optional explanation describes
the statement/class connection. Historical evidence never replaces the latest
issuer count. Plain-language status text accompanies every outcome.

## Actual audit

Full regression completed: **546 passed, zero skipped, 59 dependency warnings**,
53.74s, with UI/API checks enabled; `output/tests/historical-class-matches-verified.log`.
Focused review/serialization checks: 25 passed; focused UI/navigation checks:
two passed. These verify tested software behavior, not observed novice usability
or investment performance.

The installed 88-issuer cohort has **two historical matches and 123 unreviewed
directory securities**. No complete all-economic-class reconciliation exists.
Financial outcomes remain 39 pass / 22 fail / 27 unavailable; valuations remain
64 estimates / 10 stale / 12 multiple / two unavailable. The public release and
market snapshot remain those recorded in the coordinated-refresh milestone.

```powershell
.venv/Scripts/python.exe tools/audit_stock_research.py --as-of 2026-11-03 --output output/audits/historical-class-matches-2026-11-03.json
```

Further work: current class-specific quantities, complete common/nontraded and
preferred/security classification, economic/conversion rights and aligned price/
corporate-action evidence. Official membership, broader coverage and public
display rights remain separate gates. Strict recommendations and approved
experimental selection rules are unchanged. Stocks remain first; both stock and
Orange County rental discovery remain required, with existing rentals preserved.

Interview suggestion: show an accepted historical match, change one source hash
or share-context ID, and demonstrate the resulting explicit rejection. The dated
registry demonstrates review lineage and guards against look-ahead; it does not
establish strategy performance or full product completion.
