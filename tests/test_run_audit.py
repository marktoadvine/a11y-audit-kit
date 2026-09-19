import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_audit.py"
SPEC = importlib.util.spec_from_file_location("run_audit", SCRIPT)
RUN_AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN_AUDIT)


class ChromeResolutionTests(unittest.TestCase):
    def test_prefers_cached_headless_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            shell = (
                cache / "chrome-headless-shell" / "123" /
                "chrome-headless-shell-linux64" / "chrome-headless-shell"
            )
            chrome = cache / "chrome" / "999" / "chrome-linux64" / "chrome"
            shell.parent.mkdir(parents=True)
            chrome.parent.mkdir(parents=True)
            shell.touch()
            chrome.touch()
            with mock.patch.dict(os.environ, {"PUPPETEER_CACHE_DIR": directory}, clear=False):
                resolved, source = RUN_AUDIT.resolve_chrome()
            self.assertEqual(resolved, str(shell))
            self.assertEqual(source, "Puppeteer cache")

    def test_launch_check_reports_success(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "browser"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            launched, detail = RUN_AUDIT.check_chrome_launch(str(executable))
            self.assertTrue(launched)
            self.assertEqual(detail, "launch OK")


if __name__ == "__main__":
    unittest.main()
