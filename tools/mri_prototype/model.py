"""Read existing SimNIBS models without altering their subject-world geometry."""

from dataclasses import dataclass
from pathlib import Path

from meshio.gmsh import read as read_gmsh
import numpy as np

from volume import Volume, bounds, load_labels, load_volume


@dataclass
class Surface:
    tag: int
    points: np.ndarray
    triangles: np.ndarray


@dataclass
class HeadModel:
    directory: Path
    volume: Volume
    labels: tuple
    mesh_path: Path
    surfaces: list
    tissues: dict
    report: Path | None


def read_lut(path):
    if not path.is_file():
        return {}
    if path.stat().st_size > 1_000_000:
        raise ValueError("Tissue lookup table is unexpectedly large.")
    tissues = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = line.split("#", 1)[0].split()
        if not fields:
            continue
        try:
            label = int(fields[0])
            rgba = tuple(map(int, fields[-4:]))
            name = " ".join(fields[1:-4]).replace("_", " ")
            if not name or not 0 <= label <= 65535 or not all(0 <= value <= 255 for value in rgba):
                raise ValueError
            if label in tissues:
                raise ValueError
        except (ValueError, IndexError) as error:
            raise ValueError(f"Invalid tissue lookup table at line {number}.") from error
        tissues[label] = (name, rgba[:3])
    return tissues


def read_surfaces(path, volume):
    # shortcut: load bounded meshes in memory; use streaming for larger models.
    if path.stat().st_size > 1_000_000_000:
        raise ValueError("Mesh exceeds the prototype limit of 1 GB.")
    try:
        mesh = read_gmsh(path)
    except Exception as error:
        raise ValueError(f"Cannot read Gmsh mesh: {error}") from error
    points = np.asarray(mesh.points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.isfinite(points).all():
        raise ValueError("Mesh needs finite 3D node coordinates.")
    tagged = {}
    for index, block in enumerate(mesh.cells):
        if block.type != "triangle":
            continue
        triangles = block.data
        if triangles.ndim != 2 or triangles.shape[1] != 3 or not len(triangles):
            continue
        if triangles.min() < 0 or triangles.max() >= len(points):
            raise ValueError("Mesh triangle refers to an invalid node.")
        tags = mesh.cell_data.get("gmsh:physical", mesh.cell_data.get("gmsh:geometrical"))
        if tags is None or len(tags[index]) != len(triangles):
            raise ValueError("Mesh triangle tissue tags are missing or inconsistent.")
        for tag in np.unique(tags[index]):
            tagged.setdefault(int(tag), []).append(triangles[tags[index] == tag])
    if not tagged or len(tagged) > 256:
        raise ValueError("Mesh needs 1–256 tagged triangle surfaces; tetrahedra alone are not supported.")
    surfaces = []
    for tag, blocks in sorted(tagged.items()):
        faces = np.concatenate(blocks)
        used, inverse = np.unique(faces, return_inverse=True)
        surfaces.append(Surface(tag, points[used].copy(), inverse.reshape(-1, 3)))
    low, high = bounds(volume.image)
    surface_low = np.min([surface.points.min(axis=0) for surface in surfaces], axis=0)
    surface_high = np.max([surface.points.max(axis=0) for surface in surfaces], axis=0)
    if np.any(surface_high < low) or np.any(surface_low > high):
        raise ValueError("Mesh and MRI world coordinates do not overlap. No automatic registration is applied.")
    return surfaces


def load_model(directory):
    directory = Path(directory).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError("Choose an existing SimNIBS m2m model folder.")
    t1 = next((directory / name for name in ("T1.nii.gz", "T1.nii") if (directory / name).is_file()), None)
    labels = directory / "final_tissues.nii.gz"
    if t1 is None or not labels.is_file():
        raise ValueError("Model folder needs T1.nii[.gz] and final_tissues.nii.gz.")
    expected = directory / (directory.name.removeprefix("m2m_") + ".msh")
    candidates = [expected] if expected.is_file() else sorted(directory.glob("*.msh"))
    if len(candidates) != 1:
        raise ValueError("Model folder must identify one subject .msh file unambiguously.")
    volume = load_volume(t1)
    aligned = load_labels(labels, volume)
    tissues = read_lut(directory / "final_tissues_LUT.txt")
    surfaces = read_surfaces(candidates[0], volume)
    report = next((directory / name for name in ("charm_report.html", "results.html")
                   if (directory / name).is_file()), None)
    return HeadModel(directory, volume, aligned, candidates[0], surfaces, tissues, report)


def tissue_for_surface(tag):
    """SimNIBS tissue surfaces use 1000 + volume ID; other tags stay explicit."""
    return tag - 1000 if 1000 < tag < 2000 else None
