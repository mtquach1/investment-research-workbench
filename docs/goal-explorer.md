# Goal Explorer

The default Streamlit page connects a goal, contribution budget, and deadline to a visual projection. Chart-first mode puts the editor in a disclosure and keeps results full width; side-by-side mode remains available. Adjusting inputs recalculates without submission. The base-deposit action applies the rounded estimate, not an affordability recommendation. The page runs shared Python engines in the Streamlit server process; it does not require FastAPI or an AI key. This is **not browser-only processing**. `POST /scenarios/goal-explorer` exposes the same deterministic model to API callers. The sidebar explains privacy boundaries and can clear session references; see [privacy-boundaries.md](privacy-boundaries.md).

## Calculation contract: goal-explorer-v1

Inputs include the opening balance, fixed end-of-month deposits, a 1–60 year horizon, target in today's dollars, inflation, annual fee, and ordered low/base/high annual return assumptions. These are illustrative assumptions chosen by the user, not calibrated forecasts. Each return less the fee must exceed -100%. Requests and imported plans reject unknown fields and invalid ranges.

For each return scenario:

- Monthly growth factor: `q = (1 + annual_return - annual_fee) ** (1 / 12)`.
- Balance recurrence: `B[m] = B[m-1] * q + monthly_contribution`.
- Annual checkpoints include year zero and every completed year up to the deadline.
- Starting balance plus deposits at month `m`: `D[m] = opening_balance + m * monthly_contribution`. The opening balance may contain historical gains; its cost basis is unknown.
- Modeled growth/loss since the start: `B[m] - D[m]`.
- Future goal at year `t`: `target_today * (1 + inflation) ** t`.
- Today's-dollar balance: `B[12*t] / (1 + inflation) ** t`.
- Required fixed monthly deposit uses the existing `project_goal` annuity formula. It is zero if the projected opening balance alone funds the target. Results are rounded to cents, not a guarantee of meeting an exact target with cent-denominated deposits.

The display toggle converts balance, cumulative deposits, growth, and the goal at each checkpoint using the same inflation factor. The displayed real deposit figure is the cumulative nominal amount deflated **at the checkpoint**, not a sum of deposits discounted at their individual deposit dates. Chart inspection changes neither the deadline nor the required monthly contribution. Those headline values always describe the full plan.

The model uses the project's simplified annual return-minus-fee convention. It excludes investment taxes, withdrawals, changing deposits, account eligibility and limits, and actual market data. It does not decide whether a budget is affordable or recommend an asset allocation.

## Uncertainty and comparisons

The main chart uses three constant returns. Its low/high lines are **not** percentiles, confidence intervals, or limits on losses. An optional, explicitly triggered simulation uses the existing seeded lognormal engine, with 1,000 paths and the base return assumption. It reports terminal p10/median/p90 values and the simulated goal-reaching share. A percentile is not a best/worst case or a calibrated forecast. Changing financial or simulation assumptions hides stale results until the user runs it again; changing the inspection year does not rerun it. See [goal-risk-analysis.md](goal-risk-analysis.md).

Users can keep up to ten named input snapshots in the current session. Comparison requires the same goal name, starting balance, today's target, and inflation. Contributions, fees, returns, and deadlines may change and are disclosed in readable currency/percentage units. By default, both plans are evaluated at the same elapsed year (the earlier deadline). Users can explicitly switch to each plan's own deadline; that view warns about differing time and deposit totals. In either view a balance delta is **not a performance ranking**. Restoring a baseline restores its goal inputs and label and resets inspection to its deadline. The legacy goal-risk database comparison rules remain unchanged.

## Privacy, export, and import

There is no application-level database persistence or shared calculation cache for Explorer inputs. Session plans are lost when the session ends; this is not a promise of secure memory erasure or protection from server administrators. Inputs are processed on the Streamlit host and returned to the browser. Default session-only mode blocks legacy saved-run and AI routes. Legacy calculator pages still call FastAPI; SQLite history requires explicitly configured trusted local mode. Explorer does not call AI in either mode.

Users may explicitly download a JSON plan containing model version, label, creation timestamp, and validated inputs. Downloads contain financial assumptions and are not encrypted. Importing uploads the file to the Streamlit server. Only `goal-explorer-v1` files of at most 32,000 bytes are accepted, with a size check before parsing. Imported results or executable content are not accepted; all outputs are recomputed from validated inputs. Restore/import updates the current inputs and does not save a database record. Successful import replaces the uploader identity to drop the old UI selection. Delete removes a selected session snapshot, not exported files. Clear session workspace removes current inputs, snapshots, simulation results, and legacy in-session history without deleting databases or exported files.

PDF reports are also available through explicit preparation and download. Reports contain the full goal horizon and optional selected comparison, not just the inspected chart year. They are recomputed in memory from validated inputs; relevant input changes remove the old download. Session clearing removes prepared report references. PDFs are not encrypted and cannot be imported as editable plans. See [goal-pdf-reports.md](goal-pdf-reports.md).

## Verification and remaining work

- Independent Decimal reference case sums twelve deposits using exactly 1% monthly growth, independently of the engine's annuity formula.
- Reference cases include zero net return, 10% effective annual return with $1,000 month-end deposits ($12,540.54 after year one), already funded goals, losses, inflation conversion, and timeline/summary parity.
- Invariants cover return ordering, contribution direction, accounting identities, and horizons up to 60 years.
- AppTest covers contribution-slider synchronization, inspection, deadline reduction, navigation persistence, session comparison/restore/delete, invalid inputs, and stale simulation behavior.
- Additional AppTest checks cover two independent sessions, whole-workspace reset, upload-identity rotation, disabled storage controls, applying the base estimate, both layouts, and aligned versus separate-deadline comparison tables.
- Yearly values and simulation percentiles have static text-table alternatives. Browser spot-checks and keyboard tests do not amount to a screen-reader or WCAG audit.
- API tests verify the declared endpoint response and invalid-rate rejection. File tests cover input round trips, oversized files, unsupported versions, and untrusted output rejection.

Manual browser checks use synthetic defaults. They are not an accessibility audit, cross-browser/mobile certification, independent financial review, or user research. Successful remote CI remains unconfirmed because this checkout has no Git remote configured. Observed user task completion, a full accessibility review, and browser coverage remain release work.

## Source context

- [SEC Investor.gov compound interest calculator](https://www.investor.gov/financial-tools-calculators/calculators/compound-interest-calculator): an official educational reference for starting amounts, recurring contributions, time horizons, and interest-rate scenarios. Our effective-annual-rate convention and deposit timing are explicitly specified above; we do not claim exact parity with calculators using different compounding conventions.
- [Streamlit session state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state): state persists across reruns within a session. Persistent application copies preserve Explorer inputs when widget cleanup occurs during page navigation.
