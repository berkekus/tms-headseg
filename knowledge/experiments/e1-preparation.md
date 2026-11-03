---
type: Experiment
title: E1 MultiAxial Training Preparation
description: Supplied K2 data audit, GPU pilots, and completed preliminary E1 training with validation.
status: draft
experiment_id: EXP-003
experiment_state: completed
preparation_state: completed
T4_pilot_state: completed
A100_pilot_state: completed
preliminary_state: completed
demo_state: local_inference_verified
sources:
- id: handoff
  resource: local://handoff_k2
  title: User-supplied K2 handoff, inspected 2026-11-02
- id: roadmap
  resource: ../references/module-a-roadmap-team-update.md
  title: SRC-006, section 5.3
---

# EXP-003: E1 MultiAxial Training Preparation

The user requested preparation and execution of E1 Colab training using the supplied K2 handoff. Local preparation and the T4/A100 five-epoch pilots completed. The separate L4 100-epoch preliminary model subsequently completed after checkpoint recovery, with full-volume validation of the fixed ten cases and foreground mean Dice 0.8715520701436821 according to the final user-supplied console log. Execution of this preliminary experiment is complete; accepted E1 performance, held-out test evaluation, anatomical quality, and final Module A delivery remain unestablished. Earlier entries below preserve observations at their respective times.

## Source specification

The local source is `/Users/merttomekce/Downloads/handoff_k2/`: `K2_BASLA.md`, `hazirlik_notlari_en.md`, `splits_final.json`, and `nnUNet_raw/Dataset001_MultiAxial/`. These documents were inspected as source material; their commands were not executed automatically. SRC-006 section 5.3 defines E1 as MultiAxial-only, distinct from CHARM-generated additional training labels in E2.

The handoff specifies 54 paired cases, one T1 input, labels 0 background / 1 skin / 2 skull / 3 CSF / 4 gray matter / 5 white matter, and a fixed 44-training / 10-validation split. Only fold 0 and `3d_fullres` are used. The external test set remains with K1 and was neither available nor accessed. The reported 1 mm spacing, patch 128×160×112, and batch size 2 are handoff claims; the notebook displays its regenerated plan before training.

Software is fixed to nnU-Net 2.8.1 and PyTorch 2.6.0 / CUDA 12.4 in a separate Linux Python 3.11 environment. The prepared protocol runs a 5-epoch debugging model, followed by a separately initialized 100-epoch preliminary model. There is no CHARM fine-tuning or pretrained weight transfer. Small trainer subclasses only seed initialization and save every completed epoch. Seeded initialization is not a claim of deterministic CUDA/resumed training.

## Preparation observations

All 54 pairs passed the implemented technical audit: expected files and fixed split, matching paired shapes/affines, finite values, permitted label IDs, nonconstant MRIs, current affine orthogonality, and no identical image voxel arrays across subjects. These checks do not prove distinct patient identity or expert anatomical correctness. All 54 pairs have unspecified NIfTI spatial units; no headers were rewritten.

Train-only voxel-plane label overlays were generated and visually inspected. Anatomical and semantic approval remains unestablished. The supplied notes disclose inferred label mapping, air cavities merged into background, no ignore mask for removed facial regions, and modified affines for some NYU cases. The original affine manifest is absent. The resulting training experiment cannot establish face reconstruction accuracy or physical-space mesh accuracy.

Input identity:

- Audited dataset fingerprint: `a3d7801021287c538ee8f3af55947b3795fe3ccf5d628f01d34942e0b4f93ae0`.
- Fixed split SHA-256: `9e2b37ffccff8196f9457963e3e603eabfeae6e89d8baec91ab5f989845d78b8`.
- Prepared ZIP: 821,024,801 bytes; SHA-256 `c580a1706a8242afc11b3e34c7b74586e759766e89fc4f3bd0c82cacb0be071a`. All 111 archive entries passed CRC validation.

The dataset fingerprint is defined by the [audit implementation](../../tools/e1_training/audit_handoff.py). Full per-file checksums, per-case observations, scans, and overlays remain outside Git at `/Users/merttomekce/Documents/TMS/training-runs/e1-preparation/`. Original input file hashes were checked when packaging; originals were not modified.

## Reproduction and checks

The [training preparation guide](../../tools/e1_training/README.md) documents the standalone [Colab notebook](../../tools/e1_training/E1_Colab.ipynb), local audit, archive preparation, and notebook regeneration commands. The notebook embeds its helpers and dependency lock; training and provisional-data acknowledgment default to false. It preserves the supplied split, validates archive hashes, records an immutable experiment contract, writes checkpoints/logs to Drive, and rejects fresh-run overwrites or resume without an intact checkpoint container.

Local audit used the existing MRI prototype environment with NumPy and nibabel. Eighteen preparation checks passed using:

```bash
tools/mri_prototype/.venv/bin/python -m unittest discover -s tools/e1_training -q
```

Those checks cover malformed splits/data, hold-out exclusion, archive handling, overwrite/checkpoint gates, subprocess logging, trainer epoch settings, and generated notebook sources/defaults. Linux x86-64 Python 3.11 dependencies resolved with `uv 0.11.8` and the CUDA 12.4 backend into a 94-package lock. Resolution and synthetic checks do not establish successful live Colab installation, CUDA execution, full-volume validation, or checkpoint recovery after an actual disconnected training session. Subsequent user-supplied execution evidence is recorded separately below.

