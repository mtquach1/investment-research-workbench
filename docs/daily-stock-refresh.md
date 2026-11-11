# Complete-cohort price refresh and recovery

Implemented October 31, 2026. This completes the operator-run price-refresh slice
of stock data stage 1. Security/membership/valuation verification, source refresh,
full-index storage, SIP adoption and scheduled automation remain separate work.

## User-visible behavior

Stocks → Build portfolio → **Price freshness and refresh status** shows the
installed observation cutoff, series count, snapshot download clock, last matching
attempt and known historical gaps. It loads only when opened and never downloads
data. Withheld mode exits before reading local market history. Reports from a
different installed snapshot do not establish current freshness.

The operator refresh now updates every installed issuer and SPY together. Readers
continue seeing the old immutable snapshot until all candidate batches pass and
the atomic pointer changes. No private holdings, budgets, goals or credentials
are part of snapshots, checkpoints, reports or provider symbol selection.

## Algorithm and integrity boundaries

1. Load/hash-verify installed history and current public references. Split the
   installed issuer cohort into batches of at most 24, plus SPY in each batch.
   Use the existing fresh SEC directory check and exact CIK/ticker association;
   reject changed identities and inconsistent old endpoints before transport.
2. Select one fully completed NYSE session cutoff using the existing one-hour
   post-close buffer. Reject backward refresh; unchanged cutoff/directory with
   split evidence is an offline no-op. Holidays/early closes use the calendar.
3. Re-download raw, split-only and all-adjusted prices for the **entire installed
   window**, not just the new days. Appending a newly adjusted tail to old adjusted
   history can manufacture returns after splits/distributions. Existing IEX-only
   endpoint, retry/page/byte/time limits and entitlement refusals remain intact.
4. Validate every batch against its frozen plan: exact symbols/CIKs/roles,
   adjustment evidence and trading dates. Previously observed dates cannot be
   lost; all newly completed sessions are required for every installed series.
   Previously known gaps may remain or be repaired by actual observations.
   No imputation or forward fill. An issuer that no longer supplies observations
   requires explicit investigation, not silent removal from the cohort.
5. Save immutable hash-verified batch checkpoints and atomic per-batch pointers.
   Full plan hash binds old snapshot, public release, directory, window, cutoff,
   calendar version and cohort. Reuse requires the same plan, same New York date
   and a six-hour retrieval window. Revalidate every cached batch; reject corrupt,
   future, cross-plan or invalid bytes. Expired batches are downloaded again.
6. Require identical SPY raw/split/all observations between batches; do not mix
   different benchmark revisions. Retain individual retrieval timestamps and
   their range. One cutoff is not a claim of simultaneous provider observations.
7. Validate a complete candidate containing exactly the old cohort. Under source
   then history publication locks, check the public release is unchanged and
   compare-and-swap against the expected prior history digest. A competing writer
   wins without being overwritten. No network runs under publication locks.
8. Save advisory `LAST_REFRESH.json` with controlled reason codes, counts, hashes,
   dates and known gaps. No raw exception/provider body is logged. CURRENT is
   authoritative; a failed advisory-report write cannot turn a successful commit
   into a reported publication failure.

Windows staging initially failed with `FileNotFoundError` because nested full
hashes produced a 269-character artifact path. Job-directory locators now use
16 hex characters; every consumed checkpoint still validates the full 256-bit
plan digest and full artifact checksum. A prefix collision cannot authorize reuse.
Regression tests emulate the Windows limit and a consistently rehashed wrong plan.

## Operator commands

```powershell
# Preflight only: no requests, subscription changes or credentials required.
.venv/Scripts/python.exe tools/refresh_installed_history.py --as-of 2026-10-31

# Refresh the full installed cohort. Retry this command to resume valid batches.
.venv/Scripts/python.exe tools/refresh_installed_history.py --as-of 2026-10-31 --download

# Ignore checkpoints and download every batch again. Old artifacts are retained.
.venv/Scripts/python.exe tools/refresh_installed_history.py --as-of 2026-10-31 --download --restart-staging

# Explicit rollback: use actual digests from the published audit/current pointer.
.venv/Scripts/python.exe tools/refresh_installed_history.py --rollback-to TARGET_SHA256 --expected-current CURRENT_SHA256
```

Rollback validates an existing artifact, earlier cutoff and same symbols/CIKs,
then uses compare-and-swap publication. A changed current pointer refuses rollback.
The old snapshot's dates remain old; rollback never relabels it as freshly fetched.
No automatic fallback masks a corrupt CURRENT pointer. No recursive deletion,
automatic checkpoint pruning, scheduled task, paid-feed fallback or public access
grant is introduced. Sources such as issuer directory/universe still need their
own refresh; a stale directory can block this operator command.

## Real installed verification

On October 31 Los Angeles time, all **89 installed series** were refreshed in
four batches (24/24/24/16 issuers, with SPY repeated for consistency checking).
The completed cutoff advanced from October 28 to **October 30, 2026**. There are
**89,444 price-date observations**; known gap: COR, August 30, 2023.

Previous market snapshot:
`4672003d0a31358661a57c47b8f7c7b52f21d9824f9ab9db5aec8b0d07a7778c`

Published market snapshot:
`bd8ef356fe5633eb74e6c215b0bd3f3bbfc4728166b19fa2564d2b83dd6cd726`

Public reference release was unchanged:
`b5883d7436083ab2a20db2afd232641a68537271ea3bdbfbcbf117cc9709f026`.

Earliest/latest batch retrieval: November 1, 03:55:14–03:55:52 UTC (October 31
in Los Angeles). First real attempts preserved the old pointer when Windows
staging failed; the final attempt published all four batches successfully.

Independent matching October 30 raw-close checks against the existing secondary
diagnostic source passed the larger-of-$0.05-or-0.5% tolerance for AAPL, MSFT,
NVDA, LIN and LOW. Relative differences were approximately 0.041%, 0.012%,
0.059%, 0.013% and 0.005%. Five sampled closes do not validate all history,
corporate actions or exact reinvested returns; those claims remain withheld.

Financial rules still show 36 pass / 21 fail / 31 unavailable. Valuations now
show 59 estimates / 15 stale / 12 multiple-security cases / two unavailable:
new prices do not refresh old shares, while some filings now predate the price.
The experimental basket still fills ten positions; strict recommendations and
public redistribution remain disabled. This refresh did not adopt SIP or
refresh financial/issuer/universe/news sources.

Artifacts:

- `output/audits/daily-refresh-plan-2026-10-31.json`
- `output/audits/daily-refresh-published-2026-10-31.json`
- `output/audits/daily-refresh-coverage-2026-10-31.json`
- `output/audits/daily-refresh-price-checks-2026-10-31.log`
- `output/tests/daily-refresh-verified.log`

Full suite: **445 passed, zero skipped, 55 dependency warnings**, UI/API enabled.
Tests cover mid-job refusal/resume, old/new gaps, full-window adjusted history,
benchmark revisions, corrupt/wrong/expired staging, concurrent publishers,
source changes, no-op, binding changes, explicit rollback, Windows paths,
status-write failure and lazy/withheld UI behavior. No profitability claim.

## Next priorities

Add a separately versioned and validated SIP candidate store before any feed
migration. Refresh and improve the underlying security/class/share/financial
evidence rather than relaxing gates to retain basket size. Full-index sharded
storage and coordinated source/quote refresh remain necessary for the larger
release. Scheduling can be added only when explicitly requested; it is not
currently automatic.
