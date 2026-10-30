"""Launcher resolution checks run on either host without executing a shell."""

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from installation import command_prefix, find_charm, external_environment


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="SimNIBS & scans ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.python = self.root / "python.exe"
        self.script = self.root / "charm.py"
        self.python.touch()
        self.script.touch()
        self.launcher = self.root / "charm.cmd"

    def test_resolves_official_windows_wrapper_without_shell(self):
        self.launcher.write_text(f'@echo off\n"{self.python}" -E -u "{self.script}"  %*\n', encoding="utf-8")
        self.assertEqual(command_prefix(self.launcher),
                         [str(self.python), "-E", "-u", str(self.script)])

    def test_resolves_generated_gui_wrapper(self):
        self.launcher.write_text(f'@echo off\nstart "Loading SimNIBS" "{self.python}" -E -u "{self.script}" %*\n', encoding="utf-8")
        self.assertEqual(command_prefix(self.launcher)[0], str(self.python))

    def test_rejects_arbitrary_batch_commands(self):
        self.launcher.write_text(f'@echo off\n"{self.python}" -E -u "{self.script}" %* & echo bad\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "wrapper"):
            command_prefix(self.launcher)

    def test_rejects_moved_or_broken_installation(self):
        self.launcher.write_text(f'@echo off\n"{self.python}" -E -u "{self.script}" %*\n', encoding="utf-8")
        self.script.unlink()
        with self.assertRaisesRegex(ValueError, "installation"):
            command_prefix(self.launcher)

    def test_discovers_windows_installation_under_user_folder(self):
        launcher = self.root / "SimNIBS-4.6" / "bin" / "charm.cmd"
        launcher.parent.mkdir(parents=True)
        launcher.touch()
        with patch("installation.shutil.which", return_value=None), patch("installation.Path.home", return_value=self.root):
            self.assertEqual(find_charm(platform="win32"), str(launcher))

    def test_packaged_environment_does_not_leak_qt_paths_to_simnibs(self):
        bundled = self.root / "bundle"
        outside = self.root / "system"
        with patch("installation.sys._MEIPASS", str(bundled), create=True), patch.dict(
            "os.environ", {"PATH": str(bundled / "bin") + os.pathsep + str(outside),
                           "QT_PLUGIN_PATH": str(bundled / "plugins")}, clear=True
        ):
            env = external_environment()
        self.assertEqual(env["PATH"], str(outside))
        self.assertNotIn("QT_PLUGIN_PATH", env)

    def test_packaged_macos_resources_do_not_leak_to_external_programs(self):
        contents = self.root / "Launcher.app" / "Contents"
        with patch("installation.sys._MEIPASS", str(contents / "Frameworks"), create=True), patch.dict(
            "os.environ", {"QT_PLUGIN_PATH": str(contents / "Resources" / "plugins")}, clear=True
        ):
            self.assertNotIn("QT_PLUGIN_PATH", external_environment())


if __name__ == "__main__":
    unittest.main()
