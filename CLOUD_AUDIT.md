# Run an accessibility audit in GitHub Actions

Use the cloud workflow when Chromium cannot run in your local or agent environment.

1. Open **Actions** in your fork or repository.
2. Select **Cloud accessibility audit**.
3. Choose **Run workflow**.
4. Enter one complete `http://` or `https://` URL per line.
5. When the run finishes, download its `a11y-audit-<run id>` artifact.

The artifact is retained for 14 days and contains:

- `pa11y-desktop-results.json`
- `pa11y-mobile-results.json`
- `a11y-audit.md`

The workflow does not contain default targets or commit submitted URLs. URLs
are provided at run time, but may appear in Actions logs and artifacts; their
visibility follows repository access. Do not submit sensitive URLs or credentials.

Pa11y findings may make its process exit nonzero. The workflow requires report
files and a successful digest conversion; this confirms report generation, not
complete coverage or accessibility. Read failed checks in the digest even when
the workflow is green. It does not generate or file tickets: give the reports to
your agent for coverage review and draft triage, or review them yourself.
