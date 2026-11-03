---
type: Experiment
title: 'EXP-002: Ernie OpenBLAS Thread-Limit Retry'
description: Repeated stalled T1-plus-T2 trials and a controlled retry with child-process thread limits.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-30T11:26:36+03:00'
experiment_id: EXP-002
experiment_state: completed
sources:
- id: openblas
  resource: https://www.openmathlib.org/OpenBLAS/docs/runtime_variables/
  title: OpenBLAS runtime thread controls
- id: observations
  resource: ../references/session-observations.md
  title: Local run observations
---

# EXP-002: Ernie OpenBLAS Thread-Limit Retry

Experiment state: **completed execution** on 2026-11-02. The fresh T1-plus-T2 attempt finished with new mesh, label, and report files. The 2026-10-30 capped trial was stopped by the user during mesh-quality improvement. This troubleshooting experiment is separate from the unrun [T1-only baseline](ernie-baseline.md). Anatomical accuracy and benchmark improvement are not established.

## Observed problem

Two user-started trials produced OpenBLAS `precompiled NUM_THREADS exceeded` and `Bad memory unallocation` messages during segmentation. Their launcher logs used subject `ernie_20261030_105806` and timestamps `1793347093729410000` and `1793347704614031000` in the user's Documents folder. A later inspection of the first log found termination/SIGTERM output; that is not proof of an immediate native crash.

For the latest trial, the native window still showed Running at 13:02 elapsed while the log had not changed for several minutes. It was cancelled through the launcher; the window then reported Cancelled at 14:32. Partial files were preserved. These are observed UI/log facts, not a measured normal CHARM runtime or a proven root cause.

## Hypothesis and isolated change

Nested numerical-library thread pools may exhaust OpenBLAS thread metadata. The launcher now supplies `OPENBLAS_NUM_THREADS=1`, `OPENBLAS_DEFAULT_NUM_THREADS=1`, and `OMP_NUM_THREADS=1` to CHARM only, overriding inherited values for that child process. The log records the values. Global settings, installed packages, input files, and CHARM's configuration file were not edited.

OpenBLAS documents separate controls for OpenMP and non-OpenMP builds; `OMP_NUM_THREADS` can affect other OpenMP code too.[^openblas] The inspected environment has OpenBLAS 0.3.30 with an OpenMP package. A small direct-library diagnostic under these settings returned an actual OpenBLAS thread count of one. A launcher test also confirms that child processes receive the limits while the parent environment remains unchanged. Neither check establishes that the full reconstruction will succeed.

NumPy 2.3.0 in the installed SimNIBS environment emitted divide-by-zero/overflow/invalid `matmul` warnings for an identity-matrix multiplication whose output was correct. Those warnings persisted in the small capped-thread probe. Warnings remain visible; the diagnostic does not establish the correctness of segmentation computations.

## First capped attempt: 2026-10-30

| Field | Observed value |
| --- | --- |
| Subject ID | `ernie_blas1_20261030_112608` |
| Start | 2026-10-30 11:26:36 +03:00, native launcher |
| Hardware/runtime | User's M4 Pro; macOS 27.0.1 ARM64; installed SimNIBS 4.6.0 with Python 3.11 and NumPy 2.3.0 |
| Launcher runtime | Packaged ARM64 Python 3.14.7 / PySide6 Essentials 6.12.0; rebuilt after the thread-limit change |
| Inputs | Public SimNIBS Ernie `org/ernie_T1.nii.gz` and `org/ernie_T2.nii.gz` |
| T1 SHA-256 | `27e33241fc7c44b42dd63d613e81cadaefdfad271fd7e844fea71d0db75942ad` |
| T2 SHA-256 | `d435ec4de1aac30746fcd1b1708a10e8c2657fe284aea5fa85e1f062f54126b3` |
| Output root | Local `TMS/charm-runs/`, outside the Git checkout |
| Model directory | `m2m_ernie_blas1_20261030_112608/` under that output root |
| Launcher log | `charm.ernie_blas1_20261030_112608.1793348796714144000.launcher.log` under that output root |
| Thread controls | All three variables above set to `1`; present in the actual retry log header |
| Exit status / final outputs | Terminated: log records SIGTERM/PETSc MPI abort during mesh-quality improvement. Expected final mesh, labels, and report were not present at the last check. |
| Runtime / peak memory | Approximately 31 minutes before termination; not a successful runtime measurement. Peak memory not captured. |
| Anatomy / geometry quality | Not assessed |

