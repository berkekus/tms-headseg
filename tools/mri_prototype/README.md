# MRI Workbench prototype

A local PySide6 desktop tool for inspecting NIfTI MRI, reopening SimNIBS head models and exported project models, displaying E1 predictions, viewing tissue surfaces in 3D, exporting a model, and launching installed CHARM. It imports the `tools/charm_gui` window and runner and the `tools/headmodel` geometry package, and reuses `tools/e1_training/surface_view.py` for E1 display geometry; keep those sibling folders together.

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

SimNIBS must be installed separately to create a model. MRI and existing-model inspection do not require an installed SimNIBS runtime. Do not install these dependencies in SimNIBS's bundled Python environment. Embedded 3D uses VTK and PyVistaQt's Qt framebuffer adapter, with a desktop OpenGL context. The framebuffer adapter avoids the native-window repaint loop observed with the stock VTK Qt widget on this Mac.

## Workflow

**Batch mode:** **02 CHARM processing** now contains **Single MRI** and **IXI batch**. The batch page runs the shared training-only assignment, shows per-case records and live logs, and can monitor an existing CLI run without owning or cancelling it. Read the [batch guide](BATCH.md) before starting a long job. `--batch` opens monitoring mode without launching CHARM.

1. **Open T1 MRI** or choose **Use Ernie example**. Ernie selection fills the public T1/T2 paths and subject ID; it never starts processing. `--ernie` performs the same preload on startup.
2. Scroll the three slice controls. Adjust window level/width or use **Auto contrast**. Source dimensions, spacing, and axis codes are displayed. The views use neurological convention: left is screen left in axial/coronal views. Sagittal anterior is screen right. Positions are RAS world millimeters, and image proportions account for voxel spacing.
3. Optionally **Load tissue labels** from a discrete NIfTI segmentation of the same subject. Standalone overlays identify numeric IDs. Adjust opacity or clear the overlay.
4. In **CHARM processing**, review T1, optional T2, installed CHARM, a new subject ID, and an output folder outside Git. If the T1 path changes there, return to inspection and use **Load T1 selected in CHARM tab** before starting.
5. **Create head model** uses the existing safe runner, live logs, child-scoped thread limits, and process-tree cancellation. On successful completion with expected outputs, the generated model folder is loaded automatically for slice and 3D inspection. **Open report** and **Open 3D mesh in Gmsh** remain available for external inspection.

### Reopen a precreated model

Choose **Open head model folder…** in the inspection tab and select an `m2m_SUBJECT` directory. It must contain `T1.nii.gz` (or `T1.nii`), `final_tissues.nii.gz`, and the subject's `.msh` file. If no matching subject filename exists, there must be exactly one `.msh` file. `final_tissues_LUT.txt` and the HTML report are optional. Missing or ambiguous required assets produce an error and clear the previous model.

The same button opens a folder exported by [`tools/headmodel`](../headmodel/README.md), recognized by its `model.json`. Such a folder must pass `verify_model` first; a failed check refuses the model and clears the view. Its face-coverage status and warnings stay visible beside the 3D view. SimNIBS and project label numbers mean different tissues, so the viewer finds head and brain surfaces by role rather than by number.

**Export head model…** turns the open SimNIBS folder, or a T1 with loaded project labels, into a new exported folder and opens it. Name a new folder outside any Git checkout. SimNIBS labels use the mapping proposed in EXP-002, which is not accepted.

MRI, segmentation, and tagged mesh surfaces are read in the background. The lookup table supplies tissue names and colors for both the slice overlays and 3D controls; absent names stay numeric. **Open model report** opens the selected folder's report without needing a processing job in this session.

Select **03 3D model** to rotate with left drag, pan with Shift-drag, and zoom with the wheel. Each surface has visibility and opacity controls. The initial view shows gray matter with transparent scalp where those tags exist. **Brain**, **Head**, and **Reset camera** provide convenient views. The orientation cube labels R/L, A/P, and S/I.

**Show MRI slice planes** places the three current MRI slices into the same physical coordinate system as the mesh. Slice positions and contrast follow the inspection tab's controls. Original mesh node coordinates are retained in subject-world millimeters; the MRI affine places the image planes. No additional mesh transform, smoothing, decimation, or registration is applied. Visual checks remain necessary; bounding-box overlap alone does not establish anatomical alignment.

To preload an existing model without starting CHARM:

```bash
tools/mri_prototype/.venv/bin/python tools/mri_prototype/prototype.py --model /path/to/m2m_SUBJECT
```

Loading and resampling run in a background thread. Import controls are disabled during loading or processing; slice and contrast controls remain available. Closing during image loading asks you to wait for loading to finish. Closing during a CHARM run retains the existing confirmation/cancellation behavior. No reconstruction starts automatically, and original MRI/label files are never written.

### Open our E1 model's segmentation

