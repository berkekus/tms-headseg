"""Batch desktop checks use tiny subprocess stand-ins, never real CHARM."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import csv
import importlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox
from prototype import Window

try:
    desktop = importlib.import_module("batch_runner")
except ModuleNotFoundError:
    desktop = None


class BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.assertIsNotNone(desktop, "Batch desktop adapter is missing")
        self.temp = tempfile.TemporaryDirectory(prefix="batch desktop ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.out = self.root / "output"
        self.out.mkdir()
        self.assignment = self.root / "assignment.csv"
        with self.assignment.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["subject", "owner", "cohort", "site"])
            w.writeheader()
            for subject, owner, cohort in [("IXI100", "K2", "train"), ("IXI101", "K2", "train"),
                                           ("IXI999", "K1", "test_face")]:
                w.writerow(dict(subject=subject, owner=owner, cohort=cohort, site="HH"))
            for subject in ["IXI100", "IXI101"]:
                folder = self.data / subject
                folder.mkdir(parents=True)
                for modality in ["T1", "T2"]:
                    (folder / f"{subject}-HH-0001-{modality}.nii.gz").write_bytes(b"stand-in input")
        self.assignment_patch = patch.object(desktop, "ASSIGNMENT", self.assignment)
        self.assignment_patch.start()
        self.addCleanup(self.assignment_patch.stop)

    def job(self, **changes):
        return desktop.BatchJob(**(dict(python=Path(sys.executable), charm=Path(sys.executable),
            data=self.data, output=self.out, owner="K2", dry_run=False) | changes))

    def standin(self, body=None):
        script = self.root / "batch standin.py"
        script.write_text(body or '''import argparse,csv,json,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out');p.add_argument('--owner');p.add_argument('--data');p.add_argument('--charm');p.add_argument('--assignment');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
print('batch started',flush=True)
if a.dry_run:
    print('summary: planned',flush=True);raise SystemExit(0)
out=Path(a.out);(out/'runs').mkdir(exist_ok=True)
for row in csv.DictReader(open(a.assignment)):
    if row['owner']!=a.owner or row['cohort']!='train':continue
    subject=row['subject'];m=out/('m2m_'+subject);m.mkdir(exist_ok=True)
    for name in ['final_tissues.nii.gz','final_tissues_LUT.txt','charm_report.html']:(m/name).write_text('fixture')
    time.sleep(.2);(out/'runs'/(subject+'.json')).write_text(json.dumps({'outputs_ok':True,'state':'completed','minutes':.1}))
print('batch complete',flush=True)
''')
        return script

    def wait(self, panel):
        deadline = time.monotonic() + 9
        while panel.busy and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.02)
        self.assertFalse(panel.busy, panel.status.text())

    def panel(self):
        window = Window()
        self.addCleanup(window.close)
        self.assertTrue(hasattr(window, "batch"), "Batch controls missing from Workbench")
        panel = window.batch
        panel.python.setText(sys.executable)
        panel.charm.setText(sys.executable)
        panel.data.setText(str(self.data))
        panel.output.setText(str(self.out))
        return window, panel

    def test_command_uses_shared_train_cli_and_literal_paths(self):
        job = self.job()
        job.validate()
        cmd = job.command()
        self.assertIn("run_charm_batch.py", cmd[cmd.index("-u") + 1])
        self.assertEqual(cmd[cmd.index("--owner") + 1], "K2")
        self.assertIn(str(self.assignment), cmd)
        self.assertEqual([r['subject'] for r in desktop.training_rows('K2')], ['IXI100', 'IXI101'])
        self.assertNotIn("--cohort", cmd)
        self.assertNotIn("--dry-run", cmd)
        self.assertIn("--dry-run", self.job(dry_run=True).command())
        git = self.out / ".git"
        git.mkdir()
        with self.assertRaisesRegex(ValueError, "Git"):
            job.validate()

    def test_external_monitor_is_read_only_and_blocks_real_start(self):
        model = self.out / "m2m_IXI100"
        model.mkdir()
        log = self.out / "logs/IXI100.log"
        log.parent.mkdir()
        log.write_text("[ simnibs ] INFO: Starting segmentation.\n")
        before = {p.relative_to(self.out): p.read_bytes() for p in self.out.rglob('*') if p.is_file()}
        window, panel = self.panel()
        panel.monitor()
        self.assertTrue(panel.external_active)
        self.assertFalse(panel.run_button.isEnabled())
        self.assertFalse(window.start_button.isEnabled())
        self.assertFalse(window.inference.run_button.isEnabled())
        self.assertFalse(panel.cancel_button.isEnabled())
        self.assertIn("segmentation", panel.logs.toPlainText())
        self.assertIsNone(panel.runner)
        self.assertTrue(window.close())
        after = {p.relative_to(self.out): p.read_bytes() for p in self.out.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_successful_dry_run_enables_start_then_real_completion(self):
        window, panel = self.panel()
        script = self.standin()
        with patch.object(desktop, "BATCH", script), patch('batch_panel.QApplication.alert'):
            self.assertFalse(panel.run_button.isEnabled())
            panel.start(dry_run=True)
            self.assertTrue(panel.busy)
            self.assertFalse(window.inference.run_button.isEnabled())
            self.wait(panel)
            self.assertTrue(panel.run_button.isEnabled(), panel.status.text())
            self.assertFalse((self.out / 'm2m_IXI100').exists())
            panel.start()
            self.wait(panel)
        self.assertTrue(panel.runner.complete)
        self.assertEqual(panel.progress.value(), 2)
        self.assertIn("2 / 2", panel.summary.text())
        self.assertIn("complete", panel.status.text().lower())
        self.assertFalse((self.out / 'm2m_IXI999').exists())
        self.assertFalse(window.timer.isActive())
        self.assertFalse(window.inference.busy)

    def test_failed_preflight_and_changed_form_do_not_allow_real_start(self):
        _, panel = self.panel()
        script = self.standin("import sys;print('bad input',flush=True);sys.exit(2)")
        with patch.object(desktop, "BATCH", script):
            panel.start(dry_run=True)
            self.wait(panel)
        self.assertFalse(panel.run_button.isEnabled())
        self.assertIn("failed", panel.status.text().lower())
        script = self.standin()
        with patch.object(desktop, "BATCH", script):
            panel.start(dry_run=True)
            self.wait(panel)
            self.assertTrue(panel.run_button.isEnabled())
            panel.data.setText(str(self.root / 'different data'))
            self.assertFalse(panel.run_button.isEnabled())

    def test_close_can_decline_or_cancel_owned_batch(self):
        window, panel = self.panel()
        window.show()
        panel.preflight_key = self.job().key()
        script = self.standin("import time;print('owned batch',flush=True);time.sleep(30)")
        with patch.object(desktop, "BATCH", script):
            panel.preflight_key = panel.job().key()
            panel.start()
            self.assertTrue(panel.busy)
            with patch('prototype.QMessageBox.question', return_value=QMessageBox.StandardButton.No):
                self.assertFalse(window.close())
                self.assertFalse(panel.runner.cancelled)
            with patch('prototype.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
                self.assertFalse(window.close())
            self.wait(panel)
            self.app.processEvents()
        self.assertTrue(panel.runner.cancelled)
        self.assertFalse(window.isVisible())

    def test_completed_record_without_files_is_not_counted_as_success(self):
        (self.out / 'runs').mkdir()
        (self.out / 'runs/IXI100.json').write_text(json.dumps({'outputs_ok': True}))
        cases = desktop.read_cases(self.out, 'K2')
        self.assertNotEqual(cases[0]['state'], 'completed')

    def test_monitor_refresh_preserves_accessible_table_items(self):
        _, panel = self.panel()
        panel.monitor()
        original = panel.table.item(0)
        panel.refresh()
        self.assertIs(panel.table.item(0), original,
                      "Live refresh must not delete cells while native accessibility clients hold them")

    def test_monitor_hides_setup_to_keep_logs_visible_and_can_reopen_it(self):
        _, panel = self.panel()
        panel.monitor()
        self.assertTrue(panel.inputs.isHidden())
        panel.setup_button.click()
        self.assertFalse(panel.inputs.isHidden())
        self.assertIsNone(panel.runner)

    def test_preflight_log_stays_visible_until_monitor_is_selected(self):
        (self.out / 'logs').mkdir()
        (self.out / 'logs/IXI100.log').write_text('previous case log')
        (self.out / 'runs').mkdir()
        (self.out / 'runs/IXI100.json').write_text(json.dumps({'outputs_ok': True}))
        model = self.out / 'm2m_IXI100'
        model.mkdir()
        for name in ['final_tissues.nii.gz', 'final_tissues_LUT.txt', 'charm_report.html']:
            (model / name).write_text('fixture')
        _, panel = self.panel()
        with patch.object(desktop, 'BATCH', self.standin()):
            panel.start(dry_run=True)
            self.wait(panel)
            panel.tick()
            self.assertIn('summary: planned', panel.logs.toPlainText())
            panel.monitor()
            self.assertEqual(panel.logs.toPlainText(), 'previous case log')

    def test_failed_parent_cleanup_stops_its_worker(self):
        marker = self.root / 'orphan'
        script = self.standin(f'''import subprocess,sys
subprocess.Popen([sys.executable,'-c',"import time;from pathlib import Path;time.sleep(1);Path({str(marker)!r}).write_text('leaked')"])
sys.exit(3)
''')
        job = self.job(dry_run=True)
        with patch.object(desktop, "BATCH", script):
            runner = desktop.BatchRunner(job)
            runner.start()
        self.addCleanup(runner.close)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            runner.read_output()
            if runner.poll() is not None:
                break
            time.sleep(.02)
        runner.close()
        time.sleep(1.2)
        self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
