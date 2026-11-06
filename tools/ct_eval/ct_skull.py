"""Score a predicted skull against a CT bone reference on the same grid (plan F8, independent of charm).

Datasets such as SynthRAD2023 (D15) ship an MR and a CT already registered on one voxel grid. The CT
shows bone directly, so it gives a skull reference that no MR segmenter produced. This module

1. thresholds the CT (`BONE_HU`), closes 1-voxel gaps and drops isolated parts smaller than
   `MIN_PART_ML` (intracranial calcifications);
2. keeps only voxels where the MR has signal (`outside_acquisition` removes padding and defacing, where
   the CT may still show bone the MR never saw);
3. scores the predicted skull label in the cranial vault, from the vertex down `CALVARIA_MM`, and in
   the whole field with signal. Metrics: Dice, mean symmetric surface distance and its 95th percentile.

The CT is evaluation data only: nothing here is used for training.

    python ct_skull.py --ct ct.nii.gz --mr mr.nii.gz --pred prediction.nii.gz [--charm] [--json out.json]
"""
import argparse
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "nnunet_prep"))
sys.path.insert(0, str(HERE.parent))
from prepare_e2 import outside_acquisition  # noqa: E402
from headmodel.labels import CHARM_TO_PROJECT, SKULL  # noqa: E402

BONE_HU = 300
MIN_PART_ML = 1.0
CALVARIA_MM = 70.0


def canonical(path):
    img = nib.as_closest_canonical(nib.load(str(path)))
    return np.asanyarray(img.dataobj), img.affine, np.asarray(img.header.get_zooms()[:3], float)


def ct_bone(ct, spacing, threshold=BONE_HU, min_part_ml=MIN_PART_ML):
    """CT voxels above `threshold` HU, 1-voxel gaps closed, parts below `min_part_ml` dropped."""
    bone = ndimage.binary_closing(ct > threshold, structure=ndimage.generate_binary_structure(3, 1))
    parts, n = ndimage.label(bone)
    if n == 0:
        return bone
    sizes = np.bincount(parts.ravel())[1:] * np.prod(spacing) / 1000.0
    return np.isin(parts, np.flatnonzero(sizes >= min_part_ml) + 1)


def calvaria(reference, spacing, depth_mm=CALVARIA_MM):
    """Boolean mask of the axial slabs from the top of the reference skull down `depth_mm` (RAS grid)."""
    slices = np.flatnonzero(reference.any(axis=(0, 1)))
    if slices.size == 0:
        raise ValueError("The CT reference holds no bone.")
    top = slices.max()
    low = max(0, int(round(top - depth_mm / spacing[2])) + 1)
    region = np.zeros(reference.shape, bool)
    region[:, :, low:top + 1] = True
    return region


def surface(mask):
    return mask & ~ndimage.binary_erosion(mask, structure=ndimage.generate_binary_structure(3, 1))


def compare(pred, ref, region, spacing):
    """Dice in `region`, and surface distances (mm) for boundary points inside `region`.

    Boundaries come from the full masks, so the region's own cut planes add no false surface."""
    p, r = pred & region, ref & region
    total = int(p.sum() + r.sum())
    result = {"dice": 2.0 * int((p & r).sum()) / total if total else float("nan"),
              "pred_ml": float(p.sum() * np.prod(spacing) / 1000.0),
              "ref_ml": float(r.sum() * np.prod(spacing) / 1000.0)}
    sp, sr = surface(pred), surface(ref)
    if not sp.any() or not sr.any():
        result.update(assd_mm=float("nan"), hd95_mm=float("nan"))
        return result
    to_ref = ndimage.distance_transform_edt(~sr, sampling=spacing)[sp & region]
    to_pred = ndimage.distance_transform_edt(~sp, sampling=spacing)[sr & region]
    both = np.concatenate([to_ref, to_pred])
    result.update(assd_mm=float(both.mean()) if both.size else float("nan"),
                  hd95_mm=float(np.percentile(both, 95)) if both.size else float("nan"))
    return result


def evaluate(ct_path, mr_path, pred_path, charm=False, threshold=BONE_HU, depth_mm=CALVARIA_MM):
    ct, affine, spacing = canonical(ct_path)
    mr, mr_affine, _ = canonical(mr_path)
    labels, pred_affine, _ = canonical(pred_path)
    for name, other in (("MR", mr_affine), ("prediction", pred_affine)):
        if not np.allclose(affine, other, atol=1e-3):
            raise ValueError(f"CT and {name} are not on the same grid; resample before scoring.")
    if not (ct.shape == mr.shape == labels.shape):
        raise ValueError(f"Shapes differ: CT {ct.shape}, MR {mr.shape}, prediction {labels.shape}.")
    labels = np.rint(labels).astype(np.int64)
    if charm:
        skull_values = [k for k, v in CHARM_TO_PROJECT.items() if v == SKULL]
        pred = np.isin(labels, skull_values)
    else:
        pred = labels == SKULL
    signal = ~outside_acquisition(mr)
    ref = ct_bone(ct, spacing, threshold) & signal
    pred &= signal
    vault = calvaria(ref, spacing, depth_mm) & signal
    return {"threshold_hu": threshold, "calvaria_mm": depth_mm, "labels": "charm" if charm else "project",
            "calvaria": compare(pred, ref, vault, spacing), "field": compare(pred, ref, signal, spacing)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ct", type=Path, required=True)
    parser.add_argument("--mr", type=Path, required=True, help="The MR the prediction was made from")
    parser.add_argument("--pred", type=Path, required=True, help="Label map on the MR grid")
    parser.add_argument("--charm", action="store_true", help="--pred is charm final_tissues (labels 4, 7, 8 = skull)")
    parser.add_argument("--threshold", type=float, default=BONE_HU, help=f"Bone threshold in HU (default {BONE_HU})")
    parser.add_argument("--calvaria-mm", type=float, default=CALVARIA_MM)
    parser.add_argument("--json", type=Path, help="Write the result here")
    args = parser.parse_args(argv)
    result = evaluate(args.ct, args.mr, args.pred, args.charm, args.threshold, args.calvaria_mm)
    text = json.dumps(result, indent=2)
    print(text)
    if args.json:
        args.json.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
