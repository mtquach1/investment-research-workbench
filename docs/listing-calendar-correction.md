# Listing calendar and missing-support correction

November 7, 2026. The coverage audit found a software defect, not a reason to
relax the stock strategy. Listing receipts used their UTC date while assessment
dates use Los Angeles. A November 8 03:00 UTC receipt is November 7 in Los
Angeles; the old check incorrectly labeled it future. Conversely, an eight-day-
old local receipt could appear only seven days old under its UTC date.

`security_listing.listing_reference_fresh` now checks receipt age on the same
Los Angeles calendar as the stock screen. Both exact-symbol corroboration and
complete-directory coverage use this function. The **0–7 day inclusive** policy
is unchanged for observation and receipt dates. Future local dates, missing
observation dates and receipts without a timezone remain rejected. This date-
based policy does not certify intraday availability.

Filing-class corroboration also preserves unavailable, stale and ambiguous
listing support instead of automatically describing it as a confirmed class
conflict. Observed non-common classes, exchange conflicts and flagged/absent
listings remain conflicts. No unknown security mapping is inferred.

## Actual installed result

With the same refreshed source releases, listing coverage is now **501
corroborated / 4 not found**, and Apple's dated filing class is corroborated.
Information Technology has five eligible research peers, joining Industrials
(9), Health Care (8) and Consumer Staples (6) above the five-peer minimum.
Materials remains at four; Consumer Discretionary and Communication Services
remain at one each. No failing company was made eligible by changing thresholds.

The experimental basket now fills ten positions under the unchanged three-per-
sector cap. Installed-data workflow evaluation: **10 passed / 0 blocked / 0
failed**, using the fixed $1,000.03 examples. Audit:
`output/audits/stock-workflow-clock-corrected-2026-11-07.json`.
These are limited software behavior checks, not verified recommendations,
financial-source certification, investment-performance evidence or full release
acceptance. Strict verified recommendations remain disabled. Economic classes,
official index membership and public-display rights remain unverified.

No new source download was needed for this correction. Public release remains
`0d080e7d913bb4d15eccb5f5dfb7c9bd4282c52f032cc2baa177c20a44277dda`;
market snapshot remains
`8e593f26ae8494df137a01c1f1d9059abf423dcfbf4566e89c47bfb275c4e010`.
Policy/strategy hashes are unchanged; this code correction can change outcomes
even with unchanged source hashes. Preserve old snapshots and recompute them
explicitly. Saved snapshot/PDF schemas were not changed.

## UI and verification

Workflow checks now label the Los Angeles assessment date. Reference health
explains that receipt timestamps are shown in UTC and may show the next date
during a Los Angeles evening. Exact timestamps remain available.

TDD: five boundary/classification cases failed before implementation (two other
boundary cases already passed). Cases cover same local day after UTC midnight,
true future receipts, seven/eight-day cutoffs and unsupported listing states.
Additional checks cover complete-directory absence and naive timestamps. The
UI label test failed before implementation. Core focused run: **70 passed**,
four existing dependency warnings, 4.26s;
`output/tests/listing-clock-focused.log`. No browser visual or novice study
is claimed. No paid service, account change, provider call, trade or schedule.

Final complete regression with UI/API enabled: **618 passed, zero skipped**,
59 dependency warnings, 57.04 seconds; `output/tests/listing-clock-full.log`.

Next: finish local stock acceptance with coverage/ranking/cost evaluation,
prospective follow-up and observed beginner tasks; retain tax-lot boundaries.
Public demo isolation and deployment remain separate gates. New rentals still
follow stock completion. A useful interview example is showing the UTC/local
boundary failure, unchanged policy and successful regression-backed correction.
