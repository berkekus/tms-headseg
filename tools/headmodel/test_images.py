"""Header policy of the coordinate contract, checked on written NIfTI files."""

from pathlib import Path
import tempfile
import unittest

import nibabel as nib
import numpy as np
import SimpleITK as sitk

from headmodel.frames import lps_to_ras, voxel_to_world
from headmodel.images import read_source, rigid_affine, shear_error, write_nifti


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = np.arange(4 * 5 * 6, dtype=np.float32).reshape(4, 5, 6)
        self.affine = np.diag([2., 3., 4., 1.])
        self.affine[:3, 3] = (-3, 5, 7)

    def save(self, name, data=None, affine=None, unit="mm", qform=1, sform=1):
        affine = self.affine if affine is None else affine
        image = nib.Nifti1Image(self.data if data is None else data, affine)
        image.set_sform(affine, code=sform)
        image.set_qform(affine, code=qform)
        image.header.set_xyzt_units(unit)
        path = self.root / name
        nib.save(image, path)
        return path

    def test_reads_geometry_in_millimetres_without_warnings(self):
        source = read_source(self.save("t1.nii.gz"))
        np.testing.assert_allclose(source.affine, self.affine)
        np.testing.assert_array_equal(source.data, self.data)
        self.assertEqual(source.warnings, ())

    def test_meter_headers_are_converted_to_millimetres(self):
        meters = self.affine.copy()
        meters[:3] /= 1000
        source = read_source(self.save("m.nii.gz", affine=meters, unit="meter"))
        np.testing.assert_allclose(source.affine, self.affine, rtol=1e-5)

    def test_trailing_singleton_dimension_is_removed(self):
        source = read_source(self.save("labels.nii.gz", data=self.data[..., None]))
        self.assertEqual(source.data.shape, (4, 5, 6))

    def test_rejects_inputs_with_undefined_geometry(self):
        nan = self.data.copy()
        nan[0, 0, 0] = np.nan
        self.root.joinpath("broken.nii.gz").write_bytes(b"not a volume")
        cases = {
            "NIfTI": self.root / "scan.dcm",
            "Cannot read": self.root / "broken.nii.gz",
            "one 3D": self.save("4d.nii.gz", data=np.stack([self.data] * 2, axis=3)),
            "units": self.save("unknown.nii.gz", unit="unknown"),
            "qform or sform": self.save("uncoded.nii.gz", qform=0, sform=0),
            "non-finite": self.save("nan.nii.gz", data=nan),
        }
        for message, path in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                read_source(path)

    def test_sform_wins_and_disagreement_is_reported(self):
        moved = self.affine.copy()
        moved[:3, 3] += 12
        image = nib.Nifti1Image(self.data, moved)
        image.set_sform(moved, code=2)
        image.set_qform(self.affine, code=1)
        image.header.set_xyzt_units("mm")
        path = self.root / "disagree.nii.gz"
        nib.save(image, path)
        source = read_source(path)
        np.testing.assert_allclose(source.affine, moved)
        self.assertEqual(len(source.warnings), 1)
        self.assertIn("qform and sform differ", source.warnings[0])

    def test_shear_is_measured_and_reported(self):
        sheared = self.affine.copy()
        sheared[0, 1] = .5
        self.assertGreater(shear_error(sheared), 1e-3)
        self.assertLess(shear_error(self.affine), 1e-9)
        source = read_source(self.save("sheared.nii.gz", affine=sheared, qform=0))
        np.testing.assert_allclose(source.affine, sheared)
        self.assertTrue(any("shear" in warning for warning in source.warnings))

    def test_rigid_affine_keeps_spacing_and_removes_shear(self):
        sheared = self.affine.copy()
        sheared[0, 1] = .5
        rigid = rigid_affine(sheared)
        self.assertLess(shear_error(rigid), 1e-9)
        np.testing.assert_allclose(np.linalg.norm(rigid[:3, :3], axis=0), np.linalg.norm(sheared[:3, :3], axis=0))
        np.testing.assert_array_equal(rigid_affine(self.affine), self.affine)

    def test_writer_states_units_and_agrees_across_libraries(self):
        path = self.root / "written.nii.gz"
        write_nifti(path, self.data, self.affine)
        header = nib.load(path).header
        self.assertEqual(header.get_xyzt_units()[0], "mm")
        self.assertEqual((int(header["sform_code"]), int(header["qform_code"])), (1, 1))
        np.testing.assert_allclose(header.get_qform(), header.get_sform(), atol=1e-4)
        self.assertEqual(read_source(path).warnings, ())
        loaded = sitk.ReadImage(str(path))
        itk_world = lps_to_ras(np.array(loaded.TransformIndexToPhysicalPoint((1, 2, 3))))
        np.testing.assert_allclose(itk_world, voxel_to_world(self.affine, (1, 2, 3)), atol=.01)

    def test_writer_keeps_a_sheared_affine_in_the_sform_only(self):
        sheared = self.affine.copy()
        sheared[0, 1] = .5
        path = self.root / "sheared.nii.gz"
        write_nifti(path, self.data, sheared)
        image = nib.load(path)
        np.testing.assert_allclose(image.affine, sheared)
        self.assertEqual(int(image.header["qform_code"]), 0)

    def test_writer_preserves_integer_label_values(self):
        labels = np.array([[[0, 1], [2, 5]], [[3, 4], [5, 0]]], np.uint8)
        path = self.root / "labels.nii.gz"
        write_nifti(path, labels, np.eye(4))
        loaded = read_source(path)
        self.assertEqual(loaded.data.dtype, np.uint8)
        np.testing.assert_array_equal(loaded.data, labels)


if __name__ == "__main__":
    unittest.main()
