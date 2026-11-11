# Installed class/share evidence ledger

November 1, 2026. This completes the **installed-evidence ledger slice** of stock
stage 1. It does **not** complete the economic-class ledger or verify any issuer
valuation. No new source documents were downloaded and no evidence gate changed.

## What works

`class_share_ledger.py` assembles a typed ledger for each installed financial
issuer from integrity-checked normalized tables. `stock_screen.py` includes it
in the existing no-store `/research/stock-screen` response. The evidence inventory
also records the missing class/share reconciliation requirement. The separately
authorized experimental decision policy continues to accept disclosed estimates;
this additional inventory row does not change that policy or enable strict buys.

Each ledger preserves:

- Every directory security associated with the issuer, including ambiguous
  issuer matches; filing-only symbols are retained rather than silently dropped.
- Every installed filing-class observation, with exact symbol, title, exchange,
  context, accession, fiscal end, filing date, source URL/hash and retrieval clock.
- The issuer's reported point share observation once, with its own measurement,
  filing and retrieval dates. A quantity is never copied to each ticker, added
  across ticker aliases or treated as diluted weighted-average shares.
- Explicit gaps in full economic/nontraded class coverage, class quantities and
  aligned price/corporate-action evidence. Assigned class shares remain `None`;
  class reconciliation, economic completeness and issuer valuation flags are
  literal false. No class price aggregation is attempted.

The point-share input requires a positive finite integer in shares, the supported
DEI point tag, accession and measurement <= filing <= check date. Future, invalid
and inconsistent evidence fails closed. Stale observations retain their dated
quantities; conflicting or missing counts stay unavailable rather than zero.
Every cover context is retained; no newest filing is chosen to resolve ambiguity.
Source hashes describe lineage, not independent financial verification.

## Beginner interface

Stocks → Research screen → company inspector → **Can this share count be matched
to each share class?** leads with the unreconciled conclusion, a count in shares,
measurement/filing/check dates and a table of observed securities. Optional help
uses two classes (60 × $10 and 40 × $20) to explain why one quote can misvalue the
issuer. Detailed gaps and source receipts remain optional. Directory securities
can be preferred shares, debt or warrants; additional tickers are not automatically
common-stock classes. This ledger is not a buy assessment.

## Actual offline audit, November 1

Scope is the **88 installed financial issuers**, not the full index or all issuers
in the SEC directory. There are 125 observed directory securities and only two
installed cover-class observations. No ambiguous-directory or filing-only symbols
were present in this installed cohort; adversarial fixtures exercise both cases.

| Ledger finding | Issuers |
| --- | ---: |
| Reported issuer count within 120 days, class assignment unknown | 70 |
| Share measurement older than 120 days | 16 |
| No usable point count | 2 |
| Class quantities reconciled | 0 |

The ledger measures share age **at the check date**, independently of whether a
price exists. The existing valuation result uses its **price date**, withholds
multi-security cases before its age test, and remains 64 estimates / 10 stale /
12 multiple securities / two unavailable. These are different denominators and
clocks, not six new stale valuations. Financial results remain 39 pass / 22 fail /
27 unavailable. Download timestamps cannot repair observation-age gaps.

No installed data was mutated. Public release remains
`3f3cebcf6eba188861924e00d13e9c2949c505c452da7b450b20217c35aa1fbf`;
market snapshot remains
`bd8ef356fe5633eb74e6c215b0bd3f3bbfc4728166b19fa2564d2b83dd6cd726`.

Reproduce without credentials or network:

```powershell
.venv/Scripts/python.exe tools/audit_stock_research.py --as-of 2026-11-01 --output output/audits/class-share-ledger-2026-11-01.json
```

The audit artifact contains every ledger, counts and source identifiers. Its
console summary omits the full ledgers to keep operator output bounded.

## Validation

Full regression with UI/API checks enabled: **489 passed, zero skipped, 55
dependency warnings**, 167.62s; `output/tests/class-share-ledger-verified.log`.
The final focused UI check after escaping dollar signs in the numerical example
passed (one test, eight warnings; `output/tests/class-share-ledger-ui-final.log`).
Tests cover multiple directory issuers, filing-only symbols, multiple contexts,
invalid/future quantities, units/tag basis, 120-day boundaries, missing/conflicting
counts, API serialization and preserved experimental/strict behavior. Browser
inspection confirmed the actual stale-count dates, accessible table and corrected
example. This is not observed novice usability or investment performance evidence.
The sandbox's default temporary directory was unwritable and its UI run stalled;
tests used fresh workspace temp directories, with UI/API checks outside the sandbox.
Fresh preview: `http://127.0.0.1:8513/`; older servers were preserved.

## Remaining stage 1 work

Obtain and review complete economic-class evidence for a declared small cohort:
common/nontraded classes, preferred/debt/warrant distinctions, class-specific point
quantities, conversion/economic rights and aligned prices/corporate actions.
Current undimensioned companyfacts counts and registered 12(b) covers cannot
establish that completeness. Then implement independently checked reconciliation
and valuation; do not turn the literal-false flags true based on ticker counts.
Broader dated class coverage, coordinated reference refresh, official membership,
financial semantic gaps and source display rights remain open. Strict selection
is still a readiness checker. Stocks stay first; Orange County rental discovery
remains required after stock acceptance, with existing rental tools preserved.
