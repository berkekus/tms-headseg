"""Binary Gmsh round trips, model loading, coordinate preservation, and Qt state."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
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

from headmodel.build_model import build_model
from headmodel.images import write_nifti
from headmodel.phantom import phantom_labels


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

    def test_mri_planes_span_voxel_edges_in_the_physical_frame(self):
        volume = load_volume(self.folder / "T1.nii.gz")
        np.testing.assert_allclose(plane_geometry(volume, 2, 3), [[-1, -1.5, 12], [9, -1.5, 12], [-1, 16.5, 12]])
        np.testing.assert_allclose(plane_geometry(volume, 0, 2), [[4, -1.5, -2], [4, 16.5, -2], [4, -1.5, 26]])

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


class ProjectModelTests(unittest.TestCase):
    shape = (71, 65, 61)

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.affine = np.array([[0, 0, 3., -90], [-3., 0, 0, 105], [0, -3., 0, 96], [0, 0, 0, 1]])
        self.labels = phantom_labels(self.shape, self.affine)
        self.t1 = self.root / "T1.nii.gz"
        self.segmentation = self.root / "segmentation.nii.gz"
        write_nifti(self.t1, self.labels.astype(np.float32) * 100, self.affine)
        write_nifti(self.segmentation, self.labels, self.affine)
        self.folder = self.root / "model"

    def build(self):
        build_model(self.t1, self.segmentation, self.folder)
        return self.folder

    def wait_idle(self, window):
        deadline = time.monotonic() + 30
        while window.task is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIsNone(window.task, window.feedback.text())

    def test_project_numbers_are_not_read_as_simnibs_tissues(self):
        model = load_model(self.build())
        self.assertEqual(model.tissues[1][0], "Skin")
        self.assertEqual(model.tissues[5][0], "White matter")
        self.assertEqual({surface.role: surface.name for surface in model.surfaces}, {"head": "Head", "brain": "Brain"})

    def test_project_surfaces_stay_in_world_coordinates(self):
        model = load_model(self.build())
        head = next(surface for surface in model.surfaces if surface.role == "head")
        self.assertLess(head.points[:, 0].min(), -74)
        self.assertLess(head.points[:, 0].max(), 74)
        self.assertGreater(head.points[:, 1].max(), 96)

    def test_vtk_reads_the_declared_frame_as_binary_stl(self):
        from vtkmodules.vtkIOGeometry import vtkSTLReader
        self.build()
        record = json.loads((self.folder / "model.json").read_text(encoding="utf-8"))
        reader = vtkSTLReader()
        reader.SetFileName(str(self.folder / "head.stl"))
        reader.Update()
        self.assertIn("SPACE=RAS", reader.GetHeader())
        self.assertEqual(reader.GetOutput().GetNumberOfCells(), record["surfaces"]["head"]["triangles"])

    def test_notes_state_that_the_face_was_not_assessed(self):
        self.assertTrue(any("not assessed" in note for note in load_model(self.build()).notes))

    def test_tampered_project_model_is_refused(self):
        self.build()
        with (self.folder / "head.stl").open("ab") as file:
            file.write(b"\0")
        with self.assertRaisesRegex(ValueError, "verification"):
            load_model(self.folder)

    def test_ui_opens_a_project_model_with_role_based_presets(self):
        self.build()
        window = Window()
        self.addCleanup(window.close)
        window.load_head_model(self.folder)
        self.wait_idle(window)
        self.assertIsNotNone(window.head_model, window.feedback.text())
        view = window.mesh_view
        self.assertEqual(sorted(view.checks), [1, 2])
        self.assertIn("not assessed", view.summary.text())
        view.preset(True)
        self.assertEqual([tag for tag, check in view.checks.items() if check.isChecked()], [2])
        view.preset(False)
        self.assertEqual([tag for tag, check in view.checks.items() if check.isChecked()], [1])
        self.assertEqual(view.sliders[1].value(), 100)
        self.assertIn("Skin", window.legend.text())
        self.assertFalse(window.export_button.isEnabled())

    def charm_folder(self):
        folder = self.root / "m2m_case"
        folder.mkdir()
        charm = np.choose(self.labels, [0, 5, 7, 3, 2, 1]).astype(np.uint16)
        write_nifti(folder / "T1.nii.gz", self.labels.astype(np.float32) * 100, self.affine)
        write_nifti(folder / "final_tissues.nii.gz", charm, self.affine)
        points = np.array([[0., 0, 0], [40, 0, 0], [0, 40, 0], [0, 0, 40]])
        meshio.write(folder / "case.msh", meshio.Mesh(points, [("triangle", np.array([[0, 1, 2], [0, 2, 3]]))],
                     cell_data={"gmsh:physical": [np.array([1002, 1005])],
                                "gmsh:geometrical": [np.array([1002, 1005])]}),
                     file_format="gmsh22", binary=True)
        return folder

    def test_ui_exports_a_simnibs_folder_and_opens_the_result(self):
        window = Window()
        self.addCleanup(window.close)
        window.load_head_model(self.charm_folder())
        self.wait_idle(window)
        self.assertTrue(window.export_button.isEnabled())
        window.export_model(self.folder)
        self.wait_idle(window)
        self.assertEqual(window.head_model.directory, self.folder.resolve())
        self.assertEqual(sorted(window.mesh_view.checks), [1, 2])
        self.assertTrue((self.folder / "model.json").is_file())

    def test_ui_exports_project_labels_loaded_over_an_mri(self):
        window = Window()
        self.addCleanup(window.close)
        window.load_mri(self.t1)
        self.wait_idle(window)
        self.assertFalse(window.export_button.isEnabled())
        window.load_overlay(self.segmentation)
        self.wait_idle(window)
        self.assertTrue(window.export_button.isEnabled())
        window.export_model(self.folder)
        self.wait_idle(window)
        self.assertTrue((self.folder / "model.json").is_file())

    def test_ui_reports_an_export_that_cannot_run(self):
        self.folder.mkdir()
        window = Window()
        self.addCleanup(window.close)
        window.load_mri(self.t1)
        self.wait_idle(window)
        window.load_overlay(self.segmentation)
        self.wait_idle(window)
        window.export_model(self.folder)
        self.wait_idle(window)
        self.assertIn("already exists", window.feedback.text())


if __name__ == "__main__":
    unittest.main()