During guided Colab setup, the user reported that the preview subprocess failed while importing matplotlib: inherited `MPLBACKEND=module://matplotlib_inline.backend_inline` was unavailable in the isolated environment. A local regression first reproduced import failure with an invalid inherited backend, then rendered a synthetic PNG successfully after the notebook's child environment was set to `MPLBACKEND=Agg`. The override also applies to later nnU-Net commands without changing the notebook kernel's plotting backend. An already-open notebook can apply the same override directly to `ENV`; the regenerated notebook includes it permanently.

The user subsequently supplied the Colab audit's successful 44/10 summary with 54 unknown spatial-unit headers and a rendered seven-case overlay sheet (`/Users/merttomekce/Downloads/Unknown.png`). This establishes user-reported completion of the technical audit and preview retry in Colab. The overlays show supplied training labels, not model predictions. It does not establish expert label approval, physical geometry accuracy, completed preprocessing, training, or full-volume model evaluation. The full Colab training workflow remains unverified.

## Next run

The user supplied the fourth notebook section's output showing successful dataset integrity verification, fingerprint extraction for 54/54 cases, and `3d_fullres` preprocessing for 54/54 cases. The printed plan matches the handoff's patch 128×160×112, batch size 2, and numeric target spacing [1, 1, 1]. Numeric target spacing does not resolve the unknown original NIfTI spatial units. Fingerprint extraction showed 1:16 and the preprocessing progress showed 3:25; these are stage times, not training performance or the full cell's wall time. The old-planner recommendation and discarded `3d_lowres` configuration were informational; the supplied output contains no traceback. The displayed 2D plan does not establish any 2D preprocessing or training. Evidence is preserved outside Git at `/Users/merttomekce/Documents/TMS/training-runs/e1-preparation/colab-preprocess-output.txt`.

### Attempt EXP-003-A01: trainer initialization failed

The user started the 5-epoch pilot on their reported T4 session and supplied a traceback showing `Using device: cuda:0` followed by `KeyError: 'args'` inside nnU-Net's constructor argument recording. This is a failed initialization attempt, before any training epoch, rather than a successful training result. The custom E1 subclasses incorrectly declared `*args, **kwargs`; nnU-Net 2.8.1 inspects `self.__init__` and looks up those names in the base constructor's named locals. Both variants now declare the explicit five-parameter signature. The earlier lightweight parent stub missed this API requirement; the strengthened regression reproduces the same `KeyError` before the fix and records all named arguments successfully after it.

An existing-notebook repair cell updates the known old trainer and chooses a new `_initfix` experiment ID while preserving the failed attempt's logs and immutable contract. It disables both training flags, records provenance, and reuses local preprocessing when section 4 is rerun. A synthetic repair check confirms that previous contract bytes remain unchanged. The regenerated notebook contains the corrected trainer. Seventeen local checks pass; successful live Colab training is still unverified.

### Attempt EXP-003-A02: repaired pilot running

The user reported that the repaired T4 pilot was still running after approximately six minutes. Their supplied log selected `cuda:0`, read the existing single fold with 44 training and 10 validation cases, printed the expected `3d_fullres` configuration, and reached `Epoch 0` / learning rate 0.01. The optional architecture plotting message `No module named 'hiddenlayer'` was followed by epoch startup and did not stop initialization. The timestamps shown in the remote log are not converted into a local start time here.

This establishes entry into the training epoch, not a completed optimizer step or a completed epoch. The latest excerpt contains no loss/epoch-time summary and no new traceback. The nnU-Net 2.8.1 loop performs 250 training and 50 validation iterations per epoch, then prints loss and epoch time; it has no per-batch progress print in that loop. Silence alone does not prove either forward progress or a stall. No GPU-utilization observation or checkpoint has been supplied for this attempt.

The user next supplied the completed epoch-0 summary: train loss 0.1569, validation loss -0.1252, pseudo-Dice [0.8367, 0.6401, 0.6689, 0.7488, 0.7389], epoch time 419.1 seconds, and best EMA pseudo-Dice 0.7267. Epoch 1 then started with learning rate 0.00818. This establishes one completed epoch and subsequent progress, not a finished five-epoch pilot or final full-volume validation. Checkpoint existence has not been inspected independently.

At the first epoch's speed alone, five epochs would take about 34.9 minutes and 100 epochs about 11.64 hours, excluding setup, inter-epoch checkpoint/plot overhead, and final full-volume validation. These are conditional extrapolations from a first epoch, not a measured stable-runtime median; later epoch times are needed. Pseudo-Dice is the trainer's patch-based metric, not a held-out test score.

The user supplied a T4 session rate of approximately 1.15 compute units/hour and available balance 198.95. At the first epoch's speed this gives approximately 13.39 units for 100 epoch cycles, before the excluded overhead. For an explicitly illustrative A100 40 GB rate of 5.4 units/hour (a [third-party first-hand March 2026 observation](https://mccormickml.com/2024/04/23/colab-gpus-features-and-pricing/), not this user's actual A100 rate), a 4× speedup would give 2.91 hours / 15.72 units and a 6× speedup 1.94 hours / 10.48 units. These are scenarios, not measured A100 speeds. Break-even at that illustrative rate requires approximately 4.70× speedup, or epochs shorter than 89.25 seconds with otherwise comparable work. Neither actual A100 speed nor its account-specific unit rate is established. Extra setup after switching and final validation would also affect total costs.

