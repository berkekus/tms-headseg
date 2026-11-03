"""Read-only NIfTI inspection. Display grids use RAS world coordinates in mm."""

from dataclasses import dataclass
from itertools import product
from math import prod
from pathlib import Path

import nibabel as nib
from nibabel.processing import resample_from_to
import numpy as np


# shortcut: bound prototype memory use; use tiled/lazy rendering for larger scans.
MAX_VOXELS = 128_000_000


@dataclass
class Volume:
    path: Path
    image: nib.Nifti1Image
    source_affine: np.ndarray
    source_shape: tuple
    source_orientation: str
    source_spacing: np.ndarray
    window: tuple
    units_assumed: bool = False

    @property
    def data(self):
        return np.asarray(self.image.dataobj)


def read_image(path, assume_mm=False):
    path = Path(path).expanduser().resolve()
    if not str(path).lower().endswith((".nii", ".nii.gz")):
        raise ValueError("Choose a NIfTI file (.nii or .nii.gz). DICOM is not supported.")
    try:
        image = nib.load(path)
        if not isinstance(image, (nib.Nifti1Image, nib.Nifti2Image)):
            raise ValueError("Only NIfTI volumes are supported.")
        if len(image.shape) < 3 or any(size != 1 for size in image.shape[3:]) or min(image.shape[:3]) < 2:
            raise ValueError("Choose one 3D volume with at least two voxels on each spatial axis.")
        if prod(image.shape) > MAX_VOXELS:
            raise ValueError("Volume exceeds the prototype limit of 128 million voxels.")
        if image.get_data_dtype().kind not in "iuf":
            raise ValueError("MRI data must contain real numeric voxel values.")
        affine = np.array(image.affine, dtype=float, copy=True)
        if (not np.isfinite(affine).all()
                or abs(np.linalg.det(affine[:3, :3])) < 1e-12
                or not np.allclose(affine[3], [0, 0, 0, 1])):
            raise ValueError("Image affine is invalid or singular.")
        if not any(int(image.header[key]) > 0 for key in ("sform_code", "qform_code")):
            raise ValueError("Image needs a coded qform or sform to establish orientation.")
        unit = image.header.get_xyzt_units()[0]
        assumed = unit == "unknown" and assume_mm
        scale = {"mm": 1, "meter": 1000, "micron": .001}.get("mm" if assumed else unit)
        if scale is None:
            raise ValueError("Image spatial units are unknown. Explicit spatial units are required.")
        affine[:3] *= scale
        data = image.get_fdata(dtype=np.float32, caching="unchanged")
        data = data.reshape(image.shape[:3])
        if not np.isfinite(data).all():
            raise ValueError("Image contains non-finite voxel values.")
        return path, nib.Nifti1Image(data, affine), assumed
    except (OSError, nib.filebasedimages.ImageFileError, EOFError) as error:
        raise ValueError(f"Cannot read NIfTI volume: {error}") from error


def bounds(image):
    corners = np.array(list(product(*[(0, n - 1) for n in image.shape])))
    world = nib.affines.apply_affine(image.affine, corners)
    return world.min(axis=0), world.max(axis=0)


def load_volume(path, assume_mm=False):
    path, source, assumed = read_image(path, assume_mm=assume_mm)
    spacing = nib.affines.voxel_sizes(source.affine)
    canonical = nib.as_closest_canonical(source)
    display_spacing = nib.affines.voxel_sizes(canonical.affine)
    # Resample oblique/sheared data so plane labels describe true world planes.
    if not np.allclose(canonical.affine[:3, :3], np.diag(display_spacing), atol=1e-4):
        low, high = bounds(source)
        extent = np.ceil((high - low) / display_spacing) + 1
        if not np.isfinite(extent).all() or np.any(extent > MAX_VOXELS):
            raise ValueError("World-aligned display grid exceeds the prototype memory limit.")
        shape = tuple(map(int, extent))
        if prod(shape) > MAX_VOXELS:
            raise ValueError("World-aligned display grid exceeds the prototype memory limit.")
        affine = np.diag([*display_spacing, 1.])
        affine[:3, 3] = low
        canonical = resample_from_to(source, (shape, affine), order=1)
    sample = np.asarray(canonical.dataobj).ravel()[::max(1, canonical.dataobj.size // 1_000_000)]
    low, high = np.percentile(sample, [.5, 99.5])
    width = max(float(high - low), 1.)
    return Volume(path, canonical, source.affine.copy(), source.shape,
                  "".join(nib.aff2axcodes(source.affine)), spacing,
                  (float((high + low) / 2), width), assumed)


def load_labels(path, volume, assume_mm=False):
    path, labels, _ = read_image(path, assume_mm=assume_mm)
    data = np.asarray(labels.dataobj)
    if np.any(data < 0) or np.any(data != np.floor(data)) or np.max(data) > 65535:
        raise ValueError("Tissue labels must be non-negative integer IDs up to 65535.")
    ids = np.unique(data[data > 0]).astype(int)
    if not len(ids) or len(ids) > 256:
        raise ValueError("Choose a discrete segmentation with 1–256 nonzero label IDs.")
    low, high = bounds(labels)
    target_low, target_high = bounds(volume.image)
    if np.any(high < target_low) or np.any(low > target_high):
        raise ValueError("Label and MRI world coordinates do not overlap.")
    aligned = resample_from_to(labels, (volume.image.shape, volume.image.affine), order=0)
    result = np.asarray(aligned.dataobj, dtype=np.uint16)
    if not np.any(result):
        raise ValueError("No tissue labels overlap the MRI display grid.")
    return path, result, np.unique(result[result > 0]).astype(int)


def slice_data(data, axis, index):
    """Neurological display: L at screen left, A at top in axial view."""
    return np.flipud(np.take(data, index, axis=axis).T)
