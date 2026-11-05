"""Read existing head models without altering their subject-world geometry.

Three sources open here: a SimNIBS m2m folder, an exported project model, and an E1 prediction.
Their label numbers mean different tissues, so head and brain surfaces are found by role.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sys

import meshio
from meshio.gmsh import read as read_gmsh
import numpy as np

from volume import Volume, bounds, load_labels, load_volume, read_image

# Reuse the bounded E1 display geometry; no inference/training dependencies are imported.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from e1_training.surface_view import COLORS, extract_surfaces
from headmodel.verify_model import verify_model

E1_TISSUES = {label: (name, tuple(bytes.fromhex(COLORS[label][1:])))
              for label, name in enumerate(("Background", "Skin", "Skull", "CSF", "Gray matter", "White matter"))
              if label}

SIMNIBS_WHITE_MATTER, SIMNIBS_GRAY_MATTER, SIMNIBS_SKIN = 1001, 1002, 1005
_PROJECT_TISSUES = {"skin": ("Skin", (255, 166, 133)), "skull": ("Skull", (255, 239, 179)),
                    "csf": ("CSF", (104, 163, 255)), "gray_matter": ("Gray matter", (129, 129, 129)),
                    "white_matter": ("White matter", (230, 230, 230))}
_PROJECT_SURFACES = {"head": (1, "Head", (255, 166, 133)), "brain": (2, "Brain", (129, 129, 129))}


@dataclass
class Surface:
    tag: int
    points: np.ndarray
    triangles: np.ndarray
    name: str = ""
    color: tuple | None = None
    role: str | None = None


@dataclass
class HeadModel:
    directory: Path
    volume: Volume
    labels: tuple
    mesh_path: Path | None
    surfaces: list
    tissues: dict
    report: Path | None
    kind: str = "simnibs"
    geometry_note: str = "Subject space · original mesh geometry"
    units_assumed: bool = False
    notes: tuple = ()
    export_source: tuple | None = None
    surface_step: int | None = None
    surface_smoothing: float = 0.0


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


def describe_surfaces(surfaces, tissues, head, brains, tissue_of):
    """Name each surface and mark head and brain by role; the first available brain tag wins."""
    tags = {surface.tag for surface in surfaces}
    roles = {head: "head", next((tag for tag in brains if tag in tags), None): "brain"}
    for surface in surfaces:
        surface.role = roles.get(surface.tag)
        if tissue_of(surface.tag) in tissues:
            surface.name, surface.color = tissues[tissue_of(surface.tag)]


def load_project_model(directory):
    """Open an exported model only if it passes the independent check."""
    failures = verify_model(directory)
    if failures:
        raise ValueError(f"Model failed verification: {failures[0]}")
    record = json.loads((directory / "model.json").read_text(encoding="utf-8"))
    volume = load_volume(directory / record["reference_image"]["copy"])
    aligned = load_labels(directory / record["labels"]["file"], volume)
    tissues = {int(value): _PROJECT_TISSUES[name] for value, name in record["labels"]["values"].items()
               if name in _PROJECT_TISSUES}
    surfaces = []
    for role, description in record["surfaces"].items():
        mesh = meshio.read(directory / description["file"])
        tag, name, color = _PROJECT_SURFACES[role]
        surfaces.append(Surface(tag, np.asarray(mesh.points, dtype=np.float64), mesh.cells_dict["triangle"],
                                name, color, role))
    face = record["coverage"]["face"].replace("_", " ")
    return HeadModel(directory, volume, aligned, directory / "model.json", surfaces, tissues, None,
                     kind="project", geometry_note="Subject space · exported surfaces",
                     notes=(f"Face coverage: {face}.", *record["warnings"]))


def load_model(directory):
    directory = Path(directory).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError("Choose an existing SimNIBS m2m model folder.")
    if (directory / "model.json").is_file():
        return load_project_model(directory)
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
    describe_surfaces(surfaces, tissues, SIMNIBS_SKIN, (SIMNIBS_GRAY_MATTER, SIMNIBS_WHITE_MATTER), tissue_for_surface)
    report = next((directory / name for name in ("charm_report.html", "results.html")
                   if (directory / name).is_file()), None)
    return HeadModel(directory, volume, aligned, candidates[0], surfaces, tissues, report,
                     export_source=(t1, labels, "charm"))


def smooth_display_surface(surface, affine, factor):
    """Apply Slicer's closed-surface Windowed Sinc settings in label voxel space."""
    from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray, vtk_to_numpy
    from vtkmodules.vtkCommonCore import vtkPoints
    from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
    from vtkmodules.vtkFiltersCore import vtkWindowedSincPolyDataFilter

    points = vtkPoints()
    points.SetData(numpy_to_vtk((surface.points - affine[:3, 3]) @ np.linalg.inv(affine[:3, :3]).T, deep=True))
    cells = vtkCellArray()
    cells.SetData(numpy_to_vtkIdTypeArray(np.arange(0, surface.triangles.size + 1, 3, dtype=np.int64), deep=True),
                  numpy_to_vtkIdTypeArray(surface.triangles.astype(np.int64).ravel(), deep=True))
    poly = vtkPolyData()
    poly.SetPoints(points)
    poly.SetPolys(cells)
    # Slicer vtkBinaryLabelmapToClosedSurfaceConversionRule uses this factor mapping.
    smoother = vtkWindowedSincPolyDataFilter()
    smoother.SetInputData(poly)
    smoother.SetNumberOfIterations(int(20 + factor * 40))
    smoother.SetPassBand(10.0 ** (-4.0 * factor))
    smoother.BoundarySmoothingOff()
    smoother.FeatureEdgeSmoothingOff()
    smoother.NonManifoldSmoothingOn()
    smoother.NormalizeCoordinatesOn()
    smoother.Update()
    output = smoother.GetOutput()
    if output.GetNumberOfPoints() != len(surface.points) or output.GetNumberOfCells() != len(surface.triangles):
        raise ValueError("Surface smoothing unexpectedly changed mesh connectivity.")
    world = vtk_to_numpy(output.GetPoints().GetData()) @ affine[:3, :3].T + affine[:3, 3]
    if not np.isfinite(world).all():
        raise ValueError("Surface smoothing produced invalid coordinates.")
    return Surface(surface.tag, world.astype(np.float32), surface.triangles,
                   surface.name, surface.color, surface.role)


