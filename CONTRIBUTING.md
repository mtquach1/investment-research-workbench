# Contributing

Use Python 3.11+ and the setup in the README. Keep development synthetic/offline
unless a task explicitly needs separately authorized data. No paid service or
API key should be required for a test.

- Write a failing behavior/reference test before a functional change.
- Keep missing evidence distinct from observed financial failure. Never relax
  a gate to make an example produce a recommendation.
- Preserve original inputs, exact cent accounting, dated provenance and explicit
  experimental/verified boundaries.
- Use plain labels, units and dates; put technical detail in optional help.
- Run focused tests during development and integration tests for affected flows.
- Run the publication audit before committing. Never add real credentials,
  personal financial records or provider caches, even for a failing test.
- State what changed, how it was checked and which limitations remain. Do not
  imply investment performance from a test suite or hypothetical scenario.

External AI, database history and market-data access stay disabled in CI. Provider
network refreshes are explicit operator workflows, not normal test setup. Public
deployment and a general reuse license are separate decisions.