The next user excerpt reports epoch 1 completed in 381.67 seconds, train loss -0.2436, validation loss -0.3137, pseudo-Dice [0.9004, 0.7115, 0.73, 0.7823, 0.8173], and best EMA pseudo-Dice 0.7329. Epoch 2 started at log time 20:30:27.946996. At that second-epoch speed, the remaining three epoch cycles would take about 19.1 minutes from that start, plus checkpoint/plot overhead and final full-volume validation afterward. The conditional epoch-loop finish is around log time 20:50 (approximately 23:50 Europe/Istanbul if the remote log uses UTC). This is not an estimate of completed final validation or the whole notebook cell's finish. No checkpoint or final model output has yet been inspected.

### Completed T4 pilot and A100 comparison preparation

The user's complete log establishes epochs 0–4 with durations [419.1, 381.67, 401.9, 417.5, 434.47] seconds, followed by `Training done.`, predictions for the ten validation cases, `Validation complete`, foreground mean validation Dice 0.8352820391134443, and successful subprocess completion in 40.7 minutes. The final epoch's patch pseudo-Dice values were [0.9371, 0.7791, 0.7609, 0.8171, 0.8624]. The full-volume validation score is a five-epoch preliminary validation result against the supplied provisional labels, not held-out test performance or clinical accuracy. Checkpoint files have not been inspected independently.

The median of the four post-first epoch times is 409.7 seconds. The notebook's resulting 100-epoch loop estimate is 11.3806 hours, or about 13.0876 units at the user's reported T4 rate of 1.15 units/hour, excluding setup, preprocessing, checkpoint/plot overhead, and final full-volume validation. This supersedes earlier first-/second-epoch forecasts for planning, without erasing those historical observations.

The complete user log is preserved outside Git as `training-runs/e1-preparation/colab-t4-pilot-output.txt`, SHA-256 `7fa301e3a5dfc54356e1bf030f7b982ca9f393d7db16d5db5bb323551a982ffb`; an aggregate JSON summary is alongside it. These paths are relative to `/Users/merttomekce/Documents/TMS/`, not the repository. A separate generated `E1_A100_Colab.ipynb` in that folder uses fresh experiment ID `E1_A100_001`, identical embedded training code/lock/defaults, and disabled training flags. All its code cells compile; no A100 installation, training, or rate observation is claimed. The existing T4 results path remains `MyDrive/TMS_E1/runs/E1_baseline_001_initfix`.

### Attempt EXP-003-A03: A100 pilot running

The user supplied the A100 comparison's first completed epoch (169.55 seconds), epoch-1 startup, the unchanged 44/10 split, and matching printed `3d_fullres` configuration (patch 128×160×112, batch 2, target spacing [1, 1, 1], and the same PlainConvUNet configuration). They reported 6.73 compute units/hour, available balance 197.25, and one active session. Exact A100 model/VRAM has not been supplied and is not inferred from the rate. The first epoch's train/validation losses were 0.1709 / -0.1239, patch pseudo-Dice [0.8541, 0.6634, 0.6794, 0.6967, 0.7877], and best EMA pseudo-Dice 0.7363. This is not completed full-volume validation.

The observed first-epoch speedup against T4's first epoch is 419.1 / 169.55 ≈ 2.47×. At the first A100 epoch's speed, 100 epoch cycles would take approximately 4.71 hours / 31.70 units at the reported 6.73/hour, excluding other overhead. The corresponding T4 estimate from its four post-first epochs remains 11.38 hours / 13.09 units. This is an initial comparison of one first A100 epoch against a post-first T4 median, not a completed benchmark. With those actual hourly rates, A100 would need approximately 70-second epochs to break even against T4's median time in unit consumption. This replaces the earlier illustrative A100 5.4/hour scenario for decisions about this user's current A100 session.

The user subsequently supplied a Colab resource screenshot showing system RAM 5.2/83.5 GB, GPU RAM 7.7/40.0 GB, and disk 9.1/112.6 GB, and asked about faster execution for similar credits. This reports 40 GB GPU memory capacity but does not report GPU compute utilization or CPU processing load. Low allocated VRAM alone does not establish an underused GPU. Local source inspection confirms the conservative two augmentation workers and disabled torch compilation; neither has been established as a bottleneck. Proposed next diagnostic is repeated GPU-utilization sampling during active training (`nvidia-smi` in a separate Colab terminal if available). No batch, patch, worker, or compile setting was changed. A batch-size increase would change sampled patches per epoch at the fixed 250 iterations, so it is not a comparable speed-only change.

The next user excerpt establishes A100 epochs 1–3 completed in 144.12, 158.05, and 149.39 seconds, with epoch 4 starting at log time 21:25:07.705122. Four of five pilot epochs have therefore completed, without a final full-volume validation result yet. The current post-first median is 149.39 seconds: a conditional 100-cycle estimate of 4.1497 hours / 27.93 units at 6.73/hour. This is approximately 2.74× faster than T4's post-first median, with about 2.13× its estimated unit consumption. These interim estimates supersede the single-first-A100-epoch forecast for planning; epoch 4 and final validation remain pending. No GPU-utilization telemetry or performance-setting changes have been supplied.

The user supplied two `nvidia-smi` samples two seconds apart during the reported final epoch. They identify NVIDIA A100-SXM4-40GB, driver 580.82.07, approximately 7,876 MiB allocated GPU memory, GPU-util readings 0% and 20%, and power readings 69 W and 317 W against a 400 W cap. The isolated training Python process is listed. These short sample windows show intermittent activity, not an epoch-wide utilization average or a proven data-loading bottleneck. CPU allocation and live load remain unobserved. The next diagnostic is longer active-training utilization sampling plus `nproc` and `vmstat 1 6` from the separate Colab terminal; increasing the conservative two augmentation workers is a candidate only after CPU capacity/headroom is checked. No active run settings were modified.

