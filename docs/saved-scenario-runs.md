# Saved goal-risk scenario runs

The user can explicitly save a named goal-risk analysis. The API recomputes the analysis from the validated request before persistence; it does not accept caller-supplied output as authoritative. SQLite stores the run identifier, UTC timestamp, scenario label and type, exact validated inputs, result snapshot, and model version (`goal-risk-lognormal-v1`). Re-running the same seed and inputs under the same implementation can reproduce the result.

The history view lists recent runs, retrieves a full snapshot, and compares two saved runs. Comparison requires the same starting balance, monthly contribution, horizon, inflation assumption, goal amount, simulation count, and seed. Expected return, volatility, and fee can vary. Matching path count and seed uses common random draws to reduce simulation noise when comparing changed assumptions. The API reports p10, median, and p90 balance deltas in today's dollars and the change in simulated goal-reaching share. Positive dollar differences mean the comparison run produced a larger model output under its assumptions; they do not imply realized gains or expected performance.

## Storage and privacy boundary

**Disabled by default:** `APP_MODE=ephemeral` blocks save/list/retrieve/compare routes before request parsing, and the UI hides history and disables saving. To use this feature on a trusted local instance, explicitly set `APP_MODE=local` and restart both services. This does not add authentication. Existing database files are preserved when switching modes. See [privacy-boundaries.md](privacy-boundaries.md).

The database path is configured with `SCENARIO_DB_PATH` and defaults to `scenario_runs.sqlite3` in the API working directory. The database and SQLite sidecar files are ignored by Git. The current app has no user accounts or authentication; this feature is for a trusted local, single-user instance. Anyone able to call the local API can list saved runs. Do not expose these endpoints to a shared or hosted environment until authentication, per-user isolation, retention, and deletion are implemented.

This first vertical slice saves goal-risk runs only. Other scenario types can be added after their comparison semantics are defined. Runs with different model versions cannot be directly compared, and the current response preserves historical outputs rather than silently recalculating old runs after model changes.

## Workflow verification

The scenario label is always available in the simulation form, so users can enable saving and enter a name before the same submission. The field accepts up to 80 characters, matching the API contract. Labels with fewer than two non-whitespace characters are rejected before sending the save request.

With `RUN_UI_TESTS=1`, Streamlit AppTest drives the form, history refresh, and comparison controls against a temporary localhost API server using the real HTTP client. Tests use a separate temporary SQLite database and check stored inputs, snapshot retrieval, rendered median deltas, incompatible-run errors, and that unsaved simulations and invalid labels create no records. This verifies the widget/API/storage workflow, not browser appearance.
