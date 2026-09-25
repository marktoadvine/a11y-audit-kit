#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mark Toadvine, @marktoadvine
"""Convert one or more Pa11y CI JSON reports into a single markdown digest.

The digest groups occurrences by rule for review. A rule group may require
multiple fixes; occurrences from different runs are retained, not deduplicated.

Usage:
    pa11y_digest.py --out REPORT.md desktop=desktop.json mobile=mobile.json
    pa11y_digest.py --out REPORT.md results.json
    pa11y_digest.py INPUT.json OUTPUT.md          (legacy two-argument form)

Each input may be given as LABEL=PATH to tag its findings with a viewport or
run label. A bare PATH takes its label from the filename.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Pa11y/HTML_CodeSniffer codes look like:
#   WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail
# Axe and other runners use plain slugs like "color-contrast", which simply
# will not match and are reported without a level or success criterion.
CODE_PATTERN = re.compile(
    r"^WCAG2(?P<level>A{1,3})"
    r"\.Principle(?P<principle>\d+)"
    r"\.Guideline(?P<guideline>[\d_]+)"
    r"\.(?P<criterion>\d+(?:_\d+)+)"
    r"(?:\.(?P<technique>.+))?$"
)

TYPE_RANK = {"error": 0, "warning": 1, "notice": 2}
CONTEXT_LIMIT = 300


def parse_code(code):
    """Pull test-standard suffix, success criterion and technique out of a code."""
    match = CODE_PATTERN.match(code)
    if not match:
        return {"level": None, "criterion": None, "technique": None}
    return {
        "level": match.group("level"),
        "criterion": match.group("criterion").replace("_", "."),
        "technique": match.group("technique"),
    }


def fingerprint(code, label, url, selector):
    """Repeatable reference while code, run label, URL and selector stay unchanged."""
    raw = "|".join([code, label, url, selector])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def clean(text, limit=None):
    """Collapse whitespace and neutralise characters that break inline code."""
    flattened = " ".join(str(text).split()).replace("`", "'")
    if limit and len(flattened) > limit:
        return flattened[:limit].rstrip() + "..."
    return flattened


def label_for(path, explicit):
    if explicit:
        return explicit
    stem = Path(path).stem
    for noise in ("pa11y-", "-results", "_results", "pa11y_"):
        stem = stem.replace(noise, "")
    return stem or "run"


def parse_inputs(raw_inputs):
    """Turn ['desktop=a.json', 'b.json'] into [(label, Path), ...]."""
    parsed = []
    for item in raw_inputs:
        explicit, _, path = item.partition("=")
        if not path:
            explicit, path = "", explicit
        parsed.append((label_for(path, explicit), Path(path)))
    return parsed


def load_reports(inputs):
    """Read every report, returning findings, load failures and run metadata."""
    findings_by_code = defaultdict(list)
    failures = []
    runs = []
    pages_seen = set()
    successful_checks = 0
    pages_with_findings = set()
    total_findings = 0

    for label, path in inputs:
        try:
            with path.open(encoding="utf-8") as handle:
                report = json.load(handle)
        except FileNotFoundError:
            sys.exit(f"Error: no such report file: {path}")
        except json.JSONDecodeError as error:
            sys.exit(f"Error: {path} is not valid JSON ({error}).")

        results = report.get("results") if isinstance(report, dict) else None
        if not isinstance(results, dict):
            sys.exit(
                f"Error: {path} has no top-level 'results' object. "
                "Expected a Pa11y CI JSON report."
            )

        runs.append({
            "label": label,
            "path": path,
            "pages": report.get("total", len(results)),
            "passes": report.get("passes", 0),
            "errors": report.get("errors", 0),
        })

        for url, issues in results.items():
            if not isinstance(issues, list) or any(
                not isinstance(issue, dict) for issue in issues
            ):
                sys.exit(f"Error: {path}: invalid results for {url}; expected a list of objects.")

            failed = any("code" not in issue for issue in issues)
            if failed:
                failures.append({
                    "label": label,
                    "url": url,
                    "message": "; ".join(
                        clean(issue.get("message", "Unknown error"))
                        for issue in issues if "code" not in issue
                    ),
                })
                continue
            pages_seen.add(url)
            successful_checks += 1

            for issue in issues:
                code = issue["code"]
                selector = issue.get("selector", "")
                findings_by_code[code].append({
                    "id": fingerprint(code, label, url, selector),
                    "label": label,
                    "url": url,
                    "type": issue.get("type", "error"),
                    "selector": selector,
                    "context": issue.get("context", ""),
                    "message": issue.get("message", "No message provided"),
                    "runner": issue.get("runner", ""),
                })
                pages_with_findings.add(url)
                total_findings += 1

    return {
        "findings_by_code": findings_by_code,
        "failures": failures,
        "runs": runs,
        "pages_seen": pages_seen,
        "successful_checks": successful_checks,
        "pages_with_findings": pages_with_findings,
        "total_findings": total_findings,
    }


def summarise_group(code, occurrences):
    """Collapse a rule's occurrences into the fields a ticket needs."""
    parsed = parse_code(code)
    types = {item["type"] for item in occurrences}
    worst = min(types, key=lambda t: TYPE_RANK.get(t, 9)) if types else "error"
    return {
        "code": code,
        "level": parsed["level"],
        "criterion": parsed["criterion"],
        "technique": parsed["technique"],
        "type": worst,
        "count": len(occurrences),
        "pages": sorted({item["url"] for item in occurrences}),
        "labels": sorted({item["label"] for item in occurrences}),
        "occurrences": occurrences,
    }