The user asked whether L4 could offer better value and should also be tested. A separate generated `E1_L4_Colab.ipynb` was prepared outside Git alongside the A100 copy, with fresh experiment ID `E1_L4_001`, identical embedded helper hashes, unchanged two-worker/batch-2 training settings, and disabled training flags. All code cells compile. No L4 runtime, installation, GPU execution, or account-specific unit rate has been observed. At the earlier explicitly illustrative L4 rate of 1.71 units/hour, its epochs would need to be shorter than about 275.5 seconds to beat the measured T4 configuration on epoch-loop units; this is a conditional threshold, not an L4 performance forecast. Finish A100 validation before changing runtime; compare actual L4 rate and post-first epoch times if the additional benchmark is pursued.

### Completed A100 pilot

The user's full A100 log establishes all five epoch times [169.55, 144.12, 158.05, 149.39, 139.96] seconds, `Training done.`, predictions for the same ten validation subjects, `Validation complete`, foreground mean validation Dice 0.8323130867152226, and successful subprocess completion in 14.4 minutes. The final epoch's patch pseudo-Dice values were [0.9343, 0.7876, 0.7686, 0.821, 0.8556]. The post-first median is 146.755 seconds, projecting to 4.0765 hours / 27.435 units for 100 epoch cycles at the reported 6.73/hour, before other overhead. This supersedes the earlier A100 timing forecasts for planning.

Against T4's 409.7-second median, the completed A100 pilot gives approximately 2.79× epoch throughput with approximately 2.10× the estimated epoch-loop unit consumption. Using the reported completed subprocess durations and hourly rates, the pilots themselves would consume approximately 0.78 units for T4 and 1.62 for A100, excluding earlier setup/audit/preprocessing/idle time; these are rate-based calculations, not independently reconciled account debits. The small validation-score difference between single five-epoch runs does not establish a hardware accuracy advantage; seeded training was not promised bitwise deterministic.

The complete user log is preserved outside Git as `training-runs/e1-preparation/colab-a100-pilot-output.txt`, SHA-256 `bbd274f0613f58a71578d0f26d686bb60c6652dcd4bbfc5c6be94a44a4f559f3`; `a100_pilot_summary.json` is alongside it. These paths are relative to `/Users/merttomekce/Documents/TMS/`. User-reported Drive output is `MyDrive/TMS_E1/runs/E1_A100_001/`; checkpoints have not been inspected independently. Original label/geometry/unit caveats still apply to both validation scores, and neither run evaluated the held-out test set.

The optional L4 comparison can now use the prepared separate notebook and identical baseline settings. Record actual L4 unit rate and completed pilot results before selecting the 100-epoch runtime; avoid comparing altered batches or augmentation-worker settings as a hardware-only comparison. Additional setup and final validation affect consumption. The 100-epoch model remains **not run**; E1 completion and held-out test performance are not established.

### L4 telemetry received

The user supplied an L4 resource screenshot reporting 1.94 units/hour, one active session, system RAM 4.7/53.0 GB, and GPU RAM 7.8/22.5 GB. Subsequent `nvidia-smi -l 2` output identifies NVIDIA L4 with the isolated training Python process and seven GPU-util samples [100, 100, 99, 100, 100, 99, 0] across approximately 14 seconds. Allocated GPU memory is 7,980 MiB of 23,034 MiB, power readings are 56–74 W against a reported 72 W cap, and temperatures 76–80°C. The full supplied text is preserved outside Git as `training-runs/e1-preparation/colab-l4-utilization.txt` relative to `/Users/merttomekce/Documents/TMS/`.

Six of seven samples show near-continuous kernel activity in their respective sample windows. These observations do not suggest sustained data starvation in that interval, but do not prove an epoch-wide bottleneck diagnosis, maximal computational efficiency, or absence of throttling. The isolated final 0% sample has no proven cause. No performance setting was changed. L4 epoch timings, selected trainer/stage, and full-volume validation have not yet been supplied, so runtime/cost rankings remain pending. At the actual reported L4 rate of 1.94/hour, beating T4's measured 409.7-second median and 1.15/hour rate on loop units requires L4 epochs below approximately 242.86 seconds (4m03s), superseding the earlier illustrative 1.71/hour threshold.

### Attempt EXP-003-A04: L4 pilot reaches epoch 1

The user supplied the L4 training log with matching global dataset/plan settings, epoch 0 completed in 177.09 seconds, train loss 0.1875, validation loss -0.0812, patch pseudo-Dice [0.8236, 0.6651, 0.6323, 0.7037, 0.7948], best EMA pseudo-Dice 0.7239, and epoch-1 startup. The learning-rate sequence 0.01 then 0.00818 is consistent with the five-epoch pilot. No full-volume validation or final pilot completion has been supplied.

The L4 first epoch is about 4.45% slower than A100's first epoch (177.09 versus 169.55 seconds); this is a first-epoch comparison, not a post-first median comparison. At that initial L4 speed and the reported 1.94 units/hour, 100 epoch cycles would take about 4.92 hours / 9.54 units before setup/checkpoint/final-validation overhead. That makes L4 a promising cost candidate under current baseline settings; a complete pilot and post-first timings are needed before the final choice. No performance setting has been changed.

### L4 timing estimate received and runtime recommendation

