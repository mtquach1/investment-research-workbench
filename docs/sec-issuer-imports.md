# Bounded SEC issuer imports

Implemented October 28, 2026. This extends financial statement coverage without
adding arbitrary URLs, provider calls from visitors, or paid data dependencies.

An operator plans imports from an installed, hash-verified SEC directory no more
than seven days old. Exact ticker matches must identify one CIK; missing and
ambiguous matches reject the entire plan before downloading. Share classes such
as GOOG/GOOGL share one financial statement import. Already published issuers reuse
their existing source ID. Batches allow at most 50 inputs and 25 new issuers.

```powershell
# Offline plan; no provider request.
.venv/Scripts/python.exe tools/import_sec_issuers.py --as-of 2026-10-28 --tickers NVDA AMZN GOOGL GOOG
# Explicit operator execution, using the configured private SEC identification header.
.venv/Scripts/python.exe tools/import_sec_issuers.py --as-of 2026-10-28 --tickers NVDA AMZN GOOGL GOOG --download
```

Canonical source IDs contain exactly ten ASCII CIK digits and resolve to a fixed
SEC HTTPS template. Transport still verifies the source, bounds requests and
spaces provider access. The adapter checks the response CIK before publication.
The release writer locks publication and checks the directory hash against the
plan before any requests. Changed mappings require a new plan. Selective imports
retain other domains; default rebuilds also retain dynamically added issuers.
Individual source failures remain recorded. Serving installed snapshots never
downloads missing companies.

## Actual coverage

The first batch requested 17 tickers resolving to 16 additional issuers. Fifteen
published successfully, expanding the directory from 4 to 19 supported issuers.
NVIDIA, Amazon, Alphabet, Meta, Tesla, Adobe, Salesforce, Oracle, Broadcom, Costco,
PepsiCo, Walmart, Procter & Gamble, Johnson & Johnson and Home Depot were added.
XOM currently maps to SEC CIK 2115436 (ExxonMobil Holdings Corp); that response
failed semantic normalization. It is unavailable, with an explicit release
failure. Do not silently substitute a predecessor issuer's filings.

Release `fe2eebdbfaeaf0d1c8a8127b5c4a2504633b7ba386623795725c6d2e39cc02e3`
contains 26 datasets and 45,989 top-level records. HUD remains unavailable and the
XOM import is invalid; both failures are recorded. A directory match is not
verified index membership, historical corporate continuity or security suitability.
Quotes, valuation, matched total-return histories and live recommendations remain
incomplete. Orange County single-family rental discovery is still an equal release
requirement.

There are 95 annual observations across the 19 issuers. Thirteen latest issuer
records have all supported financial inputs; six remain incomplete. For example,
NVIDIA's supported cash-capex inputs do not currently produce free cash flow.
Missing values stay unavailable rather than being inferred from a different tag
or filing without validation.

## Verification

The focused source/import/research/pipeline suite passed 48 tests. The full model,
API and Streamlit suite passed 281 tests, with zero skips and two dependency
warnings, in 64.54 seconds. Log: ignored `output/tests/sec-expansion-full-suite.log`.
An earlier run reproduced a Windows native diagnostic in the allocation/API path;
the root cause remains unresolved despite this run completing without it.

Tests cover canonical paths, wrong response identity, stale/future/naive clocks,
ambiguous or missing matches, duplicate share classes, existing issuer reuse,
batch bounds, mapping changes before transport, offline serving and retention on
default rebuild. Browser verification uses the local UI8510 / API8009 preview.
NVIDIA ticker search resolved to CIK 1045810; moving the fiscal slider to
2025-01-26 changed displayed revenue to $130.50B and moved the chart marker.
The restarted HTTP research endpoint also returned this issuer successfully.