def sort_key(group):
    return (
        TYPE_RANK.get(group["type"], 9),
        -group["count"],
        group["code"],
    )


def render(data):
    groups = sorted(
        (summarise_group(code, items)
         for code, items in data["findings_by_code"].items()),
        key=sort_key,
    )
    failures = data["failures"]
    runs = data["runs"]

    type_counts = defaultdict(int)
    for group in groups:
        for item in group["occurrences"]:
            type_counts[item["type"]] += 1

    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "# Pa11y Accessibility Audit Digest",
        "",
        f"- **Generated:** {generated}",
        f"- **Unique URLs successfully tested:** {len(data['pages_seen'])}",
        f"- **Successful page checks (across runs):** {data['successful_checks']}",
        f"- **Pages with findings:** {len(data['pages_with_findings'])}",
        f"- **Finding occurrences (across runs):** {data['total_findings']}"
        f" (errors {type_counts['error']},"
        f" warnings {type_counts['warning']},"
        f" notices {type_counts['notice']})",
        f"- **Distinct rules:** {len(groups)}",
        f"- **Failed page checks (across runs):** {len(failures)}",
        "",
        "### Sources",
        "",
        "| Run | Report file | Pages | Passes | Errors |",
        "| --- | --- | --- | --- | --- |",
    ]
    for run in runs:
        lines.append(
            f"| {run['label']} | `{run['path']}` | {run['pages']} "
            f"| {run['passes']} | {run['errors']} |"
        )
    lines.extend([
        "",
        "> Automated findings are a starting point, not a final accessibility"
        " decision. Confirm each one in a browser and verify against WCAG 2.2"
        " before creating or closing remediation work.",
        "",
    ])

    if failures:
        lines.extend([
            "## Failed page checks",
            "",
            "These URL/run combinations were not successfully audited and are excluded"
            " from successful-check and finding counts. A URL may have succeeded in"
            " another run. Resolve these errors and rerun before treating coverage as complete.",
            "",
            "| Run | URL | Error |",
            "| --- | --- | --- |",
        ])
        for failure in failures:
            lines.append(
                f"| {failure['label']} | {failure['url']} "
                f"| {failure['message']} |"
            )
        lines.append("")

    lines.extend([
        "## Summary by rule",
        "",
        "Each row groups a rule for review, not a confirmed ticket or unique fix.",
        "Occurrences from every run are retained and counted; they are not deduplicated.",
        "The standard prefix is not a severity rating or the criterion's conformance level.",
        "IDs repeat only while rule, run label, URL and selector stay unchanged;",
        "they do not detect new, resolved or reopened issues automatically.",
        "",
        "| Rule | Standard prefix | SC | Type | Occurrences | Pages | Runs |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    if not groups:
        lines.append("| _No automated findings were reported._ | | | | | | |")
    for group in groups:
        lines.append(
            f"| `{group['code']}` "
            f"| {group['level'] or '-'} "
            f"| {group['criterion'] or '-'} "
            f"| {group['type']} "
            f"| {group['count']} "
            f"| {len(group['pages'])} "
            f"| {', '.join(group['labels'])} |"
        )
    lines.append("")

    lines.extend(["## Findings by rule", ""])
    if not groups:
        lines.extend(["No automated findings were reported.", ""])

    for group in groups:
        heading = group["criterion"] or group["code"]
        lines.extend([
            f"### {heading} — {group['count']} finding(s)"
            f" on {len(group['pages'])} page(s)",
            "",
            f"- **Rule:** `{group['code']}`",
            f"- **Type:** {group['type']}",
        ])
        if group["level"]:
            lines.append(f"- **Standard prefix:** WCAG 2 {group['level']}")
        if group["criterion"]:
            lines.append(f"- **Success criterion:** {group['criterion']}")
        if group["technique"]:
            lines.append(f"- **Technique:** {group['technique']}")
        lines.extend([
            f"- **Runs affected:** {', '.join(group['labels'])}",
            f"- **Pages affected:** {', '.join(group['pages'])}",
            "",
            "<details><summary>Occurrences</summary>",
            "",
        ])
        for item in group["occurrences"]:
            lines.append(f"- `{item['id']}` **{item['label']}** {item['url']}")
            if item["selector"]:
                lines.append(f"  - Selector: `{clean(item['selector'])}`")
            if item["message"]:
                lines.append(f"  - Message: {clean(item['message'])}")
            if item["context"]:
                lines.append(
                    f"  - Context: `{clean(item['context'], CONTEXT_LIMIT)}`"
                )
        lines.extend(["", "</details>", ""])

    by_page = defaultdict(list)
    for group in groups:
        for item in group["occurrences"]:
            by_page[item["url"]].append((group, item))

    lines.extend(["## Findings by page", ""])
    if not by_page:
        lines.extend(["No automated findings were reported.", ""])
    for url in sorted(by_page):
        entries = by_page[url]
        lines.extend([f"### {url}", "", f"{len(entries)} finding(s)", ""])
        for group, item in sorted(
            entries, key=lambda pair: sort_key(pair[0])
        ):
            criterion = f"SC {group['criterion']}" if group["criterion"] else group["code"]
            lines.append(
                f"- `{item['id']}` [{item['type']}] {criterion} "
                f"(`{group['code']}`) — {item['label']}"
            )
            if item["selector"]:
                lines.append(f"  - Selector: `{clean(item['selector'])}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    argv = sys.argv[1:]

    # Legacy form: pa11y_digest.py INPUT.json OUTPUT.md
    if (len(argv) == 2
            and not any(a.startswith("-") for a in argv)
            and argv[1].lower().endswith(".md")):
        inputs = parse_inputs([argv[0]])
        output_path = Path(argv[1])
    else:
        parser = argparse.ArgumentParser(
            description="Convert Pa11y CI JSON reports into one markdown digest.",
        )
        parser.add_argument(
            "inputs",
            nargs="+",
            metavar="[LABEL=]REPORT.json",
            help="Pa11y CI JSON report, optionally prefixed with a run label.",
        )
        parser.add_argument(
            "-o", "--out",
            required=True,
            metavar="REPORT.md",
            help="Path to write the markdown digest to.",
        )
        args = parser.parse_args(argv)
        inputs = parse_inputs(args.inputs)
        output_path = Path(args.out)

    data = load_reports(inputs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(data), encoding="utf-8")

    print(
        f"Created digest: {output_path} "
        f"({data['total_findings']} finding(s), "
        f"{len(data['findings_by_code'])} distinct rule(s), "
        f"{len(data['failures'])} failed page check(s))"
    )


if __name__ == "__main__":
    main()
