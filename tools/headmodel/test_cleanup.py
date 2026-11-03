"""Class-specific cleanup must remove noise without inventing or erasing anatomy."""

import unittest

import numpy as np
from scipy import ndimage

from headmodel.cleanup import clean_labels, head_envelope
from headmodel.frames import voxel_to_world, world_to_voxel
from headmodel.labels import CSF, GRAY_MATTER, SKIN, SKULL, WHITE_MATTER
from headmodel.phantom import RIGHT_VENTRICLE, phantom_labels


def phantom(spacing=2.):
    shape = (101, 111, 111)
    affine = np.diag([spacing, spacing, spacing, 1.])
    affine[:3, 3] = -np.array(shape) * spacing / 2
    return phantom_labels(shape, affine), affine


def voxel_at(labels, tissue):
    return tuple(np.argwhere(labels == tissue)[len(np.argwhere(labels == tissue)) // 2])


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.labels, self.affine = phantom()

    def clean(self, labels, **options):
        return clean_labels(labels, self.affine, **options)

    def test_clean_phantom_is_unchanged(self):
        result = self.clean(self.labels)
        np.testing.assert_array_equal(result.labels, self.labels)
        self.assertEqual(result.warnings, ())

    def test_floating_noise_outside_the_head_is_removed(self):
        noisy = self.labels.copy()
        noisy[2:4, 2:4, 2:4] = SKIN
        np.testing.assert_array_equal(self.clean(noisy).labels, self.labels)

    def test_small_tissue_island_takes_its_surroundings(self):
        noisy = self.labels.copy()
        x, y, z = voxel_at(noisy, WHITE_MATTER)
        noisy[x, y, z] = SKULL
        self.assertEqual(self.clean(noisy).labels[x, y, z], WHITE_MATTER)

    def test_small_brain_fragment_in_csf_becomes_csf(self):
        noisy = self.labels.copy()
        noisy[46:55, 50:60, 86:96] = CSF
        noisy[50, 55, 91] = GRAY_MATTER
        self.assertEqual(self.clean(noisy).labels[50, 55, 91], CSF)

    def test_ventricle_inside_the_brain_is_not_filled(self):
        center = np.round(world_to_voxel(self.affine, RIGHT_VENTRICLE)).astype(int)
        self.assertEqual(self.labels[tuple(center)], CSF)
        self.assertEqual(self.clean(self.labels).labels[tuple(center)], CSF)

    def test_skull_opening_stays_open(self):
        opened = self.labels.copy()
        skull = np.argwhere(opened == SKULL)
        top = skull[skull[:, 2] == skull[:, 2].max()][0]
        opened[top[0] - 3:top[0] + 4, top[1] - 3:top[1] + 4, top[2] - 8:top[2] + 1] = CSF
        result = self.clean(opened).labels
        self.assertEqual(result[top[0], top[1], top[2]], CSF)

    def test_internal_air_stays_background_while_the_envelope_is_solid(self):
        with_cavity = self.labels.copy()
        cavity = voxel_at(with_cavity, WHITE_MATTER)
        slices = tuple(slice(value - 2, value + 3) for value in cavity)
        with_cavity[slices] = 0
        result = self.clean(with_cavity)
        self.assertTrue((result.labels[slices] == 0).all())
        self.assertTrue(head_envelope(result.labels, self.affine)[slices].all())

    def with_airway(self):
        """An air pocket behind the nose, reached from outside only by a channel 4 voxels (8 mm) wide."""
        labels = self.labels.copy()
        points = voxel_to_world(self.affine, np.indices(labels.shape).reshape(3, -1).T)
        pocket = np.linalg.norm(points - (0, 70, -10), axis=1) < 9
        channel = (np.abs(points[:, 0]) < 4) & (np.abs(points[:, 2] + 10) < 4) & (points[:, 1] > 70)
        labels[(pocket | channel).reshape(labels.shape)] = 0
        return labels, pocket.reshape(labels.shape), channel.reshape(labels.shape)

    def test_air_behind_a_narrow_opening_is_inside_the_envelope(self):
        labels, pocket, _ = self.with_airway()
        envelope = head_envelope(labels, self.affine)
        self.assertTrue(envelope[pocket].all())

    def test_sealing_leaves_the_outer_surface_and_the_opening_mouth_unchanged(self):
        labels, pocket, channel = self.with_airway()
        envelope = head_envelope(labels, self.affine)
        unsealed = ndimage.binary_fill_holes(labels > 0)
        outside_airway = ~(pocket | channel)
        np.testing.assert_array_equal(envelope[outside_airway], unsealed[outside_airway])
        mouth = tuple(np.round(world_to_voxel(self.affine, (0, 99, -10))).astype(int))
        self.assertTrue(channel[mouth])
        self.assertFalse(envelope[mouth])

    def test_openings_wider_than_the_seal_stay_open(self):
        labels, pocket, _ = self.with_airway()
        self.assertFalse(head_envelope(labels, self.affine, seal_mm=2).any(where=pocket))

    def test_removed_large_brain_component_is_reported(self):
        split = self.labels.copy()
        split[13:16, 50:60, 50:62] = WHITE_MATTER  # inside the left ear, apart from the brain
        result = self.clean(split)
        self.assertTrue(any("brain component" in warning for warning in result.warnings))
        self.assertEqual(result.labels[14, 55, 56], SKIN)

    def test_volumes_are_reported_per_tissue_in_millilitres(self):
        result = self.clean(self.labels)
        count = (self.labels == GRAY_MATTER).sum()
        volume = result.volumes["gray_matter"]
        self.assertAlmostEqual(volume["before_ml"], count * 8 / 1000)
        self.assertEqual(volume["before_ml"], volume["after_ml"])
        self.assertEqual(volume["change_percent"], 0)

    def test_large_volume_change_is_a_warning_not_a_failure(self):
        noisy = self.labels.copy()
        csf = np.argwhere(noisy == CSF)
        for x, y, z in csf[::10]:
            noisy[x, y, z] = WHITE_MATTER
        result = self.clean(noisy)
        self.assertTrue(any("csf" in warning for warning in result.warnings))
        self.assertEqual(result.labels.shape, noisy.shape)

    def test_settings_are_recorded(self):
        result = self.clean(self.labels, min_island_mm3=64)
        self.assertEqual(result.settings["min_island_mm3"], 64)

    def test_labels_outside_the_schema_stop_cleanup(self):
        with self.assertRaisesRegex(ValueError, "6"):
            self.clean(np.where(self.labels == SKIN, 6, self.labels))


if __name__ == "__main__":
    unittest.main()
