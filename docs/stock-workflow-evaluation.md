# Connected stock workflow evaluation

November 7, 2026. **Stocks → Build portfolio → Validation & evaluation → Check
the connected stock workflow** now runs ten explicit software checks using
fixed example inputs and current installed evidence. No personal holdings are
read, data downloaded, trades placed or private database records written.
The optional panel shows passed/blocked/failed counts, plain-language results,
dates and downloadable versioned JSON with source/policy fingerprints. Evidence
changes clear the displayed result; a blocked path never counts as accepted.

## What is checked

1. Experimental consent is required before returning company assessments.
2. Initial $1,000.03 reconciles to additions plus unassigned cash.
3. A one-year horizon withholds additions under the existing policy.
4. A decision snapshot saves/restores exact context and cents.
5. Same-evidence recomputation reports no decision changes.
6. A separate $1,000.03 monthly deposit reconciles to additions plus cash, with
   no assumed initial purchases and no stock above its equal-weight target.
7. Excluding a baseline candidate blocks its addition without changing scores.
8. A 5% direct-position cap limits ten additions to $50 each, retaining $500.03.
9. A personal note roundtrips independently of company judgments.
10. Stale references withhold both initial and monthly additions.

`stock_acceptance.py` exposes a deterministic typed report. Checks record fixed
explanations; exceptions fail closed without exposing exception text. Missing
prerequisite evidence yields blocked paths. These are connected invariants,
not independent financial source verification, comprehensive test coverage,
strategy backtesting or investment-performance evidence. Production readiness
and investment-performance verification remain literal false. Multiple equally
optimal allocations are acceptable; no return optimality is claimed.

## Actual installed-data result

Latest [listing-calendar correction](listing-calendar-correction.md): **10 passed,
0 blocked, 0 failed** on the same refreshed evidence. A UTC/local date defect had
incorrectly blocked a sector peer. The experimental basket is now feasible;
verified recommendations and broader release acceptance remain gated. Report:
`output/audits/stock-workflow-clock-corrected-2026-11-07.json`.

Before that correction, the November 7 [full installed-cohort refresh](stock-evidence-refresh-2026-11-07.md) reported:
**7 passed / 3 blocked / 0 failed**, with current references and November 6 prices.
Zero candidates: financial/peer/sector coverage cannot fill ten positions. The
personal-note check now runs independently of market freshness/candidates.
Report: `output/audits/stock-workflow-refreshed-2026-11-07.json`. UI and JSON now
include dates, candidate counts and blockers. The earlier result below is historical.

The November 7 offline run reported **incomplete: 2 passed, 8 blocked, 0 failed**.
Consent and stale-data withholding passed. References were stale at that run, so the
remaining connected paths were not accepted on actual evidence. Synthetic
fixtures exercise all ten paths, but do not fix current data. Report:
`output/audits/stock-workflow-evaluation-2026-11-07.json`.

Reproduce without network:

```powershell
.venv/Scripts/python.exe tools/evaluate_stock_workflow.py --output output/audits/stock-workflow-evaluation.json
```

Exit codes: 0 all example checks passed, 1 a software check failed, 2 incomplete
because paths are blocked. Output contains fixed examples and public evidence
fingerprints, not the user's private inputs.

## Validation and remaining gates

TDD engine/UI checks failed before the missing modules were implemented.
Focused checks: **38 passed**, four dependency warnings, 5.95 seconds,
`output/tests/stock-acceptance-focused.log`. A prior fixture setup hit Windows
`os.replace` access denial; a fresh run passed, without weakening atomic writes.
Tests inject broken accounting and private exception text to verify failure and
sanitization, and check source-change invalidation in the UI.

The first full regression found a test-isolation defect: a consumer imported
during a full-app test retained the monkeypatched 20-company provider after that
test ended. The fixture now imports/patches that consumer explicitly. The two
tests pass in their previously failing order (`output/tests/stock-navigation-isolation.log`).
This changes test setup, not production evidence gates.

Final full regression, UI/API enabled: **609 passed, zero skipped**, 59 dependency
warnings, 52.81 seconds; `output/tests/stock-workflow-full.log`. No native diagnostic
appeared in this run; this does not establish a historical Windows issue's root cause.

This milestone does not close the stock completion gate. Next: refresh and
re-evaluate actual evidence, complete remaining correctness/coverage/ranking/cost
evaluation and prospective paper follow-up, resolve outstanding holding/tax-lot
boundaries, and observe beginner tasks. Public-demo isolation, rights review,
clean setup and deployment acceptance remain separate. No browser visual QA or
observed usability study is claimed. New rental discovery still follows stocks.

Interview demo: show an example exclusion and cap, their cent-reconciled effects,
then stale-data withholding. Explain exactly what the software checks establish
and what would require point-in-time evidence or user research.
