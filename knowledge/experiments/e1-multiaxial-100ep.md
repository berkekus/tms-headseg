---
type: Experiment
title: 'EXP-003: E1 Preliminary nnU-Net, MultiAxial Only, 100 Epochs'
description: First trained model on the fixed MultiAxial split; validation-only results from nnU-Net summary.json.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-03T10:00:00+03:00'
experiment_id: EXP-003
experiment_state: run_validation_only
sources:
- id: prep
  resource: ../../tools/nnunet_prep/README.md
  title: Dataset preparation and fixed split
- id: summary
  resource: 'K2 nnU-Net summary.json (validation, fold 0), copied to the K1 Desktop on 2026-11-03'
  title: nnU-Net validation summary
---

# EXP-003: E1 Preliminary nnU-Net, MultiAxial Only, 100 Epochs

Experiment state: **trained; validation results only.** This is a short (100-epoch) preliminary model, not a converged one. The held-out test set was not used.

## Setup

| Field | Value |
| --- | --- |
| Data | `Dataset001_MultiAxial` from `handoff_k2.zip` (SHA-256 `388dec44…c18de`), built by `tools/nnunet_prep/prepare_multiaxial.py` at commit `24b7304` |
| Split | Fixed `splits_final.json`, fold 0: 44 train / 10 validation. Verified: the 10 validation IDs in `summary.json` exactly match the fixed split. |
| Configuration | `3d_fullres`, custom trainer `nnUNetTrainer_E1Preliminary` (trainer SHA-256 `311aace0…48cc8` in K2's `experiment_contract.json`). `debug.json` shows standard nnU-Net settings: 100 epochs, initial LR 0.01 with polynomial decay, weight decay 3e-5, 250 train / 50 val iterations per epoch, batch 2, Dice+CE with deep supervision, mirroring on all axes. The trainer source file was not included in the delivery. |
| Hardware / time | NVIDIA L4 (22 GB), Colab; epochs took 141–181 s (training log 02:00–05:58, about 4 h of epochs plus validation). |
| Versions | nnU-Net 2.8.1, torch 2.6.0+cu124, CUDA 12.4, seed 42 (K2 run records). |
| Split check | K2's `splits_final.json` has the same SHA-256 as K1's (`9e2b37ff…d78b8`); K2's contract also records `test_accessed: false`. |
| Delivery | `E1_L4_001` zip received 2026-11-03: checkpoints (final and best, about 246 MB each), plans, dataset JSON, logs, progress plot, validation predictions; also an earlier `E1Smoke` run. Stored at `C:\Users\Berke\tms-data\k2_delivery` (outside Git). |

Training curve (`progress.png`, reviewed by K1): validation pseudo-Dice (moving average) rises to about 0.87 by epoch 55 and is flat afterwards; validation loss levels off near −0.63 from about epoch 40 while training loss keeps falling to −0.70, a widening but not worsening gap. Longer training on the same 44 cases may therefore add little on validation; this is an inference from one run, not a measurement.

## Validation results (10 subjects)

Mean Dice per class:

| Skin/soft tissue | Skull | CSF | Gray matter | White matter | Mean of 5 classes |
| --- | --- | --- | --- | --- | --- |
| 0.955 | 0.848 | 0.795 | 0.863 | 0.897 | **0.872** |

Per subject (skin, skull, CSF, GM, WM):

| Case | Skin | Skull | CSF | GM | WM |
| --- | --- | --- | --- | --- | --- |
| GU011 | 0.965 | 0.805 | 0.728 | 0.750 | 0.803 |
| GU012 | 0.921 | 0.784 | 0.783 | 0.850 | 0.873 |
| GU018 | 0.917 | 0.830 | 0.737 | 0.867 | 0.915 |
| GU033 | 0.969 | 0.893 | 0.786 | 0.795 | 0.839 |
| GU041 | 0.975 | 0.913 | 0.850 | 0.895 | 0.913 |
| NC012 | 0.968 | 0.860 | 0.801 | 0.864 | 0.908 |
| NC019 | 0.963 | 0.893 | 0.859 | 0.885 | 0.926 |
| NC023 | 0.943 | 0.848 | 0.797 | 0.922 | 0.955 |
| NC029 | 0.973 | 0.878 | 0.789 | 0.902 | 0.928 |
| NYU005 | 0.956 | 0.777 | 0.820 | 0.903 | 0.905 |

## Interpretation limits

- Validation only (10 subjects, mostly GU/NC; one NYU). Not a benchmark; the test set stays closed until settings are frozen.
- The proposed target "mean Dice ≥ 0.85" (SRC-007) is met on validation, but that target is not ratified (Q-06) and validation is used for model selection.
- The MultiAxial paper's test Dice 0.88 is on a different test set and protocol; the two numbers are not directly comparable.
- Skin Dice is computed on defaced labels; it says nothing about the removed face region.
- Weakest: CSF (0.795) and skull (0.848). GU011 is low across brain classes (possible lesion effect; not yet inspected). Lowest skull: NYU005 0.777, GU012 0.784.

## Next

Inspect GU011 and NYU005 predictions. For local inference the custom trainer class must be importable by nnU-Net: obtain K2's trainer file (preferred, matches the recorded hash) before running the checkpoint on the K1 machine, then time inference and build the surface demo.

## Related notes

[EXP-002 charm pilot](charm-ixi-pilot.md) · [Data inventory](../references/datasets.md) · [Acceptance](../acceptance.md)
