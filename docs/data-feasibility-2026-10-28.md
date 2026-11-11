# Joint data feasibility report — October 28, 2026

Status: **measured partial coverage, not production data approval**.
See [roadmap](PROJECT_ROADMAP.md) and the specified, unvalidated
[stock strategy](stock-strategy-v1.md).

## What was actually done

Downloaded and hashed official Census relationship data, three Zillow CSVs,
iShares IVV holdings, and four SEC company-facts JSON samples. Parsed real rows,
checked observation/filing dates against October 28, and generated a repeatable
coverage report. No paid feed/account was purchased or registered. No financial
user inputs, API keys, or AI calls are used by the audit.

Full local evidence: `output/audits/market-coverage-2026-10-28.json` contains source
URLs, retrieval timestamps, content hashes, per-geography statuses, and sample
financial tag coverage. Provider snapshots live under ignored `data_cache/`.
They are not committed or presented as cleared for redistribution. This report
summarizes coverage; it is not a property or stock recommendation.

## Orange County rental findings

| Check | Observed result |
| --- | --- |
| Geographic candidate universe | 92 Census 2020 ZCTAs with positive land overlap with county 06059; union with provider county-labeled rows added none |
| Cross-county candidates | Eight ZCTAs have positive land in more than one county |
| Single-family ZIP value series | 89 available, three missing under the 90-day audit freshness gate |
| Mixed-home ZIP rent series | 81 available, 11 missing under the same gate |
| Latest period in both ZIP files | September 30, 2026 |
| Single-family rent geography in audited download UI | Metro & U.S. only; ZIP was not offered after selecting single-family rents |
| Downloaded single-family regional rent context | A Los Angeles, CA metro series through September 2026; not a verified Orange County-only or ZIP-specific rent estimate |
| Automated single-family ZIP cash-flow screening | **Not supported by these audited source combinations** |

These 92 areas are a dated land-overlap candidate set, **not a verified complete
current USPS residential ZIP universe**. Some are border geographies or unusual
areas; land shares are not residential-address shares. A current crosswalk and
parcel/location checks remain necessary. Do not relabel the count as current
Orange County residential ZIP coverage.

Missing single-family value rows: 90743, 92678, 92697. Missing mixed-rent rows:
90623, 90716, 90742, 90743, 92617, 92624, 92655, 92676, 92678, 92697, 92861.
The audit preserves these states instead of filling values from neighboring ZIPs.

The UI finding is limited to the inspected source/options; it does not prove
that no provider anywhere offers single-family ZIP rents. Mixed rent cannot be
divided by single-family values and labeled a property yield. HUD benchmarks
also have a different purpose; the HUD page fetch returned HTTP 202 with no body
through the initial command-line request, so no HUD raw rows were audited here.

**Implementation decision:** retain single-family homes as the provisional type.
Build dated price/market context and manual specific-property rent underwriting
without claiming automated ZIP rent/yield matches. Investigate an appropriately
licensed property-type rent source before enabling those automated criteria.
Do not change to mixed-property underwriting silently or call the county audit
complete. The remaining source/rights decisions stay explicit.

Sources: [Census relationship files](https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.2020.html),
[Zillow downloads and categories](https://www.zillow.com/research/data/),
[HUD rent benchmarks](https://www.huduser.gov/portal/datasets/fmr/smallarea/index.html).

## Stock findings

| Check | Observed result |
| --- | --- |
| Sponsor holdings snapshot | IVV, October 26, 2026 |
| Equity security rows | 505, across 11 sponsor-labeled sectors |
| Non-equity rows excluded | One each: futures, money market, collateral/margins, cash |
| Positive finite snapshot prices | 505; these are not a verified daily-history feed or live executable quotes |
| Authoritative S&P 500 membership/history | Not verified by ETF holdings |
| SEC ticker/exchange mapping download | HTTP 403 from this environment; not retried as a successful source |
| SEC company facts on data.sec.gov | Successfully downloaded four reviewed issuer samples |
| Price/dividend/split history and total-return benchmark | Not yet verified or selected |

The ETF is an identifier/coverage **proxy**, not a substitute for verified index
membership. Different share classes, tracking differences, and snapshot dates
must remain visible. This snapshot does not provide a historical index universe.

Annual USD fact audit (only records filed on or before the analysis date; same
fiscal period for income/cash-flow fields):

| Sample | Annual period end | Available of seven audited tags | Missing direct aligned tags |
| --- | --- | ---: | --- |
| AAPL | 2025-09-27 | 7 | None |
| MSFT | 2026-06-30 | 7 | None |
| KO | 2025-12-31 | 6 | Liabilities |
| JPM | 2025-12-31 | 5 | Operating income and cash PPE capex |

The seven tags cover revenue, operating/net income, operating cash flow, capex,
ending assets and liabilities. This is tag/period availability, not a complete
metric engine: beginning assets, per-issuer market cap, class mappings, semantic
fallbacks, statement consistency, annual freshness/eligibility and full-universe
coverage still require work. A missing direct liabilities tag does not mean no
liabilities; a reviewed reconciliation may later recover it. JPM is a sector
exception control, not evidence that the industrial-company model suits banks.

**Implementation decision:** proceed with normalization and independent metric
fixtures on the accessible SEC samples. Do not release stock recommendations
until membership, issuer valuation, sector/security mapping, historical-risk
coverage and appropriate source rights are verified. Do not infer market cap by
blindly multiplying annual weighted-average shares by one share-class price.

Sources: [iShares IVV sponsor page](https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf),
[SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces),
[S&P index information](https://www.spglobal.com/spdji/en/indices/equity/sp-500/).
CIKs were checked against SEC filing sources before fetching company facts.

## Reproducibility and access controls

From the repository root, explicitly download missing registered sources:

```powershell
.venv\Scripts\python.exe tools/audit_market_data.py --as-of 2026-10-28 --download
```

Then reproduce from local snapshots without network:

```powershell
.venv\Scripts\python.exe tools/audit_market_data.py --as-of 2026-10-28
```

Use `--download --refresh` to fetch updated bytes deliberately. Snapshots are
content-addressed and checksum-verified. The downloader uses fixed registered
URLs, bounded streaming, timeouts, at most two attempts, transient-error backoff,
and no retries for HTTP 403. SEC requests are spaced. HTML/empty/changed-header
responses cannot replace the last valid transport/header snapshot. Same-host
HTTPS redirects are checked before following. Report writes are atomic.

This is an initial ingestion foundation, not the entire production pipeline.
Full semantic validation before publication, refresh scheduling, deployment
concurrency controls and lifecycle/retention management remain roadmap work.
The as-of filter does not reconstruct historical Zillow data vintages: retrieved
series may contain revisions. The report explicitly disclaims a point-in-time
historical dataset and readiness for public display.

## Remaining gates and next implementation slice

1. Independently verified current S&P universe/issuer mappings and access rights.
2. Suitable daily price/dividend/split and valuation source with documented rights.
3. Full-universe financial normalization/coverage and sector exceptions.
4. Current county/ZIP mapping and suitable single-family rent coverage or an
   explicitly narrower supported automated workflow.
5. Source-specific attribution/display/redistribution review for public hosting.

Next safe implementation slice: coherent annual financial metrics with traceable
fallbacks and synthetic/reference tests, alongside refinement of rental accounting
and a manual property rent editor. Keep live recommendation and automated ZIP
cash-flow claims disabled until the relevant data gates are met.
