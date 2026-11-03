"""Binary Gmsh round trips, model loading, coordinate preservation, and Qt state."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import meshio
import nibabel as nib
import numpy as np
from PySide6.QtWidgets import QApplication

from mesh_viewer import plane_geometry
from model import load_model, read_lut, read_surfaces, tissue_for_surface
from prototype import Window
from volume import load_volume


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "m2m_case"
        self.folder.mkdir()
        self.affine = np.diag([2., 3., 4., 1.])
        data = np.indices((5, 6, 7)).sum(0).astype(np.float32)
        image = nib.Nifti1Image(data, self.affine)
        image.header.set_xyzt_units("mm")
        nib.save(image, self.folder / "T1.nii.gz")
        image = nib.Nifti1Image(np.ones((5, 6, 7, 1), np.uint16), self.affine)
        image.header.set_xyzt_units("mm")
        nib.save(image, self.folder / "final_tissues.nii.gz")
        self.points = np.array([[0., 0, 0], [4., 0, 0], [0, 6., 0], [0, 0, 8.]])
        self.mesh_path = self.folder / "case.msh"
        self.write_mesh(self.points)
        (self.folder / "final_tissues_LUT.txt").write_text("1 White-Matter 230 230 230 255\n2 Gray-Matter 129 129 129 255\n5 Scalp 255 166 133 255\n")
        (self.folder / "charm_report.html").write_text("<html>example report</html>")

    def write_mesh(self, points):
        meshio.write(self.mesh_path, meshio.Mesh(points, [("triangle", np.array([[0, 1, 2], [0, 2, 3]]))],
                     cell_data={"gmsh:physical": [np.array([1002, 1005])],
                                "gmsh:geometrical": [np.array([1002, 1005])]}),
                     file_format="gmsh22", binary=True)

    def wait_idle(self, window):
        deadline = time.monotonic() + 12
        while window.task is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIsNone(window.task, window.feedback.text())

    def test_binary_mesh_preserves_world_coordinates_and_tags(self):
        before = self.mesh_path.read_bytes()
        model = load_model(self.folder)
        self.assertEqual([surface.tag for surface in model.surfaces], [1002, 1005])
        np.testing.assert_array_equal(model.surfaces[0].points, self.points[[0, 1, 2]])
        np.testing.assert_array_equal(model.surfaces[1].points, self.points[[0, 2, 3]])
        self.assertEqual(model.tissues[5], ("Scalp", (255, 166, 133)))
        self.assertEqual(model.report, (self.folder / "charm_report.html").resolve())
        self.assertEqual(self.mesh_path.read_bytes(), before)
        self.assertEqual(tissue_for_surface(1002), 2)
        self.assertIsNone(tissue_for_surface(2100))

    def test_mri_planes_use_same_physical_frame(self):
        volume = load_volume(self.folder / "T1.nii.gz")
        np.testing.assert_allclose(plane_geometry(volume, 2, 3), [[0, 0, 12], [8, 0, 12], [0, 15, 12]])
        np.testing.assert_allclose(plane_geometry(volume, 0, 2), [[4, 0, 0], [4, 15, 0], [4, 0, 24]])

    def test_missing_or_ambiguous_assets_fail_clearly(self):
        with self.assertRaisesRegex(ValueError, "existing"):
            load_model(self.folder / "missing")
        self.mesh_path.rename(self.folder / "other.msh")
        shutil.copyfile(self.folder / "other.msh", self.folder / "extra.msh")
        with self.assertRaisesRegex(ValueError, "unambiguously"):
            load_model(self.folder)
        (self.folder / "final_tissues.nii.gz").unlink()
        with self.assertRaisesRegex(ValueError, "final_tissues"):
            load_model(self.folder)

    def test_rejects_malformed_nonfinite_and_nonoverlapping_meshes(self):
        volume = load_volume(self.folder / "T1.nii.gz")
        self.write_mesh(self.points + 10000)
        with self.assertRaisesRegex(ValueError, "do not overlap"):
            read_surfaces(self.mesh_path, volume)
        self.mesh_path.write_bytes(b"not a mesh")
        with self.assertRaisesRegex(ValueError, "Cannot read"):
            read_surfaces(self.mesh_path, volume)
        bad = self.points.copy()
        bad[0, 0] = np.nan
        with patch("model.read_gmsh", return_value=SimpleNamespace(points=bad)):
            with self.assertRaisesRegex(ValueError, "finite"):
                read_surfaces(self.mesh_path, volume)

    def test_lookup_table_validation_and_numeric_fallback(self):
        lut = self.folder / "final_tissues_LUT.txt"
        lut.unlink()
        self.assertEqual(load_model(self.folder).tissues, {})
        lut.write_text("2 Gray matter 129 129 129 255\n")
        self.assertEqual(read_lut(lut)[2][0], "Gray matter")
        lut.write_text("2 Gray 300 129 129 255\n")
        with self.assertRaisesRegex(ValueError, "line 1"):
            read_lut(lut)

    def test_ui_reopens_model_without_processing_and_clears_stale_model(self):
        window = Window()
        self.addCleanup(window.close)
        window.load_head_model(self.folder)
        self.wait_idle(window)
        self.assertIsNotNone(window.head_model, window.feedback.text())
        self.assertIsNone(window.runner)
        self.assertTrue(window.existing_report_button.isEnabled())
        self.assertIn("White-Matter", window.legend.text())
        self.assertEqual(window.panels[0].colors[1], (230, 230, 230))
        self.assertEqual(set(window.mesh_view.checks), {1002, 1005})
        self.assertEqual(window.mesh_view.sliders[1005].value(), 20)
        window.mesh_view.preset(True)
        self.assertTrue(window.mesh_view.checks[1002].isChecked())
        self.assertFalse(window.mesh_view.checks[1005].isChecked())
        window.panels[0].slider.setValue(1)
        self.assertEqual(window.mesh_view.indices[2], 1)
        window.load_head_model(self.folder / "missing")
        self.wait_idle(window)
        self.assertIsNone(window.head_model)
        self.assertFalse(window.existing_report_button.isEnabled())
        self.assertEqual(window.mesh_view.checks, {})
        self.assertIsNone(window.volume)

    def test_switching_between_simnibs_and_e1_keeps_tissue_names_and_presets_separate(self):
        window = Window()
        self.addCleanup(window.close)
        window.load_head_model(self.folder)
        self.wait_idle(window)
        self.assertEqual(set(window.mesh_view.checks), {1002, 1005})
        window.load_e1_prediction(self.folder / "T1.nii.gz", self.folder / "final_tissues.nii.gz")
        self.wait_idle(window)
        self.assertEqual(window.head_model.kind, "e1", window.feedback.text())
        self.assertIn("Skin", window.mesh_view.checks[1].text())
        self.assertFalse(window.mesh_view.preset_buttons[True].isEnabled())
        self.assertTrue(window.mesh_view.preset_buttons[False].isEnabled())
        window.load_head_model(self.folder)
        self.wait_idle(window)
        self.assertEqual(window.head_model.kind, "simnibs")
        self.assertEqual(set(window.mesh_view.checks), {1002, 1005})
        self.assertIn("Scalp", window.mesh_view.checks[1005].text())
        self.assertEqual(window.mesh_view.sliders[1005].value(), 20)
        window.mesh_view.preset(True)
        self.assertTrue(window.mesh_view.checks[1002].isChecked())


if __name__ == "__main__":
    unittest.main()
