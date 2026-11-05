"""Windowed startup must retain diagnostics without requiring a terminal."""

from contextlib import contextmanager
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import launch


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="workbench-startup-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.previous_cwd, self.previous_path = Path.cwd(), sys.path[:]
        self.addCleanup(lambda: os.chdir(self.previous_cwd))
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), self.previous_path))

    @contextmanager
    def entry(self, main):
        with patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)}), \
             patch.dict(sys.modules, {"prototype": SimpleNamespace(main=main)}), \
             patch.object(launch, "show_error") as show:
            yield show

    def logs(self):
        return list((self.root / "TMSHeadSeg/logs").glob("*.log"))

    def test_startup_uses_project_root_and_retains_unicode_diagnostics(self):
        def main():
            self.assertEqual(Path.cwd(), Path(launch.__file__).resolve().parents[2])
            print("Diagnostic: \u2713")
        os.chdir(self.root)
        with self.entry(main) as show:
            self.assertEqual(launch.launch(), 0)
            show.assert_not_called()
        self.assertEqual(len(self.logs()), 1)
        self.assertIn("Diagnostic: \u2713", self.logs()[0].read_text(encoding="utf-8"))

    def test_missing_dependency_shows_error_and_writes_traceback(self):
        def main():
            raise ModuleNotFoundError("Missing fixture dependency")
        with self.entry(main) as show:
            self.assertEqual(launch.launch(), 1)
            self.assertIn("Startup log:", show.call_args.args[0])
        self.assertIn("ModuleNotFoundError", self.logs()[0].read_text(encoding="utf-8"))

    def test_clean_system_exit_does_not_show_an_error(self):
        def main():
            raise SystemExit(0)
        with self.entry(main) as show:
            self.assertEqual(launch.launch(), 0)
            show.assert_not_called()

    def test_nonzero_system_exit_is_visible(self):
        def main():
            raise SystemExit(3)
        with self.entry(main) as show:
            self.assertEqual(launch.launch(), 1)
            self.assertIn("status 3", show.call_args.args[0])
        self.assertIn("SystemExit: 3", self.logs()[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
