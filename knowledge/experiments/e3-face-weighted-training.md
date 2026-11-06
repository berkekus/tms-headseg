---
type: Experiment
title: E3 face-preserved case weighting preparation
description: E2-derived Colab experiment with double sampling weight for the 23 intact-face IXI training cases.
status: draft
experiment_state: not_run
sources:
- id: roadmap
  resource: ../references/nnunet.md
  title: Proposed E3 weighting of face-preserved examples
- id: e2
  resource: e2-preliminary-training.md
  title: Completed E2 preliminary training
- id: code
  resource: ../../tools/e3_training/README.md
  title: E3 implementation and launch guide
---

# E3 face-preserved case weighting

**Superseded by the actual supplied Dataset003 handoff on 2026-11-06.** The
[new package review](e3-data-handoff-review.md) identifies ignore-label training and
physical IXI duplicates. The notebook described below assumes the E2 archive and
is not ready for that package. Its local tests remain evidence only for the
earlier sampling-only proposal.

Prepared on 2026-11-06 after the user authorized an E2-based E3 workflow for an
evening training session. **No E3 GPU training has started or completed.**

## Question and implementation choice

Does increasing the exposure of intact-face IXI training subjects help the model,
while preserving acceptable MultiAxial performance under the same E2 references?

The roadmap proposes weighting face-preserved examples but does not fix the method
or coefficient. The initial implementation chooses **case sampling with replacement**:
weight 2 for each of the 23 IXI training cases, 1 for each of 44 MultiAxial cases.
Expected IXI share is 51.11%, versus E2's 34.33%. This is an unvalidated experiment
setting, not an accepted optimum. It changes cohort/site/pathology exposure as well
as face exposure. It does not weight facial voxels, invent removed faces or modify
the loss. A facial-region loss would require a separately reviewed mask protocol.

## Fixed baseline

- Same `handoff_k2_e2.zip`, SHA-256
  `aa5489712b83111bcd7cd163bb6d43537a0f49590e1971d8f48e9ba55c8c6fe7`.
- Same Dataset002_E2Charm labels, 67 training / 16 validation subjects. The 23/6 IXI
  and 44/10 MultiAxial split lists are retained exactly; no held-out case is added.
- Same lossless RAS preparation and exact saved E2 plans, SHA-256
  `472f3ec4e104c3c2b1b54567455103a89f73a25279a4c3054f6226943858b935`.
  1 mm spacing, patch 160×128×112, batch 2, six-stage PlainConvUNet.
- Same Python 3.11, nnU-Net 2.8.1, torch 2.6.0+cu124 dependency lock, seed 42,
  100 epochs, four augmentation workers, compile disabled, checkpoint every epoch.
- Random initialization; no E1/E2 fine-tuning. Separate E3 trainer and results root.
- The five-epoch pilot must finish before the first fresh 100-epoch invocation.
  Pilot weights do not initialize the main run. Resume preserves the whole contract.

The notebook checks the completed E2 source/train data fingerprints, split, plan and
dependency-lock hashes. Existing E2 code/outputs remain unchanged.

## Local evidence

Thirteen E3 tests passed in the local Python 3.11 / nnU-Net 2.8.1 / torch 2.6.0 CPU
inference environment. Checks exercised actual loader probabilities in loader order,
40,000 sampled case IDs (within 0.012 absolute of 46/90 IXI share), validation
isolation, a full synthetic augmentation pipeline and a finite CPU U-Net gradient/
optimizer step. An isolated installed-package import and actual 5/100-epoch trainer
constructors passed. Notebook sources and every code cell compile; all training
switches default off. Exact validation identities are checked rather than count only.

The retained real E2 audit reports, plans and split matched E3's baseline checks.
All sixteen E2 helper regression tests also passed. The final generated notebook's
eleven code cells compile; readiness metadata and test logs are staged externally.
The subgroup reporter ran on E2's actual 16-case summary: mean foreground Dice
0.91371844 for six IXI and 0.91421412 for ten MultiAxial cases. These are **E2**
reference-label agreement values, not E3 results or face-specific accuracy.

Local verification commands are in the linked launch guide. Logs and a portable
notebook copy are staged outside Git under `training-runs/e3-preparation/`.

## Remote run protocol and remaining input

Upload the standalone E3 notebook to Colab; select L4/A100 and mount the Drive with
the original E2 archive. Default archive path is
`MyDrive/TMS_E2/handoff_k2_e2.zip`; default E3 result root is
`MyDrive/TMS_E3/runs/E3_100ep_001/`. The original training archive was not found in
the inspected local Downloads/TMS folders. Its remote accessibility and a live
Colab/CUDA run remain unverified. The completed E2 model directory alone is not the
83-case training dataset.

Run audit/preview, acknowledge the data, preprocess using E2's plan, complete the
five-epoch GPU pilot, then enable the main run. Collect the entire run folder.
Success requires the final checkpoint and exact 16-case validation. The notebook
records six-case IXI and ten-case MultiAxial metrics in addition to overall Dice.
Keep final inference settings matched with E2 and inspect per-case failures.

No E3 result, performance improvement, model acceptance, GPU cost, live multi-worker
success or clinical utility is claimed. A current Workbench E3 import is outside
this training preparation. IXI111's prior exploratory test exposure remains recorded
in its own experiment and does not authorize adding it to training or tuning on it.
