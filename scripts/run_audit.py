#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Mark Toadvine, @marktoadvine
"""Run a Pa11y accessibility audit over a list of URLs and write one digest.

This is the one-command path. It checks the environment, writes throwaway
Pa11y configs for both viewports, runs them, and builds the markdown digest:

    run_audit.py --out report.md https://example.com/ https://example.com/about/

Nothing is written into the repository or the working directory except the
digest, at the path given by --out.

Run it with --check to preflight the environment without auditing anything.
That reports Node, Chromium, proxy and per-URL reachability in one pass, so a
blocked host or a missing browser is found before a full run rather than after
it.

Chromium in containers and CI needs help that Puppeteer does not give it by
default. This script resolves all of it up front:

  * --no-sandbox, because Chromium refuses to start as root without it.
  * An already-installed browser, so no ~150MB download happens per run.
  * An explicit --proxy-server when the environment sets one.
  * A pinned proxy CA, when a TLS-intercepting proxy would otherwise fail
    every page load with ERR_CERT_AUTHORITY_INVALID.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 800},
    "mobile": {"width": 390, "height": 812, "isMobile": True, "deviceScaleFactor": 2},
}

# Environment variables that conventionally hold a browser path, most
# specific first. PLAYWRIGHT_BROWSERS_PATH holds a directory, not a binary,
# so it is handled separately below.
CHROME_ENV_VARS = (
    "A11Y_CHROME_PATH",
    "PUPPETEER_EXECUTABLE_PATH",
    "CHROME_PATH",
    "CHROMIUM_PATH",
    "GOOGLE_CHROME_BIN",
)

CHROME_PATHS = (
    "/opt/pw-browsers/chromium",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/snap/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)

PROXY_ENV_VARS = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")

# Single-certificate files in these variables are treated as a proxy CA.
# A multi-certificate bundle is not: pinning every public root would weaken
# certificate checking for every site, which is not what this is for.
CA_ENV_VARS = (
    "A11Y_PROXY_CA",
    "NODE_EXTRA_CA_CERTS",
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
)

CERT_ERROR_HINT = """
Chromium could not verify the certificate for one or more targets. A proxy
that re-terminates TLS causes this. Point this script at the proxy's CA
certificate (a single PEM, not a bundle) and it will pin that one CA:

    run_audit.py --proxy-ca /path/to/proxy-ca.crt --out report.md URL...

or set A11Y_PROXY_CA to it. To find it, look for the CA your other tools were
already given, for example $SSL_CERT_FILE or $NODE_EXTRA_CA_CERTS.
""".strip()


def log(message):
    print(message, file=sys.stderr, flush=True)


def resolve_digest_script(explicit=None):
    """Find pa11y_digest.py, in the order the skill documents."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    kit_dir = os.environ.get("A11Y_AUDIT_KIT_DIR")
    if kit_dir:
        candidates.append(Path(kit_dir) / "scripts" / "pa11y_digest.py")
    candidates.append(Path.cwd() / "scripts" / "pa11y_digest.py")
    candidates.append(Path(__file__).resolve().parent / "pa11y_digest.py")

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def resolve_chrome(explicit=None):
    """Find an installed Chromium, so no per-run download is needed."""
    if explicit:
        return explicit, "--chrome"

    for var in CHROME_ENV_VARS:
        value = os.environ.get(var)
        if value and Path(value).exists():
            return value, f"${var}"

    browsers_dir = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_dir:
        candidate = Path(browsers_dir) / "chromium"
        if candidate.exists():
            return str(candidate), "$PLAYWRIGHT_BROWSERS_PATH"

    for path in CHROME_PATHS:
        if Path(path).exists():
            return path, "system"

    found = shutil.which("chromium") or shutil.which("google-chrome")
    if found:
        return found, "PATH"
    return None, None


def resolve_proxy(explicit=None):
    if explicit:
        return explicit, "--proxy"
    for var in PROXY_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value, f"${var}"
    return None, None


