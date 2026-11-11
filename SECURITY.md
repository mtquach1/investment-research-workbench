# Security and private data

This is a local research prototype. It has not passed a production security audit
and does not provide authenticated multi-user financial accounts. Keep the API
and Streamlit server on loopback. Publishing the code does not authorize hosting
a public service with local history or real-data access enabled.

Safe defaults disable database-history routes, external AI and local market-data
display. Optional local history is unauthenticated. Enabling AI explicitly allows
submitted text/metrics to be sent to an external provider; it is not needed for
the deterministic models or public synthetic demonstration.

Never commit `.env`, keys, `.streamlit/secrets.toml`, provider caches, private
exports, logs or local databases. Run `python tools/prepare_public_repository.py`
before publication. Its pattern/exact-value checks reduce accidental exposure;
they are not a guarantee that every secret, personal detail or vulnerability can
be detected. `.gitignore` does not remove files already tracked in Git.

Do not put credentials or personal financial information in an issue or pull
request. If private vulnerability reporting is enabled on the eventual GitHub
repository, use that channel; otherwise arrange a private channel with the owner
before sharing sensitive details. No hosted reporting channel is configured in
this local checkout. Rotate any credential that has actually been exposed.
