# Upload the clean public source

The recommended first upload is the generated source-only ZIP under the ignored
`output/public-release/` directory. Extract it into a **new folder** and create a
new repository there. It includes a file-hash manifest and excludes `.git`, local
credentials, cached provider data, private exports and databases. Do not upload
the original workspace folder or use `git push --mirror`.

The original checkout contains local checkpoint references and author-contact
metadata; its retained history is intentionally not rewritten. A clean source
snapshot lets the public project begin without those local records. Keep this
working checkout for ongoing development and do not delete it.

1. Review `docs/publication-readiness.md` and the archive manifest.
2. Extract the ZIP into a new folder. Confirm `.env`, `data_cache/`, `output/`
   and `.git/` are absent. Run the publication audit after initializing Git.
3. Create an empty **public** GitHub repository. Avoid adding a second README,
   ignore file or license when using the prepared source.
4. Use GitHub Desktop's **Add local repository / Publish repository**, or initialize
   Git in the extracted folder and push a new `main` branch. Check the destination
   carefully and use a GitHub no-reply commit email if desired.
5. Enable secret scanning/push protection and private vulnerability reporting
   where available. Watch the first CI run; local test results are not proof that
   GitHub Actions has succeeded.
6. Use the synthetic walkthrough in lab applications. Add screenshots only after
   checking that they contain fictional inputs and no private/provider-only data.

The automated preparation command is:

```bash
python tools/prepare_public_repository.py --report output/audits/public-repository-audit.json --export output/public-release/investment-research-workbench-source.zip
```

Use a new ZIP filename for each export; the exporter refuses to overwrite an
existing archive. A historical finding can block direct publication of the
original history while the clean current-source snapshot passes. Inspect both
statuses; do not bypass real worktree findings. Do not run `git add .` in the
original workspace as a substitute for reviewing the prepared snapshot.

No remote repository, commit, push or public application deployment is created by
this preparation command. No general reuse license is added automatically; public
visibility and granting reuse permissions are separate decisions.
