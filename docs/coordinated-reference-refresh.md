# Coordinated stock-reference refresh

November 1, 2026. Completes a bounded source-refresh deliverable within stock
stage 1. It does not complete security identity, index membership or valuation
verification. Stocks remain first; both stocks and Orange County rentals remain
required for the final product.

## Behavior

`reference_refresh.py` plans and refreshes exactly four installed sources: the
SEC ticker/issuer directory, Nasdaq-listed directory, other-exchange listing
directory and IVV fund-holdings proxy. Plans are offline and retain full previous
release identity, hashes, observation dates, retrieval clocks and record counts.

The existing immutable-release pipeline now accepts an optional publication
check, called under its writer lock before advancing `CURRENT.json`. The new
coordinator requires every selected source to normalize successfully, a new
retrieval receipt for every source and dated listing/fund observations within
seven calendar days. An absent date does not pass, except for the SEC directory,
whose source supplies no observation date. Its retrieval date is shown separately.
The full previous release ID must still match before any transport begins.

Any failed/stale required source rejects the entire candidate publication. The
exact previously installed pointer stays unchanged. Other jobs' established
partial-source behavior remains unchanged unless they opt into the new check.
All artifacts are hash-checked before serving/publication. Successful reference
publication preserves unrelated financial, filing, rental and market artifacts.

Raw source caches and unreferenced normalized artifacts can advance during a
rejected attempt; these are not the serving release and are not rolled back.
Source failures are recorded without provider bodies, credentials or private
financial inputs. A separate bounded report distinguishes installed receipts
from rejected candidate receipts; mismatched/invalid reports cannot establish
current source health. There is no scheduler or automatic retry job. The
transport budget is checked before each source request, not a hard interruption
of an already running bounded provider request.

## Actual refresh

All four free sources were re-fetched and all four source payload hashes changed.

| Source | Previous observation | New observation | Previous records | New records |
| --- | --- | --- | ---: | ---: |
| SEC issuer directory | Not provided | Not provided | 10,430 | 10,423 |
| Nasdaq listings | 2026-10-29 | 2026-10-30 | 5,621 | 5,616 |
| Other exchange listings | 2026-10-29 | 2026-10-30 | 7,672 | 7,670 |
| IVV holdings proxy | 2026-10-26 | 2026-10-30 | 505 | 505 |

Published release:
`652a3b6d9d17e4ecb0c78e552b0039b99d9ba52cac50c0f7415879ea0e8cacff`.
The source/reference counts changed; installed financial results remain
39 pass / 22 fail / 27 unavailable across 88 issuers. Valuation estimates remain
64 estimated / 10 stale / 12 multiple-security / two unavailable. Listing
corroboration remains 501 / 505; four exact symbols remain unmatched. Market
snapshot and October 30 price cutoff are unchanged. No strict gate was relaxed.

## UI and commands

Stocks → Research screen → **Are the stock reference sources up to date?** is a
lazy, read-only panel. Two status cards distinguish source age from unverified
official membership. A source table separates observation/retrieval dates and
shows retained failures. Optional before/candidate comparison and audit download
explain what changed. Reopening this panel never downloads or starts a refresh.

```powershell
# Offline plan. Add --download only to perform the coordinated refresh.
.venv/Scripts/python.exe tools/refresh_stock_references.py --as-of 2026-11-01 --output output/audits/reference-plan.json
.venv/Scripts/python.exe tools/refresh_stock_references.py --as-of 2026-11-01 --download --output output/audits/reference-refresh.json
.venv/Scripts/python.exe tools/benchmark_stock_research.py --as-of 2026-11-01 --output output/audits/stock-research-latency.json
```

The CLI cannot change providers, enroll in billing or enable recommendations.
Financial/share/price refreshes remain separate operator workflows. This is
coordinated reference publication, not one transaction across every data store.
Source freshness does not verify official membership, economic classes, current
valuation, source accuracy or public-display rights.

## Measured engineering evidence

Completed regression (recorded November 3 after the interrupted chat): **520
passed, zero skipped, 55 dependency warnings**, 74.31s, UI/API enabled;
`output/tests/reference-refresh-verified.log`. No additional run was needed to
establish that previously completed result.

The bounded offline benchmark ran three sequential stock-screen calculations
over the same 88-issuer/505-security release with artifact checks. Observed times:
1,168.304 / 927.444 / 939.421 ms; median **939.421 ms**. The descriptive nearest-rank
p95 is 1,168.304 ms, but three observations cannot support a reliable tail-latency
claim. This is a single-process calculation benchmark, not an HTTP/load test.
The OS file cache was not cleared; no cold-start claim or speedup is asserted.
The benchmark refuses unavailable research and snapshots changing between runs.

Artifacts: `output/audits/reference-refresh-2026-11-01.json`,
`reference-refresh-coverage-2026-11-01.json`,
`stock-research-latency-2026-11-01.json` (same directory).

Interview suggestion: demonstrate a successful four-source publication, then a
required-source failure with an unchanged serving pointer. Pair that reproducible
failure case with the measured latency artifact. This demonstrates transaction
design and honest measurement; it does not establish full-product completion,
production scale or investment performance.
