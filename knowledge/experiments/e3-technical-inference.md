---
type: Experiment
title: E3 Technical Team Inference
description: Downloaded checkpoint audit and technical-only implementation; native rehearsal stopped at the user's request.
status: in_progress
experiment_state: native_verification_pending_user_stopped_test
---

# E3 Technical Team Inference

## Download and implementation — 2026-11-19

The user supplied Downloads/E3_Dataset003_001 and requested E3 only in Technical Team, with Physician staying on E2. The main `nnUNetTrainer_E3Preliminary__nnUNetPlans__3d_fullres` checkpoint passed restricted loading: epoch 100, finite weights, six output heads, matching plans/dataset. SHA-256: `118078fd6b1265bc9846a0d81cb6c4353192d4316fa64abd4aac54218d9381da`. The separate E3Smoke checkpoint is not used. Training-only ignore 6 is not a seventh output. All sixteen validation predictions are present; fixed subject IDs and summary arithmetic reproduce Dice 0.9069063477804425. Independent anatomy/face accuracy remains unestablished.

Branch `feat/e3-technical-inference` adds explicit E3 CLI/report provenance, shared E2 RAS/head-crop/restore geometry and guarded standard-architecture loading without importing downloaded trainer code. Physician has no E3 selector; saving E3 as physician setup is rejected, and E1/E2 saves exclude the E3 path. Ignored local settings add the E3 path but retain E2 selection. The actual account/workstation database was not modified.

114 GUI/process/workspace tests and 28 inference/report tests passed, with new regressions first failing on old code. The real E2 checkpoint also restored with the shared initializer. These checks do not establish successful native E3 inference.

## Native test stopped; no readiness claim

The separate native E3 GU011 test reached tile 0/18 and stopped making visible progress. A read-only process sample showed Apple libBLAS frames; the root cause was not established. At the user's request, only the owned E3 QA launcher/process group was terminated, and no owned processes remained. Its desktop record is cancelled; incomplete child status is not success. **Do not resume testing without further user direction.**

The user's concurrent Physician E2/Ernie CPU run was left intact. It had 27 tiles rather than the earlier GU011 rehearsal's eighteen. Intervals at tiles 17–19 were 59/85/116 seconds; after stopping E3, later intervals returned to roughly 4–8 seconds. Concurrent workload is a plausible contributor, not a proven sole cause. E2 subsequently completed 27/27 in 7:23 plus export/report work; its desktop record reports completion. The remaining-time estimate included the slow intervals.

Evidence is outside Git in `training-runs/e3-technical-20261119-tnyz9ln8/`: artifact audit, settings before/after, native sample, cancelled desktop record and native-test-disposition.json. No native E3 pass or automatic 3D opening is claimed. Existing user work was not closed/restarted. No commit or push was requested.
