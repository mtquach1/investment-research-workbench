# Sector reference, valuation evidence and real-data selection readiness

Implemented October 28, 2026. This milestone delivers three connected research
steps and a chart redesign. It does not claim completion of live recommendations.

## 1. Dated universe and sector reference

The screen joins the October 26 IVV holdings proxy to unique CIKs in the verified
SEC directory: 505 security rows, 501 unique security-to-issuer matches. Sector
labels retain their dated fund-provider basis. Conflicting sector labels, missing
joins and references older than seven days cannot pass the current sector check.
Only installed financial issuers are analyzed; the other proxy securities are not
silently treated as covered companies. Share classes collapse to one financial
issuer for research counts, with their ticker associations retained.

This is a fund-holdings reference, not an official dated S&P constituent master.
S&P's [constituent-data notice](https://pages.marketintelligence.spglobal.com/SP-Dow-Jones-Indices-Constituent-Removal.html)
describes direct licensing requirements. No membership gate was waived, paid
source purchased, or public-display grant inferred. This combined provider-data
screen is explicitly local research and is withheld before reading data unless
that mode is enabled. Existing public-source display policies remain unchanged.

## 2. Filing-based valuation estimates

`equity_reference.py` extracts the latest known point observation of
`dei:EntityCommonStockSharesOutstanding` in shares. It rejects future/invalid
filing dates, conflicting values, invalid units/counts and unsupported forms.
Diluted weighted-average shares and public-float dollar values never substitute
for outstanding share counts. Source measurement/filing dates and accession are
preserved in normalized company evidence.

Price ingestion now downloads raw, all-adjusted and split-only daily bars, with
identical date sets required for all three modes. Forward and reverse split
adjustment evidence comes from the provider's split-only basis; dividend-adjusted
ratios are not used as split factors. For reported shares S and raw price P:

```
split factor = (raw / split-adjusted at share measurement reference)
               / (raw / split-adjusted at quote date)
estimated shares at quote date = S × split factor
estimated issuer equity value = estimated shares × P
annual earnings yield estimate = aligned annual net income / estimated equity value
annual FCF yield estimate = aligned annual FCF / estimated equity value
```

The share observation must be no more than 120 days before the quote and filed
by the quote date; the quote must be no more than seven days old. A nearby preceding
trading-day reference is allowed for non-trading measurement dates, with the
reference date retained. Missing split evidence, ambiguous counts or multiple
SEC-directory securities withhold the estimate. Negative earnings retain a
negative yield and no P/E; missing FCF remains missing.

The output method is `reported-shares-split-estimate-v1`, in USD. These are
explicit estimates: repurchases, issuance, unlisted class coverage and other
corporate actions may change shares. A single directory ticker does not prove
complete share-class coverage. Annual numerators are not TTM. The estimates never
satisfy `verified_current_market_cap`, which is a literal false in the contract.

Actual local coverage: 20 issuer histories plus SPY, 1,003 dates each (21,063
security-date records), all three adjustment modes. Snapshot:
`758edb9db3686347dad744bed4db30277a503a653c414b2448137388ec8d3c10`.
The public financial release was normalized offline from existing SEC caches:
`dc3b4275a428491fadfb0592630966510a60bcf9b6855891c63114f6bff80f98`.
No new SEC request was needed for the share-evidence normalization.

Of the 20 installed financial issuers, 16 have a supported filing-based estimate;
two lack supported evidence and two have multiple directory securities. The
financial eligibility checks pass for 12, fail for three and lack evidence for
five. These are measured coverage/check counts, not investment quality scores.

## 3. Real-data eligibility integration

`stock_screen.py` uses the same strategy specification/hash and shared financial
checks as the selection engine. It combines financial results, supported-sector
rules, cached price age, complete-history observation counts and valuation evidence.
Financial-sector peer counts are labeled accordingly; they do not claim fully
eligible valuation/risk peers. Missing evidence and observed failures remain
distinct states. No partial investment score, ranking or stock basket is fabricated.

The UI Research screen supports sector and passing-financial filters, a sortable
table, company inspection, valuation evidence and navigation into full research.
Full company analysis links back to its sector/valuation context. The endpoint
`GET /research/stock-screen` is typed, offline, no-store and locally gated.
Responses include public/market snapshot hashes and retain null scores, false
selections and disabled live recommendations.

The strict engine remains blocked by official membership/security identity,
verified current issuer market cap, consolidated exact total-return coverage,
full-universe completeness and performance evaluation. Research estimates are not
quietly fed into the verified-input strategy. A missing gate is a concrete result.

## Chart redesign

`history_chart.py` adds a blue primary line, translucent area, muted dashed SPY
comparison, endpoint dots, nearest-date hover crosshair and paired tooltips.
1W/1M/3M/YTD/1Y/All controls use actual calendar dates, including month ends and
leap days. Custom date selection remains available. UTC axes and raw exact-date
tooltips avoid browser timezone shifts. Publication markers remain separately
labeled and do not establish causation.

Observed prices use linear paths rather than invented smoothed extrema. All risk
metrics still use the complete matched daily window, not chart sampling. The
existing growth/drawdown switch, missing-session policy and exact date alignment
remain. Sources and limitations remain accessible while the main chart card is
less cluttered. The portfolio allocation dashboard and other workspaces remain.

## Remaining work

Complete official membership/security and valuation inputs, broader fundamental
coverage and sector peers, independently evaluated live portfolio construction,
and the shared comparison/reporting flow. Orange County single-family rental
discovery remains an equal release requirement. Public provider permissions,
news refresh, deployment/privacy verification and the earlier Windows native
allocation/API diagnostic are still unresolved; this milestone does not fix them.

## Verification

Full regression: 334 passed, zero skipped, 22 dependency warnings in 45.98 seconds.
The final chart tooltip correction separately passed both chart tests. Browser QA
verified the financial filter changes 20 installed issuers to 12, company inspector
navigation, and the one-year preset produces 252 shared closes from 2025-10-28
through 2026-10-28. Native chart fullscreen also renders correctly. No prior native
allocation/API diagnostic appeared in this full run; its underlying cause remains
open. Sector mapping version `ishares-sector-labels-v1` explicitly normalizes the
provider's Communication label to Communication Services; unknown labels fail
closed instead of becoming an eligible sector.
