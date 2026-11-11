# Stock stages 1–2: measured verification and usable metrics

October 29, 2026. The execution order is stocks first. This milestone advances
stages 1 and 2; neither full-universe verification nor real recommendations is
declared complete.

October 31 feasibility review supersedes the original access assumptions and
distinguishes source gaps from the unimplemented strict selection adapter. Read
[blocker audit and release decisions](BLOCKER_RESOLUTION_PLAN.md) before continuing.

## Actual scope and source evidence

A bounded SEC import requested 25 additional exact-directory issuers. Twenty-four
normalized successfully; the XOM directory mapping led to a snapshot without a
usable annual dataset. It remains unavailable rather than borrowing financials
from a guessed historical CIK. Installed financial research increased from 20 to
44 issuers. The directory still supplies issuer matches, not verified tradable
share-class identity or official index membership.

Financial facts use [SEC company-facts APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
Company-facts only aggregates supported non-custom, entity-wide facts. Missing
custom-tag coverage is a real limitation; the adapter does not fabricate operating
income or assume missing capital expenditure is zero. Numeric normalization keeps
USD, annual durations, common accessions, known filing dates and explicit gaps.

Twenty-four additional free IEX histories were downloaded through the existing
Alpaca data-only client. There are now 45 series (44 issuers plus SPY), each with
1,003 observed dates from October 28, 2022 through October 28, 2026: 45,135
security-date records. Raw, all-adjusted and split-only closes remain separate.
[Alpaca's documented adjustments and feeds](https://docs.alpaca.markets/us/reference/stockbars)
do not make single-exchange IEX history consolidated exact reinvested total return.

Bounded merge imports retain compatible old series and their original retrieval
timestamps. Interval, directory hash and adjustment basis must match before any
download. Publication rejects a changed snapshot under the writer lock, preventing
lost updates. Per-batch maximum remains 24 issuers plus SPY; the pilot store is
bounded to 100 securities, 3,000 dates each and a 64 MiB artifact. This is not
full-S&P production storage or evidence of full-universe scale.

The dated IVV proxy has 505 securities, 501 exact SEC issuer joins, 45 rows with
installed issuer financials, and 44 exact ticker price series. Financial statements
can serve multiple share classes; 45 security rows do not mean 45 financial issuers.
BRK B, BF B, HOLX and SKYD WS remain unresolved. The entire reference list now
appears in Coverage & evidence, including unanalysed securities. Nothing silently
converts an unanalysed row to a passing result.

Measured on October 29:

| Check | Result |
| --- | --- |
| Financial rules | 23 pass / 6 fail / 15 unavailable |
| Filing-based valuation context | 35 estimates / 3 stale / 4 multiple-security cases / 2 unavailable |
| Complete 756-return count gate | 44 issuer histories pass |
| Current ROA / operating margin / FCF margin / liabilities-assets | 43 / 33 / 34 / 39 available |
| Comparable annual revenue / net-income growth | 43 / 42 available |
| Independent latest-close diagnostics | AAPL, MSFT and NVDA within stated tolerance |

Diagnostics compare matching October 28 dates against Yahoo Finance; approximately
0.067%, 0.230% and 0.019% differences respectively. This does not validate every
historical quote or corporate action. No paid feed, new credentials, trading
endpoint, billing or automatic scheduled job was used.

## Metrics and research filters

`stock_metrics.py` exposes typed values, availability states and calculation basis:

- ROA, operating margin, FCF margin and liabilities/assets use the existing
  independently tested aligned annual engine.
- Annual growth compares adjacent fiscal period ends 330–400 days apart. Missing
  periods and nonpositive prior values stay unavailable rather than generating
  misleading loss-to-profit percentage growth. Current revised filing history is
  not historical point-in-time screening evidence.
- Risk metrics identify the full installed date window and session count. Active
  risk filters require 756 complete return observations and a fresh last price;
  incomplete coverage cannot pass because its observed drawdown happens to be low.
- Estimated earnings yield is usable only after an explicit research-estimate
  opt-in. It never sets verified-current-market-cap flags or strategy scores.

Filters have strict finite bounds, exact inclusive thresholds and per-company
exclusion reasons. Missing/stale values cannot pass an active threshold. Supported
fresh sectors are required for profitability/leverage filters. Drawdown loss uses
the positive magnitude of the negative drawdown; a 25% loss threshold accepts
−25%, not −40%. Filters never relax themselves to fill a basket. Missing values
sort last. A profitability scatterplot, metrics definitions table, sortable results
and full-reference coverage tab separate exploration from verification.

`POST /research/stock-screen/filter` uses the same pure filtering engine and returns
input criteria, included issuer keys, exclusions and source snapshot hashes. It is
no-store and downloads nothing. All scores/selections remain disabled. Portfolio
budgets are not sent to providers or used to decide company attractiveness.

## Reproduction

```powershell
.venv/Scripts/python.exe tools/audit_stock_research.py --as-of 2026-10-29 --output output/audits/stock-input-audit-2026-10-29.json
```

The audit is offline and records counts, all reference-security coverage, model/
source hashes and blocking requirements. Source data and diagnostic reports remain
local in ignored stores. Public financial normalization release:
`c5278a9c3d3a01af0c7f0e38c816fe03e5ba17ae06cad11041e6b5e7d463add6`.
Private price snapshot:
`f96d72f018bc85be77df62ec8db272fcfd097b03c41b9df289b254026ce1ecbb`.

## Remaining stage gates

1. Official dated S&P membership and canonical security/share-class identity.
   The [S&P page](https://www.spglobal.com/spdji/en/indices/equity/sp-500/) was
   inspected again; its accessible view did not yield a verified downloadable full
   constituent dataset. This is an access finding, not proof that free access is
   impossible. IVV holdings remain a labeled proxy.
2. Verified current issuer valuation with adequate class/issuance/corporate-action
   treatment. A dated filing-based share estimate is useful context, not a verified
   current market cap. No source's undocumented data is silently promoted.
3. Remaining full-universe financial/price coverage and missing annual inputs;
   supported sector/TTM/growth/dividend definitions where required. The versioned
   annual strategy does not currently rank on TTM growth or dividend income.
4. Consolidated/adjustment verification and public provider display permissions;
   matched point-in-time evidence before historical strategy performance claims.

Stage 3 real recommendations remains blocked. Zero cost and source permission
constraints are preserved. Existing rental features are maintained but no new
rental milestone is started under the stocks-first order.

## Verification

The full suite passed 353 tests with zero skipped and 34 dependency warnings in
37.49 seconds. Subsequent focused tests cover final filter interactions, stale/
missing data, supported sectors and API behavior. Independent fixtures also cover
annual-growth arithmetic and loss baselines, threshold equality, drawdown signs,
valuation opt-in, unresolved coverage, compatible merge timestamps, incompatible
interval rejection and stale-writer refusal. The earlier Windows native
allocation/API diagnostic did not recur in the full run; its cause remains open.
Final focused checks passed six tests. Browser QA confirmed full-reference coverage,
all 44 companies before filtering, and 23 matches / 21 explained exclusions under
the default active profitability/leverage thresholds. The filtered profitability
chart renders without overlap. The actual running API reproduced the 23/21 split
with no-store headers and live recommendations disabled. Preview: UI8510 / API8009.
