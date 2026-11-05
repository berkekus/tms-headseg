---
type: Experiment
title: E2 Trained Model Handoff Review
description: Local integrity review of the supplied E2_L4_001 training artifacts.
status: draft
experiment_id: EXP-E2-HANDOFF
experiment_state: completed_artifact_review
---

# E2 Trained Model Handoff Review

On 2026-11-05 the user supplied `/Users/merttomekce/Downloads/E2_L4_001`. The local model directory is `Dataset002_E2Charm/nnUNetTrainer_E2Preliminary__nnUNetPlans__3d_fullres`, with final and best checkpoints, plans, dataset metadata, logs and 16 validation predictions. The downloaded directory was reviewed directly. The remote Drive folder was not independently inventoried.

The final checkpoint's ZIP CRC passed and a CPU `torch.load` with `weights_only=True` and explicit NumPy scalar/dtype allowlisting succeeded. It records epoch 100 and trainer `nnUNetTrainer_E2Preliminary`; all 292 network state tensors were checked for finite floating-point values. Final checkpoint SHA-256 is `388d2fda8b58bcfedbacdc856674f9329141cbf83d899470f3d20e1faacbc043`. The best checkpoint's ZIP CRC also passed.

Training logs cover epochs 0–99 across three resumed invocations and finish with `Training done.`, full-volume prediction and `Validation complete`. The last invocation records exit code 0. Metadata specifies nnU-Net 2.8.1, PyTorch 2.6.0+cu124, T1 input, five foreground classes, `3d_fullres` and fold 0. The split has 67 training and 16 validation subjects with no overlap. The supplied audit reports RAS canonicalization. The final session metadata identifies an A100, despite the run folder's L4 name.

The mean validation Dice is **0.9140282427263056**. Per-class means are skin 0.91300821, skull 0.88582795, CSF 0.88915632, gray matter 0.93032819 and white matter 0.95182054. All 16 predictions read with finite integer IDs 0–5, and per-class predicted voxel counts match the summary. Dice arithmetic and aggregation recompute correctly. Local plans and split hashes match the experiment contract. Reference label volumes were not included in this folder, so this review did not independently recompute TP/FN or assess anatomical accuracy. The validation cohort and CHARM references differ from E1. These two mean scores do not isolate an improvement on a fixed independent benchmark.

The custom E2 trainer source and E2 notebook were absent from this folder and repository main at the initial review. The contract lists trainer SHA-256 `4b3bf86d717d61e3662d738ece787f09403956ef79403a4c8d25b06017818248`. PR #10 subsequently added the notebook and matching trainer source under tools/e2_training; its SHA-256 matches the supplied contract. The weights themselves are present and readable. New MRI inference and Workbench integration remain to verify. The success record requests runtime release; actual release was not independently checked.

An additional CPU check reconstructed the network with the installed standard trainer's architecture builder and the supplied plans, loaded the final state with `strict=True`, and manually initialized `nnUNetPredictor` successfully. This verifies a loading route that needs no custom trainer source. Missing source therefore does not block running this model. No new MRI prediction was performed in this loading check; the subsequent integration is recorded below.

## Workbench integration and GU011 comparison

After synchronizing main to `82a59e1` while preserving local work, added E1/E2 model selection to the existing inference panel. E2 uses the verified architecture loader, K3's lossless RAS preparation and source-grid restoration. E1 keeps its existing inference route. Reports and desktop run records identify the selected experiment. Known millimetre units are required for the E2 reversible-geometry path.

A real native Workbench CPU run on GU011 completed with mirror augmentation off. Model loading took 1.79 seconds and prediction/export/restoration took 204.38 seconds. Its new source-grid output opened automatically as five native 3D tissue surfaces. Source MRI, model weights, plans and dataset hashes remained unchanged. Evidence and the comparison report are under `/Users/merttomekce/Documents/TMS/training-runs/e2-workbench-d_fx2oj3`.

For the comparison, reused the retained November 3 E1 CPU prediction with mirror augmentation off. The old and new GU011 MRI arrays and numerical affines match exactly. Reconstructed an E2 reference with K1's current label mapping, border-zero masking and MultiAxial lesion rule; its per-class TP/FP/FN/TN match the downloaded GPU validation summary. Against this same reconstructed reference, mean Dice is **E1 0.81608351 / E2 0.91547354**. Per-tissue scores are skin 0.7393 / 0.8983, skull 0.8196 / 0.8828, CSF 0.7874 / 0.9008, GM 0.8306 / 0.9391 and WM 0.9035 / 0.9564. These measure agreement on one validation subject with the E2 label convention. Anatomical improvement on an independent cohort is unestablished. Both predictions retain some labels on exactly-zero MRI voxels (E1 181 / E2 460), so this comparison does not establish removal of all extracranial errors.

Validation passed 74 Workbench tests, 39 E1/E2 demo tests in the inference environment and 13 geometry prepare/restore tests. An initial demo-suite invocation in the Qt-only environment lacked Plotly; the suite passed in the inference runtime. A real initialization check caught the two architecture-builder signatures, and the loader now supports both. Native Windows execution remains unverified. The final E2 result viewer remains open for user inspection.
