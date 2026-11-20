---
type: Experiment
title: Workbench Surface Display Defaults
description: One-voxel sampling and 0.50 display smoothing for both workspaces, verified without new inference.
status: completed
experiment_state: verified_defaults_and_native_display
---

# Workbench Surface Display Defaults — 2026-11-19

The user requested **1 voxel** and **0.50 surface smoothing** as editable defaults for both Physician and Technical Team, before returning to E3 work.

Shared constants in `tools/mri_prototype/model.py` now define the segmentation loader and initial controls. The Physician reopening path previously supplied explicit Auto/0 values when no saved view existed; it now uses the same defaults. Explicit saved-view settings, including coarse/unsmoothed choices, remain preserved. Imported prebuilt meshes retain their supplied geometry. This is display configuration, not MRI resampling, new segmentation or a weight/export change.

Regressions first failed against the old Auto defaults. All **116 Workbench tests passed**, covering both roles, default source geometry, unchanged labels, manual overrides and Physician reopening without a saved view. The saved-study flow was additionally checked with an explicit 2-voxel / 0.20 saved view and passed after reopening.

The existing native `check_3d.py` opened the already-generated E2 GU011 prediction, asserted 1 voxel / 0.50 in both model and controls, rendered 3,398,014 triangles, and passed camera/visibility/opacity/linked-plane and reopening checks. Source MRI/prediction SHA-256 values were unchanged. No new inference was started and the stopped E3 test was not resumed.

Artifacts are outside Git under `training-runs/surface-defaults-20261119-zqqgk9vd/`: source hashes, `verification.json`, `model-3d.png` and `model-planes.png`. The check's own window closed on completion; the user's existing app/study was not restarted. New code/defaults take effect after reopening the application. Existing saved custom views intentionally retain their own settings.
