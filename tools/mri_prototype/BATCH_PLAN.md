# CHARM Batch Desktop Implementation Plan

**Goal:** Run and monitor the shared IXI training assignment from the existing desktop Workbench, while safely observing the already-running IXI037 pilot.

**Approved design:** The user approved adding batch processing while the pilot continues. Keep the existing single-case workflow and put a second, batch page inside `02 CHARM processing`. A separate application would duplicate the Workbench; a log-only viewer would not meet the requested launch/resume workflow. Reuse the existing batch CLI and owned process runner. No new dependencies, automatic commits, real test reconstructions, or changes to CHARM segmentation settings.

**Technology:** PySide6 widgets/timers, the existing cross-platform process ownership, Python standard-library file locking and JSON records.

## Task 1: Protect batch execution and expose truthful state

Files: `tools/charm_batch/process_lock.py`, `run_charm_batch.py`, `test_run_charm_batch.py`.

- [x] Add failing tests for an exclusive output-folder lock and a per-case running record visible before completion.
- [x] Add a non-blocking POSIX/Windows file lock held for real batches, released even on interruption. A second batch must fail before executing CHARM.
- [x] Write running and terminal case records atomically. Preserve existing geometry checks, checksum verification, sequential scheduling, cohort selection and delivery behavior.
- [x] Resolve official Windows CHARM wrappers using the existing launcher parser, retaining literal argv paths.
- [x] Run `tools/mri_prototype/.venv/bin/python -m unittest discover -s tools/charm_batch -v`; require all tests to pass with stand-ins.

## Task 2: Build the batch adapter and read-only status snapshot

Files: `tools/mri_prototype/batch_runner.py`, `test_batch.py`.

- [x] Add failing tests for owner/train-only selection, literal CLI arguments, rejecting Git output, reading external logs without launching/killing a process, and managed cancellation.
- [x] `BatchJob` invokes the existing CLI with a selected SimNIBS Python, data folder, output folder and fixed training cohort. `BatchRunner` reuses `Runner` for logs and process-tree ownership.
- [x] Show completed/failed/pending records and bounded log tails. A legacy model/log without a run record is unconfirmed external work: allow monitoring, block launch. A completed record is not anatomical QC.
- [x] Require a successful dry run for the exact current form before enabling real launch. Starting always remains an explicit user action.

## Task 3: Integrate desktop controls

Files: `batch_panel.py`, `prototype.py`, `test_batch.py`.

- [x] Add failing UI tests for batch launch gating, external read-only monitoring, disabled competing compute jobs, configuration invalidation, and close/cancellation behavior.
- [x] Add K1/K2, SimNIBS Python, CHARM, data/output paths, check-inputs, start/resume, cancel-owned-batch, monitor and open-report/folder controls.
- [x] Display the assigned training subjects, recorded completion count, per-case runtime/status, latest stage/log age and live log. Do not invent per-case percentages or ETA.
- [x] Make external monitoring read-only. Closing it must never stop the current CLI pilot. Closing an owned batch asks before cancellation and waits for child cleanup.
- [x] On terminal owned completion, show a banner and request Dock/taskbar attention. No operating-system push service is introduced.

## Task 4: Verify and document

- [x] Run the batch, prototype and CHARM launcher suites; run `git diff --check`.
- [x] Open the native Workbench on the batch page, observe existing IXI037 output and confirm that no second real CHARM run started. Test launching and cancellation only with stand-ins.
- [x] Update usage and knowledge records with measured results and native Windows limitations. Existing worker assignments and held-out cohorts remain unchanged.

Plan self-review: every requested launch, resume, monitor and completion control has a task. Background IXI037 belongs to its original CLI process and is outside GUI cancellation ownership. Native Windows execution remains a separate verification requirement.
