"""Audit the unpacked MultiAxial (D01) release.

Reads every T1/label pair, records geometry and label values, and writes one
CSV row per case plus a printed summary. Nothing is modified. Output goes to
--out (keep it outside the repository: it lists subject IDs).

Usage:
    python audit_multiaxial.py <acilmis_dosyalar dir> --out <dir>
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

GROUPS = {
    "anonymized": ("Data/Anonymized_Subjects", "_deface.nii", "_label_deface.nii"),
    "control": ("Data/Control_Subjects", ".nii", "_label.nii"),
}


def find_pairs(root: Path):
    """Yield (group, case_id, t1_path, label_path or None)."""
    for group, (base, t1_suffix, label_suffix) in GROUPS.items():
        t1_dir = root / base / "T1-Weighted MRI"
        label_dir = root / base / "Full-Head Segmentation"
        for t1 in sorted(t1_dir.glob("*.nii")):
            case_id = t1.name[: -len(t1_suffix)]
            label = label_dir / f"{case_id}{label_suffix}"
            yield group, case_id, t1, (label if label.exists() else None)


def audit_case(group, case_id, t1_path, label_path):
    t1 = nib.load(str(t1_path))
    row = {
        "group": group,
        "case_id": case_id,
        "t1_shape": "x".join(map(str, t1.shape)),
        "t1_spacing_mm": "x".join(f"{z:.3f}" for z in t1.header.get_zooms()[:3]),
        "orientation": "".join(nib.aff2axcodes(t1.affine)),
        "t1_dtype": str(t1.get_data_dtype()),
        "label_present": label_path is not None,
        "label_shape": "",
        "geometry_match": "",
        "label_values": "",
        "label_counts": "",
        "t1_zero_fraction": "",
    }
    data = np.asanyarray(t1.dataobj)
    row["t1_zero_fraction"] = f"{float((data == 0).mean()):.3f}"
    if label_path is not None:
        lab = nib.load(str(label_path))
        row["label_shape"] = "x".join(map(str, lab.shape))
        row["geometry_match"] = bool(
            lab.shape == t1.shape and np.allclose(lab.affine, t1.affine, atol=1e-3)
        )
        values, counts = np.unique(np.asanyarray(lab.dataobj).astype(np.int64),
                                   return_counts=True)
        row["label_values"] = " ".join(map(str, values))
        row["label_counts"] = " ".join(f"{v}:{c}" for v, c in zip(values, counts))
    return row


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="acilmis_dosyalar directory of D01")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    rows = []
    for group, case_id, t1, label in find_pairs(args.root):
        print(f"{group:10s} {case_id}", flush=True)
        rows.append(audit_case(group, case_id, t1, label))
    if not rows:
        print("No cases found; check the path.", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    out_csv = args.out / "d01_audit.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {out_csv}")
    print(f"Cases: {len(rows)}")
    for key in ("group", "orientation", "t1_spacing_mm", "t1_shape", "label_values",
                "geometry_match", "label_present"):
        counts: dict[str, int] = {}
        for row in rows:
            counts[str(row[key])] = counts.get(str(row[key]), 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
        print(f"{key}: " + "; ".join(f"{k} x{v}" for k, v in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