def count_certificates(path):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return text.count("-----BEGIN CERTIFICATE-----")


def resolve_proxy_ca(explicit=None):
    """Find a single-certificate proxy CA to pin, if one is configured."""
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            return None, f"--proxy-ca {explicit} does not exist"
        return str(path), "--proxy-ca"

    for var in CA_ENV_VARS:
        value = os.environ.get(var)
        if value and Path(value).is_file() and count_certificates(value) == 1:
            return value, f"${var}"
    return None, None


def spki_hash(ca_path):
    """Chromium's SPKI fingerprint for one certificate, via openssl.

    Pinning this one key lets Chromium accept the proxy's certificates
    without turning off certificate checking for everything else.
    """
    if not shutil.which("openssl"):
        return None
    pipeline = (
        f'openssl x509 -in "{ca_path}" -pubkey -noout '
        "| openssl pkey -pubin -outform der "
        "| openssl dgst -sha256 -binary "
        "| openssl enc -base64"
    )
    try:
        result = subprocess.run(
            ["sh", "-c", pipeline],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    digest = result.stdout.strip()
    return digest or None


def build_chrome_args(proxy=None, spki=None, extra=()):
    args = ["--no-sandbox", "--disable-dev-shm-usage"]
    if proxy:
        args.append(f"--proxy-server={proxy}")
    if spki:
        args.append(f"--ignore-certificate-errors-spki-list={spki}")
    args.extend(extra)
    return args


def write_config(run_dir, reports_dir, name, urls, chrome_path, chrome_args,
                 timeout, wait):
    launch = {"args": chrome_args}
    if chrome_path:
        launch["executablePath"] = chrome_path

    report = reports_dir / f"pa11y-{name}-results.json"
    config = {
        "defaults": {
            "timeout": timeout,
            "wait": wait,
            "viewport": VIEWPORTS[name],
            "chromeLaunchConfig": launch,
            # Pa11y resolves a relative fileName against the working
            # directory, not the config, so this must be absolute.
            "reporters": ["cli", ["json", {"fileName": str(report)}]],
        },
        "urls": list(urls),
    }
    path = run_dir / f".pa11yci-{name}.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path, report


def check_url(url, timeout=15):
    """Fetch a URL the way the environment would, and report what happened.

    urllib honours the proxy environment variables, so a blocked host fails
    here in a second rather than after a full two-viewport run.
    """
    request = urllib.request.Request(url, method="GET", headers={
        "User-Agent": "a11y-audit-kit/run_audit.py",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return True, f"HTTP {response.status} {response.url}"
    except urllib.error.HTTPError as error:
        # A 4xx/5xx still proves the host is reachable, which is what this
        # check is for. Pa11y will report on whatever page is served.
        return True, f"HTTP {error.code}"
    except urllib.error.URLError as error:
        return False, f"unreachable: {error.reason}"
    except Exception as error:  # noqa: BLE001 - report anything, never crash
        return False, f"unreachable: {error}"


def preflight(urls, args):
    """Report everything the run needs, in one pass. Returns (ok, facts)."""
    facts = {}
    ok = True

    node = shutil.which("node")
    if node:
        version = subprocess.run(
            [node, "--version"], capture_output=True, text=True, check=False,
        ).stdout.strip()
        facts["node"] = f"{version} ({node})"
    else:
        facts["node"] = "MISSING - install Node.js from https://nodejs.org/"
        ok = False

    facts["npx"] = shutil.which("npx") or "MISSING - ships with Node.js"
    if not shutil.which("npx"):
        ok = False

    digest = resolve_digest_script(args.digest)
    facts["digest script"] = str(digest) if digest else (
        "MISSING - set A11Y_AUDIT_KIT_DIR to a clone of a11y-audit-kit"
    )
    if not digest:
        ok = False

    chrome, chrome_source = resolve_chrome(args.chrome)
    facts["chromium"] = (
        f"{chrome} (from {chrome_source})" if chrome
        else "not found - Puppeteer will download one on first run"
    )

    proxy, proxy_source = resolve_proxy(args.proxy)
    facts["proxy"] = f"{proxy} (from {proxy_source})" if proxy else "none"

    ca, ca_source = resolve_proxy_ca(args.proxy_ca)
    if ca:
        digest_hash = spki_hash(ca)
        facts["proxy CA"] = (
            f"{ca} (from {ca_source}), pinned SPKI {digest_hash}"
            if digest_hash else
            f"{ca} (from {ca_source}), but openssl is missing so it cannot be pinned"
        )
    elif ca_source:
        facts["proxy CA"] = ca_source
    else:
        facts["proxy CA"] = "none configured"

    for url in urls:
        reachable, detail = check_url(url)
        facts[f"url {url}"] = detail
        if not reachable:
            ok = False

    return ok, facts


def print_facts(facts):
    width = max(len(key) for key in facts) if facts else 0
    for key, value in facts.items():
        log(f"  {key.ljust(width)}  {value}")


def run_pa11y(config_path, report_path, label):
    log(f"\n== {label} ==")
    result = subprocess.run(
        ["npx", "--yes", "pa11y-ci@latest", "--config", str(config_path)],
        check=False,
    )
    # Pa11y CI exits non-zero when it finds issues. That is a successful run
    # reporting findings. The report file is what says whether it really ran.
    if not report_path.is_file() or report_path.stat().st_size == 0:
        log(f"\nPa11y produced no {label} report (exit {result.returncode}).")
        return False
    return True


def summarise(report_paths):
    """Short stdout summary, so the digest need not be re-read to act on it."""
    totals = {"error": 0, "warning": 0, "notice": 0}
    codes = set()
    failed_pages = []
    cert_error = False

    for path in report_paths:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for url, issues in (data.get("results") or {}).items():
            if not isinstance(issues, list):
                continue
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                message = str(issue.get("message", ""))
                if "ERR_CERT" in message:
                    cert_error = True
                if issue.get("code") in (None, "Error") or "Error:" in message:
                    if url not in failed_pages:
                        failed_pages.append(url)
                    continue
                kind = issue.get("type", "error")
                if kind in totals:
                    totals[kind] += 1
                codes.add(issue.get("code"))

    return totals, codes, failed_pages, cert_error


def main():
    parser = argparse.ArgumentParser(
        description="Run a Pa11y audit over URLs and write one markdown digest.",
    )
    parser.add_argument("urls", nargs="*", metavar="URL", help="URLs to audit.")
    parser.add_argument("-o", "--out", metavar="REPORT.md",
                        help="Digest path (default a11y-audit-<today>.md).")
    parser.add_argument("--urls-file", metavar="FILE",
                        help="Read URLs from a file, one per line.")
    parser.add_argument("--check", action="store_true",
                        help="Preflight the environment and exit.")
    parser.add_argument("--viewport", choices=("desktop", "mobile", "both"),
                        default="both", help="Which viewports to run.")
    parser.add_argument("--chrome", metavar="PATH",
                        help="Chromium executable to use.")
    parser.add_argument("--proxy", metavar="URL",
                        help="Proxy for Chromium (default: from environment).")
    parser.add_argument("--proxy-ca", metavar="FILE",
                        help="Proxy CA certificate to pin for Chromium.")
    parser.add_argument("--chrome-arg", action="append", default=[],
                        metavar="ARG", help="Extra Chromium flag. Repeatable.")
    parser.add_argument("--digest", metavar="PATH",
                        help="Path to pa11y_digest.py.")
    parser.add_argument("--timeout", type=int, default=30000,
                        help="Per-page timeout in ms (default 30000).")
    parser.add_argument("--wait", type=int, default=2000,
                        help="Settle time in ms before scanning (default 2000).")
    parser.add_argument("--reports-dir", metavar="DIR",
                        help="Keep the raw Pa11y JSON reports in DIR.")
    parser.add_argument("--keep", action="store_true",
                        help="Keep the temporary run directory.")
    args = parser.parse_args()

    urls = list(args.urls)
    if args.urls_file:
        urls.extend(
            line.strip()
            for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    bad = [url for url in urls if not url.startswith(("http://", "https://"))]
    if bad:
        parser.error(f"URLs must start with http:// or https://: {', '.join(bad)}")

    if not urls and not args.check:
        parser.error("give at least one URL, or --check to preflight only")

    log("Preflight")
    ok, facts = preflight(urls, args)
    print_facts(facts)

    if args.check:
        log("\nReady." if ok else "\nNot ready - see MISSING/unreachable above.")
        return 0 if ok else 1

    if not ok:
        log("\nStopping: the environment cannot complete this run.")
        log("Re-run with --check after fixing the items above.")
        return 1

    digest_script = resolve_digest_script(args.digest)
    chrome, _ = resolve_chrome(args.chrome)
    proxy, _ = resolve_proxy(args.proxy)
    ca, _ = resolve_proxy_ca(args.proxy_ca)
    spki = spki_hash(ca) if ca else None
    chrome_args = build_chrome_args(proxy, spki, args.chrome_arg)

    names = ("desktop", "mobile") if args.viewport == "both" else (args.viewport,)
    out_path = Path(args.out) if args.out else Path(f"a11y-audit-{date.today()}.md")

    run_dir = Path(tempfile.mkdtemp(prefix="a11y-audit-"))
    # Absolute, because Pa11y resolves a relative reporter fileName
    # against the working directory rather than the config file.
    reports_dir = (
        Path(args.reports_dir).resolve() if args.reports_dir
        else run_dir / "reports"
    )
    reports_dir.mkdir(parents=True, exist_ok=True)

    try:
        produced = []
        for name in names:
            config_path, report_path = write_config(
                run_dir, reports_dir, name, urls, chrome, chrome_args,
                args.timeout, args.wait,
            )
            if run_pa11y(config_path, report_path, name):
                produced.append((name, report_path))

        if not produced:
            log("\nNo Pa11y report was produced, so there is nothing to digest.")
            log("This is a failed run, not a clean result.")
            return 1

        inputs = [f"{name}={path}" for name, path in produced]
        result = subprocess.run(
            [sys.executable, str(digest_script), *inputs, "--out", str(out_path)],
            check=False,
        )
        if result.returncode != 0:
            log("\nThe digest step failed.")
            return result.returncode

        totals, codes, failed_pages, cert_error = summarise(
            [path for _, path in produced]
        )
        log("")
        log(f"Digest:   {out_path.resolve()}")
        if args.reports_dir:
            log(f"Reports:  {reports_dir.resolve()}")
        log(f"Pages:    {len(urls)} requested, {len(failed_pages)} failed to load")
        log(f"Findings: {totals['error']} errors, {totals['warning']} warnings, "
            f"{totals['notice']} notices across {len(codes)} distinct rules")
        if failed_pages:
            log("\nThese pages were never audited, so no finding count covers them:")
            for url in failed_pages:
                log(f"  - {url}")
        if cert_error:
            log("\n" + CERT_ERROR_HINT)
        log("\nAutomated checks cover a minority of WCAG. Confirm findings in a "
            "browser before filing or closing work.")

        # Every page failing to load is a broken run, not a clean result.
        # Exiting 0 here would let "0 findings" read as a pass.
        if failed_pages and len(failed_pages) == len(urls):
            log("\nNo page loaded, so nothing was audited. This is not a pass.")
            return 1
        return 0
    finally:
        if args.keep:
            log(f"\nRun directory kept at {run_dir}")
        else:
            shutil.rmtree(run_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
