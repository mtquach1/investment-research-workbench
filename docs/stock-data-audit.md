# S&P 500 stock data audit — initial source inventory

Latest implementation: [normalized-release audit](public-data-pipeline.md).
An actual Alpha Vantage IBM demo contains 100 adjusted daily observations from
June 5 through October 27, 2026, including explicit dividend/split fields. It is
one independent demo, below the strategy's 756-observation requirement; it is
not joined into the fund holdings without verified security mapping. Public
display rights and full-universe/benchmark coverage remain unresolved. New SEC
downloads now require configured identifying operator contact; cached disclosure
normalization remains offline. Generated matrices list all 505 proxy securities
with explicit unverified membership/joins and four financial sample summaries.

Updated October 28, 2026. Status: actual IVV sponsor holdings and four SEC
company-facts snapshots inspected. The [joint feasibility report](data-feasibility-2026-10-28.md)
records 505 equity proxy rows, sample annual tag coverage and a blocked ticker
mapping endpoint. Authoritative index membership, full-universe financial
metrics, price history and public display rights remain unresolved. Strategy-based stock selection and portfolio recommendations
are an equal requirement of the final product; screening alone is insufficient.
See [the combined roadmap](PROJECT_ROADMAP.md).

| Need | Candidate/source role | What remains unverified |
| --- | --- | --- |
| Current universe and membership dates | S&P DJI index documentation plus an accessible appropriately licensed constituent source | Actual full security list, date coverage, share classes, access/display rights and refresh process |
| Issuer fundamentals and filing dates | SEC EDGAR submissions and XBRL company facts | Required tags, company-specific gaps, amended filings, fiscal periods, currencies, comparability and sector exceptions |
| Price/dividend/split history | Provider to select after coverage and rights audit | End-of-day coverage, identifiers, adjustment semantics, dividends, corporate actions, delistings, rate limits and public display permission |
| Benchmark | Appropriately licensed index total-return series or identified investable benchmark | Fees/tracking distinctions, matching history, distribution treatment, access/redistribution terms |
| Sector classification | Source to verify | Classification scheme/license, point-in-time changes, issuer/security mapping and missing categories |
| Historical strategy evaluation | Dated membership plus fundamentals known at each decision date | Availability/cost and completeness; current members replayed backward is not a historical universe |

## Primary-source documentation findings

- [S&P DJI S&P 500 page](https://www.spglobal.com/spdji/en/indices/equity/sp-500/)
  identifies the intended index and methodology. This does not establish free
  automated access or permission to redistribute constituent/history data.
- [S&P Global constituent-data notice](https://pages.marketintelligence.spglobal.com/SP-Dow-Jones-Indices-Constituent-Removal.html)
  discusses licensing for current/historical constituents in its Compustat
  context. Review the actual chosen source's terms; do not infer that every
  possible source has identical requirements or is unavailable.
- [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
  documents submissions and XBRL financial facts, available without API keys.
  EDGAR supplies financial disclosures, not a complete stock-price/dividend feed
  or a validated S&P membership list. Custom tags and period/unit selection can
  still create coverage/interpretation gaps.
- [SEC data-access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
  documents fair-access requirements. Implement source-aware identification,
  rate limiting and caching according to the guidance current at integration.

## Required coverage matrix and decisions

One row per security/source/metric series, with issuer CIK, share class, dated
ticker mapping, universe membership date, financial period, filing/publication
date, observation date, currency/units, retrieval date, adjustment convention,
source URI/version, missing/stale/inapplicable state, and rights review status.

Do not convert negative earnings into a favorable valuation ratio, missing
dividends into confirmed zero distributions, or annual-plus-YTD records into a
double-counted trailing year. Reconcile restatements and retain the distinction
between revised history and information actually available on an earlier date.

First deliverable: measured current-universe coverage for the proposed screening
metrics and historical replay window, plus provider options/access constraints.
No paid source, account registration, real-time quote service, or comprehensive
historical backtest is assumed. If full coverage cannot be obtained, report the
supported subset and retain the full universe's explicit missing-data states.
