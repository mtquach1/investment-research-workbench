# Chart clarity and independent price diagnostics

October 28, 2026. Local personal research; public display rights remain unapproved.

The portfolio donut now sizes its inner and outer radii from the actual plotting
area, with explicit padding and a separate wrapping legend. Fixed pixel radii could
overlap the legend and clip the top in a narrow card. The center label is smaller.

Company history opens on **Value of $100**, with an inline explanation using the
actual selected dates and endpoint values. **Share price ($)** uses stored raw daily
closes, not normalized values or adjusted closes. SPY is hidden in that view:
comparing share-price levels would not compare returns. **Drawdown** explains the
decline from an earlier peak within the selected window. Return/risk cards always
use adjusted observations, with contextual definitions in their help buttons.

Freshness distinguishes the observation date from the download timestamp. The
latter is explicitly shown in Pacific time. A calendar-aware label checks the
latest completed session plus a one-hour finalization buffer; weekends are not
reported as missing trading days. The cache is not a live quote or scheduled job.

## Independent diagnostic

Run `.venv/Scripts/python.exe tools/check_prices.py --symbols AAPL` to compare the
latest installed close against Yahoo Finance. One to five installed symbols per
command; no account, keys, paid service or browser scraping is required. The
experimental public chart endpoint is not a contracted stable API. It can fail or
change. No automatic retries, scheduling or public redistribution is enabled.

Only the exact matching New York trading date, USD currency and ticker are
accepted. The bounded request rejects redirects, oversized responses, duplicate
dates and invalid prices. A diagnostic passes within the larger of $0.05 or 0.5%
of the reference close; this is a deliberately visible engineering threshold,
not a statistical confidence interval or an exchange accuracy guarantee.

Reports are local in ignored `data_cache/local_market_history/price_checks/` and
bound to the exact primary snapshot hash and price date. Changed snapshots cannot
reuse old agreement. The UI shows the check timestamp. Provider failure reports
unavailable; disagreement is explicit. Neither replaces primary prices, enables
recommendations or verifies the full adjusted history. Yahoo's reported history
and IEX can differ in venue, session and corporate-action conventions, especially
around a split. Agreement between providers does not establish independent
underlying exchanges or an official consolidated close.

An actual Apple check on this milestone's October 28 close was within tolerance,
with approximately 0.067% difference. The private evidence contains both prices;
no quote dataset is committed. The earlier Windows native allocation/API issue
remains unresolved. Full regression: 338 passed, zero skipped, 30 dependency
warnings. After the final browser compatibility fix, 45 focused chart, diagnostic
and UI tests passed; the added three-view interaction assertions also passed.
Browser QA confirmed the complete donut with a separate wrapping legend, dollar
signs in explanations, the installed Apple reference diagnostic, and the actual
share-price chart with SPY hidden. The native frontend required object-form chart
padding; numeric padding is not compatible with its legend handling. Preview:
UI8510 / API8009. No automatic price-check job has been created.
