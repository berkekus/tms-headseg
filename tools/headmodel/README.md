# Head model geometry

Code for the K3 part of Module A, from an image on a known grid towards documented surfaces. It implements the [coordinate contract](../../knowledge/concepts/coordinates.md) and the proposed [D-004](../../knowledge/decisions/004-reversible-preprocessing-proposal.md). Nothing here is a trained model or a clinical tool.

## Setup

Use Python 3.11 or newer in an environment of your own. Keep the environment on a short path on Windows, because some packages exceed the 260-character limit.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r tools/headmodel/requirements.txt
```

## Passing a scan through the model

```python
import sys
sys.path.insert(0, "tools")
from headmodel.images import read_source
from headmodel.reversible import read_model_output, write_model_input

source = read_source("T1.nii.gz")                    # rejects undefined geometry
print(source.warnings)                               # show these to the operator
record = write_model_input(source, "case_0000.nii.gz")   # canonical grid, one geometry
# ... run nnU-Net on case_0000.nii.gz ...
labels = read_model_output("case.nii.gz", record)    # labels on the source grid
# source.affine now maps labels to world (RAS+ millimetres).
```

Store `record.to_json()` with the case if the steps run in separate processes.

To bring a training scan into the shared axis order, write the canonical array and carrier affine:

```python
from headmodel.images import write_nifti
from headmodel.reversible import canonicalize

canonical, record = canonicalize(source.data, source.affine)
write_nifti("IXI045_0000.nii.gz", canonical, record.model_affine)
```

Apply the same call to its labels so image and labels stay on one grid.

## From labels to surfaces

```python
from headmodel.cleanup import brain_mask, clean_labels, head_envelope
from headmodel.surfaces import extract_surface

result = clean_labels(labels, source.affine)         # exclusive labels, volumes, warnings
head = extract_surface(head_envelope(result.labels, source.affine), source.affine)
brain = extract_surface(brain_mask(result.labels), source.affine)
# head.vertices are world coordinates in RAS+ millimetres.
```

Cleanup follows the class-specific table in [labels and facial coverage](../../knowledge/concepts/labels-and-face.md). The head surface is the outer envelope: enclosed cavities, and air reached only through openings narrower than about 16 mm such as the airways behind the nostrils, are filled for the surface but stay background in the labels. Air within 8 mm of the outside is kept, so the skin does not change ([EXP-006](../../knowledge/experiments/ernie-fresh-charm-surfaces.md)). Brain cavities are kept. The island threshold, smoothing count, and warning limits are provisional values, not validated settings.

## Building and checking a model

```bash
python tools/headmodel/build_model.py T1.nii.gz labels.nii.gz OUTPUT_FOLDER
python tools/headmodel/verify_model.py OUTPUT_FOLDER
```

Use `--label-scheme charm` for SimNIBS `final_tissues.nii.gz`; that mapping is proposed, not accepted. Use `--format ply` for PLY surfaces. The output folder must be new and outside any Git checkout, because `.gitignore` does not cover surface files.

| File | Content |
| --- | --- |
| `head.stl`, `brain.stl` | Closed surfaces in RAS millimetres, declaring `SPACE=RAS UNITS=mm`. |
| `reference.nii.gz` | Byte-identical copy of the input T1, so the folder can be inspected on its own. It is patient data; keep it local. |
| `labels.nii.gz` | Cleaned project labels on the source grid. |
| `model.json` | Frame, units, reference image checksum and affine, per-surface checksums and integrity, cleanup volumes, warnings, timing, and software versions. It is written last. |

`coverage.face` stays `not_assessed`: nothing here establishes that a face is intact. `verify_model.py` reads the surfaces with meshio rather than the writer, then measures them against the labels. A failure exits with status 1. `compare_to_mesh.py` measures a model against a SimNIBS mesh of the same subject. Results on the public Ernie example are in [EXP-005](../../knowledge/experiments/ernie-surface-export.md).

## Files

- `frames.py`: RAS/LPS conversion, voxel/world mapping, ITK geometry.
- `images.py`: validated NIfTI reading and the project writer.
- `reversible.py`: lossless reorientation and the carrier file for the model.
- `labels.py`: project schema and source label mappings.
- `cleanup.py`: class-specific cleanup with a volume report and warnings.
- `surfaces.py`: closed surfaces in world millimetres, and integrity measures.
- `export.py`: STL and PLY writers that declare their frame.
- `build_model.py`: T1 and labels to an output folder.
- `verify_model.py`: independent check of an output folder.
- `compare_to_mesh.py`: distances to a SimNIBS mesh of the same subject.
- `phantom.py`: asymmetric synthetic head for geometry checks.

## Checks

```bash
python -m unittest discover -s tools/headmodel -t tools
```

The tests use synthetic images and real SimpleITK reads and writes. They do not need MRI data, a GPU, or SimNIBS. SimpleITK prints warnings for the intentionally sheared files.
