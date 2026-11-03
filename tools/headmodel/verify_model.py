"""Independent check of an exported model.

Surfaces are read back by meshio, not by the code that wrote them, then measured against the
exported labels in world millimetres. A mirrored, rescaled, or LPS surface fails here even
if its checksum matches. This checks geometry against the labels, not anatomical accuracy.

Usage: python tools/headmodel/verify_model.py MODEL_FOLDER
"""

import json
from pathlib import Path
import sys

import meshio
import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from headmodel.cleanup import brain_mask, head_envelope
from headmodel.export import FRAME_TAG, HEADER_READERS, SCHEMA, sha256
from headmodel.frames import world_to_voxel
from headmodel.images import WORLD_TOLERANCE_MM, read_source, world_disagreement
from headmodel.labels import validate_project_labels
from headmodel.surfaces import Mesh, is_closed

BOUNDARY_TOLERANCE_VOXELS = 1.5


def boundary_distance(points, mask, affine):
    """Millimetres from each point to the mask boundary; points beyond the image use its edge."""
    padded = np.pad(mask, 1)
    spacing = np.linalg.norm(affine[:3, :3], axis=0)
    field = (ndimage.distance_transform_edt(~padded, sampling=spacing)
             - ndimage.distance_transform_edt(padded, sampling=spacing))
    voxels = world_to_voxel(affine, points) + 1
    return np.abs(ndimage.map_coordinates(field, voxels.T, order=1, mode="nearest"))


def verify_model(folder, measurements=None):
    """Return a list of failures; pass a dict to also receive distances per surface."""
    folder = Path(folder)
    model = json.loads((folder / "model.json").read_text(encoding="utf-8"))
    failures = []
    if model.get("schema") != SCHEMA:
        failures.append(f"model.json: expected schema {SCHEMA}.")
    if (model["frame"]["name"], model["frame"]["units"]) != ("RAS", "mm"):
        failures.append("model.json: the frame is not RAS millimetres.")
    labels_path = folder / model["labels"]["file"]
    if sha256(labels_path) != model["labels"]["sha256"]:
        failures.append(f"{labels_path.name}: checksum differs from model.json.")
    labels = read_source(labels_path)
    reference = model["reference_image"]
    if sha256(folder / reference["copy"]) != reference["sha256"]:
        failures.append(f"{reference['copy']}: checksum differs from model.json.")
    if (list(labels.data.shape) != reference["shape"]
            or world_disagreement(labels.affine, np.array(reference["affine"]), labels.data.shape) > WORLD_TOLERANCE_MM):
        failures.append(f"{labels_path.name}: not on the reference image grid.")
    project = validate_project_labels(labels.data)
    # Models exported before the envelope seal existed were built without one.
    seal = model["cleanup"]["settings"].get("envelope_seal_mm", 0.)
    masks = {"head": lambda: head_envelope(project, labels.affine, seal), "brain": lambda: brain_mask(project)}
    tolerance = BOUNDARY_TOLERANCE_VOXELS * float(np.linalg.norm(labels.affine[:3, :3], axis=0).max())
    for name, record in model["surfaces"].items():
        path = folder / record["file"]
        if sha256(path) != record["sha256"]:
            failures.append(f"{path.name}: checksum differs from model.json.")
            continue
        if FRAME_TAG not in HEADER_READERS[path.suffix](path):
            failures.append(f"{path.name}: does not declare its frame ({FRAME_TAG}).")
        loaded = meshio.read(path)
        faces = loaded.cells_dict["triangle"]
        if len(faces) != record["triangles"]:
            failures.append(f"{path.name}: holds {len(faces)} triangles, model.json says {record['triangles']}.")
        if not is_closed(Mesh(loaded.points, faces)):
            failures.append(f"{path.name}: the surface is not closed.")
        distance = boundary_distance(loaded.points, masks[name](), labels.affine)
        if measurements is not None:
            measurements[name] = {"mean_mm": float(distance.mean()), "p95_mm": float(np.percentile(distance, 95)),
                                  "max_mm": float(distance.max())}
        if distance.max() > tolerance:
            failures.append(f"{path.name}: {distance.max():.1f} mm from the label boundary (limit {tolerance:.1f} mm).")
    return failures


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    measurements = {}
    failures = verify_model(sys.argv[1], measurements)
    for name, values in measurements.items():
        print(name, {key: round(value, 3) for key, value in values.items()})
    for failure in failures:
        print("FAIL:", failure)
    print("Model verified." if not failures else f"{len(failures)} check(s) failed.")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
