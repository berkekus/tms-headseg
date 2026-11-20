# E3 in Technical Team only

## Agreed design

The user requested an E3 option for Technical Team while keeping Physician on E2, then supplied the complete `E3_Dataset003_001` download. Reuse the existing local inference runtime and E2 geometry pipeline. Do not change weights, training data, physician configuration, existing results or model defaults. E3 is an explicitly named technical experiment, not an alias for E2.

The downloaded main checkpoint has trainer `nnUNetTrainer_E3Preliminary`, epoch 100, six output heads and dataset labels 0–5 plus training-only `ignore: 6`. Its plans/dataset agree with the checkpoint and all weights are finite. SHA-256: `118078fd6b1265bc9846a0d81cb6c4353192d4316fa64abd4aac54218d9381da`. Reject the separate five-epoch smoke model.

## Implementation and verification

- [x] Inspect downloaded metadata, main checkpoint and existing inference/role boundaries.
- [x] Extend `tools/e1_training/demo.py` and its tests: explicit E3 experiment, exact ignore-label metadata, main trainer/100-epoch guards, six output heads, same reversible RAS/head-crop/restore path as E2, E3 report provenance and the same fixed sixteen validation IDs. Use restricted checkpoint loading and strict state-dict loading; never import downloaded trainer code.
- [x] Extend `inference_runner.py`, `inference_panel.py`, `prototype.py` and `check_inference.py`: explicit E3 CLI argument, known-mm geometry checks, independent per-model paths and E3 only for Technical Team/standalone technical checks. Reject E3 when saving a Physician setup and exclude its path from saved Physician settings. Keep the ignored local selection E2 while adding the E3 model path.
- [x] Add failing regression tests before changing each behavior: E3 selection/provenance/geometry, E1/E2 preservation, Physician has no E3 selector and cannot receive a saved E3 model, E3 report uses the sixteen-case cohort and invalid labels/checkpoints are rejected.
- [ ] Run relevant GUI/demo tests, then a fresh native GU011 E3 CPU inference through `check_inference.py --experiment E3`. Require completed child/desktop status, correctly attributed E3 report, original MRI grid, labels 0–5, unchanged source/weight hashes and automatic 3D opening. Recheck E2 loading/physician setup.
- [ ] Update usage/evidence notes, restart the app without interrupting active user work, and leave commit/push to a later explicit request.

The earlier E2 rehearsal is an operational baseline, not evidence that E3 is more accurate. A successful E3 rehearsal likewise establishes local execution only. Patient-specific functional targeting and clinical acceptance remain outside this change.

## User stop — 2026-11-19

114 GUI and 28 inference/report tests passed; the real E2 checkpoint still loads. The native E3 run stalled at its first tile and was terminated at the user’s explicit request. Native E3 success and automatic 3D opening remain unverified. No new test or app restart is authorized until the user resumes. See `knowledge/experiments/e3-technical-inference.md`.
