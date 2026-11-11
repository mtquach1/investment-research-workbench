# Dated point-share evidence: two-filing cohort

November 1, 2026. Stock stage 1 continues with the already installed Apple FY2025
and NVIDIA FY2026 filings. This is a bounded quantity/precision evidence milestone,
not proof that every economic class is known or a current valuation is verified.
No downloads or paid sources were needed.

## Implemented

`filing_share_evidence.py` reads two supported point-share tags from bounded
inline-XBRL fragments: DEI entity common shares outstanding and US-GAAP common
shares outstanding. It preserves the issuer/context, measurement and filing
dates, accession, numeric scale, reported precision and explicit dimensions.
No ticker-to-class quantity mapping is inferred. Weighted-average and diluted
share counts do not substitute for point counts.

The parser refuses wrong issuers/units, duration or future contexts, typed
dimensions, duplicate IDs, malformed numbers, nil/continued/signed facts,
unsupported transforms and excessive structures. Explicit dimensions remain
unassigned. NVIDIA nests an issued-share tag inside the outstanding-share tag;
this narrow case requires identical context, unit, scale, precision, transform
and numeric text. No general nested-fact interpretation is claimed.

`security_identity.py` adds observations to the verified normalized artifact
summary (`sec-cover-class-shares-v2`). The existing stock-screen API and class
ledger expose source receipts for every observation. Publication rebuilt only
the two cover tables offline and retained all other installed tables.

## Actual evidence and independent reference reading

There are **16 observations**, including **10 dimensional observations**. Older
years and equity-component dimensions are retained rather than added together.
Four fixed, manually read reference cases in
`data/filing_share_reference_cases.json` matched the normalized values and
reported precision: **4 pass / 0 mismatch / 0 unavailable**. These are independent
reading/arithmetic checks of the same filings, not corroboration from a different
issuer data source. The audit requires matching accession, date, tag, source hash
and undimensioned scope; duplicates are ambiguous, not silently deduplicated.

| Filing observation | Measurement date | Shares | Precision increment (shares) |
| --- | --- | ---: | ---: |
| Apple balance sheet | 2025-09-27 | 14,773,260,000 | 1,000 |
| Apple cover | 2025-10-17 | 14,776,353,000 | 1,000 |
| NVIDIA balance sheet | 2026-01-25 | 24,304,000,000 | 1,000,000 |
| NVIDIA cover | 2026-02-20 | 24,300,000,000 | 100,000,000 |

The [Apple filing](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm)
reports balance-sheet quantities in thousands; page 31 and Note 10 reconcile
the year-end count. The [NVIDIA filing](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)
reports balance-sheet shares in millions (page 53) and a rounded cover count in
billions. Different dates and rounding cannot establish buybacks, issuance or a
class discrepancy by themselves. Precision increments describe reported rounding,
not confidence intervals or a license to accept mismatches.

## UI improvement

The ledger panel keeps the large issuer count at full width and places filing
coverage and unresolved reconciliation in separate cards below. Optional filing
comparison shows readable share units, dates, count basis and precision; older
periods/dimensions are opt-in. It clearly distinguishes these older filing counts
from the latest issuer count and never adds them together. Source details retain
full tags, dimensions and hashes. Missing class assignment stays visible.

## Reproduction and limitations

```powershell
.venv/Scripts/python.exe tools/refresh_market_data.py --as-of 2026-10-31 --source sec_cover_aapl_2025 --source sec_cover_nvda_2026
.venv/Scripts/python.exe tools/audit_filing_shares.py --as-of 2026-11-01 --output output/audits/filing-share-references-2026-11-01.json
```

Published release:
`d7528d421a6a2cd61cbff4fd14ba01a223cebfb873d1fefa48223db9088ea8d4`.
The market snapshot and October 30 price cutoff are unchanged. Actual stock
coverage remains 88 financial issuers, 39 financial passes / 22 failures / 27
unavailable; valuations 64 estimates / 10 stale / 12 multiple securities / two
unavailable. Share ledgers remain 70 recent unallocated / 16 stale at check date /
two unavailable. **Zero issuers have reconciled economic-class quantities.**

The parser is for these registered documents, not a general XBRL engine. Complete
economic/nontraded classes, preferred/debt/warrant classification, conversion
rights, aligned corporate actions/prices, broader reviewed coverage, official
membership and public-display rights remain unfinished. All strict flags remain
false; experimental selection rules are unchanged. Rental functionality is
preserved; Orange County discovery remains required after stock acceptance.

## Internship demonstration value

Validation: **509 tests passed, zero skipped, 55 dependency warnings**, 54.41s,
UI/API enabled; `output/tests/filing-share-evidence-verified.log`. Focused parser/
ledger/screen checks passed 50 tests; new UI comparison and existing navigation
checks passed two tests. The audit and coverage artifacts are in `output/audits/`
with the `filing-share-` prefix. Existing unrelated source-failure receipts remain
visible in the release; neither cover table recorded a new import failure.
These are software/reference checks, not novice usability or performance evidence.
Browser QA checked Apple's real count/rounding table, source-class row and optional
history control in a fresh full-app preview on `http://127.0.0.1:8514/`. The older
8513 process retained its prior UI module despite the file watcher; it was preserved.

Demonstrate a raw filing → hashed artifact → typed API → understandable UI →
reference-audit trace, including malformed-unit and ambiguous-context failures.
This is concrete evidence of data correctness and product judgment; test totals
alone do not demonstrate scale, investment performance or hiring readiness.
Next suggested engineering evidence: a reproducible latency/completeness benchmark
and a clean-install fixture demo, when those fit the stock acceptance milestones.
Avoid adding infrastructure solely to name technologies in an interview.
