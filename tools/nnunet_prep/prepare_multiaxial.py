"""Split MultiAxial (D01) by subject and build an nnU-Net v2 raw dataset.

Split (approved by K1, 2026-11-02): 44 train / 10 validation / 10 test.
Clinical subjects are split per center with a fixed seed. The four healthy
subjects (subj1-4) go to the test set together with both of their variants;
they must never appear in training because their intact-face twins are the
only face reference in D01.

Label mapping (release label -> project label); inferred from T1 intensity and
visual overlay, see knowledge/references/datasets.md:
    0 outside air -> 0 background      1 air cavity -> 0 background
    2 gray matter -> 4                 3 white matter -> 5
    4 CSF -> 3                         5 skull -> 2          6 skin -> 1
No ignore label is produced yet (removed-face mask is open question Q-16).

Output layout under --out (keep it outside the repository):
    nnUNet_raw/Dataset001_MultiAxial/{dataset.json,imagesTr,labelsTr}   train+val
    nnUNet_preprocessed/Dataset001_MultiAxial/splits_final.json         fixed split
    test_holdout/{defaced,intact}/                                      custodian only
    split_manifest.csv

Usage:
    python prepare_multiaxial.py <acilmis_dosyalar dir> --out <dir> [--seed 42]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

DATASET_NAME = "Dataset001_MultiAxial"
CENTERS = ("GU", "NC", "NYU")
VAL_PER_CENTER = {"GU": 5, "NC": 4, "NYU": 1}
TEST_PER_CENTER = {"GU": 2, "NC": 2, "NYU": 2}
HEALTHY_PATTERN = re.compile(r"^subj\d+$")
CENTER_PATTERN = re.compile(r"^(GU|NC|NYU)\d+$")

# release label value -> project label value
LABEL_LUT = np.array([0, 0, 4, 5, 3, 2, 1], dtype=np.uint8)
PROJECT_LABELS = {
    "background": 0, "skin": 1, "skull": 2, "csf": 3, "gray_matter": 4, "white_matter": 5,
}


def list_subjects(root: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Return clinical subjects per center and the healthy subject IDs."""
    t1_dir = root / "Data" / "Anonymized_Subjects" / "T1-Weighted MRI"
    ids = sorted(p.name[: -len("_deface.nii")] for p in t1_dir.glob("*_deface.nii"))
    clinical: dict[str, list[str]] = {c: [] for c in CENTERS}
    healthy = []
    for case_id in ids:
        match = CENTER_PATTERN.match(case_id)
        if match:
            clinical[match.group(1)].append(case_id)
        elif HEALTHY_PATTERN.match(case_id):
            healthy.append(case_id)
        else:
            raise ValueError(f"Unrecognised subject ID: {case_id}")
    return clinical, healthy


def make_split(clinical: dict[str, list[str]], healthy: list[str], seed: int) -> dict[str, str]:
    """Map every subject ID to 'train', 'val', or 'test' (stratified by center)."""
    rng = random.Random(seed)
    split: dict[str, str] = {}
    for center in CENTERS:
        members = sorted(clinical[center])
        n_val, n_test = VAL_PER_CENTER[center], TEST_PER_CENTER[center]
        if len(members) <= n_val + n_test:
            raise ValueError(f"{center}: only {len(members)} subjects, cannot split")
        rng.shuffle(members)
        for i, case_id in enumerate(members):
            split[case_id] = "test" if i < n_test else "val" if i < n_test + n_val else "train"
    for case_id in healthy:
        split[case_id] = "test"
    return split


def remap_labels(labels: np.ndarray) -> np.ndarray:
    values = np.unique(labels)
    if values.min() < 0 or values.max() >= len(LABEL_LUT):
        raise ValueError(f"Unexpected label values: {values.tolist()}")
    return LABEL_LUT[labels.astype(np.int64)]


SHEAR_TOLERANCE = 1e-3


def orthonormalize(affine: np.ndarray) -> tuple[np.ndarray, float]:
    """Return the affine with its 3x3 part replaced by the nearest rotation x zooms.

    Some NYU scans carry a sheared (non-orthonormal) sform that SimpleITK, and
    therefore nnU-Net, rejects. Training only needs the voxel grid, so the shear is
    dropped in the nnU-Net copy; the returned error (max deviation of R^T R from I)
    lets callers flag affected cases. Unaffected affines are returned unchanged.
    """
    linear = affine[:3, :3]
    zooms = np.linalg.norm(linear, axis=0)
    rotation = linear / zooms
    error = float(np.abs(rotation.T @ rotation - np.eye(3)).max())
    if error <= SHEAR_TOLERANCE:
        return affine, error
    u, _, vt = np.linalg.svd(rotation)
    fixed = affine.copy()
    fixed[:3, :3] = (u @ vt) * zooms
    return fixed, error


