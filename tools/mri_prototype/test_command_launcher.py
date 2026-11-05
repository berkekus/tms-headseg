"""Exercise Finder's shell entry point with isolated, non-Qt fixtures."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "Open MRI Workbench.command"


class CommandLauncherTests(unittest.TestCase):
    def setUp(self):
        git = shutil.which("git")
        bundled = Path(git).resolve().parents[1] / "bin/bash.exe" if git else Path("missing-bash")
        self.bash = str(bundled) if os.name == "nt" and bundled.is_file() else shutil.which("bash")
        if not self.bash:
            self.skipTest("Bash is required to exercise the macOS command entry point.")
        self.temp = tempfile.TemporaryDirectory(prefix="MRI launcher ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Project with spaces and apostrophe's"
        self.root.mkdir()
        self.entry = self.root / SOURCE.name
        self.entry.write_bytes(SOURCE.read_bytes())
        self.python = self.root / "tools/mri_prototype/.venv/bin/python"
        self.python.parent.mkdir(parents=True)
        self.launcher = self.root / "tools/mri_prototype/launch.py"
        self.launcher.write_text("# Fixture only\n", encoding="utf-8")
        self.python.write_bytes(b'#!/bin/bash\nprintf "%s\\n" "$PWD" "$@" > "$PWD/arguments.txt"\nexit "${FIXTURE_EXIT:-0}"\n')
        self.python.chmod(0o755)

    def run_entry(self, *args, code=0):
        env = dict(os.environ, FIXTURE_EXIT=str(code))
        return subprocess.run([self.bash, str(self.entry), *args], cwd=self.temp.name,
                              input="", text=True, capture_output=True, env=env, timeout=20)

    def test_project_paths_and_arguments_survive_spaces_and_shell_characters(self):
        self.assertNotIn(b"\r", SOURCE.read_bytes())
        argument = "MRI's folder $literal ; unchanged"
        result = self.run_entry("--smoke-test", argument)
        self.assertEqual(result.returncode, 0, result.stderr)
        values = (self.root / "arguments.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(values[1:], [values[0] + "/tools/mri_prototype/launch.py", "--smoke-test", argument])
        self.assertTrue(values[0].endswith(self.root.name))

    def test_missing_environment_or_entry_point_is_actionable(self):
        self.python.unlink()
        result = self.run_entry()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Complete the macOS setup", result.stderr)
        self.python.write_bytes(b"#!/bin/bash\nexit 0\n")
        self.python.chmod(0o755)
        self.launcher.unlink()
        result = self.run_entry()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Keep this file in the project root", result.stderr)

    def test_app_failure_retains_its_exit_status(self):
        result = self.run_entry(code=7)
        self.assertEqual(result.returncode, 7)
        self.assertIn("Check the startup message and log", result.stderr)


if __name__ == "__main__":
    unittest.main()
