---
name: a11y-audit
description: Run a Pa11y accessibility audit over a list of URLs and turn the results into a grouped markdown report and draft remediation tickets. Use when the user supplies URLs or a site to audit for accessibility, asks for a Pa11y or a11y or WCAG audit, asks to check pages for accessibility issues, or asks to turn accessibility findings into Jira/Hive/Linear tickets. Requires a shell with Node.js and network access to the target URLs.
---

# Accessibility audit

Audit a set of URLs with Pa11y CI, merge the results into one markdown digest,
then triage the digest into draft tickets.

One script does the mechanical part. Your job is the triage: deciding which
findings are one underlying pattern, which are template-level rather than
page-level, and which are worth a ticket at all.

This skill audits **deployed URLs**, not local code. The working directory does
not have to be the site being audited, or related to it at all.

## Run it

Two commands. Preflight first, because it is fast and tells you in one pass
whether the run can succeed:

```bash
python3 scripts/run_audit.py --check https://example.com/ https://example.com/about/
python3 scripts/run_audit.py --out a11y-audit.md https://example.com/ https://example.com/about/
```

`run_audit.py` writes the throwaway Pa11y configs, runs desktop and mobile,
builds the digest, and prints a summary. It resolves Chromium, sandbox flags
and proxy settings itself. Nothing is written anywhere except `--out`.

If `scripts/` is not in the working directory, set `A11Y_AUDIT_KIT_DIR` to a
clone of the a11y-audit-kit repository, or call the script by its full path.
Both scripts are stock Python 3 with no dependencies.

Useful flags: `--viewport desktop|mobile|both`, `--urls-file FILE`,
`--proxy-ca FILE`, `--chrome PATH`, `--keep`. Run with `--help` for the rest.

### Before you run

Ask for the URL list if the user has not supplied one. Do not invent URLs and
do not crawl for more: this tool is deliberately targeted, and auditing pages
the user did not ask for wastes their review time.

Confirm before auditing anything that is not obviously the user's to test — a
production site belonging to someone else, or a URL behind a login.

### When preflight fails

Read what it printed and fix that one thing. It reports Node, the digest
script, Chromium, the proxy, a pinnable proxy CA, and every URL's
reachability, so you should not need a second diagnostic run.

| Preflight says | Do this |
| --- | --- |
| `node MISSING` | Install Node.js. Nothing else will work. |
| `digest script MISSING` | Set `A11Y_AUDIT_KIT_DIR` to a clone of this repository. |
| `chromium not found` | Fine — Puppeteer downloads one. Slow on first run; install Chromium to avoid it. |
| `unreachable: Tunnel connection failed: 403` | An egress policy blocks the host. Report it; do not retry or route around it. |
| `unreachable` with any other reason | Check the URL, then whether this machine can reach the site at all. |

**Exit codes:** 0 means the digest was written. Non-zero means the run could
not produce one, or no page loaded at all. Pa11y's own non-zero exit for
finding issues is handled inside the script and is not an error.

### Proxies and TLS interception

Sandboxed agent environments usually route outbound HTTPS through a proxy that
re-terminates TLS. Chromium does not inherit that trust, so every page load
fails with `ERR_CERT_AUTHORITY_INVALID` and the digest shows pages that failed
to load rather than findings.

Point the script at the proxy's CA certificate. It pins that one key rather
than turning off certificate checking:

```bash
python3 scripts/run_audit.py --proxy-ca /path/to/proxy-ca.crt --out report.md URL...
```

Set `A11Y_PROXY_CA` instead to make it the default. The CA is whatever file the
environment already handed your other tools — check `$SSL_CERT_FILE`,
`$NODE_EXTRA_CA_CERTS` or `$CURL_CA_BUNDLE`. A single-certificate file there is
picked up automatically; a multi-certificate bundle is not, because pinning
every public root would weaken certificate checking for every site.

Never work around this by disabling TLS verification generally.

## Read the result before reporting it

Check **Pages that failed to load** first. Those pages were never audited, so
the headline counts do not cover them. Report them before the findings — an
audit that silently skipped a third of the site is misleading, and "0 findings"
on an unreachable page reads like a pass.

