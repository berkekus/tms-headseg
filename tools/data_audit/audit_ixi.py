"""Audit the unpacked IXI subset (D06): checksums, geometry, and head coverage.

For each subject and modality (T1, T2) it records shape, spacing, orientation,
affine shear, and whether the head touches the edge of the field of view on each
side (a cropped nose, ears, or vertex would make face evaluation unreliable).
Subject IDs are also written for cross-source overlap checks.

Coverage heuristic: foreground = voxels above 10% of the 99th intensity
percentile. For each of the six volume faces, report the share of that face's
voxels that are foreground. A value near 0 means the head ends before the edge;
a high value means the head is cut by the edge. It is a screening aid, not proof
of an intact face: inspect flagged cases visually.

Usage:
    python audit_ixi.py <acilmis_dosyalar dir> --manifest D06_manifest.json --out <dir>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

EDGE_FLAG = 0.02  # more than 2% of a volume face covered by head => edge contact


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def face_coverage(data: np.ndarray) -> dict[str, float]:
    """Share of foreground on each of the six faces, in array-axis terms."""
    mask = data > 0.1 * np.percentile(data, 99)
    out = {}
    for axis in range(3):
        for side, index in (("lo", 0), ("hi", -1)):
            face = np.take(mask, index, axis=axis)
            out[f"edge_ax{axis}_{side}"] = float(face.mean())
    return out


def audit_file(path: Path, expected: dict | None) -> dict:
    img = nib.load(str(path))
    linear = img.affine[:3, :3]
    zooms = np.linalg.norm(linear, axis=0)
    rotation = linear / zooms
    row = {
        "file": path.name,
        "shape": "x".join(map(str, img.shape)),
        "spacing_mm": "x".join(f"{z:.3f}" for z in zooms),
        "orientation": "".join(nib.aff2axcodes(img.affine)),
        "shear_error": f"{float(np.abs(rotation.T @ rotation - np.eye(3)).max()):.4f}",
        "sha256_ok": "" if expected is None else sha256(path) == expected["sha256"],
    }
    data = np.asanyarray(img.dataobj).astype(np.float32)
    if data.ndim != 3:
        row["note"] = f"ndim={data.ndim}"
        return row
    coverage = face_coverage(data)
    row.update({k: f"{v:.3f}" for k, v in coverage.items()})
    row["edge_contact_axes"] = " ".join(
        k.replace("edge_", "") for k, v in coverage.items() if v > EDGE_FLAG)
    return row


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected_files = manifest["files"]
    rows = []
    for subject in manifest["subjects"]:
        for modality in ("T1", "T2"):
            matches = sorted((args.root / subject).glob(f"*-{modality}.nii.gz"))
            if len(matches) != 1:
                rows.append({"subject": subject, "modality": modality,
                             "file": "", "note": f"{len(matches)} files found"})
                continue
            key = f"{subject}/{matches[0].name}"
            row = audit_file(matches[0], expected_files.get(key))
            site = matches[0].name.split("-")[1]
            rows.append({"subject": subject, "modality": modality, "site": site, **row})
            print(subject, modality, flush=True)

    fields = []
    for row in rows:
        fields += [k for k in row if k not in fields]
    args.out.mkdir(parents=True, exist_ok=True)
    out_csv = args.out / "d06_audit.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {out_csv}; rows: {len(rows)}")
    for key in ("modality", "site", "orientation", "shape", "spacing_mm", "sha256_ok",
                "edge_contact_axes"):
        counts: dict[str, int] = {}
        for row in rows:
            counts[str(row.get(key, ""))] = counts.get(str(row.get(key, "")), 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
        print(f"{key}: " + "; ".join(f"{k!r} x{v}" for k, v in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
