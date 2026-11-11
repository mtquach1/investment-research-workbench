# Private stock decision PDF

Implemented November 6, 2026, for the approved local-research edition. In Stocks
→ Build portfolio → Decision workflow, save/reopen a snapshot and recompute it,
then open **Export a readable private report**. Prepare the report explicitly.
Changing its settings, record or source evidence clears the prepared download.

`stock_decision_report.py` recomputes against server-owned current evidence and
returns PDF bytes in memory. No provider calls, database writes or temporary
private report files occur. POST `/research/stock-decisions/report` uses the same
bounded snapshot request, explicit experimental consent and server source mode;
responses are PDF attachments with no-store headers and generic private errors.
Stale/unavailable evidence withholds the report rather than printing old results
as current recommendations.

The report includes settings/holdings, cent-reconciled funding, recorded/current
outcome counts, every current company/holding card with its primary reason,
candidate/holding evidence dates, explained changes and source/model identifiers.
Primary reasons and unusually long labels are abbreviated visibly; complete
checks and supporting/contrary evidence stay in JSON. It is a readable summary,
not a replacement for the full evidence record. Original results/dates remain
unverified, and all experimental/verification limitations stay visible.

PDF metadata is generic; labels are escaped; no active links, attachments or
scripts are added. The PDF is not encrypted or restorable. User downloads contain
private settings and must not be bundled into the public demo without applicable
clearance. The public-demo edition remains unfinished.

Validation: 13 focused report/API-contract/API/UI checks passed, five dependency
warnings, 3.73s; `output/tests/stock-pdf-focused.log`. Coverage includes exact
cents, all cards, stale/consent withholding, inert hostile/long labels, private
metadata and download invalidation. The unchanged core had previously passed
569 full regression tests plus a full-app navigation check; no new full-suite
run is claimed for this focused PDF milestone.

A five-page synthetic example was rendered with bundled Poppler and visually
checked for wrapping, repeated headers, page boundaries and readable footers:
`output/stock-pdf-qa/synthetic-stock-review.pdf`. It contains fictional companies
and illustrative settings, not private holdings or verified recommendations.

Remaining: fuller thesis/cost/tax holding review, recurring-cash integration and
local stock usability/evaluation; then Orange County discovery and shared
comparisons. Interview suggestion: demonstrate a reproducible saved decision,
updated-evidence review and downloadable report while preserving the original.
