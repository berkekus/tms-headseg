# MRI Workbench prototype

A local PySide6 desktop tool for inspecting NIfTI MRI and launching installed SimNIBS CHARM. Everything new lives in this folder. It imports the existing `tools/charm_gui` window and runner; that tool's source and the rest of the application are not modified.

## Run

Use Python 3.11 or newer and install dependencies into this tool's own environment. From the repository root on macOS:

```bash
python3 -m venv tools/mri_prototype/.venv
tools/mri_prototype/.venv/bin/python -m pip install -r tools/mri_prototype/requirements.txt
tools/mri_prototype/.venv/bin/python tools/mri_prototype/prototype.py
```

Windows PowerShell:

```powershell
py -3 -m venv tools/mri_prototype/.venv
& tools/mri_prototype/.venv/Scripts/python.exe -m pip install -r tools/mri_prototype/requirements.txt
& tools/mri_prototype/.venv/Scripts/python.exe tools/mri_prototype/prototype.py
```

SimNIBS must be installed separately to create a model. MRI inspection does not require SimNIBS. Do not install these dependencies in SimNIBS's bundled Python environment.

## Workflow

1. **Open T1 MRI** or choose **Use Ernie example**. Ernie selection fills the public T1/T2 paths and subject ID; it never starts processing. `--ernie` performs the same preload on startup.
2. Scroll the three slice controls. Adjust window level/width or use **Auto contrast**. Source dimensions, spacing, and axis codes are displayed. The views use neurological convention: left is screen left in axial/coronal views. Sagittal anterior is screen right. Positions are RAS world millimeters, and image proportions account for voxel spacing.
3. Optionally **Load tissue labels** from a discrete NIfTI segmentation of the same subject. Colors identify numeric IDs; tissue names are deliberately not guessed. Adjust opacity or clear the overlay.
4. In **CHARM processing**, review T1, optional T2, installed CHARM, a new subject ID, and an output folder outside Git. If the T1 path changes there, return to inspection and use **Load T1 selected in CHARM tab** before starting.
5. **Create head model** uses the existing safe runner, live logs, child-scoped thread limits, and process-tree cancellation. On successful completion with expected outputs, `final_tissues.nii.gz` is loaded into the slice viewer automatically. **Open report** and **Open 3D mesh in Gmsh** use external applications.

Loading and resampling run in a background thread. Import controls are disabled during loading or processing; slice and contrast controls remain available. Closing during image loading asks you to wait for loading to finish. Closing during a CHARM run retains the existing confirmation/cancellation behavior. No reconstruction starts automatically, and original MRI/label files are never written.

## Geometry and validation

- Supports real numeric, finite 3D `.nii`/`.nii.gz` volumes with coded qform/sform and explicit mm, meter, or micron spatial units. Trailing singleton dimensions are accepted (as used by supplied SimNIBS labels); multi-volume 4D data is rejected. Unsupported or malformed data produces an inline error. A failed MRI replacement clears the old preview.
- Unit normalization and orientation changes affect the in-memory display only. Source geometry is retained. Axis permutations/flips use NiBabel; oblique/sheared scans are resampled linearly to an axis-aligned RAS display grid.
- Labels must be non-negative integer IDs up to 65535, with 1–256 foreground classes. They are resampled by affine using nearest-neighbor interpolation, preserving discrete IDs. Nonoverlapping/empty overlays are rejected.
- Matching header coordinates does **not** prove the same patient or anatomically correct registration. Confirm the subject and inspect boundaries. The tool does not register arbitrary scans or assess anatomical quality. The optional T2 input is passed to CHARM; this prototype previews T1 only.
- Source and resampled volumes are each limited to 128 million voxels. Several arrays can coexist during loading; allow memory beyond the approximately 512 MB float32 volume size at that limit.

## Checks

```bash
tools/mri_prototype/.venv/bin/python -m unittest discover -s tools/mri_prototype -v
```

The checks use asymmetric synthetic volumes for left/right and plane orientation, permuted anisotropic axes, oblique resampling, unit conversion, affine-aware discrete overlays, rejected inputs, stale-preview clearing, and a complete stand-in CHARM/automatic-overlay workflow. They do not execute real CHARM. On Windows use the environment's `Scripts/python.exe` as above.

`--smoke-test` opens the window and exits once any requested preload finishes. For example:

```bash
tools/mri_prototype/.venv/bin/python tools/mri_prototype/prototype.py --ernie --smoke-test
```

Observed on 2026-11-02 on the development Apple Silicon Mac:

- All 12 prototype checks passed, including changed-input gating and closing during an image load. The existing launcher suite passed 19 checks with one native Windows check skipped.
- The public Ernie T1 loaded as a 256 × 256 × 208 source volume with PSR source axes. Its RAS display and the separately loaded, supplied Ernie tissue labels rendered in all three views. This is supplied-example inspection, not a new reconstruction.
- The native macOS `--ernie --smoke-test` exited successfully. Inspection screenshots were also reviewed from offscreen rendering.
- The isolated environment used Python 3.14.7, PySide6 Essentials 6.12.0, NiBabel 5.4.2, NumPy 2.5.4, and SciPy 1.18.1. These checks do not establish Windows behavior or anatomical accuracy.

## Prototype boundaries

No DICOM conversion, embedded 3D renderer, editing, measurements, model training, automatic QC, or installer is included. The existing external Gmsh workflow supplies 3D inspection. Windows execution and a new full CHARM reconstruction through this prototype require separate checks; supplied Ernie segmentation files are example data, not new reconstruction evidence.

Dependencies and interfaces: [NiBabel processing](https://nipy.org/nibabel/reference/nibabel.processing.html), [Qt for Python](https://doc.qt.io/qtforpython-6/), and [existing CHARM launcher](../charm_gui/README.md).
