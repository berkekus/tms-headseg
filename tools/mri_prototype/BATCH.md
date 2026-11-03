# CHARM batch in MRI Workbench

Open **02 CHARM processing → IXI batch**. **Single MRI** retains the original one-case launcher. To open directly in read-only batch monitoring mode:

```bash
tools/mri_prototype/.venv/bin/python tools/mri_prototype/prototype.py --batch
```

On Windows use `tools/mri_prototype/.venv/Scripts/python.exe`. Keep `tools/charm_batch` and `tools/charm_gui` beside the prototype. SimNIBS 4.6.0 must be installed separately. No new dependency is required.

## Run the assigned training cases

1. Choose **K1** or **K2**, then select **Show setup**. The case list comes from the shared `ixi_assignment.csv`, restricted to that worker's `train` rows. Test, calibration and excluded rows are never submitted by this page.
2. Select SimNIBS Python (`bin/simnibs_python` on macOS, `simnibs_env/python.exe` on Windows), the matching CHARM launcher, unpacked D06 folder and an existing writable output folder outside Git. The local development paths are prefilled only when they exist.
3. Click **1 Check inputs (dry run)**. This launches the existing CLI without starting reconstruction. A successful check enables **2 Start / resume remaining cases** for the same configuration. Editing a field invalidates the check.
4. After accepting the pilot's visual QC, explicitly click **2 Start / resume remaining cases**. The CLI processes the whole assigned training list sequentially, rechecking and skipping verified completed cases. For K2 after IXI037 this leaves 14 new reconstructions. Nothing starts automatically when the window opens or a check finishes.
5. Follow the case list, recorded completion count, batch elapsed time, latest stage, local per-case elapsed time and bounded live log. Uncheck **Follow active case** to select another case. **Open selected report** is available for completed cases. Fill the separate `qc_K2.csv` or `qc_K1.csv` after visual inspection; a completed row is not QC approval.

Setup collapses while checking or monitoring to keep logs visible; **Show setup** reopens it. There is no reliable per-case percentage or ETA. Log age measures the last file write, not process liveness or a proven stall. Local elapsed time read from an older CHARM header assumes that header used this computer's timezone.

## Monitor an existing CLI run

**Monitor folder only** reads existing case records and logs. It does not acquire cancellation ownership, start CHARM, rewrite results or update QC. Closing such a window leaves the external process alone. Legacy folders/logs without execution records are shown as external/unconfirmed and prevent launching another batch from this page until completion is recorded or interruption is reviewed.

New real CLI batches hold a cross-platform output-folder lock; a second CLI batch targeting that folder fails before processing. Case records are written atomically at start and finish. The lock covers the selected output folder, not all CHARM jobs on the computer: do not launch competing jobs in another folder.

## Cancel and finish

**Cancel this batch** only stops a process tree started by this page, preserving partial files. Closing an owned running batch asks before cancellation and waits for cleanup. A subsequent explicit start reruns unfinished cases from the beginning and checks completed cases before skipping; it is not an intra-case checkpoint resume. Older completion records lacking checksums need review and a new output folder.

Owned batch completion updates the status banner and asks the Dock/taskbar for attention using Qt. This is not an operating-system push notification service. Keep the computer awake and its lid open for long runs; this page does not change power settings.

## Verification scope

Tests use stand-ins for launch, preflight, scheduling, completion, form invalidation, external read-only monitoring, competing-compute gating, cancellation and orphan cleanup. Native macOS viewing uses the real local IXI037 records; this is not a new reconstruction launched by the GUI. A dynamically refreshed Qt table crashed during native macOS accessibility queries, so the case view uses stable list items; native accessibility and screenshot inspection passed with that view. Native Windows batch GUI execution and a new real multi-case run remain unverified.

On 2026-11-03, 62 Workbench tests, 14 batch tests and 20 CHARM launcher tests passed; one native Windows launcher check was skipped. Native GUI preflight on the actual K2 data verified and skipped IXI037, planned 14 cases and reported zero failures. Existing dependency deprecation/font warnings were not suppressed.