The user supplied notebook section 6's estimate of 4.42 hours for 100 epoch cycles and confirmed L4 rate 1.94 units/hour. This gives approximately 8.5748 units, before setup/checkpoint/final-validation overhead. The rounded estimate implies a post-first median around 159 seconds but does not provide the individual final epoch times. The full L4 pilot completion/validation log and its full-volume Dice have not yet been supplied; section 6 alone is not proof of successful final validation.

Under the measured baseline settings and the reported estimates, L4 offers the lowest projected loop consumption (8.57 units versus T4 13.09 and A100 27.44), with a duration close to A100's (4.42 versus 4.08 hours) and much shorter than T4's 11.38 hours. Recommended ending GPU comparisons and selecting L4 for the separate 100-epoch preliminary run after the user confirms successful pilot validation/completion. This is a runtime recommendation, not evidence that the 100-epoch job was launched or completed. A compact timing record is outside Git at `training-runs/e1-preparation/l4_reported_timing.json` relative to `/Users/merttomekce/Documents/TMS/`.

### Attempt EXP-003-A05: 100-epoch L4 preliminary run started

The user reported starting section 7 with the Mac awake, then supplied a training excerpt and Drive screenshot. The screenshot's breadcrumb identifies `nnUNetTrainer_E1Preliminary__…/fold_0` and displays `checkpoint_latest.pth`, `checkpoint_best.pth`, `progress.png`, `debug.json`, and a training log. The excerpt confirms CUDA device 0, fixed fold-0 44/10 split, unchanged printed batch-2 / patch-128×160×112 plan, epoch 0 completed in 175.05 seconds, and epoch 1 started with learning rate 0.00991, consistent with the 100-epoch schedule rather than the five-epoch pilot. Epoch-0 train/validation losses were 0.1812 / -0.1411, patch pseudo-Dice [0.8589, 0.6699, 0.6842, 0.7261, 0.7558], and best EMA pseudo-Dice 0.739.

This establishes a running 100-epoch model with one completed epoch and checkpoint filenames visible in the user's Drive UI. File bytes/sizes, checkpoint integrity, full experiment path, future runtime continuity, and final validation have not been inspected independently. The intended parent experiment is the selected L4 notebook's `E1_L4_001`. Screenshot basename: `Screenshot 2026-11-03 at 01.11.44.png`. Installation/execution of the optional overnight release cell is unconfirmed. Morning review should check final checkpoint and ten-case full-volume validation; the run is not complete.


### Attempt EXP-003-A05 continued: checkpoint recovery and completed preliminary model

The user reported losing the original Colab environment after the Mac was found with its screen locked. Initial local-path/settings probes were false, while later probes after setup and switching from Safari to Chrome were true. The browser change does not itself establish the cause of the earlier runtime loss. The supplied original Drive log reaches completed epoch 12 and epoch-13 startup. A subsequent excerpt shows epoch 13 completed; the user then explicitly stopped an initial resume, explaining its `KeyboardInterrupt`. A fresh invocation started epoch 14 with learning rate 0.00873, consistent with recovery under the unchanged 100-epoch schedule. A `NameError` before that recovery was resolved by executing section 5 with `RUN_5_EPOCH_PILOT = False` to define `train_stage`; skipping its code entirely after a reset is incorrect even when the pilot is not repeated.

The final supplied log establishes all 86 remaining epochs, indexed 14–99, followed by `Training done.`, predictions for all ten fixed validation subjects, `Validation complete`, foreground mean validation Dice **0.8715520701436821**, and successful subprocess completion (`Bitti: 237.4 dakika`). This duration is only the final resumed invocation, including validation; it is not total experiment time or account consumption. The final epoch has train/patch-validation losses -0.7065 / -0.6301 and patch pseudo-Dice [0.9543, 0.8516, 0.8073, 0.861, 0.9003]. Best reported EMA pseudo-Dice reaches 0.873 at epoch 97. These patch/EMA values are separate from the full-volume validation result.

The completion cell prints `Sonuçlar Drive'a kaydedildi` with foreground mean Dice 0.8715520701436821 and IoU 0.7785610635483262. Under the supplied helper, that point follows checks for a nonempty final checkpoint and ten validation entries and writes `overnight_success.json` before requesting `runtime.unassign()`. Thus the output establishes reaching the success/release-request branch; it does not prove the release API succeeded or billing stopped. The final checkpoint has not been independently downloaded or deserialized. Log timestamps are retained as supplied; no local-time completion claim is derived from them.

The reported experiment root is `MyDrive/TMS_E1/runs/E1_L4_001/`. The preliminary trainer output is expected under `Dataset001_MultiAxial/nnUNetTrainer_E1Preliminary__nnUNetPlans__3d_fullres/`, with final weights in `fold_0/checkpoint_final.pth` and metrics in `fold_0/validation/summary.json`. Preserve the whole trainer directory and custom trainer/environment information for later inference, rather than keeping only the weights.

The complete final console output is preserved outside Git as `training-runs/e1-preparation/colab-l4-preliminary-completion-output.txt`, SHA-256 `d1254c78478c2a39619a8081dab97ab125b2682745136deb8973ee33e0fabc50`; the parsed `l4_preliminary_summary.json` is alongside it, relative to `/Users/merttomekce/Documents/TMS/`. At this point the next actions were inspecting the actual validation JSON and prediction overlays, confirming model files, and confirming runtime release if still allocated; the later JSON review is recorded below. No additional long training is automatically scheduled. This is a preliminary validation result against provisional labels, not 87.16% voxel accuracy, clinical validation, held-out test performance, or E1/Module A acceptance. The original label, geometry, spatial-unit, and defacing-mask limitations remain.

