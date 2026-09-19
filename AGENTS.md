# AGENTS.md

Guidance for any coding agent working in this repository.

## What this repository is

A targeted accessibility audit harness. Pa11y CI checks a hand-picked list of
URLs, and `scripts/pa11y_digest.py` converts the JSON results into a markdown
digest that is readable by both a person and an agent, grouped so that one
entry is one unit of remediation work rather than one per occurrence.

The audit is deliberately **not** a crawl. It checks only the URLs it is given.

## Layout

| Path | What it is |
| --- | --- |
| `skills/a11y-audit/SKILL.md` | The audit procedure. Canonical copy. |
| `scripts/run_audit.py` | One-command runner: preflight, both viewports, digest. |
| `scripts/pa11y_digest.py` | JSON to markdown digest converter. |
| `configs/desktop/.pa11yci.json` | Desktop viewport config, for manual runs only. |
| `configs/mobile/.pa11yci.json` | Mobile viewport config, for manual runs only. |
| `.claude/skills/a11y-audit/` | Pointer to the canonical skill. No procedure. |

## Running an audit

Read **`skills/a11y-audit/SKILL.md`** and follow it. It is written for any
agent with a shell and is the single source of truth for this workflow; this
file only summarises it.

In short:

```bash
python3 scripts/run_audit.py --check URL...            # preflight, ~2 seconds
python3 scripts/run_audit.py --out audit.md URL...     # both viewports + digest
```

then rank the findings into draft tickets. `run_audit.py` writes the throwaway
configs, resolves Chromium and proxy settings, runs both viewports and builds
the digest. Do not hand-roll those steps unless it cannot run; the skill has
the manual fallback at the bottom.

The skill needs two files from this repository, `scripts/run_audit.py` and
`scripts/pa11y_digest.py`, and writes its own Pa11y configs. If the working
directory is not this repository, `A11Y_AUDIT_KIT_DIR` points at a clone of it.

## Things that will mislead you

- **Pa11y CI exits non-zero when it finds accessibility issues.** That is a
  successful run reporting findings, not a failure. Only treat it as an error
  if no JSON report was written or the output shows a launch or config error.
- **Never write the user's URLs into `configs/`.** Those files exist for people
  running Pa11y by hand. Editing them dirties the repo on every run. Generate
  configs into a temp directory instead; the skill contains the JSON to write.
- **The audit targets deployed URLs, not local code.** The working directory has
  no relationship to the site being audited, and need not be this repository.
- **Pa11y CI resolves a relative reporter `fileName` against the current
  working directory**, not the config file. Use absolute paths in generated
  configs.
- **A 404 or login wall often returns a simple, accessible error page**, which
  the audit scores as a clean pass. A page reporting zero findings while its
  siblings report many is the signal to check that the URL resolved.
- **A page that failed to load was never audited.** The digest lists those
  separately. Report them before the findings; the headline counts do not
  cover them.
- **Chromium often needs a launch config** in containers and CI. Add
  `chromeLaunchConfig` with `--no-sandbox` and `--disable-dev-shm-usage`
  rather than giving up. `run_audit.py` always sets both.
- **A TLS-intercepting proxy fails every page load** with
  `ERR_CERT_AUTHORITY_INVALID`, because Chromium does not inherit the trust
  your shell tools were given. Pass `--proxy-ca` with the proxy's certificate,
  which pins that one key. Never disable certificate checking to get past it.
- **Preflight before auditing.** `run_audit.py --check URL...` reports Node,
  Chromium, the proxy and per-URL reachability in one pass. A blocked host or
  a missing browser is much cheaper to find there than halfway through a run.

## Conventions

- Do not file tickets. Produce drafts and stop. Filing is outward-facing and
  hard to undo, so it is a separate step the user asks for after reading them.
- Do not claim a site is accessible or compliant. Automated checks cover a
  minority of WCAG criteria. Report what was checked, what it found, and what
  it cannot tell you.
- Do not add URLs the user did not ask for, and confirm before auditing
  anything that is not obviously theirs to test.
- Keep `scripts/run_audit.py` and `scripts/pa11y_digest.py` dependency-free.
  They run on a stock Python 3 install so that no setup step stands between a
  user and their report.
