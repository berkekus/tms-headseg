"""Axis-only reorientation must be lossless and keep every voxel at its world position."""

from itertools import permutations, product
from pathlib import Path
import tempfile
import unittest

import nibabel as nib
import numpy as np
import SimpleITK as sitk

from headmodel.frames import voxel_to_world
from headmodel.images import read_source, write_nifti
from headmodel.phantom import LEFT_EAR, NOSE, phantom_labels
from headmodel.reversible import (
    GeometryRecord, canonicalize, read_model_output, restore, write_model_input,
)


def axis_orientations():
    """All 48 axis permutation and flip combinations, with unequal spacing."""
    spacing = (1.1, 2.3, 3.7)
    for axes in permutations(range(3)):
        for signs in product((1, -1), repeat=3):
            affine = np.eye(4)
            affine[:3, :3] = 0
            for column, (axis, sign) in enumerate(zip(axes, signs)):
                affine[axis, column] = sign * spacing[column]
            affine[:3, 3] = (-40, 17, 9)
            yield affine


def voxel_grid(shape):
    return np.indices(shape).reshape(3, -1).T


class ReversibleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_restore_is_exact_for_every_axis_orientation(self):
        data = np.random.default_rng(3).integers(0, 200, (4, 5, 6), dtype=np.uint8)
        for affine in axis_orientations():
            canonical, record = canonicalize(data, affine)
            self.assertEqual(nib.aff2axcodes(record.canonical_affine), ("R", "A", "S"))
            np.testing.assert_array_equal(restore(canonical, record), data)

    def test_every_voxel_keeps_its_world_position(self):
        data = np.arange(4 * 5 * 6, dtype=np.int32).reshape(4, 5, 6)
        for affine in axis_orientations():
            canonical, record = canonicalize(data, affine)
            source_world = voxel_to_world(affine, voxel_grid(data.shape))[np.argsort(data.ravel())]
            order = np.argsort(canonical.ravel())
            canonical_world = voxel_to_world(record.canonical_affine, voxel_grid(canonical.shape))[order]
            np.testing.assert_allclose(canonical_world, source_world, atol=1e-9)

    def test_anatomy_keeps_its_sides_in_every_orientation(self):
        center = np.array([35, 35, 35])
        for affine in axis_orientations():
            grid = affine.copy()
            grid[:3, :3] = np.sign(affine[:3, :3]) * 3
            grid[:3, 3] = -grid[:3, :3] @ center
            labels = phantom_labels((71, 71, 71), grid)
            canonical, record = canonicalize(labels, grid)
            head = voxel_to_world(record.canonical_affine, np.argwhere(canonical > 0))
            self.assertLess(head[:, 0].min(), LEFT_EAR[0], "left ear lost")
            self.assertLess(head[:, 0].max(), -LEFT_EAR[0] - 5, "ear appears on the right")
            self.assertGreater(head[:, 1].max(), NOSE[1], "nose lost")
            self.assertGreater(head[:, 1].min(), -NOSE[1] + 5, "nose appears at the back")

    def test_record_survives_json(self):
        _, record = canonicalize(np.zeros((4, 5, 6)), next(axis_orientations()))
        restored = GeometryRecord.from_json(record.to_json())
        np.testing.assert_array_equal(restored.source_affine, record.source_affine)
        np.testing.assert_array_equal(restored.to_canonical, record.to_canonical)
        self.assertEqual(restored.source_shape, record.source_shape)
        self.assertEqual(restored.source_axes, record.source_axes)

    def test_restore_rejects_a_different_grid(self):
        _, record = canonicalize(np.zeros((4, 5, 6)), np.eye(4))
        with self.assertRaisesRegex(ValueError, "grid"):
            restore(np.zeros((4, 5, 7)), record)

    def save_source(self, affine, name="t1.nii.gz"):
        path = self.root / name
        write_nifti(path, np.arange(4 * 5 * 6, dtype=np.float32).reshape(4, 5, 6), affine)
        return read_source(path)

    def model_round_trip(self, source):
        """Input read and output written by SimpleITK, as nnU-Net does by default."""
        record = write_model_input(source, self.root / "model_input.nii.gz")
        image = sitk.ReadImage(str(self.root / "model_input.nii.gz"))
        labels = (sitk.GetArrayFromImage(image) % 6).astype(np.uint8)
        output = sitk.GetImageFromArray(labels)
        output.CopyInformation(image)
        sitk.WriteImage(output, str(self.root / "model_output.nii.gz"))
        expected = np.asarray(nib.load(self.root / "model_input.nii.gz").dataobj) % 6
        return record, read_model_output(self.root / "model_output.nii.gz", record), restore(expected.astype(np.uint8), record)

    def test_model_output_returns_to_the_source_grid(self):
        affine = np.array([[0, 0, 1.2, -5], [-1, 0, 0, 40], [0, -1, 0, 30], [0, 0, 0, 1.]])
        source = self.save_source(affine)
        self.assertEqual("".join(nib.aff2axcodes(source.affine)), "PIR")
        record, restored, expected = self.model_round_trip(source)
        self.assertEqual(restored.shape, source.data.shape)
        np.testing.assert_array_equal(restored, expected)
        self.assertEqual(record.source_axes, "PIR")

    def test_sheared_source_passes_through_itk_and_keeps_its_affine(self):
        affine = np.diag([1., 1., 1., 1.])
        affine[0, 1] = .08
        source = self.save_source(affine)
        self.assertGreater(len(source.warnings), 0)
        record, restored, expected = self.model_round_trip(source)
        np.testing.assert_array_equal(restored, expected)
        np.testing.assert_allclose(record.source_affine, affine)

    def test_model_output_on_another_grid_is_rejected(self):
        source = self.save_source(np.eye(4))
        record = write_model_input(source, self.root / "model_input.nii.gz")
        write_nifti(self.root / "moved.nii.gz", np.zeros((4, 5, 6), np.uint8), np.diag([1, 1, 1.5, 1]))
        with self.assertRaisesRegex(ValueError, "model input"):
            read_model_output(self.root / "moved.nii.gz", record)


if __name__ == "__main__":
    unittest.main()
