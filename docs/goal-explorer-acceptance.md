# Goal Explorer acceptance checks

Use synthetic inputs only. These checks cover application behavior; they are not independent user research or a formal accessibility/security audit.

## Automated checks

Run `RUN_API_REQUEST_TESTS=1 RUN_UI_TESTS=1 python -m pytest -q` using the platform's environment-variable syntax. Windows PowerShell commands are in the README. AppTest covers:

- Contribution number entry/slider synchronization, navigation persistence, inspection at year zero, and reducing the deadline.
- Applying the base monthly estimate, including refusing to apply a sub-cent estimate that rounds to zero while a shortfall remains.
- Explicit notices when rounding leaves a small gap; no assertion that actual investment outcomes are guaranteed.
- Chart-first and side-by-side layouts without changing financial inputs.
- Session comparison, restoration, deletion, and default comparison at the earlier deadline for both plans. Switching to each deadline displays a warning.
- Hiding stale simulations when financial assumptions change, with a stable seed on reruns.
- Two separate test sessions do not share balances or baselines.
- Session reset clears baselines, risk output, legacy history references, and selected-uploader identity.
- Session-only UI hides history and disables saving; API attempts to bypass these controls are blocked independently.

## Browser task script

1. At a desktop viewport, open Goal Explorer and confirm session-only mode is visible in the sidebar.
2. Open the privacy disclosure. Confirm it says processing happens on the server, files contain financial assumptions, and reset does not promise secure erasure.
3. Open the goal editor. Enter an ordinary goal, target, opening balance, contribution, and deadline. Change a control using the keyboard and confirm recalculation.
4. Focus Inspect year. Home should show year zero's opening balance and zero growth; End should return to the deadline. Required monthly contribution must stay tied to the deadline.
5. Activate Use base monthly estimate with the keyboard. Confirm the contribution updates, and any cent-rounding gap is explained rather than hidden.
6. Keep a baseline, change the deadline, and check both plans are evaluated at the earlier year by default. The separate-deadline view must warn about different time/deposit totals.
7. Expand the yearly table and simulation section. Confirm financial data has text alternatives to the chart.
8. At a 390 × 844 viewport, confirm the sidebar collapses, controls remain usable, funding cards stack, and graph labels remain readable. There must be no page-wide horizontal overflow. Detailed tables may require horizontal scrolling; primary results must remain available as cards.
9. Clear the workspace and confirm defaults return without deleting exported files or any local database. For a hosted beta, also test framework download URLs, concurrency, browser caches, and reverse-proxy retention separately.
10. Prepare a PDF with and without a selected comparison. Download and open it; verify the figures, chart basis, comparison horizon, model/report versions, and privacy notices. Change the contribution or currency and confirm the previous download disappears. Changing only the inspection year should keep the prepared full-horizon report. Keep JSON to reopen the plan.

## Evidence and limits

October 27, 2026: desktop browser spot checks used the 1280 × 720 default viewport, keyboard Home/End on the inspection slider, and keyboard activation of the base-estimate action. The default rounded deposit produced a nine-cent shortfall in today's dollars, which the UI disclosed. Responsive checks at 390 × 844 confirmed stacked funding cards with all three required monthly amounts and balances readable. DOM measurements showed a 390-pixel document width and 380-pixel main scroll width at a 390-pixel viewport: no page-wide horizontal overflow. The temporary viewport override was reset afterward. The complete local suite passed: **135 tests, zero skips**, with one dependency deprecation warning. Source compilation and `git diff --check` also passed. This is a spot check, not mobile certification or a formal accessibility audit.

Still needed: observed tasks with potential users, assistive-technology testing, other browsers/devices, load and cross-user media-delivery tests, and a confirmed remote CI run.

PDF feature verification on October 27, 2026: **151 tests passed with zero skips**. The generator succeeds while report/temp-file writes are blocked by a test. Known financial values, concurrent plan separation, currency displays, comparison horizons, unsupported-label fallback, and stale-download behavior are covered. Normal and stress-case PDFs were rendered through Poppler and visually inspected. This does not establish tagged-PDF accessibility or production download isolation.
