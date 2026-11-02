"""Closed triangle surfaces from binary masks, in world millimetres."""

from dataclasses import dataclass

import nibabel as nib
import numpy as np
from scipy import sparse
from skimage.measure import marching_cubes

from .frames import voxel_to_world
from .reversible import canonicalize

SMOOTHING_ITERATIONS = 20
_TAUBIN_STEPS = (.5, -.53)
_OPPOSITE = dict(zip("RLAPSI", "LRPAIS"))


@dataclass(frozen=True)
class Mesh:
    vertices: np.ndarray
    faces: np.ndarray


def _taubin(vertices, faces, iterations):
    """Low-pass smoothing that keeps volume; uniform weights do not depend on the frame."""
    count = len(vertices)
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    neighbors = sparse.coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(count, count)).tocsr()
    neighbors = ((neighbors + neighbors.T) > 0).astype(float)
    average = sparse.diags(1 / np.asarray(neighbors.sum(axis=1)).ravel()) @ neighbors
    for _ in range(iterations):
        for step in _TAUBIN_STEPS:
            vertices = vertices + step * (average @ vertices - vertices)
    return vertices


def extract_surface(mask, affine, smoothing_iterations=SMOOTHING_ITERATIONS):
    """Work in voxel units so the affine applies spacing exactly once; padding closes cut edges.

    Triangulation follows the array axes, so a canonical grid makes the result independent
    of how the source file ordered them.
    """
    if not mask.any():
        raise ValueError("Cannot extract a surface from an empty mask.")
    canonical, record = canonicalize(mask, affine)
    vertices, faces, _, _ = marching_cubes(np.pad(canonical, 1).astype(np.float32), level=.5)
    vertices = _taubin(vertices.astype(float) - 1, faces, smoothing_iterations)
    mesh = Mesh(voxel_to_world(record.canonical_affine, vertices), faces.astype(np.int64))
    # The sign of a closed surface's volume settles the winding for any affine handedness.
    return mesh if enclosed_volume(mesh) > 0 else Mesh(mesh.vertices, mesh.faces[:, ::-1])


def is_closed(mesh):
    """Every edge is shared by exactly two triangles, in opposite directions."""
    faces = mesh.faces
    start = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]])
    end = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]])
    count = len(mesh.vertices)
    forward, backward = np.sort(start * count + end), np.sort(end * count + start)
    return bool(np.all(forward[1:] != forward[:-1]) and np.array_equal(forward, backward))


def enclosed_volume(mesh):
    """Signed volume in cubic millimetres; positive when normals point outward."""
    a, b, c = np.moveaxis(mesh.vertices[mesh.faces], 1, 0)
    return float((a * np.cross(b, c)).sum() / 6)


def boundary_contact(mask, affine):
    """Anatomical sides where a mask reaches the image edge, such as a cropped face."""
    sides = []
    for axis, code in enumerate(nib.aff2axcodes(affine)):
        if np.take(mask, 0, axis=axis).any():
            sides.append(_OPPOSITE[code])
        if np.take(mask, -1, axis=axis).any():
            sides.append(code)
    return sorted(sides)
