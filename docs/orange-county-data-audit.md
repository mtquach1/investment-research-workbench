# Orange County rental data audit — initial source inventory

Latest implementation: [normalized-release audit](public-data-pipeline.md).
The 92-area land-overlap set includes eight cross-county ZCTAs; Orange County is
the largest land county for 88. The alternate membership rule changes geography,
not data quality; neither rule establishes current residential-address ZIP
membership. Normalized value/mixed-rent series and metro context retain dates,
categories and gaps. An actual request for HUD's linked FY2027 workbook returned
HTTP 202 with no data; no HUD rows or property rent estimates are claimed. A
92-row local coverage matrix and UI coverage/date/source panels are implemented.

Updated October 28, 2026. Status: actual Census/Zillow snapshots inspected.
The [joint feasibility report](data-feasibility-2026-10-28.md) records 92 dated
geographic candidates, 89 available single-family value series and 81 mixed-rent
series. Audited single-family rent is metro-only. Current USPS geography and
public display/redistribution rights remain unresolved; county coverage is not
complete. The inventory below records the original source questions.

See [the authoritative roadmap](PROJECT_ROADMAP.md) for implementation order.

| Need | Candidate | Documentation supports | Still to verify |
| --- | --- | --- | --- |
| Housing values | Zillow Research ZHVI | Regional housing value indices with property-type categories including single-family | Exact Orange County ZIP/category coverage, observation dates, download access, attribution/display rights |
| Rental context | Zillow Research ZORI | Observed rent indices with all-home, single-family and multifamily categories | Which category/geography combinations actually exist for OC ZIPs; gaps and compatibility with chosen price series |
| Bedroom-specific rent benchmark | HUD SAFMR | ZIP-level FMRs used for housing voucher payment standards | OC rows/year, gross-rent/utility definitions, suitable labeling; not evidence of single-family achievable rent |
| ZIP-to-county mapping | HUD-USPS crosswalk | Quarterly geographic crosswalks with residential-address allocation information | Download/login or API-token requirements, vintage, membership rule for cross-county ZIPs |
| Map geometry | Census ZCTAs | Generalized areas representing ZIP distribution | Geometry vintage, ZIP/ZCTA correspondence, county overlap, access/usage and attribution |
| Actual property price/rent/expenses | Manual property editor initially | User-supported property scenario inputs | Validation, input provenance, scenario defaults; a future listing source needs independent rights/access review |

## Sources reviewed

- [Zillow Research housing data](https://www.zillow.com/research/data/): categories
  do not establish that every geography has every series. Regional indices do
  not represent an individual parcel's purchase price or obtainable rent.
- [HUD SAFMR data](https://www.huduser.gov/portal/datasets/fmr/smallarea/index.html):
  official ZIP-level rent benchmarks, with a distinct program purpose.
- [HUD-USPS crosswalk documentation](https://www.huduser.gov/portal/datasets/usps_crosswalk.html):
  documentation describes quarterly updates and residential allocation; file
  access currently directs users to login and API access requires a token.
- [Census ZCTA explanation](https://www.census.gov/programs-surveys/geography/guidance/geo-areas/zctas.html):
  ZCTAs are generalized geographic representations, not identical USPS ZIP areas.

## Required coverage matrix

For each ZIP/source/series record: county membership and mapping vintage,
property category, bedroom scope, units, earliest/latest observation, retrieval
time, history completeness, category compatibility, freshness policy, source URL,
access/rights review status, and usable/stale/missing/incompatible/benchmark-only
classification. Preserve the distinction between an observation and an estimate.

Do not label county coverage complete until a documented ZIP universe is joined
to actual source rows, with both supported and unsupported counts reported.
Do not substitute countywide values into missing ZIP observations without an
explicitly labeled fallback that is excluded from ZIP-specific claims.
