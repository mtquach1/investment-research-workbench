# Free local market history and portfolio dashboard

Implemented October 28, 2026. This milestone connects real price history to
company research and adds a session portfolio-composition dashboard.

October 31 correction: a separate bounded diagnostic successfully queried older
SIP raw/split/all samples with the configured credentials. The app's importer
remains IEX-only; the earlier account-access conclusion below is not a universal
restriction on historical SIP. Access still does not establish public rights.
See [blocker audit and release decisions](BLOCKER_RESOLUTION_PLAN.md).

## Verified access and actual coverage

The user configured their own Alpaca paper credentials in ignored `.env` and
enabled `MARKET_DATA_MODE=local_research`. Both credential fields loaded, and an
actual authenticated data-only request succeeded. No credential values were
printed or placed in a URL, snapshot, report or API response. No brokerage,
account, order, paid-plan or subscription endpoint is implemented or called.

Snapshot `1c7328f41e735aca2eb0fda45aab81dc1d0ad83d9c7a097ba0542495f1857278`
contains AAPL, MSFT, AMD, NVDA, AMZN and the SPY ETF proxy, each with 1,003 daily
observations from October 28, 2022 through October 28, 2026. Raw and all-adjusted
dates match; the calendar audit found no missing sessions for these six series.
This is measured six-security research coverage, not the full S&P 500 universe.