def write_case(t1_path: Path, label_path: Path, image_out: Path, label_out: Path) -> float:
    """Convert one case; return the original affine shear error (0 if orthonormal)."""
    t1 = nib.load(str(t1_path))
    lab = nib.load(str(label_path))
    if t1.ndim != 3 or t1.shape != lab.shape or not np.allclose(t1.affine, lab.affine, atol=1e-3):
        raise ValueError(f"Geometry mismatch: {t1_path.name}")
    affine, shear_error = orthonormalize(t1.affine)
    image = nib.Nifti1Image(np.asanyarray(t1.dataobj).astype(np.float32), affine)
    image.set_data_dtype(np.float32)
    mapped = remap_labels(np.asanyarray(lab.dataobj))
    label = nib.Nifti1Image(mapped, affine)
    label.set_data_dtype(np.uint8)
    for path in (image_out, label_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(image, str(image_out))
    nib.save(label, str(label_out))
    return shear_error


def source_paths(root: Path, case_id: str, variant: str) -> tuple[Path, Path]:
    if variant == "defaced":
        base = root / "Data" / "Anonymized_Subjects"
        return (base / "T1-Weighted MRI" / f"{case_id}_deface.nii",
                base / "Full-Head Segmentation" / f"{case_id}_label_deface.nii")
    base = root / "Data" / "Control_Subjects"
    return (base / "T1-Weighted MRI" / f"{case_id}.nii",
            base / "Full-Head Segmentation" / f"{case_id}_label.nii")


def build(root: Path, out: Path, seed: int) -> dict[str, str]:
    clinical, healthy = list_subjects(root)
    split = make_split(clinical, healthy, seed)
    counts = {s: sum(v == s for v in split.values()) for s in ("train", "val", "test")}
    print("Split:", counts)

    shear: dict[str, float] = {}
    raw = out / "nnUNet_raw" / DATASET_NAME
    train_ids = sorted(c for c, s in split.items() if s == "train")
    val_ids = sorted(c for c, s in split.items() if s == "val")
    for case_id in train_ids + val_ids:
        image_out = raw / "imagesTr" / f"{case_id}_0000.nii.gz"
        if image_out.exists():
            continue
        print("train/val", case_id, flush=True)
        t1, lab = source_paths(root, case_id, "defaced")
        shear[case_id] = write_case(t1, lab, image_out, raw / "labelsTr" / f"{case_id}.nii.gz")

    holdout = out / "test_holdout"
    for case_id in sorted(c for c, s in split.items() if s == "test"):
        variants = ["defaced"] + (["intact"] if HEALTHY_PATTERN.match(case_id) else [])
        for variant in variants:
            image_out = holdout / variant / "images" / f"{case_id}_0000.nii.gz"
            if image_out.exists():
                continue
            print("test", variant, case_id, flush=True)
            t1, lab = source_paths(root, case_id, variant)
            err = write_case(t1, lab, image_out, holdout / variant / "labels" / f"{case_id}.nii.gz")
            shear.setdefault(case_id, err)

    raw.mkdir(parents=True, exist_ok=True)
    (raw / "dataset.json").write_text(json.dumps({
        "channel_names": {"0": "T1"},
        "labels": PROJECT_LABELS,
        "numTraining": len(train_ids) + len(val_ids),
        "file_ending": ".nii.gz",
    }, indent=2), encoding="utf-8")

    preprocessed = out / "nnUNet_preprocessed" / DATASET_NAME
    preprocessed.mkdir(parents=True, exist_ok=True)
    (preprocessed / "splits_final.json").write_text(
        json.dumps([{"train": train_ids, "val": val_ids}], indent=2), encoding="utf-8")

    with (out / "split_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "center", "split", "affine_shear_error", "affine_orthonormalized"])
        for case_id in sorted(split):
            match = CENTER_PATTERN.match(case_id)
            error = shear.get(case_id)
            writer.writerow([case_id, match.group(1) if match else "healthy", split[case_id],
                             "" if error is None else f"{error:.4f}",
                             "" if error is None else error > SHEAR_TOLERANCE])
    return split


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="acilmis_dosyalar directory of D01")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    build(args.root, args.out, args.seed)
    print("Done:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
