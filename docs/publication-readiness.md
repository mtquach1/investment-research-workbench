# Public source preparation — November 10, 2026

Prepared for a new public research-portfolio repository. This is publication of
source, not deployment of a financial service or a claim of completed research.
The original working tree, local data and Git history are preserved.

## Scope and audit

- Current tracked and nonignored source files are checked for private filenames,
  provider-token patterns, private keys, embedded URL credentials, personal
  machine paths, contact addresses and exact sensitive values read internally
  from the local `.env`. Neither values nor value hashes are emitted.
- All reachable Git blobs, including local checkpoint references, are checked.
  Findings contain only scope, relative filename, rule and line number. History
  sizes/counts are bounded and oversized objects fail review rather than silently
  passing. Commit-contact metadata is reported as a boolean, never an address.
- Current source passes the snapshot audit. Retained checkpoint history contains
  personal workstation paths, and original author-contact metadata is present.
  No provider-token or exact-local-credential finding remains after correcting
  a false positive on a public news URL. This is a limited automated scan, not
  a guarantee that all possible sensitive data is detectable.
- The source ZIP omits **all Git history**. This is why it is suitable for a new
  public repository while direct publication/mirroring of the original checkout
  is not the recommended path. No history was rewritten, source staged, project
  committed or remote created by preparation.

## Changes made for publication

Expanded `.gitignore` covers environment variants, Streamlit secrets, keys,
databases, logs, private exports and local tool/configuration directories. An
already-tracked private file still fails the audit: ignore rules are not a repair
for Git history. The exporter checks actual bytes again before writing and
rejects unsafe links, outside-root files and existing destination archives.

The README is now a concise, research-facing overview with architecture, setup,
implemented/unfinished capabilities and evaluation limitations. Older notes are
preserved in `docs/development-history.md`. Added security/contribution policies,
data-scope attribution, a synthetic walkthrough and explicit upload instructions.
No broad reuse license was granted automatically. Existing code/data ownership
and provider terms remain relevant even when source is visible publicly.

CI has read-only repository permissions, a publication-audit step and explicit
disabled-AI/session-only/withheld-market settings. It still runs Python 3.11/3.12
UI/API tests; remote execution is unconfirmed until a GitHub repository exists.

## Verification

TDD publication checks first failed on the absent audit module, then passed.
Further tests caught URL false positives and distinguish a clean snapshot from
retained sensitive history. Tests exercise tracked private-file rejection,
deleted historical tokens, exact-value redaction, archive exclusions and
publication-path rules using synthetic repositories and fake values.

Focused verification: **23 passed**, four dependency warnings, 12.29 seconds,
`output/tests/public-preparation-focused.log`. This includes the previously
unfinished ranking/cost UI work; its earlier integration attempt was blocked by
an automatic approval-review usage limit on November 7. That action was not
executed then; the November 10 run completed. The previous full regression was
618 passed.

Clean-source full verification: **642 passed, zero skipped**, 55 dependency
warnings, 68.75 seconds, `output/tests/public-clean-source-final.log`. This ran
from the extracted source package without `.env` or provider caches, with UI/API
checks enabled and safe session-only/disabled-AI/withheld-market defaults. It
reused the installed virtual environment; a fresh dependency installation and
remote Linux CI were not claimed. `pip check` found no broken requirements.

After that run, one additional audit-only root guard was added with a failing
test: auditing a nested folder must not silently inspect a parent repository.
Final targeted publication safeguards: **18 passed**, 4.29 seconds,
`output/tests/repository-safety-final.log`. No application models changed in that
final guard. An earlier clean-source run passed 641 tests; the next full run
included the added first-commit case. Full runs were repeated only for those
new safety cases. Browser/novice usability and investment performance remain
outside these software checks.

The final upload artifact is
`output/public-release/investment-research-workbench-source.zip`. Its manifest
is verified against every included source file and omits all Git history. Use
that snapshot in a new public repository, not the original checkpoint history.

Use the final source-only ZIP and `PUBLIC_SOURCE_MANIFEST.json`, following
`docs/public-upload.md`. The manifest lists source hashes and sizes; it is not
an authorship signature or legal/security certification. Generated artifacts and
local audit logs remain under ignored `output/`.