The [Alpaca Basic plan documentation](https://docs.alpaca.markets/us/docs/about-market-data-api)
describes zero-cost access; [paper-only documentation](https://docs.alpaca.markets/us/docs/paper-trading)
limits that account to IEX. The client explicitly requests IEX and never silently
switches to SIP or paid data. IEX is one exchange, not a consolidated official
closing-price feed. Broader historical SIP access described elsewhere is not
assumed for this paper-only integration.

Alpaca [bar documentation](https://docs.alpaca.markets/us/reference/stockbars)
defines raw and all-adjusted modes. The displayed dollar close is raw. Historical
curves use all-adjusted closes, with no second dividend addition. The provider's
exact dividend-reinvestment conventions are not verified. SPY is an ETF proxy,
not the S&P 500 index itself; neither this comparison nor its differences are a
strategy backtest or proof of outperformance.

Alpaca's [terms](https://s3.amazonaws.com/files.alpaca.markets/disclosures/library/TermsAndConditions.pdf)
do not establish public redistribution permission for this application. Licensed
history is stored separately under ignored `data_cache/local_market_history`,
outside the public SEC/housing releases. Market API responses are withheld before
loading data unless local research is explicitly enabled. Keep this mode private;
public release needs its own permitted data source/use arrangement. No blanket
public-display grant or recurring refresh job was created.

## Ingestion and independently checked calculations

`alpaca_history.py` validates exact SEC ticker/issuer joins against a fresh
directory and an installed research issuer. SPY is a named benchmark proxy. Requests
use fixed data-only hosts, secret headers, bounded past intervals, completed
sessions plus a one-hour finalization buffer, explicit symbol mapping date, and
IEX feed selection. Dates before 2016 and intervals over ten years are rejected.

Both raw and all-adjusted responses paginate independently. Limits: 24 issuer
tickers plus SPY; ten pages per adjustment; 10,000 bars/page; 10 MiB/page;
50 MiB/batch; bounded retries and request spacing. Redirects, repeated page tokens,
unexpected symbols, duplicate dates, partial raw/adjusted pairs, invalid OHLC,
nonfinite prices and out-of-window or intraday timestamps fail closed. Auth or
entitlement refusals never trigger a paid fallback. Keys and provider error bodies
are excluded from operator diagnostics.

`market_history.py` publishes a typed, hash-verified immutable normalized snapshot
behind an atomic pointer. Failed downloads/publications leave the prior pointer
available. A new successful batch replaces the selected market bundle; include all
desired tickers when refreshing, rather than mixing old bars under a fresh timestamp.
The bundle preserves decimal close inputs needed to reproduce the calculations;
it is not an archive of provider raw response pages.

Risk metrics use sample daily-return standard deviation × sqrt(252), prior-peak
maximum drawdown and endpoint change. Annualized endpoint change is shown only
for spans of at least one year. NYSE sessions and early closes come from
`exchange-calendars` (tested version 4.13.2), whose version is recorded. Calendar
coverage is an explicit dependency, not an inferred Monday–Friday schedule.

Company/proxy comparisons use their exact common dates and common endpoints.
Unmatched dates are counted. Missing interior sessions are not forward-filled;
annualized daily volatility is withheld across those gaps. The 756-return
observation count is necessary but does not resolve feed, identity, total-return
or strategy-validation requirements. Portfolio recommendations remain disabled.

```powershell
# Default is an offline import plan, with no key needed and no network request.
.venv/Scripts/python.exe tools/refresh_price_history.py --symbols AAPL MSFT AMD NVDA AMZN --start 2022-10-28 --as-of 2026-10-28
# Explicit data-only refresh using locally configured paper credentials.
.venv/Scripts/python.exe tools/refresh_price_history.py --symbols AAPL MSFT AMD NVDA AMZN --start 2022-10-28 --as-of 2026-10-28 --download
```

The API `GET /research/companies/{issuer_key}/market` is typed, offline and
no-store. A caller may select among matched security symbols; issuer identity
does not silently collapse share-class price histories. No holdings or capital
budget are sent to the provider. No current issuer market cap or valuation yield
is inferred from stale/partial share counts.

## Interface

The user's dashboard reference informs the dark slate panels, mint/lavender
accents, metric cards and restrained spacing. Stocks opens Portfolio, with
Company research and Strategy lab next to it. Company research groups information
into Investment case, Business financials, Price & risk, News & events and Sources.
Revenue, cash generation and profitability live inside Business financials.

Price & risk has a matched-date range slider, growth-of-100/drawdown toggle,
endpoint differences in percentage points, drawdown, volatility and annualized
change. Reviewed announcements can be marked by publication date; a marker does
not attribute a price move to the event. Sources and calendar gaps stay visible.
An explicitly fabricated history lab is available without credentials.

The portfolio doughnut starts with the user's 20/15/25/15/10/15 example. Editable
weights determine exact slice angles; unassigned weight becomes cash, and totals
above 100% are rejected rather than normalized. Largest-remainder cent allocation
reconciles dollars to budget. A table provides exact weights and an accessible
alternative to the chart. A separate view displays the synthetic strategy basket;
custom allocations are never presented as strategy recommendations.

The S&P 500 placeholder is not a purchasable security; a fund must be selected.
VOO already tracks the S&P 500, and funds may overlap direct stock holdings. The
dashboard does not claim look-through exposure analysis or measured diversification.
Budget and edited holdings remain in this session, survive workspace navigation,
and are removed by Clear session workspace. No portfolio assumptions are cached
globally, sent to Alpaca, written to the database or placed in market snapshots.

## Verification

Full regression suite: 324 passed, zero skipped, 22 dependency deprecation warnings,
115.39 seconds. The final portfolio layout/persistence checks additionally passed
two tests after compacting controls and fixing the chart's text contrast. The
market window/drawdown test also passed after shortening its difference value
and placing the percentage-point unit in the label to avoid truncation.
Logs: ignored `output/tests/market-portfolio-final-suite.log` and
`output/tests/portfolio-layout-final.log`. An earlier focused UI test caught a
budget reset on navigation; separate session state now preserves the value.
The earlier intermittent Windows allocation/API native diagnostic remains unresolved;
this full run contained no native diagnostic and is not evidence of a fix.

Independent reference cases cover sample variance, peak drawdown, split-adjusted
versus raw changes, NYSE holidays/early close, missing-session withholding, exact
common dates, bad pagination and symbols, partial adjustment failure, auth refusal,
redirect refusal, good-pointer preservation, local display gating, cent rounding,
over-allocation and synthetic/manual origin separation. The running local API
returned 1,003 matched observations for Apple and enabled no strategy claims.
Browser checks confirmed the six proportional portfolio slices, exact table values,
dark colors, company tabs and AMD's sourced announcement marker in Price & risk.

## Remaining gates

Broader securities and benchmark validation, verified dated membership/sectors,
current issuer market caps, appropriate valuation inputs, live constrained
selection and evaluated strategy performance remain incomplete. Independent news
coverage, updated calendars, cross-domain exports/comparisons, deployment/privacy
verification and Orange County single-family rental discovery also remain required.
