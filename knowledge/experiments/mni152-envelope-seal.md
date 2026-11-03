---
type: Experiment
title: 'EXP-007: Envelope Seal on a Second Head (SimNIBS MNI152 Example)'
description: The 8 mm envelope seal from EXP-006 on a second head; it filled internal air and left the outer skin in place.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-03T18:00:00+03:00'
experiment_id: EXP-007
experiment_state: completed
sources:
- id: exp006
  resource: ernie-fresh-charm-surfaces.md
  title: EXP-006 airway defect and the 8 mm seal
- id: code
  resource: ../../tools/headmodel/README.md
  title: tools/headmodel
---

# EXP-007: Envelope Seal on a Second Head (SimNIBS MNI152 Example)

Experiment state: **completed**, one attempt on 2026-11-03 (K3).

## Question

[EXP-006](ernie-fresh-charm-surfaces.md) chose the 8 mm envelope seal on one subject. On a second head, does it still keep the airways out of the external head surface without moving the outer skin?

## Inputs

- The `m2m_MNI152` folder of the public SimNIBS 4 examples (data inventory D04). It is a head model built on the MNI152 template, an average of many brains, not one person.
- `T1.nii.gz`: SHA-256 `5807425aa5ac6ce1f0800cc139d109b864ec117b53d5007a87c373e883f4d033`. 182 × 238 × 282 voxels, 1 mm, LAS, no header warnings.
- `final_tissues.nii.gz`: SHA-256 `ab57953a016e92fb02870c558c791f55ded43b8185fcc7e503c1145b9a9ef000`. Charm labels present: 0, 1, 2, 3, 5, 6, 7, 8, 9, 10.
- Reference mesh `MNI152.msh`: SHA-256 `0f00843e7ec858b5bdb94904f25c57ffc811bf2a3546e73d577cec09fd5e0f35`. Skin is tag 1005; the brain is tags 1001 and 1002.
- The example's `charm_log.html` names development builds (`4.0b0`, `4.0b1`, `3.2.4.dev988+geb8eaf45.d20230928`). It was not made with the 4.6.0 used in EXP-001.
- Labels were mapped with the charm table in `tools/headmodel/labels.py`, including the 2026-11-03 change of blood to CSF. The rest of the table is proposed, not accepted (Q-05).

## Method

- Code: commit `55e15d4`. The `tools/headmodel` files are identical at `6468539`.
- Software: Python 3.13.1, nibabel 5.4.2, NumPy 2.5.4, SciPy 1.18.1, scikit-image 0.26.0, on the K3 Windows machine.
- Steps: `build_model.py --label-scheme charm` with default settings (seal 8 mm), then `verify_model.py` and `compare_to_mesh.py`, as in EXP-005 and EXP-006.
- Two throwaway scripts outside Git then rebuilt the head surface with seal 0 and seal 8 mm and measured it against charm's skin, the way EXP-006 did. "Far" means more than 2 mm.
- Output: `C:\Users\ahmet\tms-data\models\exp007_mni152_charm` (outside Git).

## Results

`build_model` took about 12 s (read 0.28 s, cleanup 1.68 s, surfaces 8.57 s, export 0.90 s) and wrote no warnings. Cleanup changed no tissue volume by more than 0.04%. The head touches only the inferior image edge.

| Measure | Head | Brain |
| --- | --- | --- |
| Triangles; closed; verification | 504,048; yes; passed | 646,296; yes; passed |
| Distance to exported label boundary: mean / p95 / max | 0.195 / 0.460 / 0.969 mm | 0.263 / 0.633 / 1.000 mm |
| Model to SimNIBS mesh: mean / p95 / max | 0.235 / 0.367 / 6.300 mm | 0.196 / 0.384 / 4.313 mm |
| SimNIBS mesh to model: mean / p95 / max | 9.836 / 49.465 / 73.946 mm | 1.309 / 5.107 / 18.216 mm |

Seal 0 against seal 8 mm, head surface only:

| Measure | Seal 0 | Seal 8 mm |
| --- | --- | --- |
| Triangles | 623,778 | 504,048 |
| Model to charm skin: mean, share far | 0.221 mm, 0.00% | 0.235 mm, 0.16% |
| Charm skin to model: mean / p95 / max, share far | 0.150 / 0.309 / 13.85 mm, 0.11% | 9.836 / 49.465 / 73.95 mm, 33.04% |

The large reverse distance with the seal comes from charm's skin surface itself.

- 33.0% of the skin's 64,161 vertices lie more than 2 mm from the sealed surface. All of them are inside the sealed envelope, and 99.6% lie within 2 mm of the unsealed surface. So they are walls of internal air that our unsealed surface also traced.
- They span z = −160 to +1 mm (median −61 mm) and y = −53 to +85 mm. The densest 20 mm cells sit near the midline in front of and below the brain, where the nasal cavity, paranasal sinuses, mouth, and pharynx are. These names come from coordinates, not from inspection.
- In this example the airways connect to the outside, as in the fresh Ernie labels of EXP-006. Unlike charm 4.6's Ernie skin, this mesh's skin tag also covers their walls. The supplied older Ernie mesh in [EXP-005](ernie-surface-export.md) does too.

The seal only added voxels to the envelope: 123.5 mL of internal air was filled and nothing was removed. 0.17% of the sealed surface's vertices are more than 2 mm from the unsealed surface (at most 6.1 mm). These are the patches spanning the openings. The rest of the outer skin did not move. The 0.16% of sealed-surface points far from charm's skin lie between z = −161 and −41 mm (median distance 2.8 mm). By coordinates, they fall in the same kinds of places as in EXP-006: the front of the nose and mouth, the airway opening at the bottom of the neck, and both sides at ear level.

The brain surface is unaffected by the seal. Its reverse distance (mean 1.3 mm, up to 18 mm) follows the EXP-006 pattern, where charm 4.6 builds its brain mesh from finer surfaces than our 1 mm labels; this example's builds were not checked for that.

## Conclusion

On a second head, the 8 mm seal behaved as on Ernie:

- Internal air reached through the nose or mouth was filled.
- The outer skin stayed in place, except for patches spanning openings.
- Our external surface lay within 0.24 mm of charm's skin on average.

Charm's skin surface is not a fixed reference: in this example and in the older Ernie mesh it includes airway and sinus walls, while in charm 4.6's Ernie it does not. Distances measured from charm's skin to our model are only meaningful when that mesh's skin is outer-only.

Limits:

- MNI152 is an averaged template, smoother than a single person.
- Its mouth is closed, and no model prediction or clinical scan was tested.
- The 8 mm value stays provisional.
- No person has inspected these surfaces.

## Related notes

[EXP-006](ernie-fresh-charm-surfaces.md) · [EXP-005](ernie-surface-export.md) · [Labels and facial coverage](../concepts/labels-and-face.md) · [Data inventory](../references/datasets.md)
