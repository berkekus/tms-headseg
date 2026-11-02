"""Named coordinate frames. World means RAS+ millimetres; LPS exists only at ITK boundaries."""

import nibabel as nib
import numpy as np

_LPS_SIGNS = np.array([-1., -1., 1.])


def ras_to_lps(points):
    return np.asarray(points, dtype=float) * _LPS_SIGNS


def lps_to_ras(points):
    return np.asarray(points, dtype=float) * _LPS_SIGNS


def voxel_to_world(affine, voxels):
    return nib.affines.apply_affine(affine, voxels)


def world_to_voxel(affine, points):
    return nib.affines.apply_affine(np.linalg.inv(affine), points)


def affine_to_itk(affine):
    """Spacing, LPS origin, and row-major LPS direction cosines for an RAS affine."""
    linear = _LPS_SIGNS[:, None] * affine[:3, :3]
    spacing = np.linalg.norm(linear, axis=0)
    return tuple(spacing), tuple(ras_to_lps(affine[:3, 3])), tuple((linear / spacing).ravel())


def itk_to_affine(spacing, origin, direction):
    affine = np.eye(4)
    affine[:3, :3] = _LPS_SIGNS[:, None] * (np.reshape(direction, (3, 3)) * np.asarray(spacing))
    affine[:3, 3] = lps_to_ras(origin)
    return affine
