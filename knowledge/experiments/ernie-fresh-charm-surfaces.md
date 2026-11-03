---
type: Experiment
title: 'EXP-006: Surfaces from Fresh charm 4.6 Labels'
description: The K3 surface pipeline on the labels from EXP-001; found open airways in the head surface, and measured the fix.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-03T12:30:00+03:00'
experiment_id: EXP-006
experiment_state: completed
sources:
- id: exp001
  resource: ernie-baseline.md
  title: EXP-001 fresh charm reconstruction
- id: code
  resource: ../../tools/headmodel/README.md
  title: tools/headmodel
---

# EXP-006: Surfaces from Fresh charm 4.6 Labels

Experiment state: **completed**, two attempts on 2026-11-03. Attempt 1 found a defect; attempt 2 measured the fix.

## Question

Does the K3 pipeline give correct head and brain surfaces from labels made by current SimNIBS, as opposed to the older supplied example in [EXP-005](ernie-surface-export.md)?

## Inputs

`m2m_exp001_ernie_t1/T1.nii.gz` and `final_tissues.nii.gz` from [EXP-001](ernie-baseline.md), mapped with the charm mapping proposed in EXP-002 (not accepted). Reference surfaces are the same run's mesh: tag 1005 for skin, tags 1001 and 1002 for the brain. Same machine and software as EXP-005.

## Attempt 1: commit `bf7b3a7`

Commit IDs in this note follow the published history. Before the 2026-11-03 history rewrite they were `783430d` (attempt 1) and `24703c5` (attempt 2); each pair has an identical file tree.

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

## Choosing a fix

Four envelope strategies were measured once on these labels in a throwaway script. "Far" means more than 2 mm from charm's skin; the right-hand column checks that the outer skin is unchanged.

| Strategy | Model to mesh: mean, share far | Mesh to model: mean / p95 / max |
| --- | --- | --- |
| Hole filling only (attempt 1) | 6.394 mm, 20.90% | 0.199 / 0.332 / 1.16 mm |
| Seal openings, 5 mm | 0.626 mm, 2.47% | 0.200 / 0.333 / 2.67 mm |
| Seal openings, 8 mm | 0.294 mm, 1.42% | 0.199 / 0.332 / 1.16 mm |
| Fill each axial slice | 0.354 mm, 1.53% | 0.211 / 0.350 / 4.96 mm |
| 5 mm seal plus axial filling | 0.263 mm, 0.86% | 0.211 / 0.351 / 4.96 mm |

The 8 mm seal removed most airway surface and left the outer skin exactly as before. Axial filling changed the skin, so it was not used. The seal is a closing that closes openings narrower than about 16 mm; air more than 8 mm inside the sealed head is filled, and air nearer the outside is kept. The labels themselves are not changed.

## Attempt 2: commit `83897df`

Same inputs and commands.

| Measure | Head | Brain |
| --- | --- | --- |
| Triangles | 439,384 (was 547,618) | 594,018, unchanged |
| Closed surface; verification | Yes; passed | Yes; passed |
| Distance to exported label boundary: mean / p95 / max | 0.191 / 0.459 / 0.949 mm | 0.238 / 0.557 / 1.000 mm |
| Model to SimNIBS mesh: mean / p95 / max | **0.293 / 0.380 / 11.599 mm** | 0.189 / 0.356 / 1.840 mm |
| SimNIBS mesh to model: mean / p95 / max | 0.130 / 0.272 / 1.124 mm | 1.738 / 6.783 / 17.712 mm |

The surfaces stage took 4.24 s, up from 1.76 s, because of the seal; the four stages totalled about 6.9 s. No point of charm's skin lies more than 2 mm from the sealed surface.

The remaining 1.42% of head points farther than 2 mm (median 4.1 mm, maximum 11.6 mm) fall in four clusters: both ear canals, the front of the mouth and nose, and the airway opening at the bottom of the neck. These are the mouths of openings kept on purpose. The cluster labels come from coordinates, not from inspection.

## Conclusion

On one subject, the sealed envelope gives an external head surface that matches SimNIBS 4.6's skin within about 0.3 mm on average, with the brain unchanged. The 8 mm value is provisional and was chosen on this subject. It still needs checking on more subjects, on model predictions, and on scans with open mouths.

## Related notes

[EXP-001](ernie-baseline.md) · [EXP-005](ernie-surface-export.md) · [Labels and facial coverage](../concepts/labels-and-face.md)
