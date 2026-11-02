"""Class-specific label cleanup; rules follow the table in labels-and-face.md.

The rules are proposals. Component removal can alter anatomy, so removals of real size
become warnings rather than silent edits, and nothing here is validated on clinical data.
"""

from dataclasses import dataclass
from math import ceil

import numpy as np
from scipy import ndimage

from .labels import BACKGROUND, CSF, GRAY_MATTER, SKULL, TISSUES, WHITE_MATTER, validate_project_labels

# Provisional: no island threshold is validated yet (Q-08).
MIN_ISLAND_MM3 = 100.
LARGE_COMPONENT_ML = 1.
VOLUME_WARNING_PERCENT = 2.

_ANY_TOUCH = np.ones((3, 3, 3), bool)


@dataclass(frozen=True)
class CleanResult:
    labels: np.ndarray
    volumes: dict
    warnings: tuple
    settings: dict


def _largest(mask):
    """Largest component, and the voxel counts of the components left out."""
    components, count = ndimage.label(mask, structure=_ANY_TOUCH)
    if count == 0:
        return mask, np.array([], dtype=np.int64)
    sizes = np.bincount(components.ravel())[1:]
    keep = int(sizes.argmax())
    return components == keep + 1, np.delete(sizes, keep)


def _islands(mask, min_voxels):
    components, count = ndimage.label(mask, structure=_ANY_TOUCH)
    if count == 0:
        return np.zeros_like(mask)
    small = np.bincount(components.ravel()) < min_voxels
    small[0] = False
    return small[components]


def head_envelope(labels):
    """Solid outer head: the largest tissue component with enclosed cavities filled."""
    return ndimage.binary_fill_holes(_largest(labels > BACKGROUND)[0])


def brain_mask(labels):
    return _largest((labels == GRAY_MATTER) | (labels == WHITE_MATTER))[0]


def _volumes(before, after, voxel_mm3):
    report = {}
    for value, name in TISSUES.items():
        first = int((before == value).sum()) * voxel_mm3 / 1000
        last = int((after == value).sum()) * voxel_mm3 / 1000
        change = 100 * (last - first) / first if first else (0. if not last else None)
        report[name] = {"before_ml": first, "after_ml": last, "change_percent": change}
    return report


def clean_labels(labels, affine, min_island_mm3=MIN_ISLAND_MM3):
    """Remove stray voxels and keep one exclusive label per voxel; cavities stay open."""
    original = validate_project_labels(labels)
    voxel_mm3 = abs(float(np.linalg.det(affine[:3, :3])))
    large = LARGE_COMPONENT_ML * 1000 / voxel_mm3
    warnings = []
    head, outside = _largest(original > BACKGROUND)
    if np.any(outside >= large):
        warnings.append(f"Removed a head component of {outside.max() * voxel_mm3 / 1000:.1f} mL; check anatomy.")
    cleaned = np.where(head, original, BACKGROUND)
    tissue = (cleaned == GRAY_MATTER) | (cleaned == WHITE_MATTER)
    brain, fragments = _largest(tissue)
    if np.any(fragments >= large):
        warnings.append(f"Removed a brain component of {fragments.max() * voxel_mm3 / 1000:.1f} mL; check anatomy.")
    removed = tissue & ~brain
    min_voxels = ceil(min_island_mm3 / voxel_mm3)
    for value in (SKULL, CSF, GRAY_MATTER, WHITE_MATTER):
        removed |= _islands(cleaned == value, min_voxels)
    if removed.any():
        spacing = np.linalg.norm(affine[:3, :3], axis=0)
        nearest = ndimage.distance_transform_edt(removed, sampling=spacing, return_distances=False, return_indices=True)
        cleaned = cleaned[tuple(nearest)]
    volumes = _volumes(original, cleaned, voxel_mm3)
    for name, volume in volumes.items():
        if volume["change_percent"] is not None and abs(volume["change_percent"]) > VOLUME_WARNING_PERCENT:
            warnings.append(f"Cleanup changed {name} volume by {volume['change_percent']:+.1f}%.")
    return CleanResult(cleaned, volumes, tuple(warnings), {"min_island_mm3": min_island_mm3})
