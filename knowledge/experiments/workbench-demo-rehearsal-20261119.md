---
type: Experiment
title: Workbench Update and E2 Demo Rehearsal
description: Local update, preserved work, model selection and a real native CPU rehearsal before the requested demo.
status: completed
experiment_state: completed_e2_rehearsal_e3_unavailable
---

# Workbench Update and E2 Demo Rehearsal

## Scope and checkout

On 2026-11-19, the user requested the latest repository and a check of the model used in the interface before a November 20 demo. Fetched `origin` and fast-forwarded local `main` from `f4a7233` to `d6d6c85`. The new version includes local Physician / Technical Team accounts and saved studies.

Seventeen pre-existing modified/untracked files were backed up outside Git and restored. Fifteen retain their original hashes; the experiment index and knowledge log combine the local E3 records with the upstream CT/Windows entries. The safety stash remains. No commit or push was requested.

## Model actually selected

The current selector, inference job validator and prediction CLI accept **E1 and E2 only**. There is no E3 inference route in this checkout. E3 training code and the prior supplied completion log do not establish Workbench integration. No E3 final checkpoint was found under the local Downloads or training-runs directories.

Created ignored local `outputs/workbench/settings.json` selecting **E2**, CPU and no mirrored passes, with the existing E1/E2 model paths. An actual `InferencePanel` restored these settings and validated the E2 files. This does not change trained weights or start inference. The default model version in code, without a saved configuration, remains E1.

The selected E2 trainer folder is `Dataset002_E2Charm/nnUNetTrainer_E2Preliminary__nnUNetPlans__3d_fullres` in the supplied Downloads package. Its final checkpoint SHA-256 is `388d2fda8b58bcfedbacdc856674f9329141cbf83d899470f3d20e1faacbc043`.

## Verification

- GUI requirements were already installed; `pip check` found no broken GUI requirements.
- All **110 Workbench unit tests** passed under the offscreen Qt platform.
- The separate inference runtime reports Python 3.11.14, torch 2.6.0 and nnU-Net 2.8.1.
- Ran the existing `tools/mri_prototype/check_inference.py` with `--experiment E2` on the previously used GU011 T1, CPU, no TTA.
- Real prediction completed in **124.318 s**; the native end-to-end check completed in **140.336 s**, including automatic 3D opening. Five surfaces and 193,452 triangles were present; the prediction-stage ETA appeared.
- MRI, checkpoint, plans and dataset hashes were unchanged. Both job completion records were checked.
- Sandbox native startup failed because macOS graphics services were unavailable; the authorized native retry passed. This was an environment restriction, not a failed model prediction.
- Started the normal updated application and observed the workspace-choice screen, including the first Technical Team account setup action. Left it running. Account creation/sign-in and an actual physician session remain for the user; no credentials were created or changed.

This is one known validation-case operational rehearsal, not a new accuracy evaluation, independent test or clinical acceptance.

## Local artifacts and next action

Evidence is outside Git under `training-runs/demo-rehearsal-20261119-jw7fd80j/`: settings copy, model inventory, desktop/job logs, running/completion images and the `*-verification.json` record. The fresh prediction is in `e2_20261119T201614Z_f7eb2792/prediction.nii.gz`.

Use the repository's `Open MRI Workbench.command` to reopen this version. Set up the first local account through the UI. The ignored E2 configuration is available to Technical Team and to the first Physician setup fallback. To use E3, first obtain and audit the complete trained E3 model folder, then implement explicit E3 inference/version/provenance support and rehearse it; do not relabel E2 output as E3.
