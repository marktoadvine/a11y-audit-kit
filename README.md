# a11y-audit-kit

A repeatable, agent-assisted accessibility audit workflow built around
[Pa11y CI](https://github.com/pa11y/pa11y-ci). Give a coding agent a targeted list
of URLs and a defined procedure guides it through desktop/mobile scans,
coverage review, a readable digest, and draft remediation tickets.

Pa11y performs the automated checks. A dependency-free Python script handles
report grouping and counts. The agent assists with interpretation and drafting;
a person verifies findings and decides what to fix or file.

This is a workflow and reporting kit, not a new accessibility scanner or an
autonomous compliance assessment. You can also run the scans and digest by hand.

## See the complete handoff

Start with the [worked example](examples/digest/README.md): raw desktop/mobile
reports, a [combined digest](examples/digest/audit.md), and an
[illustrative review and ticket handoff](examples/digest/handoff.md).
These are synthetic examples, not evidence of a live scan or cross-agent validation.

| Stage | Responsibility |
| --- | --- |
| Configure and run | Agent follows the canonical procedure for the supplied URLs |
| Count and group | Python preserves occurrences and their run labels |
| Review coverage | Agent surfaces failed checks and verifies intended pages where possible |
| Propose work | Agent drafts evidence-linked tickets, with assumptions marked |
| Verify and approve | Human confirms findings and authorizes any filing |

## Quick start

Two ways to use this, depending on whether you want to drive it or have an agent
drive it.

### With a coding agent

```bash
git clone https://github.com/marktoadvine/a11y-audit-kit
cd a11y-audit-kit
```

(You can also open the clone directly in your Claude/Codex/etc desktop app, rather than using CLI).

Open your coding agent in that folder and ask, in plain words:

> Audit these URLs for accessibility: example.com, example.com/about-us

Agents that support the repository's discovery files can find the procedure
automatically. Otherwise, ask the agent to read `skills/a11y-audit/SKILL.md`
first. It generates the configs, runs both viewports, builds the digest, and
drafts findings for review. Runtime installation and permissions may still
need your attention; compatibility has not been verified across every agent.

You are pointing the tool at **live URLs**, so the site being audited has
nothing to do with the folder you are in. You never need to be inside your
website's own repository.

### By hand

```bash
git clone https://github.com/marktoadvine/a11y-audit-kit
cd a11y-audit-kit/configs/desktop
# put your URLs in .pa11yci.json, then:
npx pa11y-ci@latest
python3 ../../scripts/pa11y_digest.py reports/pa11y-desktop-results.json ../../reports/audit.md
```

The rest of this README covers that route in detail.

You need [Node.js](https://nodejs.org/) either way, and Python 3 for the digest.
Check both below. If Chromium cannot run locally, see the
[GitHub Actions route](CLOUD_AUDIT.md). That route generates reports, not tickets;
an agent or person still needs to review and triage them.

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
python3 --version
```

Use an even-numbered Node.js release supported by the Pa11y CI version you run
(the included cloud workflow uses Node 22), plus Python 3. The scan also needs
Chromium and its system libraries, network access to the supplied URLs, and
permission to run the tools. A version number alone does not verify those.

## Run the audit

1. Download or clone this repository.

2. Open Terminal.

3. From the repository root, run `cd configs/desktop` and edit that folder's
   `.pa11yci.json` with your URLs. For a mobile scan, use `configs/mobile` instead.

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

Run this from the chosen viewport folder. It creates `pa11y-results.json` there.

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
both a person and a chat agent can read, grouped by rule to support review and remediation planning. A group can require
multiple fixes across unrelated components.

Run the following digest commands from the repository root, after the scans
have written their reports. For a single report:

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

- Unique URLs successfully tested and successful page checks across runs.
- Failed URL/run combinations, excluded from successful checks and findings.
  A URL can succeed in one viewport and fail in another.
- A summary by rule, including the standard prefix and success criterion parsed
  from HTML_CodeSniffer codes. Axe slugs leave these fields blank. The prefix
  identifies the test standard, not the criterion's level or user-impact severity.
- Occurrences organized by rule and by page, retaining every run's evidence.

Desktop/mobile occurrences are grouped, **not deduplicated**. Counts include
both runs; review the affected components before deciding how many fixes or
tickets are needed. Rules sort by reported type, then occurrence count and code;
this display order is not a remediation priority assessment.

An occurrence ID repeats while its rule, run label, URL and selector stay the
same. Keep explicit run labels consistent for comparisons. Changes to those
fields change the ID; identical fields share an ID, and selectors can change
with the DOM. IDs are references, not automatic regression tracking.

See the [worked example](examples/digest/README.md) for raw inputs and a rendered
digest. Run the dependency-free tests from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

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

### Using it away from this folder

The skill generates its own Pa11y configs rather than reading them from
`configs/`, so the only file it needs from this repository is
`scripts/pa11y_digest.py` — one Python file with no dependencies beyond a stock
Python 3.

That makes three more ways to use it, on top of cloning and working inside this
folder:

| Want | Do this |
| --- | --- |
| It available in every project from one shared clone | Copy `skills/a11y-audit/SKILL.md` into your agent's personal skills folder, and set `A11Y_AUDIT_KIT_DIR` to a clone of this repository |
| It to live alongside your own app, for example in CI | Copy `skills/a11y-audit/SKILL.md` and `scripts/pa11y_digest.py` into your project, add a pointer to your `AGENTS.md`, and keep `LICENSE` alongside them |
| A one-off audit, any agent | Paste the contents of `skills/a11y-audit/SKILL.md` into the chat and give it your URLs |

`A11Y_AUDIT_KIT_DIR` is how the skill finds the digest script when the working
directory is somewhere else. If it is not set, the skill looks in the working
directory, then alongside itself, then asks.

In the agent procedure, configs and raw JSON go to a temp directory; the digest
is written to your chosen output location. Manual runs use the configured report
paths. Preserve raw reports if you need an evidence archive beyond the temp run.

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

## License

MIT. See [LICENSE](LICENSE). Use it, change it, copy it into your own projects,
commercially or otherwise; just keep the copyright notice with it.

`scripts/pa11y_digest.py` carries an SPDX header so the license travels with it
when it is vendored on its own.

### Third-party tools

This repository does not bundle Pa11y. `npx pa11y-ci@latest` fetches it at run
time, and [Pa11y](https://github.com/pa11y/pa11y) and
[Pa11y CI](https://github.com/pa11y/pa11y-ci) are licensed `LGPL-3.0-only` by
their own authors.

That license governs Pa11y, not this repository. Nothing here links to or
includes Pa11y source: the configs are data it reads, and the digest script
parses the JSON it prints. Running a separately installed program and reading
its output does not make this a derivative work of it.

Live rule codes come from the selected runner by way of Pa11y. The worked
example includes representative codes and explicitly synthetic messages for
demonstration and testing.
