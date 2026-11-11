# Privacy boundaries and data lifecycle

Decision date: October 27, 2026. Scope: local educational application and a future anonymous beta. This document describes implemented application controls and deployment obligations; it is not a certification of security, legal compliance, encryption, or zero retention.

## Decisions implemented now

1. **Default mode is session-only**: `APP_MODE=ephemeral`. No user accounts are needed. Explorer calculates on the Streamlit host, not in the browser. Financial values therefore leave the browser when a user interacts with a hosted instance.
2. **No database feature in this mode**: saved-run API operations return 404 before body/ID validation. Direct route handlers also check the policy. History is hidden in the UI, saving is disabled, and existing local records cannot be listed or retrieved. Existing databases are preserved, not deleted.
3. **No AI in this mode**, even if an API key and `ENABLE_AI=true` are accidentally configured. The AI endpoint is blocked before parsing the body. Explorer never calls AI in either mode.
4. **Trusted local features require operator opt-in**: `APP_MODE=local` enables unauthenticated SQLite history. AI additionally requires `ENABLE_AI=true` and a key. These are server configuration options, not plan inputs or UI switches. Local mode is not a safe multi-user deployment mode.
5. **User-owned files**: users can explicitly download a JSON plan and upload one to resume. Files contain sensitive financial assumptions and are not encrypted. Imported output is never trusted; validated inputs are recalculated. No public share links are generated.
6. **Workspace reset** removes this application's references to inputs, plans, simulation results, selected uploads, and legacy history in the current session. It does not delete existing databases or previously downloaded files and does not promise physical memory erasure.

## Data flow inventory

| Data or action | Where it goes | Retention/control |
| --- | --- | --- |
| Goal, opening balance, deposits, deadline, returns, fees, inflation | Browser → Streamlit server → shared Python engines → browser | Session state; no Explorer database writes or shared financial cache |
| Chart values and simulation output | Streamlit memory → browser | Current session; stale simulations are hidden when assumptions change |
| Named Explorer baseline | Current Streamlit session | At most ten snapshots; delete individually or clear workspace |
| JSON export | Generated in the Streamlit process → browser download | No application-created report file on server disk; browser/OS owns downloaded copies |
| JSON import | User-selected file → Streamlit upload manager → input parser | Transport cap 1 MB; plan parser limit 32,000 bytes, checked before reading content into the parser; rejected files do not change inputs |
| Structured legacy calculator submission | Streamlit → configured FastAPI service | Calculation only, unless explicit local-mode saved-run route is used |
| Contribution allocator holdings, targets, account cash and restrictions | Browser → Streamlit → shared solver → browser; external clients may use the API route | Session references only in UI; no AI, shared financial cache, database writes, or trade execution. Sync computation, not a background worker |
| Saved goal-risk run | FastAPI → SQLite | Only in `APP_MODE=local`; exact financial input/output snapshots persist until manually managed |
| Optional AI input | Explicit local-mode `/optimize` request → OpenAI API | Submitted free text for parsing, then deterministic financial metrics for narrative generation; provider policies apply |
| Logs and infrastructure metadata | Application/framework/host/proxy | See logging boundary below; hosting may retain IP addresses, network metadata, and operational logs |

No names, Social Security numbers, account numbers, passwords, addresses, bank credentials, or brokerage connection tokens are required. Use generic goal labels. The application cannot reliably detect every identifier typed into free text, so collection minimization remains a user-facing instruction as well as a product boundary.

## Research workbench boundary

The stock demo uses server-generated synthetic companies, with no live data or
verification switch in its public API. Its only user financial input is an
illustrative cash budget. Rental feasibility uses user-entered capital, rent,
costs and constraints. Both workbench tabs run shared engines in the Streamlit
session without AI, HTTP, database writes or a private shared cache. Their typed
API routes also calculate without persistence. Results remain session references
and are removed by Clear session; prior downloads/other infrastructure retention
limits still apply. This does not add hosted authentication or resource isolation.

## Session lifecycle

Streamlit session state is isolated by its framework session. It is **not authentication** and is not an encrypted vault. The host administrator and sufficiently privileged software can access process memory. Browser extensions, downloaded files, shared devices, OS swap, crash dumps, and host-level backups are outside the workspace-clear operation.

The repository's `.streamlit/config.toml` disables usage telemetry, leaves CORS and XSRF protection enabled, disables static-file serving, binds locally by default, and sets disconnected-session TTL to 60 seconds. TTL makes a disconnected session eligible for cleanup; it is not a guarantee that data is physically erased at exactly 60 seconds. Live connected sessions do not have a fixed retention deadline. Use the explicit clear action before leaving a shared device.

