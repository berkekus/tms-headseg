"""NIfTI reading and writing under the project coordinate contract."""

from dataclasses import dataclass
from itertools import product
from pathlib import Path

import nibabel as nib
import numpy as np

from .frames import voxel_to_world

SHEAR_TOLERANCE = 1e-3
WORLD_TOLERANCE_MM = .01
UNIT_TO_MM = {"mm": 1., "meter": 1000., "micron": .001}


@dataclass(frozen=True)
class Source:
    path: Path
    data: np.ndarray
    affine: np.ndarray
    warnings: tuple


def shear_error(affine):
    """Largest departure of the direction cosines from orthonormal."""
    linear = affine[:3, :3]
    rotation = linear / np.linalg.norm(linear, axis=0)
    return float(np.abs(rotation.T @ rotation - np.eye(3)).max())


def rigid_affine(affine):
    """Nearest rotation at the same spacing; an orthonormal affine comes back unchanged."""
    if shear_error(affine) <= SHEAR_TOLERANCE:
        return affine
    zooms = np.linalg.norm(affine[:3, :3], axis=0)
    u, _, vt = np.linalg.svd(affine[:3, :3] / zooms)
    rigid = affine.copy()
    rigid[:3, :3] = (u @ vt) * zooms
    return rigid


def world_disagreement(first, second, shape):
    """Largest distance in millimetres between two affines at the image corners."""
    corners = np.array(list(product(*[(0, size - 1) for size in shape])))
    return float(np.linalg.norm(voxel_to_world(first, corners) - voxel_to_world(second, corners), axis=1).max())


def read_source(path):
    """Read one 3D volume with its affine in millimetres, or say why its geometry is undefined."""
    path = Path(path).expanduser().resolve()
    if not path.name.lower().endswith((".nii", ".nii.gz")):
        raise ValueError(f"{path.name}: choose a NIfTI file (.nii or .nii.gz).")
    try:
        image = nib.load(path)
        data = np.asanyarray(image.dataobj)
    except (OSError, EOFError, nib.filebasedimages.ImageFileError) as error:
        raise ValueError(f"Cannot read {path.name}: {error}") from error
    if len(image.shape) < 3 or any(size != 1 for size in image.shape[3:]) or min(image.shape[:3]) < 2:
        raise ValueError(f"{path.name}: choose one 3D volume with at least two voxels per axis.")
    header = image.header
    scale = UNIT_TO_MM.get(header.get_xyzt_units()[0])
    if scale is None:
        raise ValueError(f"{path.name}: spatial units are unknown; the writer must state them.")
    sform_code, qform_code = int(header["sform_code"]), int(header["qform_code"])
    if sform_code <= 0 and qform_code <= 0:
        raise ValueError(f"{path.name}: needs a coded qform or sform to define orientation.")
    affine = np.array(image.affine, dtype=float)
    affine[:3] *= scale
    if (not np.isfinite(affine).all() or abs(np.linalg.det(affine[:3, :3])) < 1e-12
            or not np.allclose(affine[3], [0, 0, 0, 1])):
        raise ValueError(f"{path.name}: the affine is invalid or singular.")
    if data.dtype.kind not in "iuf":
        raise ValueError(f"{path.name}: voxels must be real numbers.")
    if not np.isfinite(data).all():
        raise ValueError(f"{path.name}: contains non-finite voxel values.")
    warnings = []
    if sform_code > 0 and qform_code > 0:
        distance = scale * world_disagreement(header.get_sform(), header.get_qform(), image.shape[:3])
        if distance > WORLD_TOLERANCE_MM:
            warnings.append(f"qform and sform differ by up to {distance:.2f} mm; using the sform.")
    if shear_error(affine) > SHEAR_TOLERANCE:
        warnings.append("The affine contains shear, which ITK-based readers cannot represent.")
    return Source(path, data.reshape(image.shape[:3]), affine, tuple(warnings))


def write_nifti(path, data, affine):
    """Write stated millimetres and a single geometry; shear cannot be stored in a qform."""
    image = nib.Nifti1Image(data, affine)
    image.set_data_dtype(data.dtype)
    image.set_sform(affine, code=1)
    if shear_error(affine) > SHEAR_TOLERANCE:
        image.set_qform(None, code=0)
    else:
        image.set_qform(affine, code=1)
    image.header.set_xyzt_units("mm")
    nib.save(image, path)
