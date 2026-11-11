# Free-data company research

Updated October 28, 2026. Free accounts/API keys are allowed; paid data,
subscriptions, billing enrollment, paid trials and upgrades are not authorized.

## Implemented

**Latest expansion:** 19 supported issuers now replace the initial four-company
scope described below. Bounded SEC directory import plans, actual source failures
and the latest 281-test verification are documented in
[sec-issuer-imports.md](sec-issuer-imports.md).

The authorized SEC contact is configured in Git-ignored `.env`, used only for SEC
request headers. It is not copied to source manifests, reports or UI metadata.
No provider account or paid plan was created. The configured refresh resolved the
previous access blocker: 10,430 ticker/name/CIK/exchange records and four refreshed
company-facts files are now cached.

Stocks opens Company research; Strategy lab remains a separate synthetic view.
Apple, Microsoft, Coca-Cola and JPMorgan have five supported annual periods,
name/ticker search (including “Apple stock”), revenue/earnings, cash-flow and margin
charts, a period inspection slider, chart marker/legend interactions and filing
evidence. Unsupported searches remain explicit. Browsing does not trigger downloads.
The search covers four supported issuer snapshots, not every company on the web.

Each annual point retains aligned inputs from one accession. Missing inputs are
gaps, not zeroes. History can include later restatements available in the snapshot;
it is not point-in-time performance evidence. Free cash flow is defined as operating
cash flow minus cash PP&E expenditure. ROA uses average beginning/ending assets.
Dates use UTC scales and raw date tooltips to avoid browser timezone day shifts.

## Sources and scope

The [SEC reuse FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)
explicitly permits reuse of government-created content and EDGAR public filings.
The recorded SEC policy now allows the numeric filings and directory used here;
it does not cover unrelated site artwork, endorsements or other providers.
Both the release and current source policy must allow display. Current policy can
withhold an older approved release. The APIs require no account or key; automated
requests retain identifying headers and conservative request spacing.

Exact matching joins 501 of 505 fund-proxy ticker rows to a unique current SEC
issuer. `BRK B`, `BF B`, `HOLX` and `SKYD WS` remain unresolved. No punctuation
guesses, historical mappings or S&P membership claims are inferred. An issuer's
common shares, preferred shares and notes remain distinct instruments; its
statements describe the business, not the investment performance of each security.

Release `0ca48170d69ae4c8fcc3374c00b7dff181b8c76209f2ce42769d758fb5de2c2c`
contains 11 datasets and 45,974 top-level records, including the new directory and
nested annual histories. The HUD workbook remains unavailable. Price, valuation,
full-universe fundamentals, benchmark and membership gates remain incomplete;
live recommendations are disabled. Both stock and rental discovery remain required.

[Alpha Vantage support](https://www.alphavantage.co/support/) lists a standard
25-request/day free limit and a separate educational/open-source verification
route; approval is not assumed. Its [documentation](https://www.alphavantage.co/documentation/)
labels adjusted daily history and company overview as premium. Free raw compact
daily history has 100 points. A working demo does not establish free production
access or public-display rights. Do not buy upgrades or relax the strategy's
756-observation gate to conceal these limits. Next evaluate suitable free price,
history and benchmark sources, then expand issuer snapshots through verified joins.

## Code and verification

`company_research.py` serves typed offline directory/detail responses through
`GET /research/companies` and `GET /research/companies/{issuer_key}`.
`stock_financials.py` extracts bounded annual history using the existing coherent
normalizer; `source_adapters.py` retains it. `issuer_mapping.py` matches exact
tickers. `company_research_ui.py` displays the research with public-only caching;
budgets, holdings and search queries are not sent to a provider.

Tests cover annual arithmetic, amendments, date cutoffs, identity ambiguity,
integrity, policy withholding, offline HTTP and search/period interactions.
The final full run had 270 passes, exit 0, in 54.33 seconds and no native diagnostic;
the earlier 269-pass run reproduced Windows native access diagnostics in the
existing allocation/API path. The root cause remains a release concern. The full
final log is retained under ignored `output/tests/company-research-full-suite.log`.
Browser checks confirmed Apple-name lookup, fiscal-year updates and exact date
tooltips. The 2024 period inspection updated displayed Apple revenue to $391.04B
and the chart marker; raw-date tooltips retained 2025-09-27 exactly. A 390px layout
had no document overflow. Final focused company/UI checks: seven passed.
Preview: UI8510 / API8009.
