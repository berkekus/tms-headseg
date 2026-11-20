---
type: Experiment
title: Dataset003 E3 Colab training preparation
description: Revised standalone notebook for the actual 90/16 entry handoff, ignore 6 and uniform sampling of physical IXI copies.
status: draft
experiment_state: completed_validation_per_supplied_log_artifact_audit_pending
sources:
- id: handoff
  resource: e3-data-handoff-review.md
  title: Actual E3 archive review
- id: code
  resource: ../../tools/e3_training/README.md
  title: Dataset003 launch and resume guide
---

# Dataset003 E3 training preparation

On 2026-11-06 the user requested the final notebook while uploading the reviewed
ZIP/SHA to `My Drive/TMS_E3/`. The notebook targets the actual handoff. At preparation
time, no E3 GPU run was established; the later completed pilot is recorded below. The earlier sampler-only preparation
is superseded and preserved under `training-runs/e3-sampler-only-superseded-60r2wsu9/`.

## Main run completed per supplied Colab log (received 2026-11-07)

The user supplied the full main-run console output. It contains every epoch 0–99,
`Training done.`, every expected validation subject exactly once, `Validation
complete`, and `Raw E3 validation saved`. CUDA execution, the 90-entry / 16-subject
split and frozen 3d_fullres configuration are shown. No traceback or nonfinite
loss/metric token was found. The invocation reports **230.8 minutes** (about 3 h
51 min). The console timestamps show 2026-11-06; their timezone was not independently
verified. The earlier browser connectivity report did not prevent this run from
reaching completion according to the supplied output.

Mean final raw validation Dice: **0.9069063477804425**. This is the final full-volume
metric, not the last epoch's patch pseudo-Dice (or its EMA).

| Cohort | Cases | E2 raw Dice | E3 raw Dice |
| --- | ---: | ---: | ---: |
| Overall | 16 | 0.91402824 | 0.90690635 |
| IXI | 6 | 0.91371844 | 0.91135380 |
| MultiAxial | 10 | 0.91421412 | 0.90423788 |

These cohorts and reference labels are held fixed. Overall E3 is lower by
0.00712189 Dice (0.712 percentage points on the 0–100 Dice scale); the larger source
subgroup decline is in MultiAxial. Do not claim overall validation superiority.
E3's facial-surface goal, failure patterns and outside-acquisition inference masking
still require separate evaluation; these raw scores alone do not resolve them.
Two training factors changed, so a cause cannot be isolated from this comparison.

The log indicates the notebook reached its saved-success branch. The actual
checkpoint, final summary JSON, per-class/case arithmetic, weights and remote Drive
contents have not yet been downloaded/reviewed independently. Runtime release is
also unverified. Preserve/download the entire
`MyDrive/TMS_E3/runs/E3_Dataset003_001/` folder before local artifact review and
Workbench integration. No independent test or clinical/Module A acceptance is claimed.
Evidence: `training-runs/e3-preparation/colab-main-completion.txt` and
`colab-main-summary.json`.

## Observed Colab GPU pilot completion (2026-11-06)

The supplied console log confirms CUDA execution of epochs 0–4 using the fixed
90-entry training / 16-subject validation split and the saved 3d_fullres plan.
`Training done.` and `Validation complete` are present; every expected validation
ID appears exactly once. Mean full-volume validation Dice is **0.8206177438457288**.
The entire invocation reports 15.5 minutes. Epoch times are 141.01, 133.46, 133.47,
133.48 and 133.46 seconds; median post-first-epoch time projects **3.70736 hours**
for the 100-epoch loop, excluding checkpoint/plot overhead and final validation.
This is a completed smoke/pilot result, not the main model or independent anatomy
acceptance. The optional hiddenlayer plot dependency and old-plan advisory did not
prevent successful completion. Main-run start is not yet observed. Evidence:
`training-runs/e3-preparation/colab-pilot-completion.txt` and `colab-pilot-summary.json`.

## Fixed experiment

Dataset003_E3Face uses `handoff_e3.zip`, SHA-256
`c12f5fb233d829d20bdcc112e412a1eb9fe17158a4a56377cec3e1951eba7698`.
There are 90 training entries from 67 people and the same 16 E2 validation subjects.
The 23 IXI `w2` copies implement weighting via **standard uniform sampling**; the
obsolete custom weighted loader was removed. Ignore 6 marks boundary-connected
zero signal in training and is skipped by standard loss. Validation remains 0–5.
There are still six prediction channels: background plus five tissues.

