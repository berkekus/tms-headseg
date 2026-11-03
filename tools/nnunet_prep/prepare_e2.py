"""Build the E2 nnU-Net v2 raw dataset from charm labels (IXI + MultiAxial).

Decided 2026-11-04: E2 trains on charm labels only, so the GM/CSF boundary follows one
convention (EXP-002, NC033). Sources:
    IXI (D06)       cohort `train` of ixi_assignment.csv (K1 + K2), charm T1+T2
    MultiAxial (D01) cohorts `train`/`val` of multiaxial_assignment.csv, charm T1-only on the
                     Dataset001 nnU-Net images
Never included: IXI `test_face`, `calibration`, `excluded_d05`, and the MultiAxial test hold-out.

Split: MultiAxial keeps its E1 train/val split. IXI training subjects get IXI_VAL_PER_SITE validation
cases per site (fixed seed); the rest train.

Each case must have a charm delivery whose SHA256SUMS.txt matches, whose run.json reports SimNIBS 4.6.0
and outputs_ok, and (unless --allow-unchecked) a QC row marked `pass`. Labels are mapped with
headmodel.labels.CHARM_TO_PROJECT (blood 9 -> CSF, PR #5) and written on the T1 grid.

Output under --out (outside the repository):
    nnUNet_raw/Dataset002_E2Charm/{dataset.json,imagesTr,labelsTr}
    nnUNet_preprocessed/Dataset002_E2Charm/splits_final.json
    e2_manifest.csv

Usage:
    python prepare_e2.py --deliver D [D ...] --qc Q [Q ...] --ixi-images D06_DIR \
        --ma-images DATASET001_IMAGES_TR --out DIR [--require-all]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from headmodel.labels import CHARM_TO_PROJECT, map_labels, validate_project_labels  # noqa: E402
from prepare_multiaxial import PROJECT_LABELS, SHEAR_TOLERANCE, orthonormalize, save_nifti  # noqa: E402

DATASET_NAME = "Dataset002_E2Charm"
SIMNIBS_VERSION = "4.6.0"
IXI_VAL_PER_SITE = 2
GEOMETRY_ATOL = 1e-3
CHARM_BATCH = HERE.parent / "charm_batch"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def plan_cases(ixi_rows: list[dict], ma_rows: list[dict], seed: int) -> dict[str, dict]:
    """case_id -> {source, site, split}; held-out and excluded subjects are never planned."""
    cases: dict[str, dict] = {}
    for r in ma_rows:
        if r["cohort"] not in ("train", "val"):
            raise ValueError(f"{r['subject']}: MultiAxial cohort {r['cohort']!r} must not enter E2")
        cases[r["subject"]] = {"source": "MultiAxial", "site": r["site"], "split": r["cohort"]}
    rng = random.Random(seed)
    by_site: dict[str, list[str]] = {}
    for r in ixi_rows:
        if r["cohort"] == "train":
            by_site.setdefault(r["site"], []).append(r["subject"])
    for site in sorted(by_site):
        members = sorted(by_site[site])
        rng.shuffle(members)
        for i, subject in enumerate(members):
            if subject in cases:
                raise ValueError(f"{subject} appears in both sources")
            cases[subject] = {"source": "IXI", "site": site, "split": "val" if i < IXI_VAL_PER_SITE else "train"}
    return dict(sorted(cases.items()))


def find_delivery(deliver_dirs: list[Path], subject: str) -> Path | None:
    found = [d / subject for d in deliver_dirs if (d / subject / "final_tissues.nii.gz").is_file()]
    if len(found) > 1:
        sums = {(p / "SHA256SUMS.txt").read_text() for p in found}
        if len(sums) > 1:
            raise ValueError(f"{subject}: different deliveries in {[str(p) for p in found]}")
    return found[0] if found else None


def verify_delivery(folder: Path, subject: str) -> dict:
    """Check checksums and the run record; return the run record."""
    sums = folder / "SHA256SUMS.txt"
    if not sums.is_file():
        raise ValueError(f"{subject}: no SHA256SUMS.txt")
    listed = set()
    for line in filter(None, sums.read_text().splitlines()):
        digest, name = line.split("  ", 1)
        listed.add(name)
        if sha256(folder / name) != digest:
            raise ValueError(f"{subject}: checksum mismatch for {name}")
    if not {"final_tissues.nii.gz", "run.json"} <= listed:
        raise ValueError(f"{subject}: labels or run.json not covered by SHA256SUMS.txt")
    run = json.loads((folder / "run.json").read_text())
    if run.get("subject") != subject or not run.get("outputs_ok") or run.get("simnibs_version") != SIMNIBS_VERSION:
        raise ValueError(f"{subject}: run.json is not a completed SimNIBS {SIMNIBS_VERSION} run")
    return run


def find_image(source: str, subject: str, ixi_images: Path, ma_images: Path) -> Path:
    if source == "MultiAxial":
        candidates = [ma_images / f"{subject}_0000.nii.gz"]
    else:
        candidates = sorted((ixi_images / subject).glob(f"{subject}-*-T1.nii.gz")) + \
            sorted(ixi_images.glob(f"{subject}-*-T1.nii.gz"))
    candidates = [p for p in candidates if p.is_file()]
    if len(candidates) != 1:
        raise FileNotFoundError(f"{subject}: expected one T1 image, found {len(candidates)}")
    return candidates[0]


def convert_case(t1_path: Path, label_path: Path, image_out: Path, label_out: Path) -> dict:
    """Write the T1 and mapped labels on one grid; return geometry facts."""
    t1 = nib.load(str(t1_path))
    lab = nib.load(str(label_path))
    labels = np.asanyarray(lab.dataobj)
    labels = labels.reshape(labels.shape[:3]) if labels.ndim == 4 and labels.shape[3] == 1 else labels
    if t1.ndim != 3 or t1.shape != labels.shape:
        raise ValueError(f"{t1_path.name}: image {t1.shape} and labels {labels.shape} differ")
    affine_diff = float(np.abs(t1.affine - lab.affine).max())
    if affine_diff > GEOMETRY_ATOL:
        raise ValueError(f"{t1_path.name}: image and label affines differ by {affine_diff:.3g}")
    mapped = validate_project_labels(map_labels(labels, CHARM_TO_PROJECT))
    affine, shear_error = orthonormalize(t1.affine)
    save_nifti(image_out, np.asanyarray(t1.dataobj).astype(np.float32), affine)
    save_nifti(label_out, mapped, affine)
    return {"affine_diff": affine_diff, "shear_error": shear_error,
            "voxels_per_label": np.bincount(mapped.ravel(), minlength=6).tolist()}


def build(args) -> dict:
    ixi_rows = read_csv(args.ixi_assignment)
    ma_rows = read_csv(args.ma_assignment)
    cases = plan_cases(ixi_rows, ma_rows, args.seed)
    qc = {}
    for path in args.qc:
        for r in read_csv(path):
            if r.get("qc"):
                qc[r["subject"]] = r["qc"].strip().lower()

    raw = args.out / "nnUNet_raw" / DATASET_NAME
    if raw.exists() and any(raw.iterdir()):
        raise SystemExit(f"{raw} is not empty; choose a new --out so datasets are never mixed.")
    manifest, missing = [], []
    for case_id, info in cases.items():
        folder = find_delivery(args.deliver, case_id)
        if folder is None:
            missing.append((case_id, "no charm delivery"))
            continue
        run = verify_delivery(folder, case_id)
        status = qc.get(case_id, "")
        if not (status == "pass" or (status == "" and args.allow_unchecked)):  # fail/check never enter
            missing.append((case_id, f"QC {status or 'not done'}"))
            continue
        t1 = find_image(info["source"], case_id, args.ixi_images, args.ma_images)
        print(info["split"], case_id, flush=True)
        facts = convert_case(t1, folder / "final_tissues.nii.gz",
                             raw / "imagesTr" / f"{case_id}_0000.nii.gz", raw / "labelsTr" / f"{case_id}.nii.gz")
        manifest.append({"case_id": case_id, **info, "charm_owner": run.get("owner", ""),
                         "t1_only": bool(run.get("t1_only", run.get("t2") is None)),
                         "forceqform": bool(run.get("forceqform")), "qc": status or "unchecked",
                         "t1_source": t1.name, "affine_diff": f"{facts['affine_diff']:.2e}",
                         "affine_orthonormalized": facts["shear_error"] > SHEAR_TOLERANCE,
                         "voxels_per_label": " ".join(map(str, facts["voxels_per_label"]))})

    if missing:
        print(f"Not included ({len(missing)}):")
        for case_id, reason in missing:
            print(f"  {case_id}: {reason}")
        if args.require_all:
            raise SystemExit("--require-all: every planned case must be included.")
    if not manifest:
        raise SystemExit("No case could be included.")

    train_ids = sorted(m["case_id"] for m in manifest if m["split"] == "train")
    val_ids = sorted(m["case_id"] for m in manifest if m["split"] == "val")
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "dataset.json").write_text(json.dumps({
        "channel_names": {"0": "T1"},
        "labels": PROJECT_LABELS,
        "numTraining": len(manifest),
        "file_ending": ".nii.gz",
        "description": "E2: charm 4.6.0 labels on IXI (T1+T2) and MultiAxial (T1 only), blood mapped to CSF",
    }, indent=2), encoding="utf-8")
    preprocessed = args.out / "nnUNet_preprocessed" / DATASET_NAME
    preprocessed.mkdir(parents=True, exist_ok=True)
    (preprocessed / "splits_final.json").write_text(
        json.dumps([{"train": train_ids, "val": val_ids}], indent=2), encoding="utf-8")
    with open(args.out / "e2_manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)
    summary = {s: {src: sum(m["split"] == s and m["source"] == src for m in manifest) for src in ("IXI", "MultiAxial")}
               for s in ("train", "val")}
    print("Included:", summary, "missing:", len(missing))
    return {"manifest": manifest, "missing": missing}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--deliver", type=Path, nargs="+", required=True, help="charm deliver_* folders")
    parser.add_argument("--qc", type=Path, nargs="*", default=[], help="QC sheets (subject,qc,notes)")
    parser.add_argument("--ixi-images", type=Path, required=True, help="Unpacked D06 IXI folder")
    parser.add_argument("--ma-images", type=Path, required=True, help="Dataset001 imagesTr folder")
    parser.add_argument("--ixi-assignment", type=Path, default=CHARM_BATCH / "ixi_assignment.csv")
    parser.add_argument("--ma-assignment", type=Path, default=CHARM_BATCH / "multiaxial_assignment.csv")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--require-all", action="store_true", help="Fail unless every planned case is included")
    parser.add_argument("--allow-unchecked", action="store_true", help="Include cases without a QC pass")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    build(parse_args(argv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
