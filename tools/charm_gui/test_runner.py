"""Run with: python -m unittest discover -s tools/charm_gui -v."""

from pathlib import Path
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from runner import Job, Runner


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="charm launcher ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.t1 = self.root / "T1 scan ;$(touch nope).nii.gz"
        self.t1.touch()
        self.charm = self.root / "fake charm"
        self.write_charm("print('ready', flush=True)\n")

    def write_charm(self, body):
        if sys.platform == "win32":
            script = self.root / "charm.py"
            script.write_text(body, encoding="utf-8")
            self.charm = self.root / "charm.cmd"
            self.charm.write_text(f'@echo off\n"{sys.executable}" -E -u "{script}" %*\n', encoding="utf-8")
            return
        self.charm.write_text(f"#!{sys.executable}\n" + body)
        self.charm.chmod(0o755)

    def job(self, **changes):
        values = dict(charm=self.charm, t1=self.t1, t2=None,
                      output=self.root, subject="trial_01")
        return Job(**(values | changes))

    def wait_done(self, runner):
        deadline = time.monotonic() + 6
        text = ""
        while time.monotonic() < deadline:
            text += runner.read_output()
            if runner.poll() is not None:
                return text + runner.read_output()
            time.sleep(0.02)
        self.fail("Child process did not finish")

    def test_command_keeps_paths_as_single_arguments(self):
        job = self.job(t2=self.t1)
        self.assertEqual(job.command()[-3:], ["trial_01", str(self.t1), str(self.t1)])

    def test_rejects_existing_model_and_unsafe_subject(self):
        for subject in ("../other", "--help", "", "two words"):
            with self.subTest(subject=subject), self.assertRaises(ValueError):
                self.job(subject=subject).validate()
        (self.root / "m2m_trial_01").mkdir()
        with self.assertRaisesRegex(ValueError, "exists"):
            self.job().validate()

    def test_rejects_bad_inputs(self):
        for changes in ({"t1": self.root / "missing.nii.gz"},
                        {"t2": self.root / "bad.txt"},
                        {"charm": self.root / "missing"},
                        {"output": self.root / "missing"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.job(**changes).validate()

    def test_rejects_output_inside_a_git_checkout(self):
        (self.root / ".git").mkdir()
        output = self.root / "models"
        output.mkdir()
        with self.assertRaisesRegex(ValueError, "Git"):
            self.job(output=output).validate()

    def test_streams_and_records_output_without_shell_expansion(self):
        self.write_charm("import sys\nprint(sys.argv[2], flush=True)\n")
        runner = Runner(self.job())
        runner.start()
        self.addCleanup(runner.close)
        text = self.wait_done(runner)
        self.assertIn(str(self.t1), text)
        self.assertEqual(runner.returncode, 0)
        self.assertIn(str(self.t1), runner.log_path.read_text())
        self.assertFalse((self.root / "nope").exists())
        self.assertFalse(runner.complete)

    def test_success_requires_mesh_and_labels(self):
        self.write_charm("from pathlib import Path\np = Path('m2m_trial_01')\np.mkdir()\n"
                         "(p / 'trial_01.msh').touch()\n(p / 'final_tissues.nii.gz').touch()\n")
        runner = Runner(self.job())
        runner.start()
        self.addCleanup(runner.close)
        self.wait_done(runner)
        self.assertTrue(runner.complete)

    def test_output_is_visible_before_process_finishes(self):
        self.write_charm("import time\nprint('first stage', flush=True)\ntime.sleep(60)\n")
        runner = Runner(self.job())
        runner.start()
        self.addCleanup(runner.close)
        deadline = time.monotonic() + 4
        text = ""
        while "first stage" not in text and time.monotonic() < deadline:
            text += runner.read_output()
            time.sleep(0.02)
        self.assertIn("first stage", text)
        self.assertIsNone(runner.poll())

    def test_unexpected_start_failure_releases_log_files(self):
        target = "windows_process.WindowsProcess" if sys.platform == "win32" else "runner.subprocess.Popen"
        runner = Runner(self.job())
        with patch(target, side_effect=TypeError("process API rejected its arguments")):
            with self.assertRaises(TypeError):
                runner.start()
        self.assertTrue(runner.log.closed)
        self.assertTrue(runner.reader.closed)

    def test_windows_cleanup_does_not_require_unix_signals(self):
        runner = Runner(self.job())
        runner.process = Mock()
        runner.process.poll.return_value = None
        with patch("runner.sys.platform", "win32"), patch("runner.signal", SimpleNamespace(SIGTERM=15)):
            runner.close()
        runner.process.close.assert_called_once()

    @unittest.skipUnless(sys.platform == "win32", "Windows Job Object behavior")
    def test_windows_close_cleans_children_after_parent_exits(self):
        heartbeat = self.root / "orphan-heartbeat"
        child_code = ("import time\nfrom pathlib import Path\n"
                      f"p = Path({str(heartbeat)!r})\n"
                      "while True:\n p.write_text(str(time.time_ns()))\n time.sleep(0.02)\n")
        self.write_charm("import subprocess,sys,time\n"
                         f"subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
                         "time.sleep(0.5)\n")
        runner = Runner(self.job())
        runner.start()
        self.addCleanup(runner.close)
        self.wait_done(runner)
        self.assertTrue(heartbeat.exists())
        runner.close()
        time.sleep(0.1)
        last = heartbeat.read_text()
        time.sleep(0.1)
        self.assertEqual(heartbeat.read_text(), last)

    def test_failure_preserves_exit_code(self):
        self.write_charm("import sys\nprint('failed', flush=True)\nsys.exit(7)\n")
        runner = Runner(self.job())
        runner.start()
        self.addCleanup(runner.close)
        self.assertIn("failed", self.wait_done(runner))
        self.assertEqual(runner.returncode, 7)
        self.assertFalse(runner.complete)

    def test_cancel_stops_descendant_even_if_parent_exits(self):
        pidfile = self.root / "child.pid"
        heartbeat = self.root / "heartbeat"
        child_code = ("import signal,time\nfrom pathlib import Path\n"
                      "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                      f"p = Path({str(heartbeat)!r})\n"
                      "while True:\n p.write_text(str(time.time_ns()))\n time.sleep(0.02)\n")
        self.write_charm("import subprocess, sys, time\n"
                         f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
                         f"open({str(pidfile)!r}, 'w').write(str(child.pid))\n"
                         "print('running', flush=True)\ntime.sleep(60)\n")
        runner = Runner(self.job())
        runner.start()
        self.addCleanup(runner.close)
        deadline = time.monotonic() + 4
        while not heartbeat.exists() and time.monotonic() < deadline:
            time.sleep(0.03)
        self.assertTrue(heartbeat.exists())
        time.sleep(0.1)
        runner.cancel()
        self.wait_done(runner)
        self.assertTrue(runner.cancelled)
        self.assertFalse(runner.complete)
        last_heartbeat = heartbeat.read_text()
        time.sleep(0.1)
        self.assertEqual(heartbeat.read_text(), last_heartbeat)


if __name__ == "__main__":
    unittest.main()
