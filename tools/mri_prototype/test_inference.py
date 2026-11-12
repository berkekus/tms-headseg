"""Desktop inference contracts with tiny process stand-ins, never training."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import importlib
import inspect
import json
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import nibabel as nib
import numpy as np
from PySide6.QtWidgets import QApplication, QMessageBox

from prototype import Window

try:
    inference = importlib.import_module("inference_runner")
except ModuleNotFoundError:
    inference = None


class InferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="e1 desktop ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mri = self.root / "T1 scan ;$(touch nope).nii.gz"
        self.save(self.mri)
        self.model = self.root / "model"
        (self.model / "fold_0").mkdir(parents=True)
        for name in ["plans.json", "dataset.json"]:
            (self.model / name).write_text("{}")
        (self.model / "fold_0/checkpoint_final.pth").write_bytes(b"fixture, not real model weights")

    def save(self, path, units="mm"):
        values = np.indices((8, 9, 10)).sum(0).astype(np.float32)
        image = nib.Nifti1Image(values, np.eye(4))
        image.header.set_xyzt_units(units)
        nib.save(image, path)

    def job(self, **changes):
        self.assertIsNotNone(inference, "Desktop inference runner is missing")
        return inference.InferenceJob(**(dict(python=Path(sys.executable), model=self.model,
            mri=self.mri, output=self.root, subject="e1_test", device="cpu", tta=False, assume_mm=False) | changes))

    def standin(self, body=None):
        script = self.root / "predict standin.py"
        script.write_text(body or '''import argparse,json,time
from pathlib import Path
import nibabel as nib
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--out');p.add_argument('--mri');a=p.parse_args()
out=Path(a.out);out.mkdir();(out/'report').mkdir()
print('new inference started',flush=True);time.sleep(.15)
source=nib.load(a.mri);labels=(np.indices(source.shape).sum(0)%5+1).astype(np.uint8)
image=nib.Nifti1Image(labels,source.affine);image.header.set_xyzt_units('mm');nib.save(image,out/'prediction.nii.gz')
(out/'report/report.html').write_text('stand-in report')
(out/'status.json').write_text(json.dumps({'state':'completed'}))
print('new prediction complete',flush=True)
''')
        return script

    def runner(self, job, script):
        with patch.object(type(job), "command", return_value=[sys.executable, "-u", str(script), "--out", str(job.run_dir), "--mri", str(job.mri)]):
            runner = inference.InferenceRunner(job)
            runner.start()
        self.addCleanup(runner.close)
        return runner

    def wait_runner(self, runner):
        text = ""
        deadline = time.monotonic()+8
        while time.monotonic()<deadline:
            text += runner.read_output()
            if runner.poll() is not None:
                return text+runner.read_output()
            time.sleep(.02)
        self.fail("Inference stand-in did not finish")

    def wait_window(self, window):
        deadline = time.monotonic()+10
        while (window.busy) and time.monotonic()<deadline:
            self.app.processEvents();time.sleep(.01)
        self.assertFalse(window.busy, window.feedback.text())

    def test_command_is_existing_predict_cli_with_literal_paths(self):
        job = self.job(); command = job.command()
        self.assertEqual(command[0], str(Path(sys.executable)))
        self.assertIn("predict", command)
        self.assertIn(str(self.mri), command)
        self.assertIn("--disable-tta", command)
        self.assertNotIn("train", command)
        self.assertEqual(job.prediction, job.run_dir / "prediction.nii.gz")

    def test_e2_passes_model_version_and_requires_known_units(self):
        job = self.job(experiment="E2")
        job.validate()
        command = job.command()
        self.assertEqual(command[command.index("--experiment") + 1], "E2")
        self.save(self.mri, units="unknown")
        with self.assertRaisesRegex(ValueError, "known millimetre"):
            self.job(experiment="E2", assume_mm=True).validate()

    def test_model_version_switch_preserves_each_selected_folder(self):
        from inference_panel import InferencePanel
        panel = InferencePanel()
        self.addCleanup(panel.close)
        panel.model.setText(str(self.root / "E1-model"))
        panel.experiment.setCurrentText("E2")
        panel.model.setText(str(self.root / "E2-model"))
        self.assertFalse(panel.assume_mm.isEnabled())
        panel.experiment.setCurrentText("E1")
        self.assertEqual(panel.model.text(), str(self.root / "E1-model"))
        panel.experiment.setCurrentText("E2")
        self.assertEqual(panel.model.text(), str(self.root / "E2-model"))

    def test_local_setup_only_prefills_paths_and_never_runs_or_assumes_units(self):
        window=Window();self.addCleanup(window.close)
        panel=window.inference
        settings=self.root/'settings.json'
        settings.write_text(json.dumps({'python':sys.executable,'mri':str(self.mri),'output':str(self.root),
            'models':{'E2':str(self.model)},'experiment':'E2','assume_mm':True}),encoding='utf-8')
        panel.restore_local_defaults(settings)
        self.assertEqual(panel.experiment.currentText(),'E2')
        self.assertEqual(panel.model.text(),str(self.model))
        self.assertEqual(panel.mri.text(),str(self.mri))
        self.assertFalse(panel.assume_mm.isChecked())
        self.assertIsNone(panel.runner)
        self.assertFalse(window.busy)
        self.assertTrue(panel.setup_inputs.isHidden())
        settings.write_text('invalid JSON',encoding='utf-8')
        panel.restore_local_defaults(settings)
        self.assertEqual(panel.model.text(),str(self.model))

    def test_job_rejects_git_outputs_existing_runs_and_missing_weights(self):
        job = self.job();job.validate()
        job.run_dir.mkdir()
        with self.assertRaisesRegex(ValueError,"exists"):job.validate()
        gitroot = self.root / "checkout";gitroot.mkdir();(gitroot/'.git').mkdir()
        with self.assertRaisesRegex(ValueError,"Git"):self.job(output=gitroot).validate()
        with self.assertRaises(ValueError):self.job(subject="../bad").validate()
        (self.model / "fold_0/checkpoint_final.pth").unlink()
        with self.assertRaisesRegex(ValueError,"checkpoint"):self.job(subject="other").validate()

    def test_units_require_explicit_assumption_and_reject_other_units(self):
        unknown=self.root/'unknown.nii.gz';self.save(unknown,'unknown')
        with self.assertRaisesRegex(ValueError,"units"):self.job(mri=unknown).validate()
        self.job(mri=unknown,assume_mm=True).validate()
        meters=self.root/'meters.nii.gz';self.save(meters,'meter')
        with self.assertRaisesRegex(ValueError,"mm"):self.job(mri=meters).validate()

    def test_owned_process_logs_and_completion_record(self):
        job=self.job();runner=self.runner(job,self.standin())
        self.assertIn('new inference',self.wait_runner(runner))
        self.assertTrue(runner.complete)
        self.assertTrue(runner.log_path.name.startswith('e1.'))
        self.assertFalse((self.root/'nope').exists())
        record=json.loads(job.record_path.read_text())
        self.assertEqual(record['state'],'completed')
        self.assertEqual(record['mri'],str(self.mri))
        self.assertEqual(record['tta'],False)

    def test_zero_exit_without_completed_prediction_is_failure(self):
        job=self.job();runner=self.runner(job,self.standin("print('no result',flush=True)"))
        self.wait_runner(runner)
        self.assertFalse(runner.complete)
        self.assertEqual(json.loads(job.record_path.read_text())['state'],'failed')

    def test_failed_parent_cannot_leave_a_worker_running_after_close(self):
        job=self.job()
        marker=self.root/'orphan_worker_wrote_this'
        script=self.standin(f'''import subprocess,sys,time
child_code = "import time;from pathlib import Path;time.sleep(.8);Path(" + {str(marker)!r}.__repr__() + ").write_text('leaked')"
subprocess.Popen([sys.executable,'-c',child_code]);sys.exit(3)
''')
        runner=self.runner(job,script)
        self.wait_runner(runner)
        runner.close()
        time.sleep(1)
        self.assertFalse(marker.exists(),'Failed inference left a worker running after cleanup')

    def test_cancel_preserves_partial_outputs_and_cleans_owned_group(self):
        job=self.job();script=self.standin('''import argparse,time,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out');p.add_argument('--mri');a=p.parse_args()
out=Path(a.out);out.mkdir()
child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
(out/'child.pid').write_text(str(child.pid));print('partial',flush=True);time.sleep(30)
''')
        runner=self.runner(job,script);deadline=time.monotonic()+4
        while not (job.run_dir/'child.pid').exists() and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue((job.run_dir/'child.pid').is_file())
        runner.cancel();self.wait_runner(runner)
        self.assertFalse(runner.complete)
        self.assertEqual(json.loads(job.record_path.read_text())['state'],'cancelled')
        self.assertTrue(job.run_dir.exists())

    def test_ui_runs_new_prediction_and_automatically_loads_it(self):
        window=Window();self.addCleanup(window.close)
        self.assertTrue(hasattr(window,'inference'),'Inference UI is missing')
        panel=window.inference
        panel.python.setText(sys.executable);panel.model.setText(str(self.model));panel.mri.setText(str(self.mri));panel.output.setText(str(self.root))
        self.assertFalse(panel.tta.isChecked())
        self.assertFalse(panel.assume_mm.isChecked())
        script=self.standin()
        with patch.object(inference.InferenceJob,'command',lambda job:[sys.executable,'-u',str(script),'--out',str(job.run_dir),'--mri',str(job.mri)]), patch.object(window.mesh_view,'ensure_renderer'):
            panel.start()
            self.assertTrue(panel.busy)
            self.assertFalse(window.start_button.isEnabled())
            self.assertFalse(window.open_e1_button.isEnabled())
            self.wait_window(window)
        self.assertIsNotNone(window.head_model,window.feedback.text())
        self.assertEqual(window.head_model.labels[0],panel.runner.job.prediction)
        self.assertEqual(window.tabs.currentIndex(),2)
        self.assertIn('complete',panel.status.text().lower())
        self.assertIsNone(window.runner)

    def test_ui_failure_does_not_load_recorded_fallback(self):
        window=Window();self.addCleanup(window.close)
        self.assertTrue(hasattr(window,'inference'),'Inference UI is missing')
        panel=window.inference
        panel.python.setText(sys.executable);panel.model.setText(str(self.model));panel.mri.setText(str(self.mri));panel.output.setText(str(self.root))
        script=self.standin("import sys; print('inference failed',flush=True);sys.exit(3)")
        with patch.object(inference.InferenceJob,'command',return_value=[sys.executable,'-u',str(script)]):
            panel.start();self.wait_window(window)
        self.assertIsNone(window.head_model)
        self.assertIn('failed',panel.status.text().lower())

    def test_prediction_estimate_does_not_claim_the_whole_job_is_complete(self):
        window=Window();self.addCleanup(window.close)
        panel=window.inference
        panel.python.setText(sys.executable);panel.model.setText(str(self.model));panel.mri.setText(str(self.mri));panel.output.setText(str(self.root))
        old_job = self.job(subject="e1_previous")
        previous = inference.InferenceRunner(old_job)
        previous.started_at = time.monotonic() - 200
        previous.record("completed")
        self.assertGreater(previous.previous_elapsed(), 199)
        self.assertIsNone(inference.InferenceRunner(self.job(tta=True)).previous_elapsed())
        script=self.standin("import time;time.sleep(30)")
        with patch.object(inference.InferenceJob,'command',return_value=[sys.executable,'-u',str(script)]):
            panel.start()
            self.assertIn('from a previous run', panel.metrics.text())
            panel.progress_text='Predicting x:\n0%| | 0/27 [00:00<?, ?it/s]'
            panel.update_metrics()
            self.assertIn('from a previous run', panel.metrics.text())
            panel.progress_text='Predicting x:\n4%|# | 1/27 [00:05<02:16, 5s/it]'
            panel.update_metrics()
            self.assertIn('for prediction only',panel.metrics.text())
            self.assertEqual(panel.progress.maximum(),27)
            panel.progress_text+='\r100%|##| 27/27 [02:04<00:00, 5s/it]'
            panel.update_metrics()
            self.assertIn('Saving',panel.metrics.text())
            self.assertEqual(panel.progress.maximum(),0)
            self.assertTrue(panel.busy)
            panel.cancel();self.wait_window(window)

    def test_cancel_button_requires_confirmation_and_preserves_partial_output(self):
        window=Window();self.addCleanup(window.close)
        panel=window.inference
        panel.python.setText(sys.executable);panel.model.setText(str(self.model));panel.mri.setText(str(self.mri));panel.output.setText(str(self.root))
        script=self.standin("import time; print('running',flush=True);time.sleep(30)")
        with patch.object(inference.InferenceJob,'command',return_value=[sys.executable,'-u',str(script)]):
            panel.start()
            with patch('inference_panel.QMessageBox.question',return_value=QMessageBox.StandardButton.No):
                panel.cancel_button.click()
            self.assertTrue(panel.busy)
            self.assertFalse(panel.runner.cancelled)
            with patch('inference_panel.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):
                panel.cancel_button.click()
            self.wait_window(window)
        self.assertTrue(panel.runner.cancelled)
        self.assertTrue(panel.runner.log_path.exists())
        self.assertTrue(panel.runner.job.record_path.exists())
        self.assertEqual(window.result_title.text(), 'Inference cancelled')

    def test_display_failure_is_distinguished_from_completed_inference(self):
        window=Window();self.addCleanup(window.close)
        self.assertTrue(hasattr(window,'inference'),'Inference UI is missing')
        panel=window.inference
        panel.python.setText(sys.executable);panel.model.setText(str(self.model));panel.mri.setText(str(self.mri));panel.output.setText(str(self.root))
        script=self.standin()
        script.write_text(script.read_text().replace("nib.save(image,out/'prediction.nii.gz')", "(out/'prediction.nii.gz').write_bytes(b'corrupt')"))
        with patch.object(inference.InferenceJob,'command',lambda job:[sys.executable,'-u',str(script),'--out',str(job.run_dir),'--mri',str(job.mri)]):
            panel.start();self.wait_window(window)
        self.assertIsNone(window.head_model)
        self.assertTrue(panel.runner.complete)
        self.assertIn('could not open',panel.status.text().lower())

    def test_close_can_decline_then_cancel_and_wait_for_cleanup(self):
        window=Window();self.addCleanup(window.close);window.show()
        self.assertTrue(hasattr(window,'inference'),'Inference UI is missing')
        panel=window.inference
        panel.python.setText(sys.executable);panel.model.setText(str(self.model));panel.mri.setText(str(self.mri));panel.output.setText(str(self.root))
        script=self.standin("import time; print('running',flush=True);time.sleep(30)")
        with patch.object(inference.InferenceJob,'command',return_value=[sys.executable,'-u',str(script)]):
            panel.start()
            with patch('prototype.QMessageBox.question',return_value=QMessageBox.StandardButton.No):
                self.assertFalse(window.close())
                self.assertFalse(panel.runner.cancelled)
            with patch('prototype.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):
                self.assertFalse(window.close())
            self.wait_window(window)
            self.app.processEvents()
        self.assertTrue(panel.runner.cancelled)
        self.assertFalse(window.isVisible())
        self.assertEqual(json.loads(panel.runner.job.record_path.read_text())['state'],'cancelled')

    def test_k3_export_error_prefix_and_inference_error_callback_coexist(self):
        window = Window()
        self.addCleanup(window.close)
        self.assertIn('on_error', inspect.signature(window.run_task).parameters,
                      'Inference callback must coexist with K3 export failure prefixes')
        errors = []
        def fail_export():
            raise ValueError('fixture export failure')
        window.run_task(fail_export, lambda result: self.fail('Failed task returned a result'),
                        'Could not export: ', on_error=errors.append)
        self.wait_window(window)
        self.assertEqual(window.feedback.text(), 'Could not export: fixture export failure')
        self.assertEqual(errors, ['fixture export failure'])

    def test_close_dialog_can_finish_after_inference_has_already_stopped(self):
        window = Window()
        self.addCleanup(window.close)
        window.show()
        panel = window.inference
        panel.python.setText(sys.executable)
        panel.model.setText(str(self.model))
        panel.mri.setText(str(self.mri))
        panel.output.setText(str(self.root))
        script = self.standin("import time,sys;time.sleep(.15);sys.exit(3)")
        def answer_after_completion(*args):
            self.wait_window(window)
            return QMessageBox.StandardButton.Yes
        with patch.object(inference.InferenceJob, 'command', return_value=[sys.executable, '-u', str(script)]):
            panel.start()
            with patch('prototype.QMessageBox.question', side_effect=answer_after_completion):
                window.close()
            self.app.processEvents()
        self.assertFalse(window.isVisible(), 'Window must close even when inference ended during the modal question')

    def test_inference_gates_k3_export_without_losing_its_source(self):
        window = Window()
        self.addCleanup(window.close)
        self.assertTrue(hasattr(window, 'inference'), 'Inference UI is missing')
        window.load_mri(self.mri)
        self.wait_window(window)
        label_path = self.root / 'project_labels.nii.gz'
        labels = (np.indices((8, 9, 10)).sum(0) % 5 + 1).astype(np.uint8)
        image = nib.Nifti1Image(labels, np.eye(4))
        image.header.set_xyzt_units('mm')
        nib.save(image, label_path)
        window.load_overlay(label_path)
        self.wait_window(window)
        source = window.export_source
        self.assertTrue(window.export_button.isEnabled())
        panel = window.inference
        panel.python.setText(sys.executable)
        panel.model.setText(str(self.model))
        panel.output.setText(str(self.root))
        script = self.standin("import time; print('running',flush=True);time.sleep(30)")
        with patch.object(inference.InferenceJob, 'command', return_value=[sys.executable, '-u', str(script)]):
            panel.start()
            try:
                self.assertTrue(panel.busy)
                self.assertFalse(window.export_button.isEnabled())
                window.export_model(self.root / 'must_not_exist')
                self.assertIsNone(window.task)
                self.assertFalse((self.root / 'must_not_exist').exists())
                self.assertEqual(window.export_source, source)
            finally:
                panel.cancel()
                self.wait_window(window)
        self.assertTrue(window.export_button.isEnabled())
        self.assertEqual(window.export_source, source)


if __name__=='__main__':unittest.main()
