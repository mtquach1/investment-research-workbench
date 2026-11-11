# Installed financial/share-source refresh and evidence clocks

Implemented October 31, 2026. This advances stock data stage 1; canonical class
coverage, official membership, verified valuation, public display permissions,
coordinated all-source refresh and scheduled automation remain unfinished.

## What changed

`fundamental_refresh.py` plans a bounded refresh of the **installed issuer cohort**,
not a user portfolio or a list chosen to improve scores. It reads the current
verified release, approved/fresh SEC directory and exact CIK associations, refuses
duplicate/unknown issuers, and limits the cohort to 100 source records. Default
execution budget is 600 seconds before new source fetches; the underlying bounded
per-request transport still controls individual in-flight requests and retries.
This is a between-source budget, not cancellation of an in-flight socket read.

The pipeline now supports an expected full-release guard in addition to its
existing directory guard. Both are checked before transport. Publication remains
one atomic manifest change after validation. Source failures retain earlier
normalized evidence with visible failure metadata; they do not become successful
fresh downloads. Reads continue using the old complete manifest until publication.

Unchanged bytes can have a new download receipt, but their share measurement,
filing date and annual fiscal period remain unchanged. The before/after report
compares source hashes, annual periods, share dates/accessions/status and reported
share quantities, including corrections with unchanged dates. Entity-wide share
disclosures are explicitly **not a complete economic-class ledger**.

The stock screen exposes the financial source retrieval timestamp. The company
inspector adds **Trace the dates behind this estimate**: an interactive evidence
timeline and accessible table for the fiscal year end, share measurement, share
filing, market quote and UTC download date. New retrieval cannot make an older
observation current. Daily filing dates do not establish precise intraday release
times or historically tradable information.
The time axis uses UTC; hover labels use the original ISO date strings. Browser
QA caught local-time tooltip formatting shifting midnight UTC one day backward
in Los Angeles. The corrected labels preserve the exact reported date instead
of formatting a midnight timestamp in the browser's timezone.

`equity_reference.py` additionally refuses duration records in the point-share
selector. Weighted-average diluted shares, inferred missing classes and invented
zero share counts remain excluded.

## Operator commands

```powershell
# No network; inspect the exact installed sources and dated observations.
.venv/Scripts/python.exe tools/refresh_installed_fundamentals.py --as-of 2026-10-31 --output output/audits/fundamental-refresh-plan-2026-10-31.json

# Explicitly re-fetch installed SEC company-facts sources; no paid accounts.
.venv/Scripts/python.exe tools/refresh_installed_fundamentals.py --as-of 2026-10-31 --download --output output/audits/fundamental-refresh-2026-10-31.json
```

The configured SEC identification header is reused without logging its value.
Requests use fixed registered company-facts URLs, existing spacing, bounded
retries and no 403 bypass. No user financial assumptions or credentials are sent.
Progress reports only source counts. Source errors remain controlled metadata,
not raw response bodies or exception text. No account, billing, trade, paid feed,
web scraper, provider agreement or recurring job is created.

The pipeline receipt clock can advance with monotonic elapsed run time. Without
this, a valid download late in a long refresh could appear more than five minutes
in the future relative to the job's initial clock. Existing deterministic
publication/assessment dates are preserved. A seven-minute synthetic receipt
regression verifies that the receipt is assessed at its proper run time.

## Actual installed results

All **88 requested sources refreshed successfully** with no requested-source
failures. Twelve source payload hashes changed; eight share references changed.
No selected annual fiscal period changed. Unrelated earlier manifest failures
(including housing-source access) remain separate; this was not an all-domain
readiness approval.

| Company | Previous share measurement | Refreshed share measurement |
| --- | --- | --- |
| Bristol-Myers Squibb | July 22, 2026 | October 21, 2026 |
| Colgate-Palmolive | June 30, 2026 | September 30, 2026 |
| General Dynamics | April 5, 2026 | October 4, 2026 |
| Thermo Fisher Scientific | June 27, 2026 | September 26, 2026 |
| Stryker | June 30, 2026 | September 30, 2026 |
| Gilead Sciences | July 31, 2026 | October 23, 2026 |
| Amazon | July 22, 2026 | October 21, 2026 |
| Mondelez | April 24, 2026 | October 26, 2026 |

Measured assessment after refresh:

- Valuations: **64 estimated, 10 stale, 12 multiple-security, two unavailable**.
  Before refresh: 59 / 15 / 12 / two. These are estimates, not verified market caps.
- Financial rules remain **39 pass / 22 fail / 27 unavailable**; re-downloading
  did not repair unsupported annual tags or rewrite the accounting strategy.
- Independent validation: **662 passing checks, zero mismatches, 159 unavailable**.
  This checks tested arithmetic and limited statement references, not every
  source disclosure or investment outcome.
- The experimental basket still fills ten positions. Strict recommendations,
  class-complete issuer valuation and public redistribution remain unapproved.
- The IEX market snapshot remains through October 30 with 89 series and 89,444
  rows. No price dataset or return basis was changed in this milestone.

New public-reference release:
`3f3cebcf6eba188861924e00d13e9c2949c505c452da7b450b20217c35aa1fbf`.
Previous release:
`98906539b176fc42dbd9e52ae6e2e2a406d8bfe404c7150688e19e34b58631a5`.
Market snapshot remains
`bd8ef356fe5633eb74e6c215b0bd3f3bbfc4728166b19fa2564d2b83dd6cd726`.

Artifacts:

- `output/audits/fundamental-refresh-plan-2026-10-31.json`
- `output/audits/fundamental-refresh-2026-10-31.json`
- `output/audits/fundamental-refresh-summary-2026-10-31.json`
- `output/audits/fundamental-refresh-validation-2026-10-31.json`
- `output/audits/fundamental-refresh-coverage-2026-10-31.json`
- `output/tests/fundamental-refresh-verified.log`

Tests cover unchanged observations with new receipts, corrected amounts with
unchanged dates, genuinely newer share observations, source failure retention,
budget exhaustion, stale-release races, future receipt assessment and refusal of
duration-share inputs. Test counts measure software behavior, not performance.
Full regression: **474 passed, zero skipped, 55 dependency warnings**, with UI/API
request tests enabled. No strict recommendation gate was relaxed.
Browser QA confirmed General Dynamics' October 4 share measurement, October 30
filing/quote dates and November 1 UTC retrieval date agree between the timeline,
hover labels and table. Local preview remains http://127.0.0.1:8512/.

## Next work

Complete the class/share ledger for a declared supported cohort before applying
one security's price to an issuer with other economic classes. Continue broader
dated filing-class evidence and compatible financial semantic mappings. Ten
share references remain stale despite fresh retrievals; do not override that
gate without newer reported evidence. Directory/listing/universe refresh still
needs coordinated operator support. Keep the two data domains' source permissions
and the eventual public release scope explicit.
