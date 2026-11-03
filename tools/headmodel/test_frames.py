"""Frame conversions, including agreement between NiBabel and SimpleITK on real files."""

from pathlib import Path
import tempfile
import unittest

import nibabel as nib
import numpy as np
import SimpleITK as sitk

from headmodel.frames import (
    affine_to_itk, itk_to_affine, lps_to_ras, ras_to_lps, voxel_to_world, world_to_voxel,
)


def oblique_affine():
    x, y = np.radians(11), np.radians(-7)
    tilt = np.array([[1, 0, 0], [0, np.cos(x), -np.sin(x)], [0, np.sin(x), np.cos(x)]])
    turn = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    affine = np.eye(4)
    affine[:3, :3] = tilt @ turn @ np.diag([-1.1, 2.3, 3.7])
    affine[:3, 3] = (41.5, -17.25, 9.75)
    return affine


class FrameTests(unittest.TestCase):
    def test_lps_changes_only_the_first_two_signs(self):
        points = np.array([[10., -20., 30.], [-1., 2., -3.]])
        np.testing.assert_array_equal(ras_to_lps(points), [[-10, 20, 30], [1, -2, -3]])
        np.testing.assert_array_equal(lps_to_ras(ras_to_lps(points)), points)

    def test_voxel_world_round_trip_with_oblique_spacing_and_translation(self):
        voxels = np.array([[0., 0, 0], [3, 4, 5], [7.5, 1.25, 2]])
        world = voxel_to_world(oblique_affine(), voxels)
        np.testing.assert_allclose(world_to_voxel(oblique_affine(), world), voxels, atol=1e-9)

    def test_itk_geometry_round_trip(self):
        spacing, origin, direction = affine_to_itk(oblique_affine())
        np.testing.assert_allclose(spacing, (1.1, 2.3, 3.7))
        np.testing.assert_allclose(itk_to_affine(spacing, origin, direction), oblique_affine(), atol=1e-9)

    def test_both_libraries_give_one_position_for_one_voxel(self):
        data = np.arange(4 * 5 * 6, dtype=np.float32).reshape(4, 5, 6)
        image = nib.Nifti1Image(data, oblique_affine())
        image.set_qform(oblique_affine(), code=1)
        image.header.set_xyzt_units("mm")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "oblique.nii.gz"
            nib.save(image, path)
            loaded = sitk.ReadImage(str(path))
        for voxel in ((0, 0, 0), (3, 1, 2), (2, 4, 5)):
            itk_world = lps_to_ras(np.array(loaded.TransformIndexToPhysicalPoint(voxel)))
            np.testing.assert_allclose(itk_world, voxel_to_world(oblique_affine(), voxel), atol=.01)

    def test_itk_arrays_reverse_the_axis_order(self):
        data = np.arange(4 * 5 * 6, dtype=np.float32).reshape(4, 5, 6)
        array = sitk.GetArrayFromImage(sitk.GetImageFromArray(data.transpose(2, 1, 0)))
        self.assertEqual(array[5, 4, 3], data[3, 4, 5])


if __name__ == "__main__":
    unittest.main()
