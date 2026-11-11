# Registered class corroboration and conservative financial-gap recovery

Implemented October 31, 2026. This advances stock data stages 1–2. It does not
complete canonical security identity, official S&P membership, issuer valuation
verification or verified portfolio selection. No strict gate was relaxed.

## Actual improvements

- **Apple and NVIDIA** now have imported, hash-bound annual-filing cover evidence:
  CIK, exact trading symbol, registered class title, exchange, fiscal period,
  accession and filing date. Current SEC directory and listing checks corroborate
  those dated disclosures. This is not proof of every economic/nontraded class,
  current shares, latest amendments or official index membership.
- Annual financial normalization v2 can recover total liabilities as **reported
  current liabilities + reported noncurrent liabilities**, requiring two
  nonnegative instant facts from the same accession and ending date. Missing
  components are not zero. Debt-only components, duration facts, different
  vintages and conflicting duplicates cannot substitute.
- The installed sample moved from **36 pass / 21 fail / 31 unavailable** to
  **39 pass / 22 fail / 27 unavailable**. Four unavailable assessments were resolved:
  three pass and one fails the strategy. Missing financial checks remain in
  40 issuers (previously 43), including mixed missing/failed cases.
- The new component formula is used by nine latest installed issuer records;
  some replace the previous total-equity fallback, so nine derived sums are not
  nine newly complete companies. Older historical periods are also rebuilt.
- Independent validation reports **648 passing checks, zero mismatches and
  173 unavailable checks**. A published General Dynamics balance-sheet reference
  separately verifies its current/noncurrent/total liabilities and ending assets.

The 88 issuer tables were rebuilt **offline from existing cached SEC bytes**;
their raw retrieval dates remain unchanged. Only the two fixed filing-cover
documents were newly fetched. Price snapshot, October 30 cutoff, financial
strategy thresholds, provider feed and public permissions were unchanged.

## Why this fallback is narrower than guessing missing financial data

[General Dynamics FY2025 balance sheet](https://www.sec.gov/Archives/edgar/data/40533/000004053326000006/gd-20251231.htm)
reports current liabilities of $16,796 million and noncurrent liabilities of
$14,831 million. Their sum, $31,627 million, also reconciles with reported assets
of $57,249 million less shareholders' equity of $25,622 million. The reference
fixture records the first four quantities in USD millions, independently of the
normalized result. This checks one issuer/period, not every source selection.

The independent calculation service separately recomputes each installed derived
component sum using rational arithmetic. A tampered liability total cannot pass
merely because a ratio was computed consistently from that wrong total.

Ambiguous direct total liabilities remain unavailable rather than being hidden
by a fallback. The existing assets-minus-total-equity route still requires total
equity **including noncontrolling interests**; common shareholders' equity alone
does not establish total liabilities. Negative equity is not assumed impossible.

Broader `PaymentsToAcquireProductiveAssets` and industry-specific capex tags were
found in cached sources but deliberately not mapped to the strategy's narrower
PPE cash-capex definition. Operating-income/custom-tag, capex, share counts and
class-aware valuations remain important gaps. More available data is useful even
when it leads to an observed strategy failure rather than another passing stock.

## Filing-class implementation

`market_sources.py` registers two fixed official SEC documents and their reviewed
accession metadata:

- [Apple FY2025 filing](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm),
  [accession index](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.html):
  filed October 31, 2025, fiscal end September 27, 2025; common stock/AAPL/Nasdaq.
- [NVIDIA FY2026 filing](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm),
  [accession index](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.html):
  filed February 25, 2026, fiscal end January 25, 2026; common stock/NVDA/Nasdaq.

`security_identity.py` uses a bounded standard-library HTML parser; no JavaScript,
external XML entities or links inside a filing are executed/fetched. It matches
only explicit DEI identity/security fields, preserving the context connecting a
symbol, title and exchange. Only registered supported source URLs can download.
Transport is bounded to 8 MiB and uses the configured SEC identification and
existing spacing/no-403-bypass policy. Raw HTML is not served to users.

Initial imports correctly refused the unhandled nested date structure. Both real
filings put a fiscal-month/day inline fact inside the full reporting-period fact.
The parser now tracks nested inline depth and applies the supported full English
month/day/year transform. It refuses conflicting contexts, dates/CIKs/forms,
unsupported exchanges, continued/nil security facts and unrecognized transforms.
No year is guessed from the registered expected date to make validation pass.

`corroborated_filing_class` requires an in-policy fiscal period, a known filing
date, a fresh current directory and the exact currently corroborated listing
exchange. Multiple installed matching references are ambiguous; no newest class
is guessed. The parser is a narrow adapter for these reviewed filings, not a
general XBRL processor. Unknown filings and newer filings are not auto-discovered.

All-economic-classes, issuer-valuation and official-index flags remain literal
false. Positive class conflicts/ambiguity exclude experimental selection and
produce insufficient-evidence decision assessments. Absent class evidence remains
disclosed under the existing opt-in experimental policy. Public display of these
new source records remains unapproved, separately from local research access.

## Interface and reproduction

Stocks → Research screen → company inspector → **What registered share class
does the filing disclose?** shows titles, dates, status, source links and hashes.
The Decision workflow evidence inventory includes a separate provisional filing
class category. It never turns the full security-identity gate green.

```powershell
.venv/Scripts/python.exe tools/refresh_market_data.py --as-of 2026-10-31 --source sec_cover_aapl_2025 --source sec_cover_nvda_2026 --download
.venv/Scripts/python.exe tools/audit_stock_research.py --as-of 2026-10-31 --output output/audits/class-financial-coverage-2026-10-31.json
```

Installed public-reference release:
`98906539b176fc42dbd9e52ae6e2e2a406d8bfe404c7150688e19e34b58631a5`.
Market snapshot remains
`bd8ef356fe5633eb74e6c215b0bd3f3bbfc4728166b19fa2564d2b83dd6cd726`.

Local audit artifacts:

- `output/audits/class-financial-summary-2026-10-31.json`
- `output/audits/class-financial-validation-2026-10-31.json`
- `output/audits/class-financial-coverage-2026-10-31.json`
- `output/tests/class-and-financial-evidence-verified.log`

Verification: **465 tests passed, zero skipped, 55 dependency warnings**, UI/API
enabled. Tests include same-vintage component arithmetic, missing/conflicting/
negative components, refusal to hide direct-total conflicts, nested date parsing,
wrong CIK/period/context/continued facts, listing corroboration, independent sum
tampering and experimental conflict exclusion. Tests do not establish alpha.
Final focused screen/parser checks passed 16 tests after the small disclosure
layout cleanup. Browser inspection confirmed Apple's actual imported class,
filing date, source link and collapsed technical metadata without overlap.
Current preview: http://127.0.0.1:8512/ (polling enabled for source-code updates).

## Next priorities

Refresh filing/share-count inputs whose observation dates have aged, extend
reviewed filing-class coverage and define a complete economic-class/share ledger
before using one stock price for issuer-wide valuation. Preserve unresolved
membership/public-permission gates. Expand semantic financial mappings only with
statement-level references and adversarial tests; do not broaden definitions
merely to fill a basket.
