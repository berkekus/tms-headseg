---
type: Observation Record
title: User Direction and Local Observations
description: Separate explicit choices, filesystem evidence, and unmeasured results.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-23T10:06:38+03:00'
evidence_kind: mixed_explicit_direction_and_observation
sources:
- id: session
  resource: User messages and bounded local inspection on 2026-10-22, 2026-10-23, 2026-10-30, and 2026-11-02
  title: Project conversation and local inspection
---

# User Direction and Local Observations

Initial filesystem evidence date: 2026-10-22. Updated with launcher direction, diagnostics, and the completed Ernie run through 2026-11-02. This record summarizes the current project conversation and limited local inspection. It is not a raw chat transcript or a record of institutional approval.

| ID | Statement | Evidence kind | Limit |
| --- | --- | --- | --- |
| USER-01 | Build a project second brain in repository Markdown/OKF. | Direct user request. | Does not authorize implementation of every task in an attached PDF. |
| USER-02 | Write the entire knowledge base in English. | Direct user answer. | Technical filenames and commands are also English. |
| USER-03 | Keep the project independent of a particular downstream application. | Direct user answer. | No product-specific integration dependency is adopted. |
| USER-04 | Four people will work on the project; discuss work sharing and capture relevant source updates in the knowledge base. | Direct user statement and subsequent document-review request. | Names, skills, capacities, actual role assignments, and delivery dates were not supplied. Source-proposed roles are not accepted assignments. |
| USER-05 | Build a small native macOS CHARM launcher inside this repository and review it before committing. | Direct user request on 2026-10-30 after discussing the launcher scope. | Does not approve a commit, push, complete reconstruction, or replacement of the Module A plan. |
| USER-06 | Extend the launcher for Windows teammates using one shared Qt desktop codebase with per-platform packaging, after comparing Qt and Tauri. Keep the interface on the computer without a localhost web application. | Explicit approval on 2026-10-30 following research and recommendation. | Does not establish Windows test results, authorize pushing, or replace the Module A product plan. |
| OBS-01 | A SimNIBS-4.6 directory with `bin/charm` and the GUI exists locally on Apple Silicon. | Filesystem inspection in this conversation. | Not a successful launch, benchmark, CUDA check, or model run. |
| OBS-02 | Sample `org/` contains T1 and T2 MRI; `m2m_ernie/` contains a mesh, labels, surfaces, and HTML report. | Filesystem inspection. | These are supplied example outputs, not new project results. |
| OBS-03 | Example README says its Ernie model used FreeSurfer-assisted reconstruction; example dataset terms are CC BY-NC 4.0. | Local sample README. | Do not assume identical geometry from a new 4.6 run or generalize terms to other data. |
| OBS-04 | Application source and trained project weights are not present in the inspected repository. | Repository file inventory before this knowledge base was added. | Future changes require updating current state. |
| OBS-05 | The user loaded the supplied Ernie m2m folder in the SimNIBS GUI and saw a 3D model before pressing Run. | User clarification in this conversation. | Opening a supplied model is not a new CHARM reconstruction or simulation. |
| OBS-06 | A [launcher prototype](../../tools/charm_gui/README.md) now exists; its native window opened using ARM64 Python 3.14.7 with PySide6 Essentials 6.12.0. The installed CHARM help command exited successfully outside restricted execution. | Local implementation and startup checks on 2026-10-30. | Startup and stand-in process checks do not establish a complete reconstruction, anatomical quality, or runtime. External result opening still needs a real output check. |
| OBS-07 | The macOS ARM64 desktop bundle built using PyInstaller 6.22.3 and its native `--smoke-test` exited successfully. Windows wrapper resolution, owned process-tree code, and a manual Windows/macOS build workflow were added. | Local build/startup evidence and source inspection on 2026-10-30. | No Windows host or workflow execution was available in this session. A Windows executable, real reconstruction, and external result opening are not claimed. |
| OBS-08 | User-started Ernie T1-plus-T2 trials produced OpenBLAS thread-metadata/memory errors. The latest window still showed Running with a stagnant log; cancellation completed at 14:32 displayed elapsed time. A rebuilt launcher started a fresh child-scoped thread-limit retry. | Log and native-window inspection on 2026-10-30; details in [EXP-002](../experiments/ernie-thread-limits.md). | A stalled process is not a completed reconstruction. Native crash causation and effectiveness of the workaround remain unconfirmed until the controlled retry finishes. |
| OBS-09 | The fresh November 2 Ernie T1-plus-T2 run reached CHARM's finish marker at 14:36:57 +03:00, reporting 40:17 runtime. Local checks found a new nonempty mesh, readable tissue labels, and HTML report. Prior OpenBLAS memory/thread-metadata messages were absent; numerical warnings remained. | User completion update and local log/artifact inspection on 2026-11-02; details in [EXP-002](../experiments/ernie-thread-limits.md). | One completed reference-tool run does not establish anatomical accuracy, coordinate acceptance, general reliability, or Windows support. |
| OBS-10 | On the K3 Windows 11 machine, `win32job.CreateJobObject(None, None)` raised `TypeError` under pywin32 312, so no Windows CHARM job could start through the launcher or MRI Workbench. After passing an empty name, the launcher (20), Workbench (18), and data staging (3) suites passed with Python 3.13.1. `check_3d.py` passed natively on an NVIDIA RTX 4070 SUPER using a synthetic two-sphere model. | Local test runs on 2026-11-02. | Tests use stand-in processes. This does not establish a packaged Windows build, a real CHARM run, or rendering of a real head model on Windows. |
| OBS-11 | On the same machine, `check_3d.py` passed natively on the supplied `m2m_ernie` folder and on a project export of its labels. VTK's STL and PLY readers read the exports as binary, saw `SPACE=RAS UNITS=mm`, and returned the recorded triangle counts and bounds. SimNIBS is not installed here; its official 4.6.0 installer was downloaded and its SHA-256 matched GitHub's published digest, but it has not been run. | Local checks on 2026-11-02. | Viewing supplied data is not a new reconstruction. VTK readers are not a full independent-viewer check. Results are recorded in [EXP-005](../experiments/ernie-surface-export.md). |
| OBS-12 | The machine owner ran the SimNIBS 4.6.0 installer on 2026-11-03; it installed to the user folder and `find_charm` located `bin/charm.cmd`. The launcher's `Runner` then completed charm on the public Ernie T1 as [EXP-001](../experiments/ernie-baseline.md). | Installation and run records on 2026-11-03. | Runner code only, not the window or a packaged build. One subject. |

