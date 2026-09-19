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

The workflow does not contain default targets, commit submitted URLs, or publish reports. URLs are provided only at run time. Pa11y findings may make its process exit nonzero; the workflow treats the run as successful when the expected JSON report was produced.
