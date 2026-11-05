"""Windowed startup must retain diagnostics without requiring a terminal."""

from contextlib import contextmanager
import io
import os
from pathlib import Path
import sys
import subprocess
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
             patch.object(launch, "log_directory", return_value=self.root / "TMSHeadSeg/logs"), \
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

    def test_macos_error_is_a_literal_dialog_argument_with_terminal_fallback(self):
        message = 'Missing "dependency"\n/path with spaces and apostrophe\'s'
        with patch.object(launch.sys, "platform", "darwin"), \
             patch.object(launch.subprocess, "run") as run:
            launch.show_error(message)
            self.assertEqual(run.call_args.args[0][-1], message)
            self.assertNotIn(message, run.call_args.args[0][-2])
        with patch.object(launch.sys, "platform", "darwin"), \
             patch.object(launch.subprocess, "run", side_effect=subprocess.TimeoutExpired("osascript", 10)), \
             patch.object(launch.sys, "stderr", io.StringIO()) as stderr:
            launch.show_error(message)
            self.assertIn(message, stderr.getvalue())

    def test_macos_logs_use_the_user_library(self):
        with patch.object(launch.sys, "platform", "darwin"), \
             patch.object(launch.Path, "home", return_value=self.root):
            self.assertEqual(launch.log_directory(), self.root / "Library/Logs/TMSHeadSeg")


if __name__ == "__main__":
    unittest.main()
