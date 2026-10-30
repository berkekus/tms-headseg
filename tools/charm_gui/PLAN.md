# CHARM Launcher Implementation Plan

**Goal:** Provide a small native Windows/macOS window for the installed CHARM command, inside this repository, for review before committing.

**Architecture:** `app.py` owns Qt widgets and polls `runner.py`, which validates inputs and runs CHARM in a macOS process group or Windows Job Object. MRI data, generated models, and tailed log files remain in the chosen output directory. The launcher does not change segmentation or provide the final Module A application.

**Stack:** Python 3.11+, PySide6 Essentials, Windows-only pywin32, and an independently installed SimNIBS 4.6. Use a separate virtual environment; PyInstaller is a build dependency.

- [x] Add focused standard-library tests for input validation, safe argument handling, streamed output, failed/incomplete jobs, and cancellation of child processes.
- [x] Implement command discovery, fresh-subject validation, process execution, log recording, and cancellation without shell command interpolation.
- [x] Build a native window with T1/optional T2 selection, subject/output controls, elapsed time, live logs, and buttons opening existing reports/models.
- [x] Document setup and limits; update repository entry points and current knowledge without claiming a new Ernie reconstruction.
- [x] Run focused checks and launch the native preview. Leave changes uncommitted for user review.

Existing models must not be overwritten. Cancellation preserves partial files and requires a new subject ID for another run. No automatic reconstruction, fake completion percentage, embedded viewer, cloud service, or model training is included.

Review evidence: nine focused checks passed on 2026-10-30; the native preview opened and installed CHARM help exited successfully. Real reconstruction and external result opening remain unverified.

## Windows and macOS extension

User approved one shared Qt desktop codebase on 2026-10-30. Keep this folder and the existing uncommitted prototype. No browser, HTTP server, or Tauri rewrite is needed.

- [x] Add portable test fixtures and tests for generated Windows launcher parsing, safe argument handling, and log streaming before process exit.
- [x] Add `installation.py` for installation discovery and converting generated `.cmd` wrappers into direct Python arguments; never execute scan paths through a command shell.
- [x] Replace pipe-specific log reads with tailing a local log file. Add `windows_process.py` with a kill-on-close Job Object; start suspended, assign to the job, then resume. Keep macOS process-group cancellation.
- [x] Adapt the native window, result opening, and platform-specific error messages. Test the shared Qt workflow.
- [x] Add repeatable per-platform packaging and a manual build workflow. Build and inspect the macOS app locally; keep Windows build and real-SimNIBS verification explicitly pending until Windows execution is available.
- [x] Update usage and knowledge state; run focused checks and leave all changes uncommitted.

Extension evidence: the macOS ARM64 package built and passed startup testing. Local checks cover portable launcher behavior and Windows cleanup without Unix signals; the native Windows Job Object check is skipped on macOS. Windows build/execution and a real reconstruction remain pending; no remote workflow has been run.
