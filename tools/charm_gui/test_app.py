"""Headless Qt workflow check; uses a local stand-in, never real MRI processing."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import sys
import tempfile
import time
import unittest

from PySide6.QtWidgets import QApplication
from app import Window


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def test_window_does_not_autostart_and_reports_incomplete_job(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            charm = root / "charm"
            if sys.platform == "win32":
                script = root / "charm.py"
                script.write_text("print('stand-in output', flush=True)\n", encoding="utf-8")
                charm = root / "charm.cmd"
                charm.write_text(f'@echo off\n"{sys.executable}" -E -u "{script}" %*\n', encoding="utf-8")
            else:
                charm.write_text(f"#!{sys.executable}\nprint('stand-in output', flush=True)\n")
            charm.chmod(0o755)
            image = root / "T1.nii.gz"
            image.touch()
            window = Window()
            self.addCleanup(window.close)
            self.assertIsNone(window.runner)
            window.charm.setText(str(charm))
            window.t1.setText(str(image))
            window.output.setText(str(root))
            window.start_job()
            self.assertFalse(window.start_button.isEnabled())
            deadline = time.monotonic() + 5
            while window.timer.isActive() and time.monotonic() < deadline:
                self.qt.processEvents()
                time.sleep(0.02)
            self.assertFalse(window.timer.isActive())
            self.assertTrue(window.start_button.isEnabled())
            self.assertIn("incomplete", window.status.text().lower())
            self.assertIn("stand-in output", window.logs.toPlainText())
            self.assertFalse(window.model_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
