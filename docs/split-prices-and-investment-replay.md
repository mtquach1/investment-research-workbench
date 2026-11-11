# Split-adjusted prices, historical replay and proposal readiness

October 29, 2026. This milestone fixes the split display and advances stock stages
3–4. It does not complete real portfolio selection or claim verified investment
performance. The portfolio builder is currently a readiness checker, not a real
basket generator on the verified path. The user subsequently approved a separate
opt-in [experimental proxy/estimate basket](experimental-research-basket.md), now
implemented without changing these strict gates.

## Share-price chart

Share price ($) now defaults to **Split-adjusted**. Original prices (unadjusted)
is an explicit alternative. Provider split-only closes restate old prices in
current share units; they exclude dividend adjustments. A 10-for-1 split changes
one old share into ten new shares without itself destroying shareholder wealth.
The original-dollar quote in the header remains dated and unadjusted.

Actual installed NVDA evidence: June 7, 2024 raw close 1208.42 and split-adjusted
120.84; June 10 raw/split-adjusted 121.93. The default chart no longer displays a
mechanical fall from above 1000 to about 100. Provider decimal rounding is retained.
Real price movements remain visible. No smoothing/interpolation reconstructs a
price or removes genuine losses. Missing split-only evidence withholds that view;
it cannot silently fall back to raw or dividend-adjusted prices.

Value of $100 and the existing risk cards continue to use all-adjusted prices.
Source explanations distinguish these views. Changing the visible history range
does not change the split-price units of the original installed comparison.

## Historical replay

Stocks -> Historical replay runs the shared `stock-cashflow-replay-v1` engine on
installed observations. Inputs include a chosen issuer/security, date range,
starting cash, monthly deposits, per-deposit fee and additional annual account fee.
The same dates, contributions and fee policy are used for the company and SPY.

- Starting cash buys at the first selected trading close. Monthly deposits begin
  in the following calendar month and buy at its first shared trading close.
  Weekends/holidays roll forward; there is no prior-day purchase or look-ahead
  selection of an advantageous execution price.
- Price-only mode uses split-adjusted ratios and excludes dividends. Optional
  provider-all-adjusted mode incorporates distribution adjustments as a proxy,
  not verified exact dividend reinvestment. No extra dividend cash is added.
- Decimal adjusted-value accounting permits fractional units; it does not report
  executable historical share counts or independently verified split events.
- Purchase fees round half-up to cents per deposit. Additional account fees
  accrue between observations using calendar days and an effective annual rate
  on pre-deposit value; they are additional to costs embedded in quoted prices.
- Requested trading sessions must all be present for both alternatives. Missing
  endpoints/interior sessions, missing split evidence or out-of-range/future dates
  cannot be filled or extrapolated. At least two observed dates are needed.
- The chart separates account value from cumulative deposits. Net growth equals
  ending value minus deposits, after modeled fees. Contributions are not returns.
  No annualized investment-return figure is inferred from this cash-flow balance.

The source hash, typed inputs and per-date deposit/value/fee ledger are inspectable.
`POST /research/stock-replay` uses the same implementation and no-store headers.
There are no provider requests, persistent private caches, trades or scheduled jobs.
This is chosen-security history, not an evaluation of the recommendation strategy.

Research screen also supports a bounded comparison of three companies, preserving
metric definitions, availability, sector and latest annual period labels. Different
fiscal period ends are disclosed; this is not a matched-period performance claim.
Existing sourced filing/news views remain; broader news coverage/refresh is still
unfinished.

## Portfolio readiness: deliberately incomplete stage 3

Stocks -> Build portfolio and `POST /research/stock-proposal` accept a cash budget,
a tighter sector-position cap and API exclusions. They expose per-company evidence
failures, sector/peer capacity and all uncommitted cash. They cannot certify index
membership or valuations from client-provided booleans. Outputs contain no real
selections or purchases; the response schema prevents nonempty selections.

The existing exact tied-percentile/sector-quota algorithm still runs in the
synthetic lab. Connecting it to real approved inputs and completing proposal,
override, holdings-aware concentration and purchase-sizing workflows remains
implementation work. This is not a blanket external prohibition on recommendations.
Source coverage, corporate-action/share-class identity and public display rights
are separate unresolved evidence/access questions, not proven impossible at zero
cost. A separately labeled experimental basket could accept proxy/estimate inputs
only after an explicit user scope decision. It would still enforce financial and
portfolio constraints and could return no basket when insufficient sectors qualify.

## Verification

360 tests passed, zero skipped, 39 dependency warnings in 53.08 seconds. References
cover 10-for-1 price/wealth continuity, month-boundary/holiday deposits, accounting
growth separate from contributions, fee effects, missing sessions/adjustments,
mode withholding and client inability to certify source evidence. Interface tests
check replay input changes and empty proposal outputs. Actual NVDA replay ran on
1,003 shared dates with 5,800 dollars deposited under the default four-year setup.
Browser verification and screenshots record the final split chart and replay view.
The earlier Windows native allocation/API diagnostic remains unresolved; no such
diagnostic appeared in this full run. Preview: UI8510 / API8009.
