# E1 presentation demo implementation plan

**Goal:** Demonstrate the completed E1 model for the Friday presentation without a new desktop UI or additional training.

**Approved scope:** The user accepted the proposed short inference notebook and saved-result fallback on 2026-11-03. Keep implementation under `tools/e1_training`; preserve the existing MRI/CHARM application and training artifacts. No commit, push, paid runtime launch, or external sharing is part of this task.

**Architecture:** A small Python command renders MRI/reference/prediction comparisons and an offline HTML report. Its separate prediction command uses the pinned nnU-Net 2.8.1 predictor with the existing custom trainer. A generated standalone Colab notebook embeds reviewed helpers, reads the user's existing Drive experiment and audited archive, and defaults to showing recorded validation predictions. Explicitly enabled inference writes to a fresh demo folder, never to training outputs.

**Tech stack:** Existing NumPy, nibabel, matplotlib, dependency lock, custom trainer, archive extraction and subprocess logger. Python standard library for notebook generation and self-contained HTML.

## Tasks

- [x] Add failing behavioral tests in `test_demo.py`: reference-relative Dice, same-grid validation, unknown-unit disclosure, preservation of source files, no-overwrite reports, model-file checks, recorded/live distinction, and standalone notebook defaults.
- [x] Add `demo.py`: read-only volume checks, per-class metrics, three-plane comparison, self-contained `report.html`, and a single-case `predict` command. Missing reference means no Dice, not a fabricated score. Inference timing distinguishes model loading from preprocessing/prediction/export.
- [x] Add `build_demo_notebook.py` and generated `E1_Demo.ipynb`: configuration, Drive mount, isolated environment, audited validation-case selection, saved-result report, explicitly gated new inference, output display, and presentation checklist. CPU is sufficient for recorded-result mode; no training command exists.
- [x] Add `DEMO.md` with short Turkish usage instructions and exact model-folder requirements. Preserve generated demo outputs, images and weights outside Git.
- [x] Run synthetic tests and the existing preparation suite. Compile notebook cells and verify embedded sources. Run the report on the supplied GU011 prediction and inspect the rendered image.
- [x] If the user's own final checkpoint is accessible and downloaded, run actual model inference in an isolated environment and record measured outcome; otherwise state the missing checkpoint/live verification limitation explicitly. A Google Drive download warning may require user confirmation.
- [x] Update EXP-003/current/index/log with actual evidence, then provide notebook and working offline report links.

## Acceptance checks

```bash
rtk proxy tools/mri_prototype/.venv/bin/python -m unittest discover -s tools/e1_training -q
rtk proxy tools/mri_prototype/.venv/bin/python tools/e1_training/build_demo_notebook.py
rtk git diff --check
```

The notebook must contain no outputs or patient images in Git. A fresh report must recompute GU011's case mean Dice as 0.8102833287676656 and retain the original unknown-unit limitation. Saved predictions must never be described as a new live inference. This demo demonstrates tissue segmentation and display surfaces, not FEM volume meshing or held-out test success.

## Approved 3D extension (2026-11-03)

The user approved adding a rotatable 3D tissue-surface view to this demonstration before considering SimNIBS adaptation. Derive approximate triangle surfaces from the existing prediction, preserve the numerical source affine, and keep metrics on the original label volumes. Bundle Plotly JavaScript for offline viewing. Tissue checkboxes, opacity controls, brain/head/all presets and camera reset belong in the same report; retain the 2D comparisons. No model training or FEM volume meshing is involved.

- [x] Add failing geometry, bounded-complexity, offline HTML and JavaScript event tests.
- [x] Implement `surface_view.py` and `surface_controls.js`; integrate in recorded and new-inference reports.
- [x] Add pinned viewer dependencies and embedded helpers to the standalone notebook.
- [x] Check the real GU011 output, regenerate notebook/tool ZIP, update documentation and experiment evidence.
- [x] Verify tests, source parity, offline packaging, and unchanged inputs; distinguish geometry/control tests from actual browser/Colab execution.