def load_e1_model(mri_path, prediction_path, assume_mm=False, surface_step=None, surface_smoothing=0.0):
    """Read paired E1 volumes; extract display surfaces without changing originals."""
    volume = load_volume(mri_path, assume_mm=assume_mm)
    path, source, prediction_assumed = read_image(prediction_path, assume_mm=assume_mm)
    if source.shape != volume.source_shape or not np.allclose(source.affine, volume.source_affine, rtol=0, atol=1e-4):
        raise ValueError("Prediction must match the MRI source grid; no registration is applied.")
    values = np.asarray(source.dataobj)
    if not np.isin(values, range(6)).all() or not np.any(values):
        raise ValueError("Prediction needs nonempty integer labels 0–5 (skin/skull/CSF/GM/WM).")
    labels = load_labels(path, volume, assume_mm=assume_mm)
    if surface_step not in (None, 1, 2, 4):
        raise ValueError("Choose Auto, 1, 2 or 4 voxels for surface detail.")
    if not 0 <= surface_smoothing <= 1:
        raise ValueError("Surface smoothing must be between 0 and 1.")
    meshes = (extract_surfaces(values, source.affine) if surface_step is None else
              extract_surfaces(values, source.affine, step_size=surface_step, max_faces=8_000_000, adaptive=False))
    surfaces = [Surface(mesh["label"], mesh["vertices"], mesh["faces"]) for mesh in meshes]
    if surface_smoothing > 0:
        surfaces = [smooth_display_surface(surface, source.affine, surface_smoothing) for surface in surfaces]
    describe_surfaces(surfaces, E1_TISSUES, 1, (4, 5), lambda tag: tag)
    step = max(mesh["step_size"] for mesh in meshes)
    note = f"Segmentation display surfaces · sampling up to {step} voxels · not a FEM mesh"
    if surface_smoothing > 0:
        note += f"\nSlicer surface smoothing {surface_smoothing:.2f}"
    assumed = volume.units_assumed or prediction_assumed
    if assumed:
        note += "\nUnknown units assumed mm · physical scale unverified"
    # K3 export reads both files under the coordinate contract, which needs units stated in the headers.
    export = None if assumed else (Path(mri_path), Path(prediction_path), "project")
    return HeadModel(path.parent, volume, labels, None, surfaces, E1_TISSUES.copy(), None, "e1", note, assumed,
                     export_source=export, surface_step=surface_step, surface_smoothing=surface_smoothing)


def tissue_for_surface(tag, kind="simnibs"):
    """SimNIBS tissue surfaces use 1000 + volume ID; other tags stay explicit."""
    return tag if kind == "e1" else (tag - 1000 if 1000 < tag < 2000 else None)
