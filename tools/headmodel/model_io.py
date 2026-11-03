"""Bring a scan (and its labels) into the model's axis order, and model labels back to the scan.

nnU-Net does not reorient, so every training and inference file must share one axis order.
MultiAxial is stored RAS; IXI and Ernie are stored PSR. `prepare` permutes and flips axes toward
RAS without interpolation and saves the geometry record; `restore` returns model labels to the
source grid voxel for voxel, with the source affine (see D-004 and the coordinate contract).

Usage:
    python tools/headmodel/model_io.py prepare T1.nii.gz CASE_0000.nii.gz --record CASE.geometry.json \
        [--labels LABELS.nii.gz --labels-out CASE.nii.gz --label-scheme project|charm]
    python tools/headmodel/model_io.py restore PREDICTION.nii.gz CASE.geometry.json LABELS_ON_SOURCE.nii.gz
"""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from headmodel.export import sha256
from headmodel.images import WORLD_TOLERANCE_MM, read_source, world_disagreement, write_nifti
from headmodel.labels import CHARM_TO_PROJECT, map_labels, validate_project_labels
from headmodel.reversible import GeometryRecord, canonicalize, read_model_output, reorient

SCHEMA = "tms-headseg-geometry/1"
MAPPINGS = {"project": None, "charm": CHARM_TO_PROJECT}


def check_new_file(path):
    path = Path(path).expanduser().resolve()
    if path.exists():
        raise ValueError(f"{path} already exists. Files are never overwritten.")
    if any((parent / ".git").exists() for parent in path.parents):
        raise ValueError("Choose a location outside any Git checkout, to keep scans and labels out of the repository.")
    if not path.parent.is_dir():
        raise ValueError(f"{path.parent} does not exist.")
    return path


def prepare(image, out_image, record_path, labels=None, out_labels=None, label_scheme="project"):
    """Write the canonical image, optional labels on the same grid, then the record; return the record."""
    if (labels is None) != (out_labels is None):
        raise ValueError("Give both the labels and where to write them, or neither.")
    outputs = [check_new_file(path) for path in (out_image, record_path, *([out_labels] if out_labels else []))]
    if len(set(outputs)) != len(outputs):
        raise ValueError("Each output needs its own file name.")
    source = read_source(image)
    canonical, record = canonicalize(source.data, source.affine)
    moved = None
    if labels is not None:
        mask = read_source(labels)
        if (mask.data.shape != source.data.shape
                or world_disagreement(mask.affine, source.affine, source.data.shape) > WORLD_TOLERANCE_MM):
            raise ValueError(f"{mask.path.name} is not on the grid of {source.path.name}.")
        mapping = MAPPINGS[label_scheme]
        project = validate_project_labels(mask.data if mapping is None else map_labels(mask.data, mapping))
        moved = reorient(project, record)
    result = {"schema": SCHEMA, "source": {"file": source.path.name, "sha256": sha256(source.path),
                                           "axes": record.source_axes},
              "label_scheme": label_scheme if labels is not None else None,
              "warnings": list(source.warnings), "geometry": record.to_json()}
    write_nifti(outputs[0], canonical, record.model_affine)
    if moved is not None:
        write_nifti(outputs[2], moved, record.model_affine)
    outputs[1].write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return json.loads(json.dumps(result))


def restore_labels(prediction, record_path, out):
    """Write model labels on the source grid with the source affine; return the source-grid array."""
    out = check_new_file(out)
    saved = json.loads(Path(record_path).read_text(encoding="utf-8"))
    if saved.get("schema") != SCHEMA:
        raise ValueError(f"{Path(record_path).name}: expected schema {SCHEMA}.")
    record = GeometryRecord.from_json(saved["geometry"])
    labels = validate_project_labels(read_model_output(prediction, record))
    write_nifti(out, labels, record.source_affine)
    return labels


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    forward = commands.add_parser("prepare", help="Write the model's axis order and the geometry record.")
    forward.add_argument("image", type=Path)
    forward.add_argument("out_image", type=Path)
    forward.add_argument("--record", type=Path, required=True)
    forward.add_argument("--labels", type=Path)
    forward.add_argument("--labels-out", type=Path)
    forward.add_argument("--label-scheme", choices=sorted(MAPPINGS), default="project")
    back = commands.add_parser("restore", help="Return model labels to the source grid.")
    back.add_argument("prediction", type=Path)
    back.add_argument("record", type=Path)
    back.add_argument("out", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.image, args.out_image, args.record, args.labels, args.labels_out, args.label_scheme)
            for warning in result["warnings"]:
                print("WARNING:", warning)
            geometry = result["geometry"]
            print(f"{result['source']['axes']} {tuple(geometry['source_shape'])} -> RAS {tuple(geometry['canonical_shape'])}")
        else:
            labels = restore_labels(args.prediction, args.record, args.out)
            print(f"Labels on the source grid {labels.shape}: {np.unique(labels).tolist()}")
    except ValueError as error:
        raise SystemExit(f"ERROR: {error}")


if __name__ == "__main__":
    main()
