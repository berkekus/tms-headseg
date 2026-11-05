---
type: Experiment
title: K4 E2 CPU Inference Timing Baseline
description: Three fresh-process runs of one public MRI with fixed local E2 settings.
status: draft
experiment_id: K4-TIME-001
experiment_state: completed
sources:
- id: scope
  resource: ../../tools/qa/README.md
  title: Repeated real E2 CPU timing entry point
---

# K4 E2 CPU Inference Timing Baseline

## Question and protocol

On 2026-11-06, establish a
central, repeatable timing record for the available E2 model on the public Ernie
T1, using three sequential fresh desktop/inference processes. This is a local
one-case baseline, not an E1/E2 speed comparison, clinical validation or GPU test.
The existing native helper verifies new inference, matching source hashes,
completed records and automatic 3D opening on every repeat. No held-out subject
or reference labels are used. Mirroring is off; inference uses four math threads.

Hardware: Intel Core i7-13620H, 10 cores/16 logical processors, 16,870,064,128
bytes physical RAM, Windows 11. Runtime: Python 3.13.6, torch 2.6.0+cpu,
nnunetv2 2.8.1. CPU only. Each process reloads the model; OS file cache and other
desktop load are uncontrolled. No cold-cache or persistent warm-model claim.
Git base is `5373e7d` with local UI/QA changes; exact native helper SHA-256,
hardware inventory and paths are captured in the run's protocol.json.

Model/input fingerprints are retained in each verification record and checked
across repeats. The previously verified E2 checkpoint is
`388d2fda8b58bcfedbacdc856674f9329141cbf83d899470f3d20e1faacbc043`;
public Ernie T1 is `27e33241fc7c44b42dd63d613e81cadaefdfad271fd7e844fea71d0db75942ad`.

## Boundaries and reproduction

- Model preparation: predictor/model initialization and E2 input geometry preparation.
- Prediction: prediction, file export and restoration to the source grid.
- Desktop total: request through report and automatic 3D opening, including helper
  event processing/screenshots. Process startup is separately retained; human
  file selection and application startup are outside this total.
- The desktop total includes the first two intervals; do not add them again.
- Display-only smoothing/rebuilding is a separate operation, not model inference.

Reusable entry point: `tools/qa/benchmark_inference.py --desktop-python <desktop-env-python>
--python <inference-env-python> --model <trusted-E2-folder> --mri <public-T1>
--output <fresh-outside-Git-folder> --repeats 3`.
The script reuses the existing reviewed inference route without changing model
code, weights or source MRI. It retains logs/predictions, every failed attempt,
per-repeat CSV, a protocol and a successful-only median with failure counts.

## Execution and results

Completed output: `C:/Projects/tms-demo/k4-benchmark-20261106/` outside Git. Initial
restricted execution could not create that folder and ran no inference; execution
then started with normal host access. Three new inference runs completed, 3/3
PASS, with automatic 3D opening. All source hashes matched across runs and were
rechecked after completion; medians were independently recomputed from the CSV.

| Run | Model/preparation (s) | Prediction/restore (s) | Desktop total (s) |
| --- | ---: | ---: | ---: |
| 1 | 9.598 | 129.814 | 186.532 |
| 2 | 3.882 | 128.628 | 158.623 |
| 3 | 3.914 | 128.238 | 158.602 |
| Median | 3.914 | 128.628 | 158.623 |

The first run took longer in preparation/desktop work; uncontrolled cache/load
means the cause is not isolated. No performance gate is approved by this
measurement. This completes the available-model CPU timing baseline; future
models/hardware need new records. Readable summary and verified CSV copy:
`outputs/qa/k4-timing-20261106/`; the full evidence directory is canonical.
