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
head = extract_surface(head_envelope(result.labels), source.affine)
brain = extract_surface(brain_mask(result.labels), source.affine)
# head.vertices are world coordinates in RAS+ millimetres.
```

Cleanup follows the class-specific table in [labels and facial coverage](../../knowledge/concepts/labels-and-face.md). The head surface is the outer envelope, so enclosed air cavities stay background in the labels but do not appear in the surface. Brain cavities are kept. The island threshold, smoothing count, and warning limits are provisional values, not validated settings.

## Files

- `frames.py`: RAS/LPS conversion, voxel/world mapping, ITK geometry.
- `images.py`: validated NIfTI reading and the project writer.
- `reversible.py`: lossless reorientation and the carrier file for the model.
- `labels.py`: project schema and source label mappings.
- `cleanup.py`: class-specific cleanup with a volume report and warnings.
- `surfaces.py`: closed surfaces in world millimetres, and integrity measures.
- `phantom.py`: asymmetric synthetic head for geometry checks.

## Checks

```bash
python -m unittest discover -s tools/headmodel -t tools
```

The tests use synthetic images and real SimpleITK reads and writes. They do not need MRI data, a GPU, or SimNIBS. SimpleITK prints warnings for the intentionally sheared files.