## Desktop E1 integration inspection — 2026-11-03

After the user-requested ten-commit fast-forward, source inspection still finds the existing [MRI Workbench](../../tools/mri_prototype/README.md): `prototype.py` offers slice-label loading and a `MeshView` tab, while `model.py:load_model` requires an existing SimNIBS MRI/label/mesh folder. `volume.py:load_labels` resamples discrete NIfTI labels for slice overlays; it does not extract 3D surfaces. The desktop source contains no E1/nnU-Net inference connection. The separate [E1 demo](../../tools/e1_training/DEMO.md) already contains prediction/report and display-surface code. Reusing the desktop renderer with an explicit E1 label map is proposed, not implemented. MRI import still requires explicit spatial units and a coded affine; new team preparation metadata must not be confused with the original training handoff. This was source inspection, not a new native graphics test.

### Follow-up implementation

The user subsequently requested pushing the three existing commits and continuing the desktop 3D integration. The push succeeded through `ab89d23`. The [Workbench](../../tools/mri_prototype/README.md) now has paired MRI/E1 prediction import with source-specific names/presets and explicit provisional-unit opt-in. Native GU011 display checks and source-hash preservation passed; see [EXP-003](../experiments/e1-preparation.md). Desktop inference is still not implemented. The change was initially left local for review; the user then reported a successful manual 3D trial and requested commit/push. This supersedes the missing-display connection observed at the earlier sync inspection, not its historical evidence.

## Source revision observation

During creation, the proposal file changed from the fingerprinted four-page snapshot to a five-page snapshot. The current source note summarizes the captured five-page revision and retains the earlier observed fingerprint. A source document describing an approval process is not proof that approval or data access was obtained.

## Not established

Anatomical quality scores, coordinate/export acceptance, training access, final team roles, and approved delivery dates have not been recorded. EXP-002's observed execution result and runtime apply to one new public Ernie T1-plus-T2 reconstruction, not the supplied example model or the planned project segmenter.

## Portability

Local installation and data paths differ by machine. The [baseline protocol](../experiments/ernie-baseline.md) uses environment variables rather than recording a collaborator's home directory.

## Related notes

[Current state](../current.md) · [Decisions](../decisions/index.md) · [Catalog](source-catalog.md)
