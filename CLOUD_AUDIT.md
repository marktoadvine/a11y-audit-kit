# Run an accessibility audit in GitHub Actions

Use the cloud workflow when the audit cannot run where you are: Chromium will
not start, or your environment's egress policy blocks the sites you need to
reach. `python3 scripts/run_audit.py --check URL...` tells you which of those
you are looking at before you resort to this.

1. Open **Actions** in your fork or repository.
2. Select **Cloud accessibility audit**.
3. Choose **Run workflow**.
4. Enter one complete `http://` or `https://` URL per line.
5. When the run finishes, read the digest in the run's summary page. Download
   the `a11y-audit-<run id>` artifact if you also want the raw JSON.

The artifact is retained for 14 days and contains:

- `pa11y-desktop-results.json`
- `pa11y-mobile-results.json`
- `a11y-audit.md`

The workflow does not contain default targets, commit submitted URLs, or publish reports. URLs are provided only at run time. Pa11y findings may make its process exit nonzero; the workflow treats the run as successful when the expected JSON report was produced.
