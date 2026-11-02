"""Measure exported surfaces against a SimNIBS mesh of the same subject, in world millimetres.

This checks world alignment and scale against an independently produced surface. Using the
same subject's labels, it is not a measure of anatomical accuracy.

Usage: python tools/headmodel/compare_to_mesh.py MODEL_FOLDER SUBJECT.msh
"""

import json
from pathlib import Path
import sys

import meshio
import numpy as np
from scipy.spatial import cKDTree

SIMNIBS_SKIN = 1005
SIMNIBS_GRAY_MATTER = 1002
SIMNIBS_WHITE_MATTER = 1001
_REFERENCES = {"head": (SIMNIBS_SKIN,), "brain": (SIMNIBS_WHITE_MATTER, SIMNIBS_GRAY_MATTER)}


def sample_triangles(vertices, faces, divisions=4):
    """Regular points on each triangle, so distances approach point-to-surface values."""
    u, v = np.meshgrid(*[np.linspace(0, 1, divisions + 1)] * 2)
    keep = u + v <= 1 + 1e-9
    weights = np.stack([1 - u[keep] - v[keep], u[keep], v[keep]], axis=1)
    return np.einsum("fvc,pv->fpc", vertices[faces], weights).reshape(-1, 3)


def tagged_triangles(mesh):
    faces = {}
    for index, block in enumerate(mesh.cells):
        if block.type == "triangle":
            tags = mesh.cell_data["gmsh:physical"][index]
            for tag in np.unique(tags):
                faces.setdefault(int(tag), []).append(block.data[tags == tag])
    return {tag: np.concatenate(blocks) for tag, blocks in faces.items()}


def summary(distance):
    return {"mean_mm": float(distance.mean()), "p95_mm": float(np.percentile(distance, 95)),
            "max_mm": float(distance.max())}


def compare_model(folder, mesh_path):
    """Distance from each exported surface to its reference, and the reverse direction."""
    folder = Path(folder)
    model = json.loads((folder / "model.json").read_text(encoding="utf-8"))
    mesh = meshio.read(mesh_path)
    faces = tagged_triangles(mesh)
    report = {}
    for name, record in model["surfaces"].items():
        ours = meshio.read(folder / record["file"])
        ours = sample_triangles(ours.points.astype(float), ours.cells_dict["triangle"])
        reference = sample_triangles(np.asarray(mesh.points, float),
                                     np.concatenate([faces[tag] for tag in _REFERENCES[name]]))
        report[name] = {"model_to_mesh": summary(cKDTree(reference).query(ours, workers=-1)[0]),
                        "mesh_to_model": summary(cKDTree(ours).query(reference, workers=-1)[0])}
    return report


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    print(json.dumps(compare_model(sys.argv[1], sys.argv[2]), indent=2))


if __name__ == "__main__":
    main()
