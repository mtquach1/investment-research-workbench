# Company news and event context

Implemented October 28, 2026. News context is a required part of explained stock
research, alongside financials and portfolio fit. It does not change the current
five-factor score or predict stock-price direction.

## Delivered slice

Company research has a News & events tab. It includes a filterable SEC filing
timeline, original factual summaries of two manually reviewed official
announcements, announcement/source/review dates, and a timezone-aware scheduled
earnings call. The initial examples are AMD's October 27 Meta collaboration
update and Sandisk's announced October 29, 1:30 p.m. Pacific earnings call.

The summaries separate announced facts from research considerations. AMD's
context includes the announced $1 billion investment in Meta's equity offering,
not just potential deployment benefits. Sandisk's schedule is an event-risk
flag. Passing the scheduled time changes its status to outcome unverified; it
does not confirm that the call occurred or infer results, sentiment or returns.
Reviewed context older than seven days is flagged. Missing context never means
there is no news. Official company announcements provide the issuer's perspective;
independent reporting is not included in this slice.

Official reviewed sources:

- [AMD collaboration update](https://ir.amd.com/news-events/press-releases/detail/1302/amd-and-meta-advance-strategic-partnership-to-power-metas-superintelligence-infrastructure)
- [Sandisk earnings call announcement](https://investor.sandisk.com/news-releases/news-release-details/sandisk-report-first-quarter-fiscal-year-2027-results-october-29)
- [SEC submissions API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)

## Coverage and ingestion

The normalized release contains recent supported 8-K, 10-K and 10-Q metadata,
including amendments, for 21 issuers: 2,251 filings total. UI/API show at most 100
recent supported filings per issuer, filterable by type and 90-day/year/all-cached
windows. SEC recent submissions cover a bounded recent set, not a complete archive
or broad news feed. An 8-K item 2.02 identifies a results-of-operations disclosure;
it does not supply a future earnings date or actual article headline. Filing
dates remain distinct from event occurrence dates. Timeline axes use UTC and raw
date tooltips avoid browser timezone shifts.

Financial coverage is now 20 issuers, including AMD; 13 latest records have all
supported financial inputs. Sandisk has filing/event coverage but its financial
import failed normalization. It is explicitly labeled Events only and receives
no financial score. XOM's financial import and the HUD source also remain
unavailable. Failed financial imports were not bypassed.

Release `9e4689534ba5c8285f6bb2e1da81bca915bea70fa32b9c837d731f2b26b8525f`
contains 48 datasets and 46,011 top-level records, with nested filing histories.
All 21 filing feeds published; their earlier transport/normalization failures were
resolved and cleared after successful bounded refresh. JPMorgan's 26,551-row recent
submissions response required supporting busy issuers under an explicit 50,000-row
ceiling and existing 25 MiB transport limit. Unsupported forms are not event rows.

```powershell
# Offline normalization of installed issuer filing caches.
.venv/Scripts/python.exe tools/refresh_company_events.py --as-of 2026-10-28
# Explicit bounded operator download for installed issuers (at most 25).
.venv/Scripts/python.exe tools/refresh_company_events.py --as-of 2026-10-28 --download
# Exact ticker resolution through the verified SEC directory for a new event issuer.
.venv/Scripts/python.exe tools/refresh_company_events.py --as-of 2026-10-28 --tickers SNDK --download
```

Fixed SEC CIK URL templates, current/release display policy, byte/row limits,
column alignment, issuer identity, accession uniqueness, safe filing links,
source hashes, source locks and atomic release publication remain enforced.
Known-directory ticker imports check the mapping hash under the publication lock.
Downloads use the existing private SEC contact header; it never enters events,
source manifests or reports. Browsing never downloads. No recurring job, account,
paid service or new package was created.

The two announcement summaries are manually reviewed facts and links in
`data/company_event_context.json`, not an automatically scraped news service or
permission to redistribute article bodies. The strict reviewed catalog has a
content hash and issuer/site allowlist. Corrupt context is withheld independently
of verified filings. A 24-hour-old or failed filing refresh is disclosed.

API: `GET /research/companies/{issuer_key}/events`. Responses are typed, offline,
and explicitly declare incomplete news coverage and no effect on strategy scores.
The fiscal-year slider changes financial analysis; it does not move current
announcements to an earlier year. Source context and event dates stay visible.

## Verification

Verification: 300 full-suite tests passed, zero skipped, two dependency warnings,
31.51 seconds. The initial run passed 299 checks and found the OpenAPI contract
test's route list needed the new events endpoint; after updating it the full
suite passed. Final log: ignored `output/tests/company-events-full-suite-final.log`.
Tests cover wrong CIKs, unsafe links, duplicate/misaligned metadata, future dates,
busy issuer bounds, empty feeds, timezone/schedule transitions, stale context,
policy withholding, failed-refresh retention, offline API and event-only UI flows.
An earlier Windows allocation/API native diagnostic remains unresolved; this run
had no such diagnostic and does not establish a fix.

The running API returned Sandisk's upcoming source-confirmed call and disabled
score effects. Browser verification confirmed ticker search, the Events only
label, official announcement links and the filterable filing timeline.

## Remaining work

- Broader, reliably refreshed announcements and earnings calendars, including
  changed/cancelled schedules and source permissions for each additional provider.
- Independent reporting and additional material-event types with careful sourcing.
- Price-chart event markers after price coverage is established; do not infer causation.
- Portfolio event exposure when supported live portfolio selection exists.
- Free price/total-return and benchmark coverage, valuation/risk calculations,
  sector/membership identity and evaluated stock selection remain major gates.
- Orange County single-family rental discovery remains an equal release requirement.
