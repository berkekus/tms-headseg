---
type: Experiment
title: 'EXP-006: Surfaces from Fresh charm 4.6 Labels'
description: The K3 surface pipeline on the labels from EXP-001; finds that open airways enter the head surface.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-03T12:30:00+03:00'
experiment_id: EXP-006
experiment_state: running
sources:
- id: exp001
  resource: ernie-baseline.md
  title: EXP-001 fresh charm reconstruction
- id: code
  resource: ../../tools/headmodel/README.md
  title: tools/headmodel
---

# EXP-006: Surfaces from Fresh charm 4.6 Labels

Experiment state: **running**. Attempt 1 is complete and found a defect; a fix and attempt 2 follow.

## Question

Does the K3 pipeline give correct head and brain surfaces from labels made by current SimNIBS, as opposed to the older supplied example in [EXP-005](ernie-surface-export.md)?

## Inputs

`m2m_exp001_ernie_t1/T1.nii.gz` and `final_tissues.nii.gz` from [EXP-001](ernie-baseline.md), mapped with the charm mapping proposed in EXP-002 (not accepted). Reference surfaces are the same run's mesh: tag 1005 for skin, tags 1001 and 1002 for the brain. Same machine and software as EXP-005.

## Attempt 1: commit `783430d`

`build_model.py`, then `verify_model.py` and `compare_to_mesh.py`, as in EXP-005.

| Measure | Head | Brain |
| --- | --- | --- |
| Closed surface; verification | Yes; passed | Yes; passed |
| Distance to exported label boundary: mean / p95 / max | 0.197 / 0.472 / 1.000 mm | 0.238 / 0.557 / 1.000 mm |
| Model to SimNIBS mesh: mean / p95 / max | **6.394 / 44.525 / 74.984 mm** | 0.189 / 0.356 / 1.840 mm |
| SimNIBS mesh to model: mean / p95 / max | 0.130 / 0.272 / 1.124 mm | 1.738 / 6.783 / 17.712 mm |

Stage times: read 0.28 s, cleanup 1.94 s, surfaces 1.76 s, export 0.50 s. Cleanup changed no tissue volume by more than 0.29%.

### Defect found

Every point of charm's skin lies close to our head surface, but 20.9% of our head surface lies more than 2 mm from charm's skin:

- None of those points is below charm's skin. Both surfaces span the same superior-inferior range, so the neck is not the cause.
- 99.3% of them are inside charm's skin surface. That test is approximate, because charm's tag 1005 surface is open where the volume is cut.
- They lie between z = −117 and +31 mm, median −34 mm, where the nasal cavity, pharynx, and upper airway are.

Reading: in these labels the airways connect to outside air through the nose or mouth. Hole filling only closes fully enclosed cavities, so the "external" head surface also traced the airway walls. In the supplied older labels those cavities were enclosed, which is why EXP-005 did not show this. The brain surface is unaffected.

The location argument identifies the region, not each structure; no person has inspected these surfaces yet.

## Related notes

[EXP-001](ernie-baseline.md) · [EXP-005](ernie-surface-export.md) · [Labels and facial coverage](../concepts/labels-and-face.md)