Also sanity-check that each URL returned the page you expected. A 404 or a
login wall often returns a simple, *accessible* error page, which Pa11y scores
as a clean pass. A page reporting zero findings when its siblings report many is
the signal to check the URL resolved. Pa11y reports the URL it ended on, so a
redirect shows up there.

## Triage into draft tickets

Work from the **Summary by rule** table. One row is one candidate ticket.

Order by what blocks users, not by count:

- **Errors before warnings before notices.** Notices are advisory and many are
  not defects.
- **Level A before AA before AAA** at equal type.
- A rule hitting many pages is usually a shared template or component. Say so
  in the ticket and name the fix site once, rather than filing per page.

For each ticket worth opening, draft:

- A title naming the success criterion and the component, not the raw rule
  code. "Nav links fail 1.4.3 contrast" beats the full `WCAG2AA.Principle1...`
  string.
- The affected URLs and selectors, from the occurrence list.
- The WCAG success criterion, so a reviewer can verify the fix.
- The occurrence fingerprints, so a rerun can tell a reopened issue from a new
  one.

Collapse a rule that appears at both viewports into one ticket, noting both.
Split one only where the fix genuinely differs by viewport.

Read the context HTML before writing the ticket. A finding on an element that
is `aria-hidden`, or on decorative text, may not be a defect at all — say so
rather than filing it.

Flag anything automation cannot settle. Pa11y checks what is machine checkable;
it cannot judge whether alt text is *accurate*, whether a heading order is
*logical*, or whether a focus order makes sense. Say which findings need a human
pass rather than implying the list is complete.

## Stop and show the drafts

Present the digest path and the draft tickets. **Do not file them.**

Creating tickets is outward-facing and hard to undo, and a mis-triaged batch
costs more to clean up than to review. Filing is a separate, explicit step the
user asks for after reading them.

Give the user, briefly: where the digest is, pages that failed to load, the
finding counts by type and how many distinct rules, the ranked ticket drafts,
and what still needs manual review.

Do not claim a site is accessible or compliant. Automated checks cover a
minority of WCAG criteria. The honest framing is what was checked, what it
found, and what it cannot tell you.

## Running the steps by hand

Only needed if you cannot run `run_audit.py` — a different runner, or a CI job
that wants each step separate. It does the following, and the fallback is to do
it yourself:

```bash
RUN_DIR="$(mktemp -d)"
mkdir -p "$RUN_DIR/reports"
```

Write one config per viewport to `$RUN_DIR/.pa11yci-<name>.json`:

```json
{
  "defaults": {
    "timeout": 30000,
    "wait": 2000,
    "viewport": { "width": 1440, "height": 800 },
    "chromeLaunchConfig": {
      "args": ["--no-sandbox", "--disable-dev-shm-usage"]
    },
    "reporters": [
      "cli",
      ["json", { "fileName": "$RUN_DIR/reports/pa11y-desktop-results.json" }]
    ]
  },
  "urls": ["https://example.com/"]
}
```

Mobile uses the same file with the output name changed to
`pa11y-mobile-results.json` and this viewport:

```json
"viewport": { "width": 390, "height": 812, "isMobile": true, "deviceScaleFactor": 2 }
```

Then run both and merge:

```bash
npx pa11y-ci@latest --config "$RUN_DIR/.pa11yci-desktop.json"
npx pa11y-ci@latest --config "$RUN_DIR/.pa11yci-mobile.json"
python3 scripts/pa11y_digest.py \
  desktop="$RUN_DIR/reports/pa11y-desktop-results.json" \
  mobile="$RUN_DIR/reports/pa11y-mobile-results.json" \
  --out a11y-audit.md
```

Four things bite here, which is why the script exists:

- Pa11y CI resolves a relative reporter `fileName` against the **current
  working directory**, not the config file. Use absolute paths.
- `deviceScaleFactor` is camelCase. Puppeteer silently ignores unknown viewport
  keys, so a lowercase spelling means the run is at 1x and nothing warns you.
- Chromium will not start as root without `--no-sandbox`.
- Keep the 2 second `wait`. It is what lets client-rendered pages settle;
  dropping it produces false "missing content" findings.

Run both viewports unless the user asks for one. Mobile finds different issues
— reflow, touch target spacing, menus that only exist at small widths — and the
digest merges them, so the second run is cheap.
