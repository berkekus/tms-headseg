# Experiment Register

[Project map](../index.md) · [Current state](../current.md)

Concurrent records retain their original IDs: the two EXP-002 notes describe distinct IXI and Ernie runs; the EXP-003 notes describe the same E1 model, with team-summary and local preparation/demo evidence respectively. Use the linked note title to distinguish them.

- [EXP-003: E1 Preliminary nnU-Net, 100 Epochs](e1-multiaxial-100ep.md) — EXP-003 — run_validation_only. Validation mean Dice 0.872 (10 subjects, fixed split verified); preliminary, test set unused.
- [EXP-002: charm Pilot on IXI Subjects](charm-ixi-pilot.md) — EXP-002 — partially_run. One of three subjects completed (≈66 min, SimNIBS 4.6.0, labels visually plausible); two pending.
- [EXP-001: Ernie T1 Baseline](ernie-baseline.md) — EXP-001 — not_run. A ready-to-follow baseline protocol; no run or measured result is claimed.
- [EXP-002: Ernie OpenBLAS Thread-Limit Retry](ernie-thread-limits.md) — EXP-002 — completed execution. November 2 T1-plus-T2 run finished in 40:17 with new mesh, labels, and report; anatomical quality remains unreviewed. Earlier stopped attempts are preserved.
- [EXP-003: E1 MultiAxial Training Preparation](e1-preparation.md) — EXP-003 — preliminary experiment execution completed. The L4 100-epoch model resumed from checkpoints and completed fixed ten-case full-volume validation: mean Dice 0.87155 against provisional labels; final resumed invocation 237.4 minutes. T4/A100 pilots and earlier failures retained. Validation JSON arithmetic and fixed split checked; CSF mean Dice 0.7950 is lowest, GU011 case macro-Dice 0.8103 is lowest. GU011 prediction grid/counts checked and limited overlays inspected; reference-relative CSF/gray-matter volume deficits recorded. Broader anatomical review, held-out test evaluation and E1 acceptance remain pending; the final checkpoint is now independently loaded and used for real GU011 CPU inference, and a presentation notebook/offline report now includes bounded 3D display surfaces and tissue controls (37 tests pass; browser/Colab rehearsal pending); runtime release was requested but not verified.
