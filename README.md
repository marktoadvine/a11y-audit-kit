# a11y-audit-kit

A plug-and-play setup for humans or agents to run Pa11y, and convert the report.json into a digestible
markdown, using a python script.

This repository runs automated accessibility checks on your selected pages using
[Pa11y CI](https://github.com/pa11y/pa11y-ci).
Pa11y offers a sitemap.xml crawl, but this process keeps things manual and
targeted for efficient testing within internal teams and reporting.

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

The agent picks up the skill on its own, runs the audit at both desktop and
mobile, writes the markdown digest, and hands back findings ranked into draft
tickets. Nothing to configure.

You are pointing the tool at **live URLs**, so the site being audited has
nothing to do with the folder you are in. You never need to be inside your
website's own repository.

### One command

If you would rather run it yourself, `scripts/run_audit.py` does the whole
flow — both viewports, then the digest — from a list of URLs:

```bash
git clone https://github.com/marktoadvine/a11y-audit-kit
cd a11y-audit-kit
python3 scripts/run_audit.py --check https://example.com/
python3 scripts/run_audit.py --out audit.md https://example.com/ https://example.com/about-us/
```

`--check` preflights first: Node, Chromium, proxy settings and whether each URL
is actually reachable from this machine. It is worth the two seconds, because
it catches the things that otherwise fail a full run halfway through.

The script resolves Chromium's launch flags, an already-installed browser and
proxy settings on its own. See [Proxies and TLS
interception](#proxies-and-tls-interception) if you are behind one.

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
Both are checked below.

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

3. Go to the folder holding the config you want to run, `configs/desktop` or
   `configs/mobile`.

   Tip: On a MacOS, type `cd ` with a space after it. Drag that folder from Finder into Terminal, then press Return.

   ```bash
   cd configs/desktop
   ```

4. Run:

   ```bash
   npx pa11y-ci@latest
   ```

Pa11y CI reads the `.pa11yci.json` in the folder you run it from, and audits
every URL in that file's `"urls"` list.

> **Run it from the right folder.** Pa11y CI only looks in the current folder,
> and this repository keeps its configs in `configs/desktop` and
> `configs/mobile` rather than at the top level. Run it from the repository
> root and it finds no config, audits nothing, and still prints
> `✔ 0/0 URLs passed` with a success exit code — a pass that means the opposite
> of what it looks like. `scripts/run_audit.py` takes URLs as arguments and
> avoids this entirely.

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

1. Open the config you are running — `configs/desktop/.pa11yci.json` or
   `configs/mobile/.pa11yci.json` — in a code editor. They hold separate URL
   lists, so keep them in step if you run both.

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

### Using it away from this folder

The skill generates its own Pa11y configs rather than reading them from
`configs/`, so the only files it needs from this repository are
`scripts/run_audit.py` and `scripts/pa11y_digest.py` — two Python files with no
dependencies beyond a stock Python 3. Keep them together; the runner calls the
digest script and looks for it beside itself.

That makes three more ways to use it, on top of cloning and working inside this
folder:

| Want | Do this |
| --- | --- |
| It available in every project, no clone | Copy `skills/a11y-audit/SKILL.md` into your agent's personal skills folder, and set `A11Y_AUDIT_KIT_DIR` to a clone of this repository |
| It to live alongside your own app, for example in CI | Copy `skills/a11y-audit/SKILL.md`, `scripts/run_audit.py` and `scripts/pa11y_digest.py` into your project, add a pointer to your `AGENTS.md`, and keep `LICENSE` alongside them |
| A one-off audit, any agent | Paste the contents of `skills/a11y-audit/SKILL.md` into the chat and give it your URLs |

`A11Y_AUDIT_KIT_DIR` is how the skill finds the digest script when the working
directory is somewhere else. If it is not set, the skill looks in the working
directory, then alongside itself, then asks.

Nothing a run produces is written into this repository or your working
directory. Pa11y's configs and raw JSON go to a temp directory, and only the
digest is written where you ask for it.

## Proxies and TLS interception

Sandboxed agent environments — Codex, Claude Code on the web, most CI
containers — send outbound HTTPS through a proxy that re-terminates TLS. Your
shell tools are usually given that proxy's CA certificate, but Chromium keeps
its own trust store and does not inherit it. Every page load then fails with:

```text
Error: net::ERR_CERT_AUTHORITY_INVALID
```

The digest reports those pages as **failed to load**, not as findings, which is
correct but easy to misread as a clean site.

Point `run_audit.py` at the proxy's CA and it pins that one key:

```bash
python3 scripts/run_audit.py --proxy-ca /path/to/proxy-ca.crt --out audit.md https://example.com/
```

Set `A11Y_PROXY_CA` to make it the default. The certificate is whatever file
the environment already handed your other tools — check `$SSL_CERT_FILE`,
`$NODE_EXTRA_CA_CERTS` or `$CURL_CA_BUNDLE`. If one of those points at a file
holding a single certificate, `run_audit.py` picks it up on its own. A
multi-certificate bundle is left alone on purpose: pinning every public root
would weaken certificate checking for every site you visit.

This pins one CA rather than passing `--ignore-certificate-errors`, which turns
off certificate checking altogether. Prefer the narrow fix.

Two other things that bite in the same environments, both handled by
`run_audit.py` already:

- Chromium refuses to start as root without `--no-sandbox`.
- Puppeteer downloads its own Chromium (~150MB) per run unless pointed at an
  installed one. The script checks `$PUPPETEER_EXECUTABLE_PATH`, `$CHROME_PATH`,
  `$PLAYWRIGHT_BROWSERS_PATH` and the usual system locations.

If a host is blocked by policy rather than TLS, preflight says so plainly:

```text
url https://example.com/  unreachable: Tunnel connection failed: 403 Forbidden
```

That is an egress rule, not a bug in the audit. Run it somewhere with access —
the [cloud workflow](CLOUD_AUDIT.md) is one option.

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

Rule codes like `WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail` come from
HTML_CodeSniffer by way of Pa11y, at run time. None of that text is stored here.