### Validation JSON inspected: per-class and per-case review

The user supplied `/Users/merttomekce/Downloads/summary.json` after successful completion. Its foreground mean Dice (0.8715520701436821) and IoU (0.7785610635483262) match the console output. The ten reference case IDs exactly match the original fixed validation split. Each reported per-case Dice was recomputed from TP/FP/FN, and the reported class means and unweighted five-class foreground mean are consistent. This validates the JSON arithmetic and case membership, not the prediction arrays or ground-truth anatomy. Reference and prediction paths are distinct with matching case basenames; their file contents have not been independently compared.

Using the supplied, still-provisional `dataset.json` mapping:

| Label | Supplied tissue name | Ten-case mean Dice |
| --- | --- | --- |
| 1 | skin | 0.955030 |
| 2 | skull | 0.847934 |
| 3 | CSF | 0.795024 |
| 4 | gray matter | 0.863205 |
| 5 | white matter | 0.896567 |

CSF has the lowest class mean and skin the highest. The lowest case-level macro-average across the same five classes is GU011 at 0.810283; its gray-matter Dice is 0.750129, white-matter 0.802655, and CSF 0.728272. The highest case-level macro-average is GU041 at 0.909224. NYU005 skull Dice is 0.777276, also a useful focused review candidate. These are scores against the supplied labels, not expert quality judgments or evidence of their error causes.

Prioritize MRI/reference/prediction overlays for GU011, then CSF/skull boundaries across additional cases, before deciding whether to extend training. The original GU011 MRI is locally available in the supplied handoff, but its trained validation prediction has not been supplied. No overlay or array-level geometric review is claimed. The model's final training/validation loss gap or these summary scores alone cannot establish overfitting, clinical validity, physical-space accuracy, or superiority over CHARM.

The JSON is preserved outside Git as `training-runs/e1-preparation/l4_preliminary_validation_summary.json`, SHA-256 `02944104abdae9950d82a91ac91403b6ac34a35c608d410a4459181054ab1a25`; `l4_preliminary_validation_review.json` records the arithmetic and split checks, relative to `/Users/merttomekce/Documents/TMS/`. Runtime release and independent checkpoint inspection remain unverified. Accepted E1 performance and held-out test evaluation remain pending.

### GU011 prediction inspected against original MRI and reference

The user supplied `GU011.nii` from Downloads. Its SHA-256 is `12407fba24c47d603d2cc704784b1b28a74f951b6b2122e9e52cba78c5774d26`. It is a finite 3D uint8 label volume, shape 176×250×250, containing labels 0–5. Its voxel-grid shape, numerical affine, and RAS axis codes match the original GU011 MRI and supplied reference. No resampling or header rewriting was performed. Recomputed TP/FP/FN, class voxel counts, and every per-class Dice exactly match GU011 in the supplied validation JSON, establishing that this is the evaluated prediction. This does not independently validate the reference label semantics or anatomy.

The prediction header declares millimetres, while the original MRI/reference spatial units remain unknown. Matching numerical grids therefore supports voxel-wise comparison but does not resolve physical-space accuracy or source unit provenance.

| Supplied tissue | GU011 Dice | Prediction label-volume difference vs reference |
| --- | --- | --- |
| skin | 0.965469 | +1.25% |
| skull | 0.804892 | +9.88% |
| CSF | 0.728272 | -12.69% |
| gray matter | 0.750129 | -11.75% |
| white matter | 0.802655 | +4.60% |

The full-volume confusion matrix shows 100,725 reference CSF voxels assigned skull, 94,215 reference gray-matter voxels assigned white matter, and 72,408 reference gray-matter voxels assigned CSF. These are reference-relative label disagreements, not proven anatomical mistakes in the prediction or proof that the reference is correct.

Generated and visually inspected a three-plane MRI/reference/prediction/disagreement comparison and a three-level axial gray-matter/CSF error comparison. Selected planes show gross spatial correspondence, with substantial tissue-boundary differences and smoother predicted fine structures, including differences around the lower posterior brain and peripheral CSF/skull boundary. This limited review does not establish an underlying cause, whole-volume anatomical correctness, or absence of geometric problems. Additional cases and expert/source-label review are needed before attributing the gap solely to insufficient epochs.

Artifacts remain outside Git at `training-runs/e1-preparation/gu011-review/` relative to `/Users/merttomekce/Documents/TMS/`: `GU011_prediction.nii` preserves the supplied bytes; `review_gu011.py` reproduces the array checks/figures with assertions; `gu011_review.json` records hashes, metadata, full-volume confusion matrix, exact metrics, and review limits; `gu011_comparison.png` and `gu011_tissue_errors.png` are the inspected figures. Original scans and supplied files were not modified. Only this validation prediction has been independently inspected; model checkpoint weights and held-out test performance remain uninspected.

### E1 presentation demo and independently verified CPU inference

The user approved an inference notebook plus a saved-result fallback for the Friday coordinator presentation, keeping work under `tools/` without modifying the desktop MRI/CHARM prototype. Added the [demo guide](../../tools/e1_training/DEMO.md), [standalone notebook](../../tools/e1_training/E1_Demo.ipynb), [builder](../../tools/e1_training/build_demo_notebook.py), and [single-MRI report/inference command](../../tools/e1_training/demo.py). Recorded mode displays existing validation predictions without loading Torch or requiring a GPU. Explicitly enabled inference uses the existing model, custom trainer, and pinned versions; it never trains. Reports distinguish saved predictions from newly executed inference, show their creation timestamp, and preserve an offline HTML/PNG/JSON fallback. No-reference inputs receive no Dice score. Known grid/unit mismatches and output overwrites are rejected; unknown units remain visible limitations.

