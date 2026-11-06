"""Build E3 (Dataset003_E3Face) from a built E2 dataset: ignore voxels without signal, weight intact faces.

E2 labels the defaced MultiAxial face as background, which teaches "the face is air". E3 changes two things
and keeps every case, label rule and the validation split of E2:

1. In training cases, voxels outside the acquisition (exactly zero and connected to the volume border:
   the defacing wedge and padding; `prepare_e2.outside_acquisition`) get nnU-Net's `ignore` label (6).
   They carry no signal, so the loss skips them instead of calling them background.
2. Intact-face IXI training cases appear `--ixi-weight` times (copies named `<case>w<n>`), so faces are
   seen more often. Copies stay in training; validation is identical to E2 for a fair comparison.

At inference, predictions in voxels without signal should be set to background (the same rule), because
the model was not taught anything there.

    python prepare_e3.py --e2 <e2_full folder> --out <new folder> [--ixi-weight 2]
"""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_e2 import DATASET_NAME as E2_NAME, outside_acquisition  # noqa: E402
from prepare_multiaxial import PROJECT_LABELS  # noqa: E402

DATASET_NAME = "Dataset003_E3Face"
IGNORE = 6


def read_e2(e2):
    e2 = Path(e2)
    raw = e2 / "nnUNet_raw" / E2_NAME
    with open(e2 / "e2_manifest.csv", newline="", encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))
    split = json.loads((e2 / "nnUNet_preprocessed" / E2_NAME / "splits_final.json").read_text(encoding="utf-8"))[0]
    return raw, manifest, split


def ignore_outside(image_path, label_path, label_out):
    """Write the label with voxels outside the acquisition set to IGNORE; return the ignored volume in mL."""
    image = np.asanyarray(nib.load(str(image_path)).dataobj)
    label_img = nib.load(str(label_path))
    labels = np.asanyarray(label_img.dataobj).astype(np.uint8)
    if labels.shape != image.shape:
        raise ValueError(f"{label_path.name}: labels {labels.shape} and image {image.shape} differ")
    outside = outside_acquisition(image)
    labels[outside] = IGNORE
    out = nib.Nifti1Image(labels, label_img.affine, label_img.header)
    out.set_data_dtype(np.uint8)
    nib.save(out, str(label_out))
    return float(outside.sum()) * float(np.prod(label_img.header.get_zooms()[:3])) / 1000.0


def build(e2, out, ixi_weight=2):
    if ixi_weight < 1:
        raise ValueError("--ixi-weight must be at least 1.")
    raw_e2, manifest, split = read_e2(e2)
    raw = Path(out) / "nnUNet_raw" / DATASET_NAME
    if raw.exists() and any(raw.iterdir()):
        raise SystemExit(f"{raw} is not empty; choose a new --out so datasets are never mixed.")
    (raw / "imagesTr").mkdir(parents=True)
    (raw / "labelsTr").mkdir()
    by_case = {row["case_id"]: row for row in manifest}
    if set(split["train"]) | set(split["val"]) != set(by_case):
        raise ValueError("E2 manifest and splits_final.json list different cases.")
    rows, train_ids = [], []
    for case in sorted(by_case):
        info = by_case[case]
        image = raw_e2 / "imagesTr" / f"{case}_0000.nii.gz"
        label = raw_e2 / "labelsTr" / f"{case}.nii.gz"
        is_train = case in split["train"]
        copies = ixi_weight if is_train and info["source"] == "IXI" else 1
        for n in range(copies):
            new_id = case if n == 0 else f"{case}w{n + 1}"
            shutil.copy2(image, raw / "imagesTr" / f"{new_id}_0000.nii.gz")
            if is_train:
                ignored = ignore_outside(image, label, raw / "labelsTr" / f"{new_id}.nii.gz")
                train_ids.append(new_id)
            else:
                shutil.copy2(label, raw / "labelsTr" / f"{new_id}.nii.gz")  # validation stays exactly E2
                ignored = 0.0
            rows.append({"case_id": new_id, "source_case": case, "source": info["source"],
                         "split": "train" if is_train else "val", "weight_copy": n + 1,
                         "ignore_ml": f"{ignored:.1f}"})
        print(("train" if is_train else "val"), case, f"x{copies}", flush=True)
    labels = dict(PROJECT_LABELS)
    labels["ignore"] = IGNORE
    (raw / "dataset.json").write_text(json.dumps({
        "channel_names": {"0": "T1"}, "labels": labels, "numTraining": len(rows), "file_ending": ".nii.gz",
        "description": f"E3: E2 cases and labels; training voxels without signal are ignore ({IGNORE}); "
                       f"IXI training cases x{ixi_weight}; validation identical to E2",
    }, indent=2), encoding="utf-8")
    preprocessed = Path(out) / "nnUNet_preprocessed" / DATASET_NAME
    preprocessed.mkdir(parents=True, exist_ok=True)
    (preprocessed / "splits_final.json").write_text(
        json.dumps([{"train": sorted(train_ids), "val": sorted(split["val"])}], indent=2), encoding="utf-8")
    with open(Path(out) / "e3_manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {s: {src: sum(r["split"] == s and r["source"] == src for r in rows) for src in ("IXI", "MultiAxial")}
               for s in ("train", "val")}
    print("E3 cases:", summary)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--e2", type=Path, required=True, help="Folder built by prepare_e2.py (with e2_manifest.csv)")
    parser.add_argument("--out", type=Path, required=True, help="New folder outside Git")
    parser.add_argument("--ixi-weight", type=int, default=2, help="Times each IXI training case appears (default 2)")
    args = parser.parse_args(argv)
    build(args.e2, args.out, args.ixi_weight)
    return 0


if __name__ == "__main__":
    sys.exit(main())
