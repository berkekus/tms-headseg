"""Lossless reorientation for model input, and its exact inverse.

Geometry travels with voxel indices: the affine written for the model is only a carrier,
so a sheared source keeps its true world mapping when labels return to the source grid.
"""

from dataclasses import dataclass

import nibabel as nib
from nibabel import orientations
import numpy as np

from .images import WORLD_TOLERANCE_MM, read_source, rigid_affine, shear_error, world_disagreement, write_nifti

_IDENTITY = np.array([[0., 1.], [1., 1.], [2., 1.]])


@dataclass(frozen=True)
class GeometryRecord:
    source_shape: tuple
    source_affine: np.ndarray
    source_axes: str
    to_canonical: np.ndarray
    canonical_shape: tuple
    canonical_affine: np.ndarray
    source_shear_error: float

    @property
    def model_affine(self):
        return rigid_affine(self.canonical_affine)

    def to_json(self):
        return {"source_shape": list(self.source_shape), "source_affine": self.source_affine.tolist(),
                "source_axes": self.source_axes, "to_canonical": self.to_canonical.tolist(),
                "canonical_shape": list(self.canonical_shape),
                "canonical_affine": self.canonical_affine.tolist(),
                "source_shear_error": self.source_shear_error}

    @classmethod
    def from_json(cls, values):
        return cls(tuple(values["source_shape"]), np.array(values["source_affine"]), values["source_axes"],
                   np.array(values["to_canonical"]), tuple(values["canonical_shape"]),
                   np.array(values["canonical_affine"]), values["source_shear_error"])


def canonicalize(data, affine):
    """Permute and flip axes toward RAS+ without interpolation; an oblique affine stays oblique."""
    to_canonical = orientations.io_orientation(affine)
    canonical = orientations.apply_orientation(data, to_canonical).copy()
    record = GeometryRecord(tuple(data.shape), affine.copy(), "".join(nib.aff2axcodes(affine)),
                            to_canonical, tuple(canonical.shape),
                            affine @ orientations.inv_ornt_aff(to_canonical, data.shape),
                            shear_error(affine))
    return canonical, record


def restore(data, record):
    """Return an array on the canonical grid to the source grid, voxel for voxel."""
    if tuple(data.shape) != record.canonical_shape:
        raise ValueError(f"Array shape {tuple(data.shape)} is not the canonical grid {record.canonical_shape}.")
    return orientations.apply_orientation(data, orientations.ornt_transform(_IDENTITY, record.to_canonical)).copy()


def write_model_input(source, path):
    """Write the canonical image with one ITK-readable geometry and return its record."""
    canonical, record = canonicalize(source.data, source.affine)
    write_nifti(path, canonical, record.model_affine)
    return record


def read_model_output(path, record):
    """Return labels on the source grid after checking they stayed on the model input grid."""
    output = read_source(path)
    if (tuple(output.data.shape) != record.canonical_shape
            or world_disagreement(output.affine, record.model_affine, output.data.shape) > WORLD_TOLERANCE_MM):
        raise ValueError(f"{output.path.name} is not on the model input grid.")
    return restore(output.data, record)
