---
type: Reference
title: nnU-Net Reference
description: Dataset, split, and configuration details to resolve before training.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: format
  resource: https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/dataset_format.md
  title: nnU-Net dataset format
- id: splits
  resource: https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/manual_data_splits.md
  title: nnU-Net custom splits
- id: usage
  resource: https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/how_to_use_nnunet.md
  title: nnU-Net usage
- id: ignore
  resource: https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/ignore_label.md
  title: nnU-Net ignore label
---

# nnU-Net Reference

The roadmap proposes nnU-Net v2. Exact package and framework versions have not been selected.

- Image channels and label maps must share geometry. Label zero is background and label values are consecutive. Generate `numTraining` from the actual dataset inventory.[^format]
- Custom `splits_final.json` belongs under `nnUNet_preprocessed/DatasetXXX_Name`. Its entries contain `train` and `val` case IDs. Internal validation examples remain in the dataset's training directories; an independent test set is held out.[^splits]
- `3d_lowres` is not generated for every dataset. Inspect the resulting plans rather than assuming that configuration exists. nnU-Net already performs preprocessing, so justify any additional fixed-resolution resampling.[^usage]
- An `ignore` label supports unknown annotation regions; it does not restore anatomy absent from the MRI.[^ignore]

## Proposed experiments

E1: labeled data only. E2: add screened reference-method pseudo-labels. E3: test weighting of face-preserved examples. Keep validation/test subjects fixed; pseudo-labeled additions belong to training. Record distinct dataset/plan/model identifiers so experiments cannot overwrite each other.

Device selection, augmentation, model ensemble count, and model-loading cost belong in each runtime record. Local Apple Silicon exploration and an NVIDIA training environment are different compute contexts.

## Related notes

[Labels and face coverage](../concepts/labels-and-face.md) · [Acceptance](../acceptance.md) · [Roadmap review](../reviews/roadmap-review.md)

[^format]: Official dataset format reference. [Open source](https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/dataset_format.md).
[^splits]: Official manual split instructions. [Open source](https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/manual_data_splits.md).
[^usage]: Official usage and configuration documentation. [Open source](https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/how_to_use_nnunet.md).
[^ignore]: Official ignore-label documentation. [Open source](https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/ignore_label.md).
