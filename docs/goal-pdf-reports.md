# Downloadable goal reports

Goal Explorer can explicitly prepare and download a readable PDF of the current plan. The production generator returns bytes from `BytesIO`; it does not write a report, create a temporary report file, contact AI, or use the database. This feature is available in default session-only mode.

## User workflow

1. Enter a valid goal and a plan label of at least two characters.
2. Choose today's or future dollars using the chart display control.
3. Optionally keep/select a compatible baseline, choose the comparison horizon, and enable **Include selected baseline in PDF**.
4. Select **Prepare PDF report**, then **Download PDF report**.
5. Store the file privately. Keep a JSON export to reopen or edit the plan; PDFs are not imported as authoritative calculations.

Preparing is explicit. The PDF is not generated on every slider movement. A prepared document stays available across changes to the inspected chart year or layout because it always describes the full plan horizon. Changing financial inputs, plan label, currency display, included baseline, or the included comparison mode removes the old download and requires preparation again. Invalid financial inputs or labels also remove it. Session reset drops the prepared byte buffer along with the other application references.

## Report contents

The usual report has two pages, with an optional third comparison page:

- Plan label, goal, UTC creation time, financial model version (`goal-explorer-v1`), and report format version (`goal-report-pdf-v1`).
- Opening balance, fixed monthly deposits, deadline, target in today's dollars, and its inflated future cost.
- Base deadline balance, modeled growth/loss, cumulative opening balance plus deposits, and goal surplus/shortfall, with explicit currency basis.
- A vector chart of low/base/high constant-return paths, opening balance plus deposits, and the goal. Distinct colors and dash patterns support inspection without relying only on color.
- Return, fee, inflation, and deposit timing assumptions; each scenario's ending balance, goal gap, and required monthly deposit.
- Selected yearly checkpoints and model/rounding limitations.
- Optional baseline comparison using the same checkpoint helper as the UI. The default uses the earlier deadline for both plans; separate deadlines are explicitly labeled. Changed assumptions, deposit totals, goal gaps, and balance deltas are disclosed. The comparison does not establish a better strategy.

All outputs are recomputed from revalidated inputs. Caller-supplied balances or chart results are not accepted. Simulation percentiles, actual holdings, and actual account progress are not included; the report explicitly distinguishes its constant-return lines from probability bounds. Required deposits are rounded estimates. A positive modeled amount below one cent is displayed as `< $0.01 (model)` when the opening balance alone does not fund the goal, rather than presenting it as a usable zero-deposit solution.

The report uses embedded package fonts. Unsupported label characters are visibly represented by their Unicode code points (for example `[U+1F3E1]`) rather than silently lost or rendered as black squares. Long labels wrap; very large financial amounts use approximate scientific notation. The JSON plan remains the source of validated input precision. This first version is not a fully localized or tagged-accessibility PDF implementation.

## Privacy boundary

PDF preparation occurs on the Streamlit server, not exclusively in the browser. Prepared financial inputs and report bytes are held in this session. Fonts are shared non-financial resources; there is no shared report-result cache. The document is **not encrypted**. Its PDF metadata uses a generic title rather than repeating the goal name, but its visible contents intentionally contain the financial assumptions.

The app does not create persistent report files or share links in its production export path. Streamlit manages download buffers and delivery URLs; reviewing their access, cache, cleanup, and proxy behavior remains a public-deployment requirement. Clearing a session removes application references, not previously downloaded files or guaranteed secure memory erasure. Report download handling follows [privacy-boundaries.md](privacy-boundaries.md).

`tools/preview_goal_report.py` is a **developer-only** fixture generator that deliberately writes synthetic example PDFs for visual QA. It reads no user sessions. Its `output/` and `tmp/` artifacts are Git-ignored. It is not called by the app or report generator and is not a server persistence feature.

## Verification

- PDF parsing checks verify known financial results, explicit units, versions, UTC dates, comparison horizons, privacy notices, and page counts.
- Filesystem writes and temporary-file creation are blocked during a generator test; successful output must still be returned as bytes.
- Reports for different plans must not contain each other's labels. Malicious-looking paragraph markup is escaped; PDFs must contain no JavaScript/open actions, attachments, or link annotations from those labels.
- UI tests cover explicit preparation, download availability, stale report invalidation, incompatible baselines, currency changes, generic failure messages, invalid inputs, and workspace clearing.
- Poppler renders are visually inspected for normal, long-label, and extreme-value fixtures. Text extraction alone is not used as visual proof.

October 27, 2026: the full local suite passed **151 tests with zero skips**. A browser spot check prepared and downloaded a two-page report through Streamlit; reopening the downloaded bytes confirmed the expected default balance and contribution requirement. A synthetic three-page comparison example and a two-page 60-year stress fixture were rendered through Poppler and visually reviewed. The downloaded report was confirmed unencrypted, as disclosed.

An independently reviewed financial model, user research, tagged-PDF accessibility testing, confirmed CI, and deployment security verification remain separate work.

## Technical reference

[ReportLab document templates](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/) accept a writable in-memory stream, allowing the application to return document bytes without creating report files.
