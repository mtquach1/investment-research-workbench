# Annual financial normalization v1

Implemented October 28, 2026 in `stock_financials.py`. This is a coherent annual
financial metrics engine, not a stock picker, TTM engine, valuation feed, or
outperformance result. The [strategy specification](stock-strategy-v1.md)
describes later selection. The user's objective is to outperform S&P 500 total
return after modeled costs; no such result has been established.

## Coherence and evidence

Select the latest full-year USD revenue observation with a known 10-K/10-K/A
filing on or before the analysis date. Period length must be 330-400 days. For
ties, use filing date, configured revenue-tag precedence, then accession ID.
Income and cash-flow fields must use the exact same fiscal start/end and
accession. Beginning assets must be at the preceding fiscal year-end, ending
assets at the chosen period end, both from that accession.

This deliberately fails closed on a partial amended filing instead of mixing
vintages silently. Conflicting values for the same tag/period/accession are
ambiguous and excluded. Wrong currencies, incomplete periods, future filings,
future period ends and invalid values do not fill missing inputs. A 550-day
period-age gate is inherited from the research strategy; this is not a claim
that older annual numbers are universally unusable.

Every value records tag, units, fiscal dates, filing date and accession. Reports
also carry the original source SHA-256. Derived values identify their inputs:

- FCF = operating cash flow minus nonnegative cash PPE capex, same annual period.
- Missing direct liabilities may be reconstructed as total assets minus total
  equity **including noncontrolling interests**, from the same filing/end date.
  Plain parent stockholders' equity is insufficient for this fallback.

Available metrics are ROA (net income / average assets), operating margin,
FCF margin and liabilities/assets. Invalid/nonpositive denominators remain null
with reasons. Negative profits/cash flows are retained as financial observations;
future strategy eligibility gates must still be applied. `financials_complete`
means this narrow set is calculable and within its period-age gate, not that
the company is eligible or recommended.

Earnings/FCF yields stay null with `requires_verified_issuer_market_cap`. The
module does not invent share counts, mix issuer/share classes, or infer a current
market cap from annual weighted-average shares. `recommendation_ready` is false.
Sector-specific eligibility is a later stage, not inferred from accounting tags.

## Real cached sample check

From the audited snapshots as of October 28, 2026: AAPL, MSFT and KO have complete
aligned financial inputs under these rules. KO uses the documented total-equity
liabilities fallback. JPM remains incomplete because operating income and PPE
capex are unavailable in the required form; the strategy separately excludes
Financials. These are coverage checks, **not stock recommendations**.

```powershell
.venv\Scripts\python.exe tools/normalize_stock_samples.py --as-of 2026-10-28
```

This command is offline and checksum-verifies cached provider snapshots. It
writes `output/audits/annual-financials.json`. Decimals serialize as strings to
retain source precision. It does not download, call AI, save user finances, or
serve this provider data publicly. Data access/rights gates remain in the
[feasibility report](data-feasibility-2026-10-28.md).

Independent synthetic cases verify arithmetic, amended filing isolation,
publication dates, duplicate conflicts, currencies, quarter-versus-year mismatch,
beginning assets, capex signs, and liability provenance. Wider annual coverage,
reviewed additional taxonomy mappings, issuer valuation and point-in-time
strategy evaluation remain incomplete.

Reference: [SEC XBRL/company-facts API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