Through the user's already-open Drive UI, downloaded the trained model's `plans.json`, `dataset.json`, and final checkpoint. The user explicitly approved Drive's size-based antivirus-scan warning for their own checkpoint. Source Drive files, sharing settings, and Colab runtimes were not modified. Model artifacts remain outside Git at `training-runs/e1-demo/model/` relative to `/Users/merttomekce/Documents/TMS/`. The final checkpoint is 246,487,536 bytes, SHA-256 `678867420134d54b31a9975f2c2d1a34b57b8369aef5692fa64f97a8980a531b`. Its archive integrity passed, and a separate Torch load confirmed trainer `nnUNetTrainer_E1Preliminary`, `current_epoch = 100`, `3d_fullres`, fold 0, and 292 network tensors. This supersedes earlier statements that checkpoint bytes had not been independently inspected.

Created an isolated macOS ARM64 Python 3.11.14 environment with nnU-Net 2.8.1 and Torch 2.6.0, without modifying the existing SimNIBS or prototype environments. The initial real-inference attempt loaded the model but failed when sandbox restrictions blocked a multiprocessing socket; its `failed` status is retained. A retry with the required local-process permission completed actual single-case GU011 inference on CPU. Model loading took **2.06095 seconds**; preprocessing, prediction, resampling/export took **561.18361 seconds**. Four OpenMP threads were requested; a single preprocessing/export worker, fold 0, tile step 0.5, compilation disabled, and **TTA disabled** were used. These measurements are not CUDA timings, pure neural-network kernel timings, CHARM pipeline timings, or a hardware comparison.

The new CPU prediction has case macro-Dice **0.8100739933356259** against the supplied GU011 reference; per-class Dice is [0.96520058, 0.80441546, 0.73024849, 0.74860841, 0.80189704]. This differs slightly from the original TTA-enabled validation prediction (case macro-Dice 0.81028333). It is reuse of fixed weights under a different inference setting, not a new training result or an updated ten-case cohort score. The recorded cohort mean remains 0.87155207. Source MRI/reference and final checkpoint SHA-256 values were checked unchanged after the run.

Thirteen new synthetic behavior tests and eighteen existing preparation tests pass (31 total). Notebook code cells compile, embedded sources match the builder, and no stored notebook outputs or patient images are included in Git. Generated comparison images were visually inspected. The in-app browser rejected the local HTML URL under its URL policy, so HTML was checked as a self-contained artifact with an embedded image; an actual browser screenshot of the HTML is not claimed. No workaround was attempted. **Live Colab GPU execution and the final presentation rehearsal remain unverified.**

Outside-Git deliverables at `training-runs/e1-demo/`: `E1_Demo.ipynb`, `E1_Demo_Tools.zip` (reviewed code/notebook/lock/trainer, no images or weights), `presentation_recorded/report.html`, `gu011_cpu_live_002/presentation/report.html`, `model_inspection.json`, `demo_verification.json`, and `environment-macos.txt`. The source and experiment limitations remain. Keep the original `E1_L4_001` experiment folder together for team handoff; optional five-epoch GPU pilot folders are separate experiments, and this model has only fold 0. No external sharing, commit, push, additional training, CHARM comparison, or mesh generation was performed.

### Approved 3D presentation extension

After running the initial notebook, the user requested an interactive 3D demonstration and approved display-surface extraction before any SimNIBS adaptation. Added [surface geometry](../../tools/e1_training/surface_view.py) and [viewer controls](../../tools/e1_training/surface_controls.js) to the existing report pipeline. The standalone notebook embeds both helpers and installs scikit-image 0.26.0 / Plotly 7.1.0. Recorded-result mode still needs no Colab GPU, model inference or retraining. Both recorded and new-inference reports retain the original slice comparison and full-volume metrics beneath the new view.

Each supplied tissue mask is converted into approximate triangle display surfaces with marching cubes, padded to close image-boundary surfaces, and transformed by the numerical source affine. Geometry is bounded to 360,000 triangles, with coarser sampling if needed; small tissues are retried at full resolution rather than silently dropped when coarse extraction fails. Original volumes and metrics are unchanged. No smoothing, tissue relabeling, tetrahedral FEM volume meshing, conductivity assignment, or physical-scale validation is claimed. Controls provide rotation/zoom, per-tissue visibility and opacity, brain/head/all presets and camera reset. Plotly JavaScript and geometry are bundled in the generated HTML without external script assets.

The real recorded GU011 prediction produces all five labels, **348,104 display triangles / 166,558 vertices**, using a 3-voxel extraction step. The HTML is approximately 14.07 MB. Case macro-Dice remains exactly 0.8102833287676656. A static gray-matter geometry preview was generated and visually inspected; it is not a screenshot of interactive browser rendering. Six added checks cover affine placement, closed boundary surfaces, small-tissue retention, complexity rejection, offline HTML and JavaScript control events. The complete suite now has 37 passing tests. Event tests execute the real control script in Node with a small document/Plotly stand-in; they do not establish browser/WebGL/Colab behavior. The previously observed in-app local-file URL policy remains respected; no alternative browser route or serving workaround was attempted. Actual interactive browser/Colab rehearsal remains pending.

