"""Crop a RAS-ordered T1 to the head, so neck and shoulders do not reach the model.

E2 fails on a wide field of view (Ernie Extended: head, neck and shoulders; EXP-008) and works once the
image is cut to the head. The crop is found from the image alone:

1. Foreground = voxels above half the Otsu threshold; the largest 6-connected part is the body.
2. The vertex is the highest slice where that part covers at least MIN_SLICE_AREA_MM2.
3. Keep from VERTEX_MARGIN_MM above the vertex to HEAD_HEIGHT_MM below it.
4. The left-right and front-back limits come from the slab WIDTH_SLAB_MM below the vertex, which lies above
   the shoulders, plus SIDE_MARGIN_MM.

Inputs must be stored in RAS order (axis 2 increases superiorly); predict_e2.py reorients first.
"""
import nibabel as nib
import numpy as np
from scipy import ndimage

HEAD_HEIGHT_MM = 240.0
VERTEX_MARGIN_MM = 10.0
WIDTH_SLAB_MM = 180.0
SIDE_MARGIN_MM = 15.0
MIN_SLICE_AREA_MM2 = 100.0


def _otsu(values, bins=256):
    hist, edges = np.histogram(values, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    weight = np.cumsum(hist)
    mean = np.cumsum(hist * centers)
    total, total_mean = weight[-1], mean[-1]
    w0, w1 = weight[:-1], total - weight[:-1]
    valid = (w0 > 0) & (w1 > 0)
    between = np.zeros(len(w0))
    m0 = mean[:-1][valid] / w0[valid]
    m1 = (total_mean - mean[:-1][valid]) / w1[valid]
    between[valid] = w0[valid] * w1[valid] * (m0 - m1) ** 2
    return centers[np.argmax(between)]


def body_mask(data):
    values = data[np.isfinite(data)]
    if values.size == 0 or np.ptp(values) == 0:
        raise ValueError("Image has no contrast; cannot find the head.")
    upper = np.percentile(values, 99.5)
    threshold = _otsu(np.clip(values, values.min(), upper)) / 2
    foreground = np.nan_to_num(data) > threshold
    foreground = ndimage.binary_opening(foreground, iterations=2)
    parts, count = ndimage.label(foreground)
    if count == 0:
        raise ValueError("No foreground found; cannot find the head.")
    sizes = np.bincount(parts.ravel())
    sizes[0] = 0
    return parts == np.argmax(sizes)


def head_box(data, spacing):
    """Return (x, y, z) slices of the head in a RAS-ordered 3D array with voxel spacing in mm."""
    sx, sy, sz = (float(s) for s in spacing[:3])
    mask = body_mask(data)
    area = mask.sum(axis=(0, 1)) * sx * sy
    slices = np.flatnonzero(area >= MIN_SLICE_AREA_MM2)
    if slices.size == 0:
        raise ValueError("No slice holds enough head; cannot find the vertex.")
    top = int(slices.max())
    z0 = max(0, int(np.floor(top - HEAD_HEIGHT_MM / sz)))
    z1 = min(data.shape[2], int(np.ceil(top + VERTEX_MARGIN_MM / sz)) + 1)

    slab = mask[:, :, max(0, int(top - WIDTH_SLAB_MM / sz)):top + 1]
    xs = np.flatnonzero(slab.any(axis=(1, 2)))
    ys = np.flatnonzero(slab.any(axis=(0, 2)))
    mx, my = SIDE_MARGIN_MM / sx, SIDE_MARGIN_MM / sy
    x0, x1 = max(0, int(xs.min() - mx)), min(data.shape[0], int(xs.max() + mx) + 1)
    y0, y1 = max(0, int(ys.min() - my)), min(data.shape[1], int(ys.max() + my) + 1)
    return slice(x0, x1), slice(y0, y1), slice(z0, z1)


def crop_head(img):
    """Crop a RAS-ordered NIfTI to the head. Returns the cropped image (same world positions) and the box."""
    if nib.aff2axcodes(img.affine) != ("R", "A", "S"):
        raise ValueError(f"Expected RAS voxel order, got {''.join(nib.aff2axcodes(img.affine))}.")
    data = np.asarray(img.dataobj)
    if data.ndim != 3:
        raise ValueError("Expected a 3D image.")
    box = head_box(data, img.header.get_zooms()[:3])
    return img.slicer[box], box


def paste(labels, shape, box):
    """Put labels predicted on the cropped grid back into a background volume of the full shape."""
    full = np.zeros(shape, dtype=labels.dtype)
    full[box] = labels
    return full


def describe(box, shape):
    return {"source_shape": list(shape), "box_voxels": [[s.start, s.stop] for s in box],
            "cropped_shape": [s.stop - s.start for s in box]}


def _save_mm(data, affine, path):
    out = nib.Nifti1Image(data, affine)
    out.header.set_xyzt_units("mm")
    out.set_qform(affine, code=1)
    out.set_sform(affine, code=1)
    nib.save(out, path)


def crop_file(src, dst):
    """Crop a RAS-ordered NIfTI file to the head and save it; return the crop record."""
    img = nib.load(src)
    cropped, box = crop_head(img)
    _save_mm(np.asarray(cropped.dataobj), cropped.affine, dst)
    return describe(box, img.shape)


def paste_file(prediction, full_image, record, dst):
    """Paste labels predicted on the cropped grid back onto the grid of `full_image` and save them."""
    full = nib.load(full_image)
    box = tuple(slice(a, b) for a, b in record["box_voxels"])
    if list(full.shape[:3]) != record["source_shape"]:
        raise ValueError("The crop record does not belong to this image.")
    head = nib.load(prediction)
    if not np.allclose(head.affine, full.slicer[box].affine, atol=1e-3) or list(head.shape) != record["cropped_shape"]:
        raise ValueError("Prediction is not on the cropped grid; refusing to paste it back.")
    labels = paste(np.asarray(head.dataobj).astype(np.uint8), full.shape[:3], box)
    _save_mm(labels, full.affine, dst)
    return labels
