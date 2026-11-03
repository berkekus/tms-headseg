"""Turn a T1 and its labels into documented head and brain surfaces.

Usage: python tools/headmodel/build_model.py T1.nii.gz labels.nii.gz OUTPUT_FOLDER
"""

import argparse
from importlib import metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import time

import nibabel as nib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from headmodel.cleanup import ENVELOPE_SEAL_MM, brain_mask, clean_labels, head_envelope
from headmodel.export import FRAME_TAG, SCHEMA, WRITERS, describe_surface, sha256
from headmodel.images import WORLD_TOLERANCE_MM, read_source, world_disagreement, write_nifti
from headmodel.labels import BACKGROUND, CHARM_TO_PROJECT, TISSUES, map_labels
from headmodel.surfaces import boundary_contact, extract_surface

SCHEMES = {
    "project": (None, "Project schema."),
    "charm": (CHARM_TO_PROJECT, "Proposed in EXP-002, not accepted; see Q-05."),
}
_PACKAGES = ("nibabel", "numpy", "scipy", "scikit-image")


def check_output(out):
    if out.exists():
        raise ValueError(f"{out} already exists. Models are never overwritten.")
    if any((parent / ".git").exists() for parent in (out, *out.parents)):
        raise ValueError("Choose an output folder outside any Git checkout, to keep head surfaces out of the repository.")


def build_model(t1, segmentation, out, label_scheme="project", surface_format="stl"):
    """Write the reference copy, labels, two surfaces, and model.json last, so a partial folder cannot verify."""
    out = Path(out).expanduser().resolve()
    check_output(out)
    moments = [time.perf_counter()]
    reference = read_source(t1)
    labels = read_source(segmentation)
    if (labels.data.shape != reference.data.shape
            or world_disagreement(labels.affine, reference.affine, labels.data.shape) > WORLD_TOLERANCE_MM):
        raise ValueError(f"{labels.path.name} is not on the grid of {reference.path.name}.")
    mapping, mapping_state = SCHEMES[label_scheme]
    project = labels.data if mapping is None else map_labels(labels.data, mapping)
    moments.append(time.perf_counter())
    cleaned = clean_labels(project, reference.affine)
    moments.append(time.perf_counter())
    masks = {"head": head_envelope(cleaned.labels, reference.affine), "brain": brain_mask(cleaned.labels)}
    meshes = {name: extract_surface(mask, reference.affine) for name, mask in masks.items()}
    moments.append(time.perf_counter())
    contact = boundary_contact(masks["head"], reference.affine)
    warnings = [*reference.warnings, *labels.warnings, *cleaned.warnings]
    if set(contact) - {"I"}:
        warnings.append(f"Head reaches the image edge on side(s) {', '.join(contact)}; anatomy there may be cut.")
    out.mkdir(parents=True)
    reference_copy = "reference.nii.gz" if reference.path.name.lower().endswith(".gz") else "reference.nii"
    shutil.copyfile(reference.path, out / reference_copy)
    write_nifti(out / "labels.nii.gz", cleaned.labels, reference.affine)
    surfaces = {}
    for name, mesh in meshes.items():
        path = out / f"{name}.{surface_format}"
        WRITERS[surface_format](path, mesh)
        surfaces[name] = describe_surface(path, mesh)
    moments.append(time.perf_counter())
    stages = ("read", "cleanup", "surfaces", "export")
    model = {
        "schema": SCHEMA,
        "frame": {"name": "RAS", "units": "mm", "declared_in_surface_files": FRAME_TAG,
                  "definition": "World coordinates of the reference image affine."},
        "reference_image": {"file": reference.path.name, "copy": reference_copy, "sha256": sha256(reference.path),
                            "shape": list(reference.data.shape), "affine": reference.affine.tolist(),
                            "axes": "".join(nib.aff2axcodes(reference.affine))},
        "labels": {"file": "labels.nii.gz", "sha256": sha256(out / "labels.nii.gz"),
                   "values": {str(BACKGROUND): "background", **{str(k): v for k, v in TISSUES.items()}},
                   "source_scheme": label_scheme, "mapping_state": mapping_state},
        "surfaces": surfaces,
        "cleanup": {"settings": {**cleaned.settings, "envelope_seal_mm": ENVELOPE_SEAL_MM},
                    "volumes": cleaned.volumes},
        "coverage": {"head_touches_image_edge": contact, "face": "not_assessed"},
        "warnings": warnings,
        "timing_seconds": dict(zip(stages, (b - a for a, b in zip(moments, moments[1:])))),
        "software": {"python": platform.python_version(), **{name: metadata.version(name) for name in _PACKAGES}},
    }
    (out / "model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
    return model


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("t1", type=Path)
    parser.add_argument("labels", type=Path)
    parser.add_argument("out", type=Path, help="New folder outside any Git checkout")
    parser.add_argument("--label-scheme", choices=sorted(SCHEMES), default="project")
    parser.add_argument("--format", choices=sorted(WRITERS), default="stl")
    args = parser.parse_args()
    try:
        model = build_model(args.t1, args.labels, args.out, args.label_scheme, args.format)
    except ValueError as error:
        raise SystemExit(f"Cannot build the model: {error}") from error
    for name, surface in model["surfaces"].items():
        print(f"{name}: {surface['triangles']:,} triangles, {surface['volume_ml']:.0f} mL, closed={surface['closed']}")
    print("Seconds:", {stage: round(value, 2) for stage, value in model["timing_seconds"].items()})
    for warning in model["warnings"]:
        print("Warning:", warning)


if __name__ == "__main__":
    main()
