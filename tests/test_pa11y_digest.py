import importlib.util
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/pa11y_digest.py'
spec = importlib.util.spec_from_file_location('digest', SCRIPT)
digest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(digest)


class DigestTests(unittest.TestCase):
    def example(self):
        return digest.load_reports([
            (label, ROOT / 'examples/digest' / (label + '.json'))
            for label in ('desktop', 'mobile')
        ])

    def load(self, report):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            path.write_text(json.dumps(report))
            return digest.load_reports([('test', path)])

    def test_mixed_viewport_coverage(self):
        data = self.example()
        self.assertEqual(data['successful_checks'], 4)
        self.assertEqual(data['pages_seen'], {
            'https://example.test/', 'https://example.test/about',
            'https://example.test/contact',
        })
        self.assertEqual(len(data['failures']), 2)
        self.assertEqual(data['total_findings'], 4)
        self.assertEqual(len(data['pages_with_findings']), 2)
        rendered = digest.render(data)
        self.assertIn('**Unique URLs successfully tested:** 3', rendered)
        self.assertIn('**Successful page checks (across runs):** 4', rendered)
        self.assertIn('**Failed page checks (across runs):** 2', rendered)
        self.assertIn('another run', rendered)

    def test_same_rule_retains_components_and_runs(self):
        data = self.example()
        self.assertEqual(len(data['findings_by_code']), 1)
        code, items = next(iter(data['findings_by_code'].items()))
        group = digest.summarise_group(code, items)
        self.assertEqual(group['count'], 4)
        self.assertEqual(group['labels'], ['desktop', 'mobile'])
        self.assertEqual(len(group['pages']), 2)
        self.assertEqual(len({item['id'] for item in items}), 4)
        self.assertIn('#product-photo', {item['selector'] for item in items})
        self.assertIn('not a confirmed ticket or unique fix', digest.render(data))

    def test_all_failed_is_not_successful_coverage(self):
        data = self.load({'results': {'https://example.test/': [{'message': 'timeout'}]}})
        self.assertEqual(data['successful_checks'], 0)
        self.assertFalse(data['pages_seen'])
        self.assertEqual(data['total_findings'], 0)
        self.assertEqual(len(data['failures']), 1)

    def test_clean_page_counts_as_successful(self):
        data = self.load({'results': {'https://example.test/': []}})
        self.assertEqual(data['successful_checks'], 1)
        self.assertEqual(data['total_findings'], 0)
        self.assertFalse(data['failures'])

    def test_invalid_results_do_not_silently_look_clean(self):
        for report in ([], {}, {'results': {'url': None}}, {'results': {'url': [None]}}):
            with self.subTest(report=report), self.assertRaises(SystemExit):
                self.load(report)

    def test_references_repeat_only_with_consistent_fields(self):
        fields = ['rule', 'desktop', 'https://example.test/', '#logo']
        reference = digest.fingerprint(*fields)
        self.assertEqual(reference, digest.fingerprint(*fields))
        for index in range(len(fields)):
            changed = fields.copy()
            changed[index] += '-changed'
            self.assertNotEqual(reference, digest.fingerprint(*changed))

    def test_axe_slug_does_not_invent_wcag_metadata(self):
        data = self.load({'results': {'url': [{'code': 'color-contrast', 'type': 'error'}]}})
        self.assertEqual(digest.parse_code('color-contrast'), {
            'level': None, 'criterion': None, 'technique': None,
        })
        self.assertIn('| `color-contrast` | - | - | error | 1 | 1 | test |', digest.render(data))

    def test_standard_prefix_does_not_override_occurrence_order(self):
        groups = [
            {'type': 'error', 'level': 'A', 'count': 1, 'code': 'a'},
            {'type': 'error', 'level': 'AA', 'count': 3, 'code': 'b'},
        ]
        self.assertEqual(sorted(groups, key=digest.sort_key)[0]['code'], 'b')

    def test_committed_example_matches_generator(self):
        inputs = digest.parse_inputs([
            'desktop=examples/digest/desktop.json',
            'mobile=examples/digest/mobile.json',
        ])
        # The CLI contract and documented regeneration command run at repo root.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'audit.md'
            result = subprocess.run([
                sys.executable, str(SCRIPT), '--out', str(output),
                *[f'{label}={path}' for label, path in inputs],
            ], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            without_timestamp = lambda text: re.sub(
                r'^- \*\*Generated:\*\*.*$', '', text, flags=re.MULTILINE)
            self.assertEqual(
                without_timestamp(output.read_text()),
                without_timestamp((ROOT / 'examples/digest/audit.md').read_text()),
            )

    def test_handoff_references_exist_in_fixture_evidence(self):
        data = self.example()
        known = {item['id'] for items in data['findings_by_code'].values()
                 for item in items}
        handoff = (ROOT / 'examples/digest/handoff.md').read_text()
        referenced = set(re.findall(r'`([0-9a-f]{12})`', handoff))
        self.assertEqual(referenced, known)

    def test_cli_single_legacy_and_multi_input(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'nested' / 'audit.md'
            source = ROOT / 'examples/digest/desktop.json'
            cases = [
                [str(source), str(output)],
                ['--out', str(output), str(source)],
                ['--out', str(output), 'desktop=' + str(source),
                 'mobile=' + str(ROOT / 'examples/digest/mobile.json')],
            ]
            for args in cases:
                with self.subTest(args=args):
                    result = subprocess.run([sys.executable, str(SCRIPT), *args],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(output.read_text().startswith('# Pa11y Accessibility'))
                    output.unlink()


if __name__ == '__main__':
    unittest.main()
