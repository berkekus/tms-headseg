"""E1 volume/display integration; synthetic data, no inference or native GL."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import nibabel as nib
import numpy as np
from PySide6.QtWidgets import QApplication

import model
from prototype import Window
from volume import load_volume


class E1ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.affine = np.diag([2., 3., 4., 1.])
        self.affine[:3, 3] = [10, 20, 30]
        self.labels = np.zeros((14, 15, 16), np.uint8)
        for label in range(1, 6):
            self.labels[2 * label:2 * label + 2, 3:8, 4:10] = label
        self.mri = self.save("T1.nii.gz", self.labels.astype(np.float32) * 10)
        self.pred = self.save("prediction.nii.gz", self.labels)

    def save(self, name, data, affine=None, units="mm"):
        image = nib.Nifti1Image(data, self.affine if affine is None else affine)
        image.header.set_xyzt_units(units)
        path = self.root / name
        nib.save(image, path)
        return path

    def load(self, mri=None, prediction=None, **kwargs):
        loader = getattr(model, "load_e1_model", None)
        self.assertTrue(callable(loader), "E1 prediction import is missing")
        return loader(mri or self.mri, prediction or self.pred, **kwargs)

    def wait_idle(self, window):
        deadline = time.monotonic() + 12
        while window.task is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIsNone(window.task, window.feedback.text())

    def test_e1_surfaces_and_labels_retain_source_grid_and_names(self):
        before = [p.read_bytes() for p in (self.mri, self.pred)]
        loaded = self.load()
        self.assertEqual(loaded.kind, "e1")
        self.assertIsNone(loaded.mesh_path)
        self.assertIsNone(loaded.report)
        self.assertEqual([s.tag for s in loaded.surfaces], [1, 2, 3, 4, 5])
        self.assertEqual(loaded.tissues[1][0], "Skin")
        self.assertEqual(loaded.tissues[4][0], "Gray matter")
        np.testing.assert_array_equal(loaded.labels[1], self.labels)
        skin = loaded.surfaces[0]
        # Surface is generated from source voxels, then transformed once to world mm.
        self.assertGreaterEqual(skin.points[:, 0].min(), 11)
        self.assertLessEqual(skin.points[:, 0].max(), 18)
        self.assertLessEqual(sum(len(s.triangles) for s in loaded.surfaces), 360_000)
        self.assertIn("display", loaded.geometry_note.lower())
        self.assertEqual([p.read_bytes() for p in (self.mri, self.pred)], before)

    def test_unknown_units_require_explicit_opt_in_and_stay_visible(self):
        unknown = self.save("unknown.nii.gz", self.labels.astype(np.float32), units="unknown")
        unknown_pred = self.save("unknown_pred.nii.gz", self.labels, units="unknown")
        before = [p.read_bytes() for p in (unknown, unknown_pred)]
        with self.assertRaisesRegex(ValueError, "units"):
            self.load(mri=unknown, prediction=unknown_pred)
        loaded = self.load(mri=unknown, prediction=unknown_pred, assume_mm=True)
        self.assertTrue(loaded.volume.units_assumed)
        self.assertIn("assumed", loaded.geometry_note.lower())
        with self.assertRaisesRegex(ValueError, "units"):
            load_volume(unknown)
        self.assertEqual([p.read_bytes() for p in (unknown, unknown_pred)], before)

    def test_known_units_do_not_acquire_an_assumption_when_opt_in_enabled(self):
        loaded = self.load(assume_mm=True)
        self.assertFalse(loaded.volume.units_assumed)
        self.assertNotIn("assumed", loaded.geometry_note.lower())

    def test_prediction_only_unknown_units_have_explicit_model_provenance(self):
        pred = self.save("unknown_prediction.nii.gz", self.labels, units="unknown")
        loaded = self.load(prediction=pred, assume_mm=True)
        self.assertTrue(getattr(loaded, "units_assumed", False), "Prediction unit assumption must be recorded independently of MRI units")
        self.assertFalse(loaded.volume.units_assumed)
        self.assertIn("assumed", loaded.geometry_note.lower())

    def test_mixed_meter_and_mm_headers_share_world_coordinates(self):
        affine = self.affine.copy()
        affine[:3] /= 1000
        meters = self.save("meters.nii.gz", self.labels.astype(np.float32), affine, "meter")
        loaded = self.load(mri=meters)
        np.testing.assert_allclose(loaded.volume.source_affine, self.affine, atol=1e-5)
        self.assertEqual(loaded.labels[1].shape, self.labels.shape)

    def test_invalid_labels_and_shifted_prediction_are_rejected(self):
        self.assertTrue(callable(getattr(model, "load_e1_model", None)), "E1 prediction import is missing")
        for name, values in [("invalid", self.labels + 1), ("continuous", self.labels + .25),
                             ("empty", np.zeros_like(self.labels))]:
            path = self.save(name + ".nii.gz", values)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.load(prediction=path)
        shifted = self.affine.copy()
        shifted[0, 3] += 2
        with self.assertRaisesRegex(ValueError, "grid"):
            self.load(prediction=self.save("shifted.nii.gz", self.labels, shifted))

    def test_source_orientation_can_differ_from_display_without_losing_alignment(self):
        affine = self.affine.copy()
        affine[0, 0] = -2
        mri = self.save("LAS.nii.gz", self.labels.astype(np.float32), affine)
        pred = self.save("LAS_pred.nii.gz", self.labels, affine)
        loaded = self.load(mri=mri, prediction=pred)
        np.testing.assert_array_equal(loaded.labels[1], self.labels[::-1])
        skin = loaded.surfaces[0]
        self.assertLess(skin.points[:, 0].max(), 9)

    def test_ui_uses_e1_presets_and_clears_failed_replacement(self):
        window = Window()
        self.addCleanup(window.close)
        self.assertTrue(hasattr(window, "load_e1_prediction"), "Desktop E1 action is missing")
        window.load_e1_prediction(self.mri, self.pred)
        self.assertFalse(window.open_e1_button.isEnabled())
        self.wait_idle(window)
        self.assertEqual(window.head_model.kind, "e1", window.feedback.text())
        self.assertIsNone(window.runner)
        self.assertFalse(window.existing_report_button.isEnabled())
        self.assertIn("Gray matter (4)", window.legend.text())
        self.assertIn("Skin", window.mesh_view.checks[1].text())
        window.mesh_view.preset(True)
        self.assertTrue(window.mesh_view.checks[4].isChecked())
        self.assertFalse(window.mesh_view.checks[2].isChecked())
        window.mesh_view.preset(False)
        self.assertTrue(window.mesh_view.checks[1].isChecked())
        self.assertEqual(window.mesh_view.sliders[1].value(), 100)
        self.assertEqual(window.panels[0].colors[4], window.head_model.tissues[4][1])
        window.load_e1_prediction(self.mri, self.root / "missing.nii.gz")
        self.wait_idle(window)
        self.assertIsNone(window.head_model)
        self.assertIsNone(window.volume)
        self.assertEqual(window.mesh_view.checks, {})
        self.assertIn("Could not load", window.feedback.text())

    def test_picker_cancellation_preserves_the_existing_mri(self):
        window = Window()
        self.addCleanup(window.close)
        window.load_mri(self.mri)
        self.wait_idle(window)
        old = window.volume
        self.assertTrue(hasattr(window, "choose_e1_prediction"), "Desktop E1 action is missing")
        with patch("prototype.QFileDialog.getOpenFileName", side_effect=[(str(self.mri), ""), ("", "")]):
            window.choose_e1_prediction()
        self.assertIs(window.volume, old)
        self.assertIsNone(window.task)

    def test_e1_prediction_with_stated_units_exports_through_k3(self):
        loaded = self.load()
        self.assertEqual(loaded.export_source, (self.mri, self.pred, "project"))
        window = Window()
        self.addCleanup(window.close)
        window.load_e1_prediction(self.mri, self.pred)
        self.wait_idle(window)
        self.assertTrue(window.export_button.isEnabled())
        folder = self.root / "e1_export"
        window.export_model(folder)
        self.wait_idle(window)
        self.assertTrue((folder / "model.json").is_file())
        self.assertEqual(window.head_model.kind, "project")
        self.assertEqual({surface.role for surface in window.head_model.surfaces}, {"head", "brain"})

    def test_e1_prediction_with_assumed_units_is_not_exported(self):
        unknown = self.save("unknown.nii.gz", self.labels.astype(np.float32), units="unknown")
        self.assertIsNone(self.load(mri=unknown, assume_mm=True).export_source)
        window = Window()
        self.addCleanup(window.close)
        window.load_e1_prediction(unknown, self.pred, assume_mm=True)
        self.wait_idle(window)
        self.assertFalse(window.export_button.isEnabled())
        self.assertIn("export needs", window.feedback.text().lower())

    def test_assumption_is_shown_in_ui_and_not_used_by_later_mri_import(self):
        window = Window()
        self.addCleanup(window.close)
        self.assertTrue(hasattr(window, "load_e1_prediction"), "Desktop E1 action is missing")
        unknown = self.save("unknown.nii.gz", self.labels.astype(np.float32), units="unknown")
        window.load_e1_prediction(unknown, self.pred, assume_mm=True)
        self.wait_idle(window)
        self.assertIn("assumed", window.metadata.text().lower())
        self.assertIn("assumed", window.feedback.text().lower())
        self.assertIn("assumed", window.mesh_view.summary.text().lower())
        window.load_mri(unknown)
        self.wait_idle(window)
        self.assertIsNone(window.volume)
        self.assertIn("units", window.feedback.text())


if __name__ == "__main__":
    unittest.main()
