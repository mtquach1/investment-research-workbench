# Guided holding review - November 7, 2026

The local stock workflow now opens on Decision workflow. Data detail is optional;
the first view explains the experimental scope, input order, investment time and
position-size limit in plain language. Numeric help illustrates a 30% position.
Stale-data messages preserve settings and point users to the Research screen.

For entered holdings, **Review a stock I already own** separately checks the
current company assessment and the user's stated reason for owning the stock.
Reasons/notes are user statements, never company facts or ranking inputs. A
lower ranking alone is not a sell signal. Missing company evidence takes
precedence, with known concerns retained. No sale is recommended automatically.

An optional whole-position illustration subtracts an assumed fee from the user's
entered value. If total purchase cost is entered, its difference is shown; missing
cost remains unknown, not zero. Exact integer cents reconcile. Fees above value
are rejected. This is pre-tax arithmetic, not execution pricing, tax basis, tax
lots or a tax-aware sale recommendation. It remains usable from entered amounts
when company evidence is unavailable, with that evidence gap explicitly labeled.

`holding_research.py` provides the typed review and explanations. They are
deterministic and grounded in tested results; no language model, provider call,
paid service or score rewrite is involved. POST `/research/stock-holding-review`
uses server evidence, no-store responses and private validation errors.

Notes and cost illustrations stay in session and have a private JSON download.
Personal reason/notes now also have a separate [restorable note format](personal-holding-notes.md);
sale assumptions are cleared on restore and company evidence is recomputed.
They are explicitly separate from the existing decision snapshot/PDF format;
snapshot compatibility is preserved. Acquisition lots and full tax analysis
remain unfinished. A [one-deposit monthly preview](monthly-stock-contributions.md)
is implemented separately; no recurring execution is assumed. Strict verified
recommendations remain gated; both stocks and Orange County rentals stay required.

Validation: 21 focused engine/UI/API/contract checks passed, five dependency
warnings, 11.41s; `output/tests/holding-review-focused.log`. An earlier focused
engine/decision/contract run passed 41 checks. UI tests cover exact amounts,
unknown purchase cost and stale-data behavior. No new full regression or novice
usability study is claimed. Browser layout review remains pending.

Interview demo: show missing evidence withholding a company judgment while the
user's separate, traceable cost illustration remains available. Explain why the
tool preserves uncertainty rather than presenting a forced buy/sell answer.
