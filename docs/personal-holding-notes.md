# Reopen personal holding notes

November 7, 2026. In **Review a stock I already own**, download a **personal
note (restorable JSON)** to retain the reason state and optional text. Reopen
it through **Reopen a personal note → Restore personal note** after entering
the matching holding and opting in. Uploading alone changes nothing. Restoring
explicitly replaces that symbol's reason/notes and clears sale assumptions.

Personal notes are unverified opinions, not company evidence. Saved dates are
user-supplied and unverified. Company conclusions always recompute from current
evidence; stale evidence continues to withhold them. Notes can be reopened after
the entered holding value changes because no holding value or acquisition cost
is imported. There is no automatic sale, score change or investment forecast.

`holding_notes.py` uses a strict versioned contract: exact symbol, saved date,
one of four personal-reason states, and at most 500 text characters. Restore
rejects files above 16 KiB, malformed/deeply nested JSON, duplicate fields,
unknown fields/versions, future dates, missing consent and symbols absent from
entered holdings. No imported outcomes, evidence, fees, costs or tax basis.
Checks validate file shape, not authorship or truth; there is no signature.

Session drafts retain reason/notes while switching holdings or closing the
review panel. Drafts outside the entered symbol set are pruned when the panel
renders; clearing private data removes all session drafts and widget state.
No database, global private cache, provider call or API route was added.
Private JSON is unencrypted; save it privately. Existing full-review downloads
remain read-only records; decision snapshots/PDF formats are unchanged.

Optional **Why is this before tax?** help distinguishes entered purchase cost
from verified basis and explains that acquisition lots/dates, account treatment
and tax rules are unmodeled. Full tax-lot analysis remains unfinished; the
existing illustration is not a taxable-gain calculation.

TDD: initial tests failed on the absent module; UI restore failed before its
implementation; excessive-nesting rejection failed before its fix. Final run:
**29 passed**, four existing dependency warnings, 4.47 seconds, UI enabled.
Includes note roundtrips/rejection, explicit restore/cost reset, switching
holdings, stale evidence, privacy clearing and existing holding/decision UI
regressions. Log: `output/tests/holding-notes-focused.log`. No full-suite rerun,
browser visual review, live-data refresh or observed novice study claimed.

Next: local stock acceptance/evaluation, outstanding tax/lot and evidence
boundaries, then rental discovery. A useful interview demonstration is restoring
a personal opinion while stale evidence still withholds a company judgment.
