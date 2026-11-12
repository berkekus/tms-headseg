"""Synthetic geometry and offscreen UI checks; no real CHARM reconstruction."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import nibabel as nib
import numpy as np
from PySide6.QtWidgets import QApplication, QDialog, QPlainTextEdit

from prototype import Window
from viewer import render_slice, label_color
from volume import load_volume, load_labels, slice_data


class PrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = np.indices((5, 6, 7)).astype(np.float32)
        self.data = self.data[0] * 100 + self.data[1] * 10 + self.data[2]
        self.path = self.save("T1.nii.gz", self.data, np.diag([2., 3., 4., 1.]))

    def save(self, name, data, affine, unit="mm"):
        image = nib.Nifti1Image(data, affine)
        image.header.set_xyzt_units(unit)
        path = self.root / name
        nib.save(image, path)
        return path

    def wait_idle(self, window):
        deadline = time.monotonic() + 12
        while (window.task is not None or window.timer.isActive()) and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIsNone(window.task, window.feedback.text())
        self.assertFalse(window.timer.isActive())

    def window(self):
        window = Window()
        self.addCleanup(window.close)
        return window

    def test_startup_fits_available_screen_and_slice_controls_remain_reachable(self):
        window = self.window()
        window.show_fitted()
        self.app.processEvents()
        available = window.screen().availableGeometry()
        self.assertTrue(window.isMaximized())
        self.assertLessEqual(window.frameGeometry().width(), available.width())
        self.assertLessEqual(window.frameGeometry().height(), available.height())
        self.assertGreaterEqual(window.frameGeometry().left(), available.left())
        self.assertGreaterEqual(window.frameGeometry().top(), available.top())
        self.assertTrue(window.welcome.isVisible())
        window.load_mri(self.path)
        self.wait_idle(window)
        self.app.processEvents()
        for panel in window.panels:
            self.assertTrue(panel.rect().contains(panel.slider.geometry()))
        self.assertGreater(window.inspection_sidebar.verticalScrollBar().maximum(), 0)

    def test_left_right_and_slice_orientation(self):
        affine = np.diag([-2., 3., 4., 1.])
        affine[0, 3] = 8
        volume = load_volume(self.save("LAS.nii", self.data, affine))
        self.assertEqual(volume.source_orientation, "LAS")
        np.testing.assert_allclose(volume.image.affine, np.diag([2, 3, 4, 1]))
        self.assertEqual(slice_data(volume.data, 2, 4)[2, 0], 434)
        self.assertEqual(slice_data(volume.data, 1, 3)[2, 0], 434)
        self.assertEqual(slice_data(volume.data, 0, 0)[2, 3], 434)

    def test_loading_feedback_stays_visible_and_ui_responsive_until_worker_finishes(self):
        window = self.window()
        window.show_fitted()
        gate = threading.Event()
        self.addCleanup(gate.set)
        def load_when_released():
            gate.wait(5)
            return load_volume(self.path)
        window.run_task(load_when_released, window.mri_loaded, activity="Opening T1 MRI")
        try:
            self.app.processEvents()
            self.assertTrue(window.activity_banner.isVisible())
            self.assertIn("Opening T1 MRI", window.activity_label.text())
            self.assertIn("Completion time is not yet known", window.activity_label.text())
            self.assertFalse(window.open_button.isEnabled())
            self.assertIn("Preparing preview", window.panels[0].canvas.empty_message)
            window.tabs.setCurrentIndex(1)
            self.app.processEvents()
            self.assertEqual(window.tabs.currentIndex(), 1)
            self.assertTrue(window.activity_banner.isVisible())
            with patch("prototype.LoadTask") as duplicate:
                window.run_task(lambda: None, lambda result: None)
                duplicate.assert_not_called()
        finally:
            gate.set()
            self.wait_idle(window)
        self.assertTrue(window.activity_banner.isHidden())
        self.assertFalse(window.activity_timer.isActive())
        self.assertTrue(window.open_button.isEnabled())
        self.assertEqual(window.volume.path, self.path.resolve())
        self.assertEqual(window.panels[0].canvas.accessibleDescription(), window.panels[0].position.text())

    def test_e2_controls_can_be_reached_in_a_short_window_without_starting_inference(self):
        window = self.window()
        window.show_fitted()
        window.showNormal()
        window.resize(900, 560)
        window.tabs.setCurrentIndex(3)
        window.inference.experiment.setCurrentText("E2")
        self.app.processEvents()
        scroll = window.inference_scroll
        self.assertGreater(scroll.verticalScrollBar().maximum(), 0)
        scroll.ensureWidgetVisible(window.inference.run_button)
        self.app.processEvents()
        center = window.inference.run_button.rect().center()
        point = window.inference.run_button.mapTo(scroll.viewport(), center)
        self.assertTrue(scroll.viewport().rect().contains(point))
        self.assertEqual(window.inference.run_button.text(), "Create E2 segmentation")
        self.assertFalse(window.inference.assume_mm.isEnabled())
        self.assertIsNone(window.inference.runner)
        self.assertFalse(window.busy)

    def test_notifications_do_not_shift_tabs_or_scroll_recovery_actions_away(self):
        window = self.window()
        window.show_fitted()
        window.showNormal()
        window.resize(1000, 700)
        self.app.processEvents()
        tab_bounds = window.tabs.geometry()
        action = window.welcome_open_button
        open_position = action.mapTo(window, action.rect().center())
        window.inspection_sidebar.verticalScrollBar().setValue(window.inspection_sidebar.verticalScrollBar().maximum())
        window.load_mri(self.root / "missing.nii")
        self.app.processEvents()
        self.assertEqual(window.tabs.geometry(), tab_bounds)
        self.wait_idle(window)
        self.app.processEvents()
        self.assertEqual(window.tabs.geometry(), tab_bounds)
        self.assertEqual(action.mapTo(window, action.rect().center()), open_position)
        self.assertTrue(action.isVisible())
        self.assertTrue(window.open_button.isEnabled())
        self.assertFalse(window.error_details_button.isVisible())
        full_error = "<not markup> " + "long-path/" * 1000
        window.show_notice("error", "Long error", full_error)
        self.app.processEvents()
        self.assertEqual(window.tabs.geometry(), tab_bounds)
        self.assertTrue(window.error_details_button.isVisible())
        self.assertLess(len(window.error_message.text()), len(full_error))
        captured = []

        def read_details(dialog):
            captured.append(dialog.findChild(QPlainTextEdit).toPlainText())
            return QDialog.DialogCode.Rejected

        with patch.object(QDialog, "exec", new=read_details):
            window.error_details_button.click()
        self.assertEqual(captured, [full_error])
        window.dismiss_error_button.click()
        self.app.processEvents()
        self.assertEqual(window.tabs.geometry(), tab_bounds)
        window.load_mri(self.path)
        self.wait_idle(window)
        self.assertEqual(window.notifications.currentWidget(), window.result_banner)
        self.assertIn("MRI loaded", window.result_message.text())
        self.assertEqual(window.tabs.geometry(), tab_bounds)

    def test_page_validation_errors_are_visible_without_starting_processes(self):
        window = self.window()
        window.show_fitted()
        window.tabs.setCurrentIndex(3)
        window.inference.python.clear()
        window.inference.run_button.click()
        self.assertEqual(window.notifications.currentWidget(), window.error_banner)
        self.assertEqual(window.error_title.text(), "Inference could not start")
        self.assertIsNone(window.inference.runner)
        window.tabs.setCurrentIndex(1)
        window.processing_tabs.setCurrentIndex(1)
        window.batch.python.clear()
        window.batch.check_button.click()
        self.assertEqual(window.error_title.text(), "Batch could not start")
        self.assertIsNone(window.batch.runner)
        window.processing_tabs.setCurrentIndex(0)
        window.start_job()
        self.assertEqual(window.error_title.text(), "MRI inspection required")
        self.assertIsNone(window.runner)

    def test_display_callback_exception_cannot_report_success(self):
        window = self.window()
        window.show_fitted()
        def broken_display(value):
            raise RuntimeError("display failed")
        window.run_task(lambda: None, broken_display)
        self.wait_idle(window)
        self.assertEqual(window.notifications.currentWidget(), window.error_banner)
        self.assertIn("display failed", window.error_message.text())
        self.assertTrue(window.open_button.isEnabled())

    def test_start_screen_guides_users_without_starting_processing(self):
        window = self.window()
        window.show_fitted()
        self.app.processEvents()
        self.assertTrue(window.welcome.isVisible())
        self.assertTrue(window.sidebar_column.isHidden())
        self.assertTrue(window.welcome_open_button.isVisible())
        self.assertFalse(window.e1_assume_mm.isChecked())
        self.assertTrue(window.e1_assume_mm.isHidden())
        window.welcome_generate_button.click()
        self.assertEqual(window.tabs.currentIndex(), 3)
        self.assertIsNone(window.inference.runner)
        self.assertFalse(window.busy)
        window.tabs.setCurrentIndex(0)
        window.load_mri(self.path)
        self.wait_idle(window)
        self.assertEqual(window.preview_stack.currentWidget(), window.slice_container)
        self.assertTrue(window.sidebar_column.isVisible())

    def test_permuted_axes_keep_physical_spacing(self):
        affine = np.array([[0., 2., 0., 0.], [3., 0., 0., 0.], [0., 0., 4., 0.], [0., 0., 0., 1.]])
        volume = load_volume(self.save("ARS.nii", self.data, affine))
        self.assertEqual(volume.image.shape, (6, 5, 7))
        np.testing.assert_allclose(volume.image.affine, np.diag([2, 3, 4, 1]))
        np.testing.assert_allclose(volume.source_spacing, [3, 2, 4])

    def test_oblique_volume_is_world_aligned_without_modifying_source(self):
        affine = np.eye(4)
        angle = .2
        affine[:2, :2] = [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
        path = self.save("oblique.nii", self.data, affine)
        before = path.read_bytes()
        volume = load_volume(path)
        np.testing.assert_allclose(volume.image.affine[:3, :3], np.eye(3), atol=1e-5)
        self.assertEqual(path.read_bytes(), before)

    def test_meter_units_are_converted_to_mm(self):
        volume = load_volume(self.save("meters.nii", self.data, np.diag([.002, .003, .004, 1.]), "meter"))
        np.testing.assert_allclose(volume.source_spacing, [2, 3, 4], rtol=1e-6)

    def test_rejects_corrupt_4d_unknown_units_and_nonfinite(self):
        corrupt = self.root / "corrupt.nii.gz"
        corrupt.write_bytes(b"not a volume")
        bad = self.data.copy()
        bad[0, 0, 0] = np.nan
        paths = [corrupt, self.save("4d.nii", np.stack([self.data, self.data], axis=3), np.eye(4)),
                 self.save("unknown.nii", self.data, np.eye(4), "unknown"),
                 self.save("nan.nii", bad, np.eye(4))]
        for path in paths:
            with self.subTest(path=path), self.assertRaises(ValueError):
                load_volume(path)

    def test_accepts_singleton_dimensions_used_by_simnibs_labels(self):
        path = self.save("singleton.nii", np.ones((5, 6, 7, 1), np.uint8), np.eye(4))
        volume = load_volume(path)
        self.assertEqual(volume.data.shape, (5, 6, 7))
        _, labels, ids = load_labels(path, volume)
        self.assertEqual(labels.shape, (5, 6, 7))
        np.testing.assert_array_equal(ids, [1])

    def test_labels_use_affine_and_preserve_discrete_ids(self):
        volume = load_volume(self.path)
        labels = np.zeros((5, 6, 7), np.uint16)
        labels[1, 2, 3] = 9
        affine = np.diag([2., 3., 4., 1.])
        affine[0, 3] = 2  # source voxel 1 maps to target voxel 2
        _, aligned, ids = load_labels(self.save("labels.nii.gz", labels, affine), volume)
        self.assertEqual(aligned[2, 2, 3], 9)
        np.testing.assert_array_equal(ids, [9])
        np.testing.assert_array_equal(np.unique(aligned), [0, 9])
        image = render_slice(volume, aligned, 2, 3, 0, 1, 1)
        self.assertEqual(image.pixelColor(2, 3).getRgb()[:3], label_color(9))

    def test_rejects_nonoverlapping_and_continuous_labels(self):
        volume = load_volume(self.path)
        affine = np.eye(4)
        affine[:3, 3] = 1000
        for path in [self.save("far.nii", np.ones_like(self.data), affine),
                     self.save("probabilities.nii", self.data + .1, np.eye(4))]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                load_labels(path, volume)

    def test_ui_background_load_navigation_and_failed_replacement(self):
        window = self.window()
        window.load_mri(self.path)
        self.assertFalse(window.open_button.isEnabled())
        self.wait_idle(window)
        self.assertEqual(window.volume.path, self.path.resolve())
        window.panels[0].slider.setValue(1)
        self.assertIn("2/7", window.panels[0].position.text())
        window.width.setValue(200)
        self.assertEqual(window.panels[1].width, 200)
        window.load_mri(self.root / "missing.nii")
        self.wait_idle(window)
        self.assertIsNone(window.volume)
        self.assertIsNone(window.panels[0].canvas.image)
        self.assertIn("Could not load", window.feedback.text())

    def test_empty_mri_shows_visible_error_and_valid_retry_recovers(self):
        window = self.window()
        window.show()
        invalid = self.root / "invalid_mri.nii"
        invalid.touch()
        with patch("prototype.QFileDialog.getOpenFileName", return_value=(str(invalid), "")):
            window.choose_mri()
        self.wait_idle(window)
        self.assertTrue(window.error_banner.isVisible())
        self.assertEqual(window.error_title.text(), "MRI could not be opened")
        self.assertIn("empty", window.error_message.text().lower())
        self.assertIn("Open MRI", window.error_recovery.text())
        self.assertTrue(window.activity_banner.isHidden())
        self.assertFalse(window.activity_timer.isActive())
        self.assertIn("No MRI preview", window.panels[0].canvas.empty_message)
        self.assertIsNone(window.volume)
        self.assertTrue(window.open_button.isEnabled())
        self.assertIsNone(window.panels[0].canvas.image)
        window.tabs.setCurrentIndex(1)
        window.tabs.setCurrentIndex(0)
        window.load_mri(self.path)
        self.wait_idle(window)
        self.assertTrue(window.error_banner.isHidden())
        self.assertEqual(window.error_message.text(), "")
        self.assertEqual(window.volume.path, self.path.resolve())

    def test_cancelled_picker_keeps_error_and_dismiss_does_not_load_a_scan(self):
        window = self.window()
        window.show()
        window.load_mri(self.root / "missing.nii")
        self.wait_idle(window)
        message = window.error_message.text()
        with patch("prototype.QFileDialog.getOpenFileName", return_value=("", "")):
            window.choose_mri()
        self.assertTrue(window.error_banner.isVisible())
        self.assertEqual(window.error_message.text(), message)
        window.dismiss_error_button.click()
        self.assertTrue(window.error_banner.isHidden())
        self.assertEqual(window.panels[0].canvas.empty_message, "Open a T1 MRI to inspect slices")
        self.assertIsNone(window.volume)
        self.assertTrue(window.open_button.isEnabled())

    def test_requires_inspection_and_automatically_loads_job_labels(self):
        window = self.window()
        window.t1.setText(str(self.path))
        window.start_job()
        self.assertIsNone(window.runner)
        self.assertIn("Load and inspect", window.feedback.text())
        window.load_mri(self.path)
        self.wait_idle(window)
        script = self.root / "standin.py"
        script.write_text("import sys,shutil,meshio\nfrom pathlib import Path\nimport nibabel as nib\nimport numpy as np\n"
                          "subject, t1 = sys.argv[1:3]\np = Path('m2m_' + subject)\np.mkdir()\n"
                          "img = nib.load(t1)\nlabels = nib.Nifti1Image(np.ones(img.shape, np.uint16), img.affine)\n"
                          "labels.header.set_xyzt_units('mm')\nnib.save(labels, p / 'final_tissues.nii.gz')\n"
                          "shutil.copyfile(t1, p / 'T1.nii.gz')\n"
                          "mesh = meshio.Mesh(np.array([[0.,0,0],[2.,0,0],[0,3.,0]]), [('triangle', np.array([[0,1,2]]))], "
                          "cell_data={'gmsh:physical':[np.array([1001])], 'gmsh:geometrical':[np.array([1001])]})\n"
                          "meshio.write(p / (subject + '.msh'), mesh, file_format='gmsh22', binary=False)\n"
                          "print('stand-in complete', flush=True)\n", encoding="utf-8")
        if sys.platform == "win32":
            charm = self.root / "charm.cmd"
            charm.write_text(f'@echo off\n"{sys.executable}" -E -u "{script}" %*\n', encoding="utf-8")
        else:
            charm = self.root / "charm"
            charm.write_text(f'#!{sys.executable}\nexec(compile(open({str(script)!r}).read(), {str(script)!r}, "exec"))\n')
            charm.chmod(0o755)
        window.charm.setText(str(charm))
        window.t2.clear()
        window.output.setText(str(self.root))
        window.subject.setText("prototype_check")
        window.start_job()
        self.assertFalse(window.open_button.isEnabled())
        self.wait_idle(window)
        self.assertTrue(window.runner.complete)
        self.assertIsNotNone(window.overlay)
        self.assertEqual(window.tabs.currentIndex(), 0)
        self.assertIn("Label 1", window.legend.text())
        self.assertTrue(window.open_button.isEnabled())

    def test_changed_processing_path_requires_new_inspection(self):
        window = self.window()
        window.load_mri(self.path)
        self.wait_idle(window)
        other = self.save("other.nii", self.data, np.eye(4))
        window.t1.setText(str(other))
        window.start_job()
        self.assertIsNone(window.runner)
        self.assertIn("Load and inspect", window.feedback.text())

    def test_close_waits_for_active_image_worker(self):
        window = self.window()
        window.show()
        gate = threading.Event()
        window.run_task(lambda: gate.wait(2), lambda result: None)
        self.assertFalse(window.close())
        self.assertIn("loading is finishing", window.feedback.text())
        gate.set()
        self.wait_idle(window)
        self.assertTrue(window.close())


if __name__ == "__main__":
    unittest.main()
