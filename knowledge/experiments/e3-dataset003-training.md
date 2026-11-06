---
type: Experiment
title: Dataset003 E3 Colab training preparation
description: Revised standalone notebook for the actual 90/16 entry handoff, ignore 6 and uniform sampling of physical IXI copies.
status: draft
experiment_state: prepared_not_run
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
ZIP/SHA to `My Drive/TMS_E3/`. The notebook now targets the actual handoff. **No E3
GPU training or model result is established.** The earlier sampler-only preparation
is superseded and preserved under `training-runs/e3-sampler-only-superseded-60r2wsu9/`.

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
