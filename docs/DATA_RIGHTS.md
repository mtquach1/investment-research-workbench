# Public source and data boundaries

This repository publishes software, inline synthetic test fixtures and four
small manually curated reference/configuration files under `data/`. It does not
bundle raw provider responses, bulk market histories, real account data or private
financial exports. Reference records contain public source links and dated
observations; they are not a complete licensed research dataset or a certification
of source accuracy.

| Material | Publication treatment |
| --- | --- |
| Python/UI code, strategy configuration and synthetic fixtures | Included in the source snapshot; no general reuse license selected yet. |
| `data/company_event_context.json` | Small reviewed event references with original public-source links; not copied news articles. |
| `data/financial_reference_cases.json` | Small financial arithmetic reference cases and source provenance. |
| `data/filing_share_reference_cases.json` | Small dated filing/share reference cases, not full filings. |
| `data/reviewed_class_quantities.json` | Small manually reviewed class/statement links and evidence identifiers; incomplete by design. |
| `data_cache/`, IEX/Alpaca histories, SEC downloads and listing/fund snapshots | Excluded. Users obtain data separately under provider terms. Free access does not imply permission to redistribute. |
| `output/`, reports, private notes, saved plans and databases | Excluded. |

Source URLs and access/display policy decisions are in `market_sources.py`,
`source_policy.py` and the dated source audit docs. SEC financial numeric-data
review does not confer rights to unrelated feeds, fund lists, logos or articles.
The public code does not grant provider rights. Do not upload a populated local
cache or infer a right to publicly host real-data views from this source release.

Dependencies retain their own licenses. No third-party font binaries, photographs
or provider logos are bundled. A future project license should cover only material
the owner is entitled to license; data terms need separate review. This document
records publication scope rather than legal certification.