The selected command is `charm ernie_blas1_20261030_112608 <absolute Ernie T1> <absolute Ernie T2>` with the output root as working directory and the three explicit environment variables. It uses a new subject ID, not the supplied `m2m_ernie` or the stalled trial's folder. The selected CHARM settings remain defaults; T2 stays included to avoid changing the input combination during this diagnostic.

This attempt passed the earlier OpenBLAS stall, completed segmentation and cortical registration, and reached mesh-quality improvement without another `Bad memory unallocation` message in the inspected log. The user explicitly reported stopping the session. This is progress evidence for the workaround, not a completed reconstruction.

## Fresh attempt: 2026-11-02

The user requested restarting and testing again after stopping the previous session. Existing output directories were preserved; this attempt starts from the public T1 and T2 inputs rather than resuming partial meshes.

| Field | Observed value |
| --- | --- |
| Subject ID | `ernie_blas1_20261102_135521` |
| Start | 2026-11-02 13:56:35 +03:00, native launcher |
| Output root | Same local `TMS/charm-runs/`, outside Git |
| Model directory | `m2m_ernie_blas1_20261102_135521/` |
| Launcher log | `charm.ernie_blas1_20261102_135521.1793616995593363000.launcher.log` |
| Inputs | Public Ernie T1 and T2 paths selected in the native window |
| Thread controls | All three variables set to `1`; verified in this attempt's log header |
| Launcher checks | 19 passed, one native Windows check skipped on macOS |
| End | 2026-11-02 14:36:57 +03:00, CHARM finish marker |
| Reported runtime | `00:40:17`, CHARM's own total running time; not a project-model speed result |
| Terminal outcome | Finish marker and expected outputs present; OS exit code not independently captured |
| Final mesh | `ernie_blas1_20261102_135521.msh`, 180,177,939 bytes; Gmsh header `$MeshFormat`, `2.2 1 8` |
| Tissue labels | `final_tissues.nii.gz`, 958,183 bytes; successfully read with nibabel |
| HTML report | `charm_report.html`, 14,002,630 bytes |
| OpenBLAS failure messages | Neither `Bad memory unallocation` nor `precompiled NUM_THREADS exceeded` appears in the completed log |

The window visibly reported Running with the math-library thread limit after starting. The user chose to monitor the run and later supplied its finish lines; local inspection confirmed the same finish marker, runtime, and expected new outputs. `matmul` and `dot` runtime warnings remain in the completed log. They were not suppressed.

Basic artifact checks read a uint16 label volume with shape `(256, 256, 208, 1)`, 1 mm spatial voxels, a finite affine, and labels `0, 1, 2, 3, 5, 6, 7, 8, 9, 10`. These are reference-tool output codes, not an accepted project label mapping. Mesh header and nonempty files do not establish mesh integrity or MRI alignment. The HTML report and reconstructed anatomy still need visual review; numerical surface-distance, Dice, and coordinate acceptance were not evaluated.

The thread-limit workaround allowed this public Ernie case to finish without the prior OpenBLAS memory/thread-metadata messages. This supports using it for this installation and case; it does not identify the exact internal library defect, establish general reliability, or validate every remaining warning as harmless.

## Interpretation limits

One public subject cannot establish general reliability or clinical suitability. The retry changes thread policy and is not an independent replication with identical execution settings. Do not claim that warning suppression, file presence, or progress alone establishes an accurate model. Record the terminal outcome, errors, output checks, and any further changes before closing this experiment.

[^openblas]: [Official OpenBLAS runtime controls](https://www.openmathlib.org/OpenBLAS/docs/runtime_variables/).
