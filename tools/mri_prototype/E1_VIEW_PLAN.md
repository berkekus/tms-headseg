# E1 segmentation display implementation plan

**Goal:** Open an MRI and an existing E1 NIfTI prediction in MRI Workbench, sharing the slice and native 3D views.

**Architecture:** Reuse the reviewed `e1_training.surface_view.extract_surfaces` function and existing `HeadModel`/VTK scene. Add an explicit E1 source kind so tissue IDs 1 skin, 2 skull, 3 CSF, 4 GM, 5 WM never inherit SimNIBS names or presets. No inference, training, original-file changes or FEM export is added.

**Tech stack:** Existing PySide6, NiBabel, NumPy, VTK/PyVistaQt; the demo's scikit-image 0.26.0 surface extractor.

## Scope and decisions

- The user accepted reusing the desktop viewer after the repository review and requested continuing after pushing the three existing commits. Work remains in the current tools checkout, with no repeated approval gate.
- Header action: **Open E1 segmentation…**, choosing MRI then prediction. Canceling either picker preserves the current scene. Both inputs load and surface extraction runs on the existing background worker.
- Inputs must have matching source grids, finite values and nonempty integer labels 0–5. General MRI/SimNIBS import retains strict coded-affine and spatial-unit checks.
- Original E1 MRI headers have unknown units. A separate, default-off **E1: assume mm** checkbox explicitly opts into the handoff's unit assumption for this import only. Metadata, 3D summary and status retain the provisional-unit warning; originals remain byte-identical. The option does not repair files or prove physical/anatomical accuracy.
- Surfaces use the normalized source affine, not the resampled overlay grid; overlays are nearest-neighbor aligned to the MRI display grid. At most 360,000 display triangles; coarse sampling is stated.
- Keep the existing initial slice tab. Status directs the user to **03 3D model**. Rotation, opacity, brain/head presets, MRI planes and switching back to SimNIBS must work.

## Tasks

- [x] 1. Add failing synthetic checks in `test_e1_model.py`: paired-grid surface import, E1 naming/presets, malformed inputs, unknown-unit opt-in, unchanged originals, failure clearing and scene switching. Run the new suite and confirm failure because E1 import is missing.
- [x] 2. In `volume.py`, add optional `assume_mm=False` reading and a `Volume.units_assumed` flag, keeping defaults strict. In `model.py`, add optional mesh path, source-kind/description defaults, `load_e1_model(mri_path, prediction_path, assume_mm=False)` and source-aware surface-ID lookup. Add scikit-image to `requirements.txt`.
- [x] 3. In `prototype.py`, connect the header action/checkbox and existing worker, clear stale state on failed replacement, retain E1 tissue colors in 2D and show explicit unit caveats. In `mesh_viewer.py`, choose controls/presets from source kind, show display-only provenance, and keep original SimNIBS behavior.
- [x] 4. Run all MRI, E1 and CHARM checks. Extend `check_3d.py` to load E1 pairs with explicit unit opt-in and verify actual native rendering, actor bounds, mouse rotation, opacity, MRI planes and reopening. Use original GU011 MRI/prediction read-only; store screenshots outside Git.
- [x] 5. Update tool usage and canonical experiment/current/log notes with actual evidence and unresolved limits. Review the diff. Leave new implementation available for review; the completed push covers only the earlier three commits.

Commands from repository root:

```bash
QT_QPA_PLATFORM=offscreen tools/mri_prototype/.venv/bin/python -m unittest discover -s tools/mri_prototype -p test_e1_model.py -v
QT_QPA_PLATFORM=offscreen tools/mri_prototype/.venv/bin/python -m unittest discover -s tools/mri_prototype -q
```

## Execution record

- Preflight: remote main updated to `ab89d23`; no implementation changes initially. Existing viewer expects tagged mesh triangles and hardcodes SimNIBS presets. Existing E1 surface extraction already has geometry/control checks. Original GU011 MRI and prediction are available locally.
- Review: this plan adds one display workflow. Unknown-unit assumptions remain explicit and scoped; no claim of simulation readiness or automatic anatomical QC.

- Verification: nine E1 tests failed as expected before implementation, then passed. A tenth E1 provenance check also failed then passed during review. Final suite: MRI 29 passed, E1 37 passed, CHARM 19 passed/one Windows skip. Native GU011 Qt/VTK check passed; screenshots inspected, originals hash-identical. Earlier three commits pushed; new display implementation was left local for review. The user subsequently reported a successful manual 3D trial and authorized committing/pushing the extension.
