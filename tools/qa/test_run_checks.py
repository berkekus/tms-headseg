"""Exercise report trust boundaries with isolated synthetic unittest suites."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import run_checks as qa


class ReportContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qa-report-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tests = self.root / "tests"
        self.tests.mkdir()
        self.out = self.root / "out"
        self.out.mkdir()

    def run_fixture(self, body, dependencies=(), timeout=15, temp_root=None):
        (self.tests / "test_fixture.py").write_text(body, encoding="utf-8")
        return qa.run_suite(qa.Suite("fixture", self.tests, dependencies), self.out, timeout, temp_root)

    def test_skipped_check_is_not_counted_as_passed(self):
        result = self.run_fixture("""import unittest
class Checks(unittest.TestCase):
    def test_pass(self): self.assertTrue(True)
    @unittest.skip('native graphics not rehearsed')
    def test_skip(self): pass
""")
        self.assertEqual(result["status"], "PASS_WITH_SKIPS")
        self.assertEqual(result["tests_run"], 2)
        self.assertEqual(result["passed_methods"], 1)
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(qa.overall([result]), "PASS_WITH_SKIPS")

    def test_subtest_failures_are_not_subtracted_from_method_count(self):
        result = self.run_fixture("""import unittest
class Checks(unittest.TestCase):
    def test_subtests(self):
        for value in [1, 2]:
            with self.subTest(value=value): self.assertEqual(value, 0)
""")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["tests_run"], 1)
        self.assertEqual(result["passed_methods"], 0)
        self.assertEqual(len(result["failures"]), 2)

    def test_missing_dependency_is_blocked_before_test_execution(self):
        result = self.run_fixture("raise AssertionError('must not be discovered')\n",
                                 ("tms_qa_deliberately_missing_dependency",))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["tests_run"], 0)
        self.assertTrue(result["blockers"])

    def test_empty_discovery_cannot_pass(self):
        result = self.run_fixture("# No checks\n")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["tests_run"], 0)

    def test_temp_inside_git_is_blocked_before_test_execution(self):
        (self.root / ".git").mkdir()
        result = self.run_fixture("raise AssertionError('must not be discovered')\n", temp_root=self.root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["tests_run"], 0)
        self.assertTrue(any("Git checkout" in reason for reason in result["blockers"]))

    def test_expected_failure_remains_incomplete_coverage(self):
        result = self.run_fixture("""import unittest
class Checks(unittest.TestCase):
    @unittest.expectedFailure
    def test_known_failure(self): self.fail('known issue')
""")
        self.assertEqual(result["status"], "PASS_WITH_SKIPS")
        self.assertEqual(result["expected_failures"], 1)
        self.assertEqual(result["passed_methods"], 0)

    def test_worker_crash_cannot_reuse_or_invent_result(self):
        result = self.run_fixture("import os\nos._exit(17)\n")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["exit_code"], 17)
        self.assertIn("without a result", result["reason"])
        self.assertIsNone(result["tests_run"])

    def test_timeout_is_a_failure(self):
        result = self.run_fixture("import time\ntime.sleep(30)\n", timeout=.5)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("timed out", result["reason"])
        self.assertIsNone(result["passed_methods"])

    def test_existing_output_is_preserved(self):
        sentinel = self.out / "summary.json"
        sentinel.write_text('{"old": true}', encoding="utf-8")
        result = subprocess.run([sys.executable, str(Path(qa.__file__)), "--out", str(self.out)],
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(sentinel.read_text(encoding="utf-8")), {"old": True})


if __name__ == "__main__":
    unittest.main()