1. Start the Workbench using the command above. If its environment predates this extension, install the updated requirements first; E1 surfaces need `scikit-image==0.26.0`.
2. Click **Open E1 segmentation…** in the header. Choose the source T1 MRI, then its saved E1 prediction (`.nii` or `.nii.gz`). Select the corresponding subject's prediction from `fold_0/validation/`, or an output from the separate E1 inference demo. This action reads a prediction; it does not run the neural network.
3. Original E1 handoff MRIs have unknown header units. For those originals only, explicitly enable **E1: assume mm** before importing if using the handoff's millimetre assumption. It is off by default, applies only to this E1 import, and never rewrites headers. The metadata and 3D view state that units are assumed and physical scale is unverified. Later team-prepared copies with explicit units need no opt-in. Ordinary MRI and SimNIBS imports remain strict.
4. Inspect the three slice overlays, then select **03 3D model**. Rotate, zoom, change tissue visibility/opacity, choose **Brain** or **Head**, and optionally show the linked MRI slice planes.

E1 IDs are **1 skin / 2 skull / 3 CSF / 4 gray matter / 5 white matter**. These differ from SimNIBS IDs; names, colors and presets switch with the imported source. The prediction must contain nonempty integer IDs 0–5 and match the original MRI's shape and affine after unit normalization. Different grids are rejected, not registered. Matching metadata does not prove subject identity or anatomical accuracy.

The shared marching-cubes extractor uses the prediction's original affine for surface placement and bounded, approximate geometry (at most 360,000 triangles). The summary states the display sampling step. Source labels and scores are unchanged. These surfaces need no `.msh` conversion and are **not** a simulation-ready tetrahedral FEM mesh. Loading a new input that fails clears the previous scene; canceling a file picker leaves it unchanged.

The header import action displays a completed prediction. To generate a new one, open **04 E1 segmentation**: select the inference Python, trusted model folder, MRI and output parent, then click **Generate E1 segmentation**. Successful new output opens automatically in 2D/3D. See the [desktop inference guide](INFERENCE.md) for setup, cancellation, provenance and checks. The existing K3 import/export workflow is preserved; training and model weights remain outside the desktop environment in the [E1 handoff](../e1_training/HANDOFF.md).

## Geometry and validation

- Supports real numeric, finite 3D `.nii`/`.nii.gz` volumes with coded qform/sform and explicit mm, meter, or micron spatial units. Trailing singleton dimensions are accepted (as used by supplied SimNIBS labels); multi-volume 4D data is rejected. Unsupported or malformed data produces an inline error. A failed MRI replacement clears the old preview.
- Unit normalization and orientation changes affect the in-memory display only. Source geometry is retained. Axis permutations/flips use NiBabel; oblique/sheared scans are resampled linearly to an axis-aligned RAS display grid.
- Labels must be non-negative integer IDs up to 65535, with 1–256 foreground classes. They are resampled by affine using nearest-neighbor interpolation, preserving discrete IDs. Nonoverlapping/empty overlays are rejected.
- Matching header coordinates does **not** prove the same patient or anatomically correct registration. Confirm the subject and inspect boundaries. The tool does not register arbitrary scans or assess anatomical quality. The optional T2 input is passed to CHARM; this prototype previews T1 only.
- Source and resampled volumes are each limited to 128 million voxels. Several arrays can coexist during loading; allow memory beyond the approximately 512 MB float32 volume size at that limit.
- Model import reads tagged triangles from Gmsh files, including SimNIBS binary version 2.2. Tetrahedra are not rendered, and missing triangle tags are rejected. Surface tags `1000 + tissue ID` use the corresponding lookup-table entry; other tags remain explicit. At most 256 surface groups and mesh files up to 1 GB are accepted. Whole-mesh parsing and rendering can consume several times the input file size in memory.

## Checks

```bash
tools/mri_prototype/.venv/bin/python -m unittest discover -s tools/mri_prototype -v
```

The checks use asymmetric synthetic volumes for left/right and plane orientation, permuted anisotropic axes, oblique resampling, unit conversion, affine-aware discrete overlays, rejected inputs, stale-preview clearing, and a complete stand-in CHARM/automatic-model workflow. Binary Gmsh fixtures check unchanged mesh coordinates, tissue tags, lookup tables, missing/ambiguous assets, and reopening without processing. These checks avoid creating an OpenGL window and do not execute real CHARM. On Windows use the environment's `Scripts/python.exe` as above.

For an explicit native graphics check, supply an existing model directory:

```bash
tools/mri_prototype/.venv/bin/python tools/mri_prototype/check_3d.py /path/to/m2m_SUBJECT
```

This first measures where a single bright voxel lands in an orthographic render of its MRI plane, then opens and closes a native window and checks rendered geometry, mouse rotation, tissue visibility/opacity, linked MRI-plane bounds, and reopening. It never starts CHARM. Optional `--screenshots /path/to/local/review` saves inspection images; keep those outside Git. Run this check in a normal desktop session with graphics access, not the Qt offscreen platform.

