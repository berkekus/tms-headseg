---
type: Experiment
title: MultiAxial K2 CHARM Preflight
description: Preflight for the nine K2 MultiAxial T1-only reconstructions.
status: draft
experiment_id: EXP-MULTIAXIAL-K2
attempt_id: MA-K2-20261104-01
experiment_state: running
---

# MultiAxial K2 CHARM Preflight

On 2026-11-04, verified all six Drive ZIP SHA-256 sums and extracted the package to `/Users/merttomekce/Documents/TMS/charm-runs/multiaxial-k2-20261104-tctddmoz`. The supplied K2 assignment matches the original E1 split for all nine inputs: eight train, and GU011 validation. There are no held-out test inputs in the package.

The package runner adds T1-only support and a train/validation cohort selector to the IXI workflow. It is staged separately from the Git checkout. With local SimNIBS 4.6.0, all nine NIfTI payloads read as finite, nonempty 3D images with coded transforms and millimetre units. The dry run planned nine cases, zero failures and zero `--forceqform` flags. All 18 supplied runner tests passed with stand-ins. Logs and the input audit are in the staging folder. The preflight paused before reconstruction at the user's request.

After the user approved adding MultiAxial monitoring and proceeding, opened Workbench on the batch output and launched the sequential CLI at 15:45:16 +03:00 on 2026-11-04. The process is detached and uses `caffeinate -i` for the duration of the batch. The live record showed GU011 running at “Adjusting neck,” eight pending, zero completed. The Workbench suite passed 63 tests, and an offscreen check verified the nine real rows, active state and live log. The native monitor was opened as a separate process. Completion and visual QC are pending.

The command below runs from the staging folder. Keep GU011 in validation. Review and record segmentation quality before handing labels to K1. The package flags that CHARM may extend tissue into defaced regions. Check this during QC and confirm K1's masking disposition before using the labels for E2.

```bash
"$HOME/Applications/SimNIBS-4.6/bin/simnibs_python" tools/charm_batch/run_charm_batch.py \
  --owner K2 --assignment tools/charm_batch/multiaxial_assignment_K2.csv \
  --cohort train,val --t1-only --data data --out out \
  --charm "$HOME/Applications/SimNIBS-4.6/bin/charm"
```

[IXI batch and handoff](ixi-k2-preflight.md)