Reset rotates the file-uploader identity so the cleared selection is not silently reloaded. Successful import also rotates it and clears the previous UI reference. Framework-managed upload and download buffers and their delivery URLs follow framework cleanup; they are not an authenticated document vault. Review media/download URL access and caching before public deployment. We do not claim immediate secure destruction of these buffers. Configure the deployment so financial processes and upload buffers are not captured in routine backups or debug dumps.

## API, errors, and logs

- Saved-run and AI policy checks occur before request parsing and inside their handlers. These controls do not rely on hiding UI buttons or on CORS.
- All API middleware responses include `Cache-Control: no-store`, `Pragma: no-cache`, `Referrer-Policy: no-referrer`, and `X-Content-Type-Options: nosniff`. Streamlit and any reverse proxy require their own review; these headers do not cover every hosting layer.
- Validation errors return a generic 422 message instead of FastAPI's default input echo. Unexpected API failures return a generic 500 response and a fixed diagnostic event without financial exception text, request path, payload, or traceback. Some model-specific errors return fixed field/range explanations.
- `python run_api.py` binds to loopback and disables Uvicorn URL access logs. Other launch commands and reverse proxies may log paths, query strings, IP addresses, headers, or payloads; review them separately.
- Do not put financial values in URLs, query parameters, metric labels, analytics, error trackers, trace attributes, or debug logs. Operational monitoring should use event codes and aggregate counts rather than request content. Protect access to the remaining operational logs and define a short retention schedule before deployment.
- Streamlit browser error details are disabled. This does not disable all server-side framework diagnostics or protect against a host that logs sensitive information. Production log capture, retention, and redaction require deployment testing.

## Optional AI boundary

Default session-only mode blocks all AI processing. In trusted local mode, an operator can explicitly enable `/optimize`. The route sends the submitted description to the configured OpenAI model to parse a financial profile; it then sends completed tax metrics to format prose. Do not submit unnecessary identifiers. The UI's current Goal Explorer does not invoke this route.

Both SDK requests set `store=False`. This disables the requested response-storage behavior; it is **not a blanket zero-retention promise**. Provider abuse-monitoring, account controls, and applicable retention policies remain separate. Any future public AI feature needs an explicit user disclosure and authorization flow before transmission, a data-minimized payload, and provider-policy review. It must not inherit local mode's opt-in as authorization for anonymous users.

## PDF report boundary

PDF export is implemented as explicit preparation and download. The production generator recomputes validated inputs and creates report bytes in memory; it does not create server report files, temporary report files, persistent share links, or email delivery. Prepared bytes remain in the session until replaced, invalidated by changed inputs, reset, or cleaned up by the framework. Reports disclose assumptions, model/report versions, UTC creation time, and that they are not encrypted. Browser-based generation would further reduce server exposure but is not the current architecture. JSON remains the validated input format for reopening a plan; PDF is a readable report, not an authoritative source of imported calculations. See [goal-pdf-reports.md](goal-pdf-reports.md).

Developer-only visual QA writes synthetic PDFs under Git-ignored `output/` and `tmp/` folders. This fixture script reads no user session and is never invoked by the production report path. Framework-managed download buffers/URLs and host-level logs/backups remain subject to the deployment boundaries above.

## Threats covered and remaining release gates

The public-source cache and normalized release store contain provider snapshots
and research metadata only. The data-readiness endpoint accepts no financial
payload and makes no downloads. Its Streamlit metadata cache lasts at most 30
seconds and never receives budgets, holdings, comparisons or uploaded plans.
Refresh is an operator CLI action over fixed registered URLs. SEC operator contact
is read only for download headers and is not written to source manifests, release
artifacts or coverage responses. Public-source audit matrices are separate from
private user plan/PDF exports. Source access/display review and host-level backup,
logging and deletion policies remain separate. See [public-data-pipeline.md](public-data-pipeline.md).

Tests cover accidental activation through an API key, direct API bypass of UI controls, malformed requests to disabled routes, reading a pre-existing local database in session-only mode, payload/exception reflection, session reset, and separation between two UI test sessions. They do not prove the absence of every vulnerability or certify cross-user isolation under production concurrency.

Before public exposure, keep `APP_MODE=ephemeral` and AI disabled, and complete HTTPS/proxy configuration, proxy/WebSocket log review, resource and abuse limits, concurrent-session testing, dependency review, backup/crash-dump policy, incident response, and an independent security review. No authentication or ownership model has been implemented for the local database. Enabling local mode is not a substitute for those controls.

## References

- [OWASP logging guidance](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html): avoid recording sensitive inputs, tokens, and unnecessary personal information.
- [Streamlit configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml): session cleanup eligibility, telemetry, upload limits, and browser error behavior. Operator overrides can change repository defaults.
- [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data): response storage and provider retention are different controls.