`--smoke-test` opens the window and exits once any requested preload finishes. For example:

```bash
tools/mri_prototype/.venv/bin/python tools/mri_prototype/prototype.py --ernie --smoke-test
```

Initial slice-only prototype observations on 2026-11-02 on the development Apple Silicon Mac:

- All 12 prototype checks passed, including changed-input gating and closing during an image load. The existing launcher suite passed 19 checks with one native Windows check skipped.
- The public Ernie T1 loaded as a 256 × 256 × 208 source volume with PSR source axes. Its RAS display and the separately loaded, supplied Ernie tissue labels rendered in all three views. This is supplied-example inspection, not a new reconstruction.
- The native macOS `--ernie --smoke-test` exited successfully. Inspection screenshots were also reviewed from offscreen rendering.
- The isolated environment used Python 3.14.7, PySide6 Essentials 6.12.0, NiBabel 5.4.2, NumPy 2.5.4, and SciPy 1.18.1. These checks do not establish Windows behavior or anatomical accuracy.

Embedded 3D extension observations on the same date:

- All 18 prototype checks passed. The native `check_3d.py` passed on the completed November 2 Ernie reconstruction: 10 surfaces and 1,160,466 triangles. It verified mesh/actor bounds, mouse rotation, tissue controls, MRI-plane bounds/position linkage, and reopening in an existing renderer.
- The model folder's MRI, generated labels, subject mesh, lookup table, and report loaded without rerunning CHARM. Native inspection screenshots were reviewed. This demonstrates viewing that existing reconstruction; it does not establish anatomical accuracy or a new reconstruction through the extended prototype.
- The environment additionally used meshio 5.3.5, VTK 9.7.1, and PyVistaQt 0.13.1. Native Windows rendering, packaged installers, and broad hardware compatibility remain unverified.

Windows observations on 2026-11-02 on an NVIDIA RTX 4070 SUPER, with Python 3.13.1 and VTK 9.7.1:

- All 26 prototype checks passed. `check_3d.py` passed natively on the supplied Ernie folder and on a project export built from its labels. Screenshots of the export were reviewed by the agent running the check, not by a clinician.
- Opening an exported Ernie model includes verification, which took about 10 seconds. This demonstrates viewing on Windows, not anatomical accuracy. Packaged installers and other graphics hardware remain unverified.
- After merging the E1 display on 2026-11-03, all 38 prototype checks passed on Windows, and `check_3d.py` passed natively for a SimNIBS folder, a project export, and the E1 path. The E1 run used fresh Ernie labels mapped to the project schema as a stand-in prediction, with stated millimetre units; no real E1 prediction was available on this machine.

E1 desktop extension observations on 2026-11-03:

- All 29 prototype checks passed, including ten new E1 checks and a SimNIBS/E1 switching regression. The E1 tool suite passed 37 checks; CHARM passed 19 with one native Windows check skipped.
- The native check below passed on the original GU011 MRI and its recorded prediction, using explicit `--assume-mm`. Five surfaces / 348,104 triangles rendered. Actor bounds, mouse rotation, visibility/opacity, linked MRI planes and reopening passed; screenshots were inspected. Source MRI/prediction hashes remained unchanged.
- The native macOS environment added scikit-image 0.26.0. NumPy 2.5 emits dependency deprecation warnings during marching cubes; the display checks still passed. Windows rendering and anatomical/physical-scale validation are not established.

```bash
tools/mri_prototype/.venv/bin/python tools/mri_prototype/check_3d.py \
  --e1-mri /outside/git/GU011_0000.nii.gz \
  --e1-prediction /outside/git/GU011.nii \
  --assume-mm --screenshots /outside/git/e1-desktop-review
```

`--assume-mm` explicitly opts into the provisional original-handoff assumption; omit it for inputs with known units. The check opens and closes a native window and never runs the model.

## Prototype boundaries

No DICOM conversion, editing, measurements, model training, automatic QC, electric-field display, coil placement, or installer is included. The embedded viewer displays existing SimNIBS surfaces or display surfaces extracted from E1 predictions; it does not reproduce the full SimNIBS simulation interface. Windows execution and a new full CHARM reconstruction through this prototype require separate checks; supplied Ernie segmentation files are example data, not new reconstruction evidence.

Dependencies and interfaces: [NiBabel processing](https://nipy.org/nibabel/reference/nibabel.processing.html), [Qt for Python](https://doc.qt.io/qtforpython-6/), [PyVistaQt framebuffer adapter](https://github.com/pyvista/pyvistaqt/blob/main/pyvistaqt/rwi.py), [SimNIBS coordinates](https://simnibs.github.io/simnibs/build/html/documentation/coordinates.html), [surface numbering](https://simnibs.github.io/simnibs/build/html/tutorial/visualization.html), and [existing CHARM launcher](../charm_gui/README.md).