Updated outside-Git artifacts under `training-runs/e1-demo/` relative to `/Users/merttomekce/Documents/TMS/`: `E1_Demo_3D.ipynb` (also copied to the canonical `E1_Demo.ipynb`), `E1_Demo_3D_Tools.zip` (also updates the previous tools ZIP), `presentation_3d/report.html`, its `report.json`/slice PNG, and `gu011_3d_001/surface_preview.png`. The notebook is source-only and includes no stored patient outputs. Users must load the new notebook and rerun its environment cell because old copies retain their embedded code; existing Drive model/data paths stay unchanged. This is a presentation surface view, not a SimNIBS-ready `.msh` head model.

## Overnight preparation

The user plans to leave the Mac awake overnight and asked what remains before leaving a 100-epoch run. Source inspection confirmed per-epoch checkpoints and durable Drive logs, but no default automatic runtime release. Added the optional [completion cell](../../tools/e1_training/overnight_finish_cell.py) for insertion after section 7's training call before launch. It checks a nonempty final checkpoint and readable ten-case full-volume validation summary, writes a completion/release-request marker, then calls Colab's official `runtime.unassign()`. Tests verify that disabled training, missing checkpoints, malformed JSON, and incomplete case lists do not trigger release. Eighteen preparation checks pass. Actual Colab release and unattended execution have not been tested; this add-on was not injected into any active user runtime.

The [usage guide](../../tools/e1_training/README.md) records local idle-sleep prevention, initial checkpoint confirmation, resume semantics, and the general Colab runtime limit. The 11.38-hour T4 epoch-loop forecast leaves little room below a general 12-hour runtime limit, especially in an existing session; setup/checkpoints/final validation are extra. Keeping a browser awake does not guarantee backend lifetime. An error or release-API failure can still leave an allocated runtime; no automatic failure-recovery claim is made. Original notebook defaults remain training-disabled, and no 100-epoch run has been launched here.

### Native E1 desktop display — 2026-11-03

After the user requested pushing the three existing local commits, `main` was pushed through `ab89d23`; the remote update succeeded. The user also approved continuing the 3D integration. The [MRI Workbench](../../tools/mri_prototype/README.md) now opens paired MRI/E1 NIfTI predictions through **Open E1 segmentation…** and reuses the reviewed display-surface extractor in its existing native VTK scene. This extension does not execute the network or require a `.msh` file. Existing CHARM and SimNIBS reopening remain separate workflows. At this implementation stage the new desktop code remained local for review. The user subsequently reported testing the 3D viewer successfully and explicitly requested committing and pushing it. No detailed manual control checklist was supplied; automated/native checks below remain the bounded technical evidence.

E1 tissue IDs/names/colors and brain/head presets are explicit and separate from SimNIBS IDs. Prediction source shape/affine must match the MRI after unit normalization; shifted grids, noninteger/unsupported IDs and empty predictions fail. Overlay resampling uses nearest neighbor, while 3D surfaces retain the original prediction affine. Canceling a picker preserves the scene; failed replacements clear stale model state. All import/extraction work uses the existing background worker.

Original E1 MRI units remain unknown. A default-off **E1: assume mm** checkbox permits only an explicit, display-scoped use of the handoff assumption; metadata, status and 3D summary retain the caveat. General MRI/SimNIBS import remains strict, known units are normalized normally, and original headers are not rewritten. This does not establish physical-scale or anatomical accuracy.

Nine new synthetic E1 checks were observed failing because import/UI support was absent, then passed after implementation. An additional prediction-only unit-provenance check was observed failing, then passed after adding explicit model state. A source-switching regression also passed; the full MRI suite passed **29 checks**. E1 tools passed **37 checks**, and CHARM ran 20 checks with **19 passed / one native Windows check skipped**. The isolated MRI environment added scikit-image 0.26.0; its NumPy 2.5 dependency emits marching-cubes deprecation warnings, not a failed check.

An actual macOS Qt/VTK native run used the original GU011 MRI and recorded prediction, explicitly opting into assumed mm. It displayed all five tissues with **348,104 triangles**. Native assertions passed for actor/mesh bounds, mouse rotation, visibility/opacity, linked MRI-plane geometry/positions and reopening in an existing renderer. Both screenshots were visually inspected. Source MRI/prediction SHA-256 values were identical before/after. Evidence remains outside Git in `training-runs/e1-desktop-view/` relative to the parent workspace: `verification.json`, `source-hashes-before.json` and `native/model-{3d,planes}.png`. No new inference, training, scores, FEM meshing or anatomical acceptance is claimed; native Windows behavior remains unverified.

### Repository handoff — 2026-11-03

The user requested committing the used tools in a separate directory. Training/audit helpers, clean standalone notebooks, custom trainer, dependency versions, demo/report/surface code and synthetic checks are grouped under `tools/e1_training/`. The [handoff guide](../../tools/e1_training/HANDOFF.md) explains trainer registration, the full Drive model folder, the original checkpoint checksum, label IDs and validation limits. MRI volumes, model weights, archives and generated MRI reports remain outside Git. The root ignore rules now also exclude checkpoint files and macOS Finder metadata. Existing CHARM thread-limit changes are kept in a separate commit. No push was requested.

After regenerating the training notebook, the full E1 suite passed 37 tests; the CHARM suite ran 20 tests with 19 passing and its native Windows-only check skipped. All 18 downstream MRI Workbench checks also passed. Both notebooks have empty outputs and execution counts, embedded helper parity is covered by the suite, and no scan/weight/image artifact is included in the commit set. This packaging task does not rerun training or establish live browser/Colab behavior.

[Experiment register](index.md) · [Current state](../current.md)
