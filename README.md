# pa11y snake
# A plug-and-play setup to run Pa11y and convert the report.json into a digestible markdown, using a python script.

This repository runs automated accessibility checks on your selected pages using [Pa11y CI](https://github.com/pa11y/pa11y-ci).
Pa11y offers a sitemap.xml crawl, however, this snake process keeps things manual and targetted for efficient testing within internal teams and reporting.

## What does it do?

Pa11y CI checks the URLs listed in `.pa11yci.json` and reports potential accessibility issues.

It can help identify issues with:

- Alternative text
- Form labels
- Heading structure
- Color contrast
- ARIA and landmarks
- Keyboard-accessible controls

Automated results are a starting point—not a final accessibility decision. Review all findings manually and verify against [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Before you start

You need [Node.js](https://nodejs.org/) installed.

Open Terminal and run:

```bash
node --version
```

If you see a version number, you are ready.

## Run the audit

1. Download or clone this repository.

2. Open Terminal.

3. Go to the repository folder.

   Tip: On a MacOS, type `cd ` with a space after it. Drag the repository folder from Finder into Terminal, then press Return.

4. Run:

   ```bash
   npx pa11y-ci@latest
   ```

Pa11y CI automatically reads `.pa11yci.json` and audits every URL in its `"urls"` list.

To stop the audit early, press:

```text
Control + C
```

## Export results

To save results as a JSON file, run:

```bash
npx pa11y-ci@latest --json > pa11y-results.json
```

This creates `pa11y-results.json` in the repository folder.

Running the command again replaces the existing report. To keep a dated copy:

```bash
npx pa11y-ci@latest --json > pa11y-results-2026-08-17.json
```

## Add or remove URLs

1. Open `.pa11yci.json` in a code editor.

2. Add or remove URLs inside the `"urls"` list.

Example:

```json
{
  "urls": [
    "https://www.websitename.com/",
    "https://www.websitename.com/about-us"
  ]
}
```

Important:

- Put every URL inside double quotes.
- Add a comma after each URL except the final URL.
- Save the file before running the audit.

## Make the markdown digest

Pa11y CI writes JSON. The Python script turns it into a markdown digest that
both a person and a chat agent can read, grouped so that one entry is one unit
of remediation work rather than one per occurrence.

Run it on a single report:

```bash
python3 scripts/pa11y_digest.py --out reports/audit.md configs/desktop/reports/pa11y-desktop-results.json
```

Or merge the desktop and mobile runs into one digest, labelling each run:

```bash
python3 scripts/pa11y_digest.py \
  desktop=configs/desktop/reports/pa11y-desktop-results.json \
  mobile=configs/mobile/reports/pa11y-mobile-results.json \
  --out reports/audit.md
```

Each input may be given as `LABEL=PATH`. A bare path takes its label from the
filename.

The digest contains:

- A summary of pages tested, findings by type, and distinct rules.
- Any pages that **failed to load**, listed separately. Those pages were never
  audited, so the headline counts do not cover them.
- A summary table of one row per rule, with the WCAG conformance level and
  success criterion parsed out of the rule code so findings can be ranked by
  severity rather than only by count.
- Findings by rule, and again by page, with a short stable id per occurrence so
  a rerun can tell a reopened issue from a new one.

A note on reading the output: the same issue found at both viewports is one
unit of work, not two. The digest merges those, and the `Runs` column shows
which viewports each rule appeared in.

## Run it from a chat agent

`skills/a11y-audit/SKILL.md` packages the whole flow: hand an agent a list of
URLs and it writes throwaway configs, runs both viewports, builds the digest,
then ranks the findings into draft tickets for Jira, Hive or similar.

The skill deliberately stops at drafts and does not file anything. Filing is a
separate step you ask for after reading them.

It needs a shell, Node.js, and network access to the target URLs, so it works
in agents with a real terminal and not in browser-only chat.

### Any agent can use it

The skill is plain markdown in a vendor-neutral directory, so it is not tied to
one tool. What differs between agents is only how they *find* it, and there is
no shared convention for that yet, so the repository points each one at the same
canonical file:

| File | Read by |
| --- | --- |
| `skills/a11y-audit/SKILL.md` | The procedure itself. Edit this one. |
| `AGENTS.md` | Codex, Cursor, Gemini CLI, Jules and others that follow the AGENTS.md convention |
| `.claude/skills/a11y-audit/SKILL.md` | Claude Code, which auto-discovers skills under `.claude/skills/` |

The last two are pointers containing no procedure. To use the skill from an
agent that reads neither, point it at `skills/a11y-audit/SKILL.md` directly, or
just paste that file in — it is written to be followed by any agent with a
shell, and assumes nothing about the tool running it.

## Review findings

For each Pa11y CI finding:

1. Open the reported URL in a browser.
2. Confirm the issue manually.
3. Identify the affected component or page template.
4. Fix the issue in your design and codebase.
5. After deployment, manually retest and rerun the audit.

## Notes

- The audit checks only URLs listed in `.pa11yci.json`.
- It does not crawl the whole website or follow links automatically.
- Pa11y CI exits with a non-zero status when it finds accessibility issues.
  That is a successful run reporting findings, not a broken run. Review the
  reported findings.
- A 404 or login page often returns a simple, accessible error page, which the
  audit scores as a clean pass. If a page reports no findings when its siblings
  report many, check that the URL resolved to the page you expected.
- The audit uses the latest Pa11y CI version, so results may change after future tool updates.

## Helpful commands

Check your current folder:

```bash
pwd
```

See all files, including hidden files:

```bash
ls -la
```

Check the Pa11y CI version:

```bash
npx pa11y-ci@latest --version
```

View Pa11y CI options:

```bash
npx pa11y-ci@latest --help
```

Open a specific file in Terminal editor:

```bash
nano filenamehere.json
```