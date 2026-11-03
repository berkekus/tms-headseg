---
type: Experiment
title: IXI K2 Batch Preparation and Preflight
description: Verified K2 data preparation, completed IXI037 CHARM execution and local desktop batch integration; anatomical QC remains pending.
status: draft
experiment_state: completed_execution_qc_pending
sources:
- id: assignment
  resource: ../../tools/charm_batch/ixi_assignment.csv
  title: Shared IXI subject assignment
- id: tool
  resource: ../../tools/charm_batch/README.md
  title: CHARM batch procedure
---

# IXI K2 Batch Preparation and Preflight

Observed on 2026-11-03. Preparation passed and the single IXI037 reconstruction completed. Anatomical QC and E2 training have not occurred. The allocation remains provisional as stated in the shared procedure.

## Inputs and local records

- Download folder: `/Users/merttomekce/Downloads/D06_IXI_T1_T2`.
- All ten ZIP package sizes and SHA-256 values matched `paket_manifest.json`.
- Extracted only the 15 K2 training subjects listed in the shared CSV, into `/Users/merttomekce/Documents/TMS/data/D06_K2`, outside Git. All 30 T1/T2 files matched the individual sizes and SHA-256 values in `D06_manifest.json`.
- No K1, test, calibration or excluded subject images were extracted or inspected. Full archive download and package verification do not constitute test-image inspection.
- Local preparation evidence: `/Users/merttomekce/Documents/TMS/data/D06_K2_preparation.json`. MRI files and the downloaded archives remain outside Git.

## Batch fixes and checks

The local batch runner now rejects excessive qform/sform differences during a dry run, before returning `planned`. It rechecks input hashes, recorded settings and output hashes before skipping a completed case, and restores the delivery package from verified outputs. An unverifiable completion, including an older record without hashes, fails without automatically rerunning or replacing the saved result; use a new output folder after review. These changes leave CHARM flags, label mapping and child thread limits unchanged.

Four regression tests were added to the existing eight checks. They cover dry-run rejection, changed/missing outputs, changed inputs and rebuilding a missing delivery file. The failures were reproduced before fixing the runner. Tests use a stand-in CHARM and do not establish anatomical quality or native Windows execution.

## Real-input dry run

Installed package metadata reports SimNIBS **4.6.0** with Python **3.11.14**, native **arm64**. The run used the installed SimNIBS Python:

```bash
env OPENBLAS_NUM_THREADS=1 OPENBLAS_DEFAULT_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /Users/merttomekce/Applications/SimNIBS-4.6/bin/simnibs_python -E \
  /Users/merttomekce/Documents/TMS/tms-headseg/tools/charm_batch/run_charm_batch.py \
  --owner K2 \
  --data /Users/merttomekce/Documents/TMS/data/D06_K2 \
  --out /Users/merttomekce/Documents/TMS/charm-runs/ixi-k2 \
  --charm /Users/merttomekce/Applications/SimNIBS-4.6/bin/charm \
  --dry-run
```

Exit status was **0**: **15 planned, 0 failed**, with `--forceqform` selected for **12** subjects. Local records are `preflight.log` and `preflight.json` in the output folder. No `m2m_*` folder or per-subject execution JSON was created; real CHARM was not launched. This checks file discovery and the runner's header policy, not reconstruction success, runtime, or anatomical alignment.

## Single-subject pilot started

The user authorized continuing after preflight. A process check found no active CHARM or batch run, and the output volume had 38.1 GiB free. Started the same command above with `--dry-run` replaced by `--only IXI037`, with child math-library thread limits set to 1 and `caffeinate -i` preventing idle system sleep only while this batch process runs. No persistent power setting was changed.

The real CHARM log confirms SimNIBS **4.6.0** and start time **2026-11-03 15:16:26 +03:00**. The selected qform/sform flag is `--forceqform`, with a maximum header difference of about `1.6e-6`. The model folder was created; this only establishes startup, not completion or output quality.

The next startup check found the process still running and the log growing to about 25 KB, through EM and L-BFGS blocks. Divide-by-zero, overflow and invalid-value `matmul` warnings recurred, as in the earlier Ernie case. Continued progress does not establish that all numerical warnings are harmless; execution outputs and anatomy still require review.

Local output: `/Users/merttomekce/Documents/TMS/charm-runs/ixi-k2/m2m_IXI037`. Live log: `logs/IXI037.log` in the batch output root. `pilot-start.json` retains launch metadata and the local runner hash. Only IXI037 was selected; the other 14 cases have not started.

## Completion verified

The owned CLI session exited **0**. CHARM finished at **2026-11-03 15:49:18 +03:00** and reported **00:32:52**; the batch record measures **33.0 minutes**, starting before CHARM's own startup marker. `runs/IXI037.json` records `outputs_ok: true` and SimNIBS 4.6.0. Input hashes, saved raw-output hashes and every delivery checksum were independently rechecked and passed.

The new `IXI037.msh` is **157,218,175 bytes**. `final_tissues.nii.gz` reads as **256 × 256 × 150 × 1**, with raw labels `[0, 1, 2, 3, 5, 6, 7, 8, 9, 10]`; these remain CHARM IDs, not accepted project label mappings. The report, LUT and delivery package exist. Numerical `matmul`/`dot` warnings remain; neither earlier OpenBLAS memory-unallocation message nor precompiled-thread warning appeared. File readability and execution success are not anatomical acceptance. The QC entry has not been marked pass.

## Desktop batch integration

After fetching origin, main already matched the local base `e2b7f7c`; no incoming batch GUI existed. The user authorized adding one while the independent pilot continued. [MRI Workbench batch mode](../../tools/mri_prototype/BATCH.md) now uses the existing CLI and training assignment, with dry-run gating, recorded case counts/runtime, logs, external read-only monitoring, process-tree cancellation and an owned-completion attention request. New CLI batches use an output-folder lock and atomic running/terminal records; the already-running legacy pilot was never attached for cancellation or restarted.

Native macOS checks displayed **1/15 completed, 14 pending** from the actual IXI037 results. Stand-ins cover launching and cancellation. An accessibility crash in the dynamically refreshed Qt table was isolated and avoided using stable list items, without disabling accessibility. Native Windows execution and a real new multi-case desktop batch are unverified.

Final checks passed **62 Workbench tests**, **14 batch tests under SimNIBS Python 3.11.14**, and **20 CHARM launcher tests**, with one native Windows check skipped. The native GUI then ran a real-input **dry run only**: **1 verified completion skipped, 14 planned, 0 failed**. `desktop-verification.json` outside Git records source hashes and the GUI check log. No additional reconstruction or QC approval was performed.

## Next action

Inspect IXI037's report and record visual QC before explicitly starting the remaining 14 K2 training subjects from the batch page. Record execution and visual QC separately. Test/calibration subjects remain assigned to K1; this preparation does not approve or alter the split.
