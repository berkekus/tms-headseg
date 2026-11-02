"""Surface position, scale, side, and integrity, measured in world millimetres."""

import unittest

import numpy as np
from scipy.spatial import cKDTree

from headmodel.frames import voxel_to_world
from headmodel.images import rigid_affine
from headmodel.phantom import LEFT_EAR, NOSE, phantom_labels
from headmodel.reversible import canonicalize
from headmodel.surfaces import Mesh, boundary_contact, enclosed_volume, extract_surface, is_closed


def grid_affine(spacing, center_voxel, world_center=(0, 0, 0)):
    affine = np.diag([*spacing, 1.])
    affine[:3, 3] = np.asarray(world_center) - np.asarray(spacing) * center_voxel
    return affine


def ball(shape, affine, center, radius):
    points = voxel_to_world(affine, np.indices(shape).reshape(3, -1).T)
    return (np.linalg.norm(points - center, axis=1) <= radius).reshape(shape)


class SurfaceTests(unittest.TestCase):
    center = np.array([11., -7., 19.])

    def sphere(self, spacing=(1.5, 2., 1.2), radius=30.):
        shape = (61, 51, 71)
        affine = grid_affine(spacing, np.array(shape) / 2, self.center)
        return ball(shape, affine, self.center, radius), affine

    def test_radius_is_correct_with_anisotropic_spacing(self):
        mask, affine = self.sphere()
        mesh = extract_surface(mask, affine, smoothing_iterations=0)
        radii = np.linalg.norm(mesh.vertices - self.center, axis=1)
        self.assertAlmostEqual(radii.mean(), 30, delta=.4)
        self.assertLess(radii.max() - radii.min(), 2.5)

    def test_center_is_not_shifted_by_padding(self):
        mask, affine = self.sphere()
        mesh = extract_surface(mask, affine, smoothing_iterations=0)
        np.testing.assert_allclose(mesh.vertices.mean(axis=0), self.center, atol=.2)

    def test_surface_is_closed(self):
        mask, affine = self.sphere()
        self.assertTrue(is_closed(extract_surface(mask, affine)))

    def test_a_hole_or_a_flipped_triangle_is_not_closed(self):
        mask, affine = self.sphere()
        mesh = extract_surface(mask, affine)
        self.assertFalse(is_closed(Mesh(mesh.vertices, mesh.faces[1:])))
        flipped = mesh.faces.copy()
        flipped[0] = flipped[0][::-1]
        self.assertFalse(is_closed(Mesh(mesh.vertices, flipped)))

    def test_cropped_mask_still_gives_a_closed_surface(self):
        mask, affine = self.sphere()
        self.assertTrue(is_closed(extract_surface(mask[30:], affine)))

    def test_normals_point_outward_for_both_handedness(self):
        mask, affine = self.sphere(spacing=(1.5, 1.5, 1.5))
        flipped = affine.copy()
        flipped[0] = -flipped[0]
        exact = 4 / 3 * np.pi * 30 ** 3
        for current in (affine, flipped):
            self.assertAlmostEqual(enclosed_volume(extract_surface(mask, current)) / exact, 1, delta=.02)

    def test_smoothing_reduces_staircase_without_shrinking(self):
        mask, affine = self.sphere(spacing=(1.5, 1.5, 1.5))
        rough = extract_surface(mask, affine, smoothing_iterations=0)
        smooth = extract_surface(mask, affine)
        error = lambda mesh: np.linalg.norm(mesh.vertices - self.center, axis=1).std()
        self.assertLess(error(smooth), error(rough) * .6)
        self.assertAlmostEqual(enclosed_volume(smooth) / enclosed_volume(rough), 1, delta=.01)

    def test_asymmetric_anatomy_lands_on_the_correct_sides(self):
        shape = (121, 141, 131)
        affine = grid_affine((1.5, 1.5, 1.5), np.array(shape) / 2)
        mesh = extract_surface(phantom_labels(shape, affine) > 0, affine)
        self.assertAlmostEqual(mesh.vertices[:, 0].min(), -80, delta=1.5)
        self.assertAlmostEqual(mesh.vertices[:, 0].max(), 70, delta=1.5)
        self.assertAlmostEqual(mesh.vertices[:, 1].max(), 102, delta=1.5)
        self.assertAlmostEqual(mesh.vertices[:, 1].min(), -85, delta=1.5)
        self.assertLess(NOSE[1], mesh.vertices[:, 1].max())
        self.assertGreater(LEFT_EAR[0], mesh.vertices[:, 0].min())

    def test_same_anatomy_from_a_differently_ordered_source_grid(self):
        shape = (121, 141, 131)
        ras = grid_affine((1.5, 1.5, 1.5), np.array(shape) / 2)
        psr = np.array([[0, 0, 1.5, -90.75], [-1.5, 0, 0, 104.25], [0, -1.5, 0, 96.75], [0, 0, 0, 1]])
        first = extract_surface(phantom_labels(shape, ras) > 0, ras).vertices
        second = extract_surface(phantom_labels((141, 131, 121), psr) > 0, psr).vertices
        distance, _ = cKDTree(second).query(first)
        self.assertLess(distance.max(), 1e-6)

    def test_sheared_source_affine_defines_the_surface(self):
        affine = grid_affine((1.5, 1.5, 1.5), np.array((61, 61, 61)) / 2)
        affine[0, 1] = .3
        mask = np.zeros((61, 61, 61), bool)
        mask[20:40, 20:40, 20:40] = True
        mesh = extract_surface(mask, affine, smoothing_iterations=0)
        expected = voxel_to_world(affine, np.argwhere(mask))
        tree = cKDTree(expected)
        distance, _ = tree.query(mesh.vertices)
        self.assertLess(distance.max(), 1.5)
        rigid = extract_surface(mask, rigid_affine(affine), smoothing_iterations=0)
        self.assertGreater(np.abs(rigid.vertices - mesh.vertices).max(), 1)

    def test_empty_mask_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            extract_surface(np.zeros((4, 4, 4), bool), np.eye(4))

    def test_boundary_contact_names_anatomical_sides(self):
        mask = np.zeros((10, 10, 10), bool)
        mask[3:7, 3:7, 0:5] = True
        self.assertEqual(boundary_contact(mask, np.eye(4)), ["I"])
        psr = np.array([[0, 0, 1., 0], [-1., 0, 0, 0], [0, -1., 0, 0], [0, 0, 0, 1]])
        canonical_like = np.zeros((10, 10, 10), bool)
        canonical_like[0:5, 3:7, 3:7] = True
        self.assertEqual(boundary_contact(canonical_like, psr), ["A"])
        self.assertEqual(boundary_contact(np.zeros((4, 4, 4), bool), np.eye(4)), [])

    def test_canonical_and_source_grids_agree_on_contact(self):
        affine = np.array([[0, 0, 1., 0], [-1., 0, 0, 0], [0, -1., 0, 0], [0, 0, 0, 1]])
        mask = np.zeros((10, 10, 10), bool)
        mask[9, 3:7, 3:7] = True
        canonical, record = canonicalize(mask, affine)
        self.assertEqual(boundary_contact(mask, affine), boundary_contact(canonical, record.canonical_affine))


if __name__ == "__main__":
    unittest.main()