All entries receive lossless RAS preparation. Saved E2 plans are reused with only
`dataset_name` changed to Dataset003: same architecture, 1 mm spacing, patch
160×128×112 and batch 2. This is not byte-identical to E2 plans. Keep the same
Python 3.11 / nnU-Net 2.8.1 / torch 2.6.0+cu124 lock, seed 42, 100 epochs, four
augmentation workers, compile off and checkpoint every epoch. Start from random
weights; the separate five-epoch pilot does not initialize the main run.

E3 changes both annotation-ignore policy and source exposure, including associated
site/pathology confounding. No isolated effect or improved facial accuracy is claimed.

## Guards, launch and outputs

Default inputs are `/content/drive/MyDrive/TMS_E3/handoff_e3.zip` and its `.sha256`.
Output root is `MyDrive/TMS_E3/runs/E3_Dataset003_001/`. All training/resume flags
start False. Original archive/source bytes are fixed; RAS uses a semantic hash of
decoded values, dtype, shape, affine, units, metadata and split to tolerate
irrelevant Mac/Linux gzip encoding differences. A five-epoch GPU pilot with final
weights and exact 16-case validation is required before a fresh main run. Saved
contracts reject changed data/code/settings on resume.

Raw validation remains intact. Final success checks exact subject identities and
finite mean Dice; six-case IXI / ten-case MultiAxial metrics are exported separately.
Preserve the whole run folder and sources. Future E3 inference needs explicit
background masking outside acquisition; this is recorded as a requirement and is
not applied to raw validation. Workbench E3 loading remains outside this preparation.

## Observed local verification

- Full source audit, RAS copy of all 106 entries and subsequent full audit passed.
  All converted entries are RAS and copy/ignore/grid checks pass.
- GU002 and IXI037 passed actual nnU-Net `DefaultPreprocessor.run_case` with the
  Dataset003 plan. Shapes: 1×200×202×166 / 1×240×240×180. Ignore counts retained:
  1,409,483 / 3,994,070. The label manager has six heads and ignore 6; annotation
  location keys exclude ignore as a tissue.
- Fifteen E3 checks and sixteen E2 regressions pass in one process. They exercise
  source split/copy/ignore guards, current notebook/compiled cells, uniform sampling,
  real trainer construction, pilot/resume gates, final validation identities,
  gzip-invariant fingerprints and a synthetic CPU U-Net optimizer step. Changing
  ignore logits leaves loss unchanged and their gradients zero. E2 globals remain
  unchanged by the private E3 adapter.
- Embedded helpers import in an isolated temporary folder without repository imports.
  All notebook code cells compile. Training remains disabled by default.

Evidence: `training-runs/e3-data-audit-20261106-0eb37kl5/` and
`training-runs/e3-preparation/`. Portable notebook: `E3_Dataset003_Colab.ipynb`;
repository `E3_Colab.ipynb` contains identical code.

Actual upload completion, account access, CUDA/multi-worker execution and training
duration/results remain unverified until the operator runs the GPU pilot.
No paid training, commit or push was started by this preparation.

## Colab preprocessing metadata failure and correction

The user later supplied a section 4 log: dataset integrity and all 106 fingerprint
entries passed, then `nnUNetv2_preprocess` failed because the preprocessed dataset
folder lacked `dataset.json`. Installing a frozen plan bypassed the normal planner
step that supplies that metadata. Earlier per-case preprocessing checks did not
exercise this dataset-level CLI boundary.

The generator now copies the audited RAS dataset JSON beside the frozen plans
before invoking preprocessing. A new regression executes the generated cell and
asserts metadata is staged before the CLI call. The existing Colab session can
copy this one file and rerun section 4 without changing the scientific contract,
re-uploading data or restarting the runtime. The supplied log does not establish
pilot/training completion.

The new regression failed with the same missing-file error before the fix and
passes afterwards. Sixteen E3 checks plus sixteen E2 regressions now pass. A real
one-case GU002 dataset-level CLI trial reproduced the error without metadata and
completed after copying it. An initial sandboxed attempt encountered OpenMP SHM
restrictions and was stopped; the native retry exited 0 and wrote the expected
preprocessed case files. Evidence is under
`training-runs/e3-preprocess-cli-fix-5czf51s0/`. Full remote preprocessing and GPU
pilot completion still require the user's subsequent logs.
