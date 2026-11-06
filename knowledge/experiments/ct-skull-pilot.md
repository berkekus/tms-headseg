---
type: Experiment
title: 'EXP-010: CT Skull Reference Pilot (SynthRAD2023, Three Cases)'
description: E2 and charm skull scored against CT bone on three D15 brain cases; equal in the calvaria (Dice 0.813–0.834), both 11–27% thinner than CT.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-06T22:00:00+03:00'
experiment_id: EXP-010
experiment_state: completed_pilot
sources:
- id: d15
  resource: https://zenodo.org/records/7260705
  title: SynthRAD2023 Grand Challenge training data (CC BY-NC 4.0)
- id: tool
  resource: ../../tools/ct_eval/README.md
  title: tools/ct_eval, CT skull scoring
- id: e2
  resource: e2-preliminary-training.md
  title: EXP-008, the E2 model scored here
---

# EXP-010: CT Skull Reference Pilot (SynthRAD2023, Three Cases)

Experiment state: **pilot completed** (2026-11-06, K1 desktop). Three cases only; this is not a result. The CT data is used for evaluation only.

## Question

How close are E2's and charm's skulls to bone seen on CT, a reference that no MR segmenter produced?

## Why it matters

Until now E2 was scored against charm labels, the same labels it was trained on. That cannot reveal charm's own errors. CT shows bone directly, so it scores E2 and charm on equal terms (plan F8).

## Method

1. D15 (SynthRAD2023 Task 1, brain): 180 cases from three centers, 60 each. MR and CT come registered on one 1 mm grid.[^d15] One case per center was extracted: 1BA001, 1BB002 and 1BC001.
2. Alignment check: the CT bone outline was drawn over T1 slices. In all three cases it lay on the dark skull band. 1BB002's MR is contrast-enhanced, and 1BC001 has a defacing block.
3. Headers: only the qform is set (sform code 0). E2 and the scoring read the qform. charm refuses files whose qform and sform differ, so charm got copies with sform = qform; the voxels and the affine are unchanged.
4. E2 `results_e2_L4_20261105` via `predict_e2.py` (head crop on). charm 4.6.0, T1 only, via `run_charm_batch.py` with a three-row assignment (53–60 min per case).
5. Scoring: `tools/ct_eval/ct_skull.py`.[^tool]
   - **Reference:** CT above 300 HU, 1-voxel gaps closed, parts under 1 mL dropped.
   - **Signal only:** voxels where the MR has signal.
   - **Main region:** the top 70 mm of the skull (calvaria).
   - **Metrics:** Dice and the mean symmetric surface distance (ASSD).

Data: `tms-data\ct_eval_D15_pilot_20261106` (outside Git); scores in `scores\`.

## Results

Calvaria, 300 HU:

| Case | E2 Dice | charm Dice | E2 ASSD | charm ASSD | Volume E2 / charm / CT |
| --- | --- | --- | --- | --- | --- |
| 1BA001 | 0.813 | 0.816 | 1.21 mm | 1.21 mm | 156 / 159 / 215 mL |
| 1BB002 (contrast) | 0.828 | 0.830 | 1.16 mm | 1.12 mm | 225 / 210 / 254 mL |
| 1BC001 | 0.834 | 0.830 | 1.03 mm | 1.02 mm | 199 / 177 / 233 mL |

In the whole field, which adds the skull base, face and vertebrae, charm is slightly ahead: Dice 0.739–0.766 against 0.711–0.759 for E2. For E2, moving the threshold between 200 and 400 HU changes the calvaria Dice by up to 0.06 and reorders the cases, so comparisons must use one threshold.

## Interpretation

- In the calvaria, E2 matches charm against an independent reference: Dice differences are 0.004 or less.
- Both draw the skull thinner than CT, by 11–27% (E2) and 17–26% (charm). E2 loses bone at both the inner and outer edges. E2 probably inherits this from charm labels. Skull thickness shapes the TMS electric field, so a CT-informed skull label is a measurable way to improve on charm.
- Limits:
  - There are only three cases.
  - 1BA001 has an intracranial calcification over 1 mL that the reference counts as bone.
  - The CT threshold is a modelling choice, not ground truth.

## Proposed next steps (not decided)

1. Score E2 on all 180 D15 cases (a few hours). Run charm on a 20–30-case subset (about one day).
2. If the thinning holds, plan a "CT-corrected skull label" experiment. Before any CT enters training, the D15 cases must be split into test-only and training cases.
3. D14 comes second: its MR–CT alignment is unverified and its MRs are contrast-enhanced.

Open team decisions:
- Which D15 cases are locked for testing?
- Who runs the charm subset, and on which machine?
- Should CT-corrected training come after E3 or alongside it?

[^d15]: [SynthRAD2023, Zenodo](https://zenodo.org/records/7260705)
[^tool]: [tools/ct_eval](../../tools/ct_eval/README.md)
