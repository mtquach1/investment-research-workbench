# Listing evidence, broader coverage and responsive research reads

October 29, 2026. This advances the stocks-first data gate. It does not enable
verified recommendations, declare complete index coverage or establish strategy
performance. The experimental path and strict path remain separate.

## Independent listing references

Two fixed, free [Nasdaq Trader directory files](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)
are imported through the existing bounded downloader and immutable release pipeline:
[Nasdaq listings](https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt) and
[other-exchange listings](https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt).
No account, credentials, paid endpoint or provider membership was added.

The adapter requires exact headers, bounded rows/bytes, valid flags, unique
records and a final creation timestamp. Future dates, malformed/truncated rows,
duplicate records and unknown Nasdaq market categories are refused. An unknown
other-exchange code is retained as unsupported. File creation timezone is not
asserted; the creation date and retrieval date are separately checked within
seven days. This is a dated listing reference, not historical tradability proof.

Matching uses only exact source symbols from the explicit ACT, CQS and NASDAQ
namespaces. No punctuation replacements or company-name fuzzy joins are used.
The listing exchange must agree with the SEC directory before corroboration.
The SEC `CBOE` label is mapped explicitly to BZX, supported by Cboe's own
[primary-listing transfer notice](https://cdn.cboe.com/resources/release_notes/2018/Cboe-Corporate-Listing-Transfer.pdf).
Provider names/type hints, ETF/test flags and Nasdaq listing-status flags remain
inspectable. A non-normal listing status is not converted into a financial diagnosis.

Measured result for the 505 dated ETF reference securities: **501 corroborated
listing/exchange matches and four without an exact listing match**: `BRK B`,
`BF B`, `HOLX`, `SKYD WS`. These rows remain unresolved. Their absence is a
statement about these directory snapshots, not proof of delisting or index removal.

Corroboration does not verify legal share-class/issuer identity, official S&P 500
membership, all economic classes, issuer-wide valuation or suitability. Those
contract fields remain false. Positive listing conflicts, ambiguity, flags or
absence exclude experimental candidates when observed. Unavailable/stale listing
coverage cannot establish verified recommendations and remains disclosed.

Research screen → Coverage & evidence adds a listing coverage chart and per-row
status/name/date. Company inspection shows exact matching namespaces, source
hashes and reasons. Share-count age before the quote is displayed explicitly.
Published source metadata remains separate from licensed quote data. The new
directory records are local research only pending public-display review.

## Balanced expansion before score inspection

Twenty-four companies were selected for underrepresented-sector coverage before
inspecting their scores:

- Materials: LIN, APD, SHW, ECL, VMC, MLM.
- Utilities: NEE, DUK, SO, AEP, EXC, XEL.
- Consumer Discretionary: LOW, TJX, BKNG, MAR, ORLY, AZO.
- Communication Services: TMUS, VZ, T, DIS, CMCSA, CHTR.

All 24 SEC source imports normalized; this is an ingestion result, not a statement
that all required financial facts were available. Compatible IEX raw/all/split
histories were merged at the original October 28 completed cutoff. The previous
series, source clocks and adjustment basis were retained. The importer now binds
current issuer evidence using the current assessment clock, independently of the
requested price-end date. A newer public release no longer prevents an older
price cutoff; historical membership is not inferred from this current mapping.

Measured scope: **88 issuer records, 89 price series including SPY, 89,266 daily
rows**. Financial rules: 36 pass, 21 fail, 31 unavailable. Valuations: 63 estimates,
seven stale, 12 multiple-security cases and six unavailable. None is a verified
current issuer capitalization. Full installed-history risk checks still require
756 complete returns. Missing dates are not fabricated.

The independent calculation audit now reports **640 passes, zero mismatches,
168 unavailable checks**, including the same two limited official annual-report
reference cases. The experimental basket still fills ten positions in four
sectors. Adding source records does not relax peer, financial or sector rules.

Independent latest-close diagnostics for AAPL, MSFT, NVDA, LIN and LOW all fell
within the existing larger-of-$0.05-or-0.5% tolerance on October 28. These checks
are attached to the new market snapshot. They do not verify full history,
consolidated total return, adjustment conventions or issuer market capitalization.

## Data integrity and navigation

An adversarial check now prevents an issuer's former ticker history from pricing
a different current security solely because the stored CIK agrees. Both ticker
association and issuer must match; mismatches withhold price, valuation and risk.

Expansion exposed a repeatable 30-second company-navigation timeout. A thread
trace identified repeated artifact reads. `read_verified` used a 32 MiB maximum
read for every small artifact; it now reads the measured size plus a growth
sentinel, preserving maximum-size, full checksum and strict JSON checks. Growth,
corruption and duplicate JSON fields remain rejected.

Company detail verifies the manifest and the artifacts it consumes, rather than
re-reading unrelated companies, listing directories and housing data. Corruption
in the requested financial facts or SEC associations still fails closed. A
separate issuer's corrupt facts do not prevent reading an intact selected issuer;
whole-release audits still detect the corruption. The closed source panel now
loads only when opened, retaining its public-metadata cache and all documentation.
No financial user input or credentials were added to a global cache.

## Reproduction and remaining gates

Local artifacts:

- `output/stock-coverage-listing-audit.json`: measured coverage and listing hashes.
- `output/listing-milestone-financial-validation.json`: independent arithmetic audit.
- `output/listing-milestone-price-checks.log`: five bounded second-source diagnostics.
- `output/coverage-expansion-plan.json`: batch chosen before score inspection.
- `output/coverage-expansion-sec.json`, `output/coverage-expansion-market.json`: imports.

Public release: `b5883d7436083ab2a20db2afd232641a68537271ea3bdbfbcbf117cc9709f026`.
Market snapshot: `4672003d0a31358661a57c47b8f7c7b52f21d9824f9ab9db5aec8b0d07a7778c`.
No user budgets or credentials are included in these coverage artifacts.

Rebuild listing references with the existing operator command:

```powershell
.venv/Scripts/python.exe tools/refresh_market_data.py --as-of 2026-10-29 --source nasdaq_listed_directory --source nasdaq_other_directory --download
.venv/Scripts/python.exe tools/audit_stock_research.py --as-of 2026-10-29 --output output/stock-coverage-listing-audit.json
```

Remaining: official dated index/security evidence, independently supported current
issuer-wide valuation across economic share classes, missing annual facts,
full-universe coverage, point-in-time evaluation including removed securities,
public data rights, stock reports and proposal/override comparisons. No paid
service was used and no strict gate was waived. Price history remains through
October 28; this milestone does not schedule daily refresh or invent later prices.

## Verification

Full suite with UI and API request tests enabled: **391 passed, zero skipped,
55 dependency warnings, 126.96s**. Log:
`output/tests/listing-coverage-verified.log`. The initial full run exposed a real
company-navigation timeout, fixed without raising its 30-second limit. A coverage
test was updated to explicitly open the lazy panel and still checks that its
contents disclose scope without changing the rental calculation.

Tests cover malformed/truncated/future/duplicate listing records, exact explicit
aliases, exchange disagreement, stale references, missing-reference distinctions,
listing-flag exclusions, local-display gates, old-symbol pricing, current-release/
historical-price date separation, bounded/growing/corrupt files and selective
consumed-artifact verification. Browser QA confirmed the live coverage chart;
the running API returned 88 issuers and 501 corroborations, with no-store and
strict recommendations disabled. Final chart spacing and count-unit explanations
are presentation changes following that full run.
