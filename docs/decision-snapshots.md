# Private stock decision snapshots and change review

November 6, 2026. Advances the local stock workflow under the user's approved
local-research/public-demo-first release sequence. It does not enable verified
recommendations or clear provider data for public use.

## Working workflow

Stocks → Build portfolio → Decision workflow → opt in → **Save, reopen and compare
decisions**. Save a named record in this session or restore a downloaded snapshot.
Compare using exact saved settings or the current editor settings. Recompute
explicitly against current server-loaded evidence; inspect changed outcomes,
paper amounts, scores, reasons, symbols/coverage and evidence findings. A separate
list identifies source/policy/strategy/settings changes, including source changes
that produce no company-level outcome change.

The UI shows recorded assessment, saved-record and current-check dates separately.
Records stay in this session (maximum ten). Download to retain a copy; removing
a record and the existing workspace reset drop application references. Import
does not enable consent or automatically compute a current assessment. Settings
or evidence edits invalidate the displayed comparison. Original records are
preserved separately from recomputed results. No broker orders, notifications,
background job, provider refresh, global private cache or database persistence.

## Validation and trust

`decision_snapshots.py` uses `stock-decision-snapshot-v1`, a checksum, complete
typed original assessment and exact input context. Both the downloadable indented
JSON and import must fit 1 MiB. Structure/text/card limits, unique identities,
strict integer cents, reconciled funding/holdings/outcome counts, dated records,
source/policy hashes and literal-false verification flags are enforced. Duplicate
JSON keys, oversized/deep inputs, future records, duplicate session records,
unknown versions and inconsistent amounts are rejected. Saved cent amounts and
fractional constraints are not rounded to the editor's whole-dollar controls.

The checksum is not a signature. Imported dates and original results remain
unverified, even if someone recomputes a valid checksum for a plausible edited
record. Such a record cannot control the current source data or computed result.
Recorded evidence is compared as an untrusted baseline, not replayed as a current
recommendation. Stale, withheld or unavailable current evidence returns no current
assessment; old candidates are not carried forward. Rank loss remains distinct
from a sell instruction under the unchanged experimental decision policy.

Legacy raw assessment JSON remains downloadable for inspection; it is not a
restorable snapshot. The UI identifies the supported named snapshot format.
Files and comparison exports contain personal settings/holdings: save privately.
They are not encrypted vaults or suitable public-demo assets by default.

## Model and API

- `freeze_decision`, `restore_decision`, `review_decision` are deterministic/pure
  given the assessment, date and server screen. No implicit clock/provider reads.
- `POST /research/stock-decisions/snapshot-review` requires explicit experimental
  acknowledgement, accepts a bounded snapshot string and optional typed context
  override, and recomputes from server-owned evidence and configuration.
- Responses are no-store. Validation errors omit private payloads. Request-supplied
  screens/verification flags cannot override the server. Session isolation, consent,
  malformed imports and stale-evidence behavior are tested.

Actual local check on the unchanged installed 88-company release, November 6:
19 pass / 59 insufficient-evidence / ten experimental candidates with the default
illustrative settings. Compact snapshot size: 275,820 bytes. Same-source/settings
recomputation produced zero changes. No private user holdings were needed for this
check and no provider data was re-downloaded or certified.

## Remaining local stock acceptance

Validation: **569 passed, zero skipped, 59 dependency warnings**, 91.65s, UI/API
enabled; `output/tests/decision-snapshots-verified.log`. Focused engine/decision/
API-contract checks passed 54 tests; focused UI/API checks passed four. Tests cover
private request/session isolation, exact cents, changed settings, invalid/forged/
oversized imports, duplicates, stale evidence, original preservation and comparison
invalidation. These are software checks, not novice usability/performance evidence.
An additional full-app navigation regression passed after that suite (one test;
`output/tests/decision-snapshot-full-app.log`). Browser layout QA used the same
component in an isolated localhost preview on port 8518 with illustrative
five-year saved vs one-year current settings and installed local evidence. The
comparison displayed changed findings, dates, private-download labels and USD
units. Earlier full-app browser navigation was inconclusive and encountered a
stale-tab error; the automated full-app save/compare navigation check passed.
The isolated preview is a development check, not the public-demo edition.

PDF summaries are now implemented; fuller thesis/acquisition-lot/cost/tax holding review, recurring-cash
integration, broader event context and end-to-end usability/evaluation remain.
Current quantities, complete economic classes, official membership and valuation
verification remain strict conditional gates. Finish local stocks before new
Orange County discovery; preserve both domains and their existing calculations.
Public synthetic/cleared-demo isolation and deployment still require implementation.

Interview suggestion: demonstrate saving an assessment, changing a source or
constraint, and getting an explained recomputation while the original remains
intact. Then show stale evidence withholding the new assessment. This demonstrates
reproducibility and safe failure handling, not investment outperformance or scale.
