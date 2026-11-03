"""Read-only technical audit of the fixed E1 handoff; never trains a model."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import nibabel as nib
import numpy as np


from colab_helpers import DATASET, require, sha256

LABELS = {"background": 0, "skin": 1, "skull": 2, "csf": 3, "gray_matter": 4, "white_matter": 5}


def audit(root):
    root = Path(root).resolve()
    dataset = root / "nnUNet_raw" / DATASET
    for path in (root / "test_holdout", dataset / "imagesTs", dataset / "labelsTs"):
        require(not path.exists(), f"Hold-out/test directory must stay outside this training package: {path.name}")
    metadata = json.loads((dataset / "dataset.json").read_text())
    require(metadata.get("labels") == LABELS, "Unexpected six-class label contract.")
    require(metadata.get("channel_names") == {"0": "T1"}, "Expected one T1 channel.")
    require(metadata.get("file_ending") == ".nii.gz", "Expected .nii.gz images.")
    folds = json.loads((root / "splits_final.json").read_text())
    require(len(folds) == 1 and set(folds[0]) == {"train", "val"}, "Expected exactly one fixed train/val fold.")
    train, val = folds[0]["train"], folds[0]["val"]
    require(len(train) == 44 and len(val) == 10, "Expected 44 train and 10 validation subjects.")
    require(all(isinstance(case, str) and re.fullmatch(r"[A-Za-z0-9_-]+", case) for case in train + val), "Invalid case ID.")
    require(len(set(train + val)) == 54, "Duplicate or overlapping train/validation subjects.")
    cases = set(train + val)
    require(metadata.get("numTraining") == len(cases), "dataset.json numTraining disagrees with the split.")
    images = {p.name for p in (dataset / "imagesTr").iterdir()}
    labels = {p.name for p in (dataset / "labelsTr").iterdir()}
    require(images == {f"{case}_0000.nii.gz" for case in cases}, "imagesTr contains missing, extra, or incorrectly named inputs.")
    require(labels == {f"{case}.nii.gz" for case in cases}, "labelsTr contains missing, extra, or incorrectly named labels.")
    report = {"dataset": DATASET, "train_count": 44, "validation_count": 10,
              "test_included": False, "labels": LABELS, "cases": [], "files": {},
              "warnings": [
                  "Label semantic mapping is inferred in the handoff and still needs review.",
                  "Removed-face ignore masks are absent; this is a preliminary tissue experiment, not validated face reconstruction.",
                  "Handoff reports orthonormalized NYU affines; original transforms/manifests are not included. Physical-space accuracy is not established.",
                  "Exact duplicates are checked, but subject identity and external test separation still rely on K1 provenance."
              ]}
    hashes = {}
    for case in sorted(cases):
        image_path = dataset / "imagesTr" / f"{case}_0000.nii.gz"
        label_path = dataset / "labelsTr" / f"{case}.nii.gz"
        image, label = nib.load(image_path), nib.load(label_path)
        require(isinstance(image, (nib.Nifti1Image, nib.Nifti2Image)) and isinstance(label, (nib.Nifti1Image, nib.Nifti2Image)), f"{case}: expected NIfTI images.")
        require(len(image.shape) == 3 and image.shape == label.shape, f"{case}: image/label shape mismatch or non-3D data.")
        require(0 < np.prod(image.shape, dtype=np.int64) <= 128_000_000, f"{case}: unsupported volume size.")
        require(np.isfinite(image.affine).all() and abs(np.linalg.det(image.affine[:3, :3])) > 1e-8, f"{case}: invalid affine.")
        require(np.allclose(image.affine, label.affine, atol=1e-4, rtol=0), f"{case}: image/label affines disagree.")
        units = (image.header.get_xyzt_units()[0], label.header.get_xyzt_units()[0])
        require(all(unit in ("mm", "unknown") for unit in units), f"{case}: spatial units need explicit conversion before nnU-Net.")
        if "unknown" in units:
            report["warnings"].append(f"{case}: NIfTI spatial units are unspecified; 1 mm is a handoff claim, not verified metadata.")
        data = image.get_fdata(dtype=np.float32, caching="unchanged")
        target = np.asanyarray(label.dataobj)
        require(np.isfinite(data).all() and np.isfinite(target).all(), f"{case}: non-finite values.")
        require(float(data.max()) > float(data.min()), f"{case}: constant image.")
        ids, counts = np.unique(target, return_counts=True)
        require(set(ids.tolist()) <= set(LABELS.values()), f"{case}: unexpected or non-integer label values: {ids.tolist()}")
        require(np.any(ids > 0), f"{case}: empty foreground labels.")
        voxel_hash = hashlib.sha256(np.ascontiguousarray(data).tobytes()).hexdigest()
        require(voxel_hash not in hashes, f"{case}: duplicate image voxel data with {hashes.get(voxel_hash)}.")
        hashes[voxel_hash] = case
        spacing = nib.affines.voxel_sizes(image.affine)
        directions = image.affine[:3, :3] / spacing
        require(np.allclose(directions.T @ directions, np.eye(3), atol=1e-4), f"{case}: sheared affine is incompatible with this ITK training handoff.")
        row = {"id": case, "split": "train" if case in train else "val", "shape": list(image.shape),
               "voxel_sizes_in_header_units": spacing.tolist(), "axis_codes": "".join(nib.aff2axcodes(image.affine)),
               "header_spatial_units": list(units),
               "label_counts": {str(int(key)): int(value) for key, value in zip(ids, counts)},
               "image_voxels_sha256": voxel_hash}
        report["cases"].append(row)
        for path in (image_path, label_path):
            report["files"][path.relative_to(root).as_posix()] = sha256(path)
        print(f"Checked {case} ({row['split']})", flush=True)
    for path in (dataset / "dataset.json", root / "splits_final.json"):
        report["files"][path.relative_to(root).as_posix()] = sha256(path)
    report["dataset_sha256"] = hashlib.sha256(json.dumps(report["files"], sort_keys=True).encode()).hexdigest()
    report["split_sha256"] = sha256(root / "splits_final.json")
    report["centers"] = {part: dict(Counter(re.sub(r"\d+$", "", case) for case in folds[0][part])) for part in ("train", "val")}
    report["technical_checks_passed"] = True
    report["anatomical_or_semantic_approval"] = False
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.handoff)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Passed technical checks: 44 train / 10 val. Report: {args.out}")


if __name__ == "__main__":
    main()
