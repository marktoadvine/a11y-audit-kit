---
name: a11y-audit
description: Run a Pa11y accessibility audit over a list of URLs and turn the results into a grouped markdown report and draft remediation tickets. Use when the user supplies URLs or a site to audit for accessibility, asks for a Pa11y or a11y or WCAG audit, asks to check pages for accessibility issues, or asks to turn accessibility findings into Jira/Hive/Linear tickets. Requires a shell with Node.js and network access to the target URLs.
---

# Accessibility audit

Audit a set of URLs with Pa11y CI, merge the results into one markdown digest,
then triage the digest into draft tickets.

The digest is the human-readable artifact. The triage is the part that needs
judgment: deciding which findings are one underlying pattern, which are
template-level rather than page-level, and which are worth a ticket at all.

This skill audits **deployed URLs**, not local code. The working directory does
not have to be the site being audited, or related to it at all.

## Before you start

This skill needs a shell, Node.js, and network access to the target URLs. If
any of those is missing, say so rather than producing a partial result.

Ask for the URL list if the user has not supplied one. Do not invent URLs and
do not crawl for more: this tool is deliberately targeted, and auditing pages
the user did not ask for wastes their review time.

Confirm before auditing anything that is not obviously the user's to test — a
production site belonging to someone else, or a URL behind a login.

## Steps

### 1. Locate the digest script

The only file this skill needs is `pa11y_digest.py`, a single dependency-free
Python script from the a11y-audit-kit repository. Resolve its path first, in this
order, and reuse the result as `$DIGEST` throughout:

1. `$A11Y_AUDIT_KIT_DIR/scripts/pa11y_digest.py`, if that variable is set.
2. `./scripts/pa11y_digest.py`, if the working directory is the a11y-audit-kit
   repository.
3. Relative to this skill file, if you read it from disk. The repository root
   is two levels above `skills/a11y-audit/`.
4. Otherwise ask the user where the repository is, or offer to clone it:
   `git clone https://github.com/marktoadvine/a11y-audit-kit`

Confirm the path exists before running the audit. Finding out after a
multi-page scan that the results cannot be processed wastes the whole run.

### 2. Set up a run directory

Everything the audit writes goes in a throwaway directory, so a run never
touches the working directory or the repository:

```bash
RUN_DIR="$(mktemp -d)"
mkdir -p "$RUN_DIR/reports"
```

### 3. Write one config per viewport

Write these configs yourself — do not read them from `configs/`, which holds
the human-facing copies for manual runs and may not be present at all.

Pa11y CI resolves a relative reporter `fileName` against the **current working
directory**, not the config file, so use an absolute path.

```json
{
  "defaults": {
    "timeout": 30000,
    "wait": 2000,
    "viewport": { "width": 1440, "height": 800 },
    "reporters": [
      "cli",
      ["json", { "fileName": "$RUN_DIR/reports/pa11y-desktop-results.json" }]
    ]
  },
  "urls": [
    "https://example.com/",
    "https://example.com/about-us/"
  ]
}
```

Write that to `$RUN_DIR/.pa11yci-desktop.json` with the user's URLs and the
real absolute path expanded. For mobile, write the same file to
`$RUN_DIR/.pa11yci-mobile.json` with the output name changed to
`pa11y-mobile-results.json` and this viewport:

```json
"viewport": { "width": 390, "height": 812, "isMobile": true, "deviceScaleFactor": 2 }
```

`deviceScaleFactor` is camelCase. Puppeteer silently ignores unknown viewport
keys, so a lowercase spelling means the run is at 1x and nothing warns you.

Run both viewports unless the user asks for one. Mobile finds different issues
— reflow, touch target spacing, menus that only exist at small widths — and the
digest merges them, so the second run is cheap.

Keep the 2 second `wait`. It is what lets client-rendered pages settle before
the scan; dropping it produces false "missing content" findings.

### 4. Run the audit

```bash
npx pa11y-ci@latest --config "$RUN_DIR/.pa11yci-desktop.json"
npx pa11y-ci@latest --config "$RUN_DIR/.pa11yci-mobile.json"
```

**Pa11y CI exits non-zero when it finds accessibility issues.** That is a
successful run reporting findings, not a failure. Only treat it as an error if
no JSON report was written, or the output shows a launch or config error.

If Chromium fails to launch (common in containers and CI), add a launch config
to the `defaults` block rather than giving up:

```json
"chromeLaunchConfig": {
  "args": ["--no-sandbox", "--disable-dev-shm-usage"]
}
```

If the environment already has a browser installed, add its `executablePath` to
that same block instead of letting Puppeteer download one.

### 5. Build the digest

```bash
python3 "$DIGEST" \
  desktop="$RUN_DIR/reports/pa11y-desktop-results.json" \
  mobile="$RUN_DIR/reports/pa11y-mobile-results.json" \
  --out "a11y-audit-$(date +%F).md"
```

The script groups by rule code, parses the WCAG level and success criterion out
of each code, and merges both viewports.

Write the digest somewhere the user will keep it, not in the temp directory, and
tell them the path. If the working directory is not somewhere they would want a
file, ask where to put it.

### 6. Check coverage before reporting

Read the **Pages that failed to load** section first. Those pages were never
audited, so the headline counts do not cover them. Report them before the
findings — an audit that silently skipped a third of the site is misleading,
and "0 findings" on an unreachable page reads like a pass.

Also sanity-check that each URL returned the page you expected. A 404 or a
login wall often returns a simple, *accessible* error page, which Pa11y scores
as a clean pass. A page reporting zero findings when its siblings report many is
the signal to check the URL resolved.

### 7. Triage into draft tickets

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

Flag anything automation cannot settle. Pa11y checks what is machine checkable;
it cannot judge whether alt text is *accurate*, whether a heading order is
*logical*, or whether a focus order makes sense. Say which findings need a human
pass rather than implying the list is complete.

### 8. Stop and show the drafts

Present the digest path and the draft tickets. **Do not file them.**

Creating tickets is outward-facing and hard to undo, and a mis-triaged batch
costs more to clean up than to review. Filing is a separate, explicit step the
user asks for after reading the drafts.

## Reporting

Give the user, briefly:

- Where the digest is.
- Pages that failed to load, if any.
- The finding counts by type, and how many distinct rules.
- The ranked ticket drafts.
- What still needs manual review.

Do not claim a site is accessible or compliant. Automated checks cover a
minority of WCAG criteria. The honest framing is what was checked, what it
found, and what it cannot tell you.
