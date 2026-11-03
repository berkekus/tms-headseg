# Desktop E1 inference plan

**Goal:** Select an MRI, run the completed E1 model locally, then automatically open the new prediction in the existing 2D/3D viewer.

**Approved scope:** The user explicitly requested connecting the already-working `demo.py predict` inference to the desktop. Keep this in the tools prototype. No training, new architecture, cloud service, DICOM conversion or automatic commit/push is included.

## Design

- Add an **04 E1 segmentation** tab with inference Python, completed model folder, source MRI, output parent, CPU/CUDA, optional mirror augmentation and explicit unknown-unit assumption. Existing local runtime/model may prefill if present; no installation/download happens automatically.
- Reuse the existing inference CLI in an isolated subprocess. Qt remains in its own environment. CPU with four math-library threads and augmentation off is the initial local setting; settings/timings stay explicit.
- Reuse the CHARM runner's owned process groups/Windows job object, durable log tailing, cancellation escalation and cleanup. Two class-level defaults allow E1 log naming and four threads without changing CHARM defaults.
- Each job has a fresh run ID, never overwrites a model/output, and stays outside Git. Validate MRI header geometry and supported units before launch, plus required model files. The existing inference CLI validates weights/labels/runtime versions before loading.
- Input is T1 NIfTI in mm, or unknown units explicitly treated as mm for this provisional handoff. Other units require an independently prepared mm copy before this initial inference workflow; ordinary viewing still supports its existing unit conversions.
- Show elapsed time, live log, busy indicator, cancellation and explicit failure. No fabricated completion percentage, recorded fallback, or accuracy score without a reference.
- Only successful process exit plus completed status/prediction/report triggers automatic load. The existing worker reads the new segmentation, then selects **03 3D model**. Preserve source-specific names and unit caveats.
- Prevent simultaneous CHARM/import/inference jobs. Closing an active inference asks to stop it, then waits for owned-process cleanup. Partial files/logs and a separate desktop job status are retained after failure/cancellation.

## Steps

- [x] Add failing job/runner/UI checks: shell-safe arguments, fresh outputs, invalid headers/model paths, completion/failure/cancel state, live log and cross-workflow gating.
- [x] Add `inference_runner.py`, with `InferenceJob` and a small existing-runner subclass; add only log-prefix/thread defaults to `tools/charm_gui/runner.py`.
- [x] Add `inference_panel.py`; wire it into `prototype.py`, including close/cancel and automatic result loading. Keep torch out of the Qt process.
- [x] Run prototype, CHARM and E1 suites; fix observed regressions. Confirm clean notebook/source parity when shared code changes.
- [x] Exercise an actual new CPU prediction through the GUI/controller using our final checkpoint and GU011 MRI; inspect the native 3D result and source hashes. Keep outputs/screenshots outside Git.
- [x] Update README, handoff and experiment/current/log records with verified results and remaining platform limitations. Leave changes local for user review.

## Ledger

- Preflight: branch clean at `dceccce`. The Python 3.11 inference environment and independently verified final model exist outside Git. Desktop currently only imports saved predictions. Existing CLI inference already writes fresh predictions, measured timings, completed/failed status and offline reports.

- K3 merge integration: adapted the saved wiring onto `0fc3b2d`, preserving `run_task`'s positional export error prefix and all K3 geometry/renderer/Windows job-object changes. Added tests for export gating/source preservation and callback coexistence.
- Independent review: found a close-dialog completion race; reproduced it in a failing test, fixed the post-dialog state check, and confirmed the regression passes. Reviewer confirmed resolution with no remaining findings.
- Verification so far: prototype 52 passed; K3 geometry 78 passed after installing its declared SimpleITK dependency (2.5.7) into the isolated prototype environment; CHARM 20 passed / one Windows skip. Fresh native CPU prediction on merged code is running; no training/commit/push.

- Final merged-code native run: `e1_20261103T115050Z_4b3a1a46` passed; CPU model load 2.137456 s, prediction/export 526.869956 s, total 538.322069 s. Five surfaces / 348,104 triangles auto-opened, MRI/model hashes unchanged. Guides and canonical experiment/current/log updated. All 187 checks passed, plus one Windows-only skip. No training, commit or push; native Windows/CUDA remain unverified.

- Publication authorization: after reviewing the completed native run and verification, the user explicitly requested commit/push. Data, checkpoints and generated reports remain outside Git.
