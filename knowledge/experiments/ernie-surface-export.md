---
type: Experiment
title: 'EXP-005: Surfaces and Export from Supplied Ernie Labels'
description: First real-data run of cleanup, surfaces, export, and verification, measured against the supplied SimNIBS mesh.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-02T23:30:00+03:00'
experiment_id: EXP-005
experiment_state: completed
sources:
- id: data
  resource: https://simnibs.github.io/simnibs/build/html/dataset.html
  title: Official SimNIBS example dataset
- id: code
  resource: ../../tools/headmodel/README.md
  title: tools/headmodel
---

# EXP-005: Surfaces and Export from Supplied Ernie Labels

Experiment state: **completed**, one subject, one attempt series. Run on 2026-11-02 on the K3 Windows machine.

## Question

Do the K3 cleanup, surface, and export stages produce closed surfaces at the right place, scale, and side on a real non-RAS head, and how long do they take?

## What this does not test

The labels are the ones supplied with the example, not a model prediction and not a new CHARM reconstruction. Agreement with the supplied mesh therefore shows world alignment and surface fidelity, not anatomical accuracy. [EXP-001](ernie-baseline.md) remains a separate experiment. The sample README states this Ernie model used FreeSurfer-assisted surfaces.

## Inputs

Public `simnibs4_examples.zip` (CC BY-NC 4.0), SHA-256 `a7e729db1306657f5c4f9a5dee493e22eb5a4c6fb2fd62f8ec81dc0cca4196e6`, unpacked outside Git.

| File in `m2m_ernie/` | SHA-256 |
| --- | --- |
| `T1.nii.gz` | `bf53e74da73b0faa8d9e7bf8831365530b00de0479a9fe410a303f2127896e81` |
| `final_tissues.nii.gz` | `53efead2a2dc4b030e036a2ab85caf95be206dce0f021bd1b64ad77a39443b82` |
| `ernie.msh` | `847707671cc93db548948b46b715c4c67513e1cb7fbed289b6609963174e67cc` |

The T1 and labels share one grid: 256 × 256 × 208, 1 mm, PSR orientation, no shear, no qform/sform warning. Labels were translated with the charm mapping proposed in EXP-002, which is not accepted (Q-05).

## Environment

Windows 11, Intel Core i7-14700KF, 31.8 GB RAM. Python 3.13.1, NiBabel 5.4.2, NumPy 2.5.4, SciPy 1.18.1, scikit-image 0.26.0, meshio 5.3.5. These stages use the CPU only.

## Commands

```bash
python tools/headmodel/build_model.py "$ERNIE/m2m_ernie/T1.nii.gz" "$ERNIE/m2m_ernie/final_tissues.nii.gz" "$OUT" --label-scheme charm
python tools/headmodel/verify_model.py "$OUT"
python tools/headmodel/compare_to_mesh.py "$OUT" "$ERNIE/m2m_ernie/ernie.msh"
```

## Measured results

| Measure | Head | Brain |
| --- | --- | --- |
| Triangles | 532,336 | 579,908 |
| Closed surface | Yes | Yes |
| Enclosed volume | 4,880 mL | 1,329 mL |
| STL size | 26.6 MB | 29.0 MB |
| Distance to exported label boundary: mean / p95 / max | 0.197 / 0.467 / 0.993 mm | 0.236 / 0.552 / 1.045 mm |
| Model to SimNIBS mesh: mean / p95 / max | 0.225 / 0.368 / 0.800 mm | 0.187 / 0.353 / 4.009 mm |
| SimNIBS mesh to model: mean / p95 / max | 0.746 / 6.732 / 19.949 mm | 1.743 / 5.865 / 17.187 mm |

The head reference is tag 1005; the brain reference is tags 1001 and 1002 together. Distances use points sampled on triangles, so they run slightly above true point-to-surface values. Verification passed with no warnings. The head did not touch any image edge. Cleanup changed 560 voxels, and no tissue volume moved more than 0.14%.

Median of three timed runs, in seconds: read 0.28, cleanup 1.96, surfaces 2.47, export 0.83, about 5.5 in total.

## Reading the large reverse distances

The mesh-to-model values are high by design, not from misalignment:

- **Head:** 6.5% of the tag 1005 points lie more than 2 mm from our surface, and 99.9% of those sit at least 2 voxels inside our solid envelope. They are internal air-cavity surfaces, which the envelope leaves out on purpose. The remaining points give a mean of 0.144 mm.
- **Brain:** tag 1001 is mostly the gray/white interface, which lies inside the single brain-union surface. Compared with tag 1002 alone the brain gave a mesh-to-model mean of 0.436 mm, but the forward maximum rose to 83 mm because white matter bordering CSF and the brainstem have no tag 1002 surface.

These explanations are measured for the head and reasoned for the brain.

## Smoothing

Model-to-mesh means on this one subject for 0, 5, 10, 20, 40, and 80 iterations were 0.269, 0.240, 0.232, 0.225, 0.221, 0.220 mm for the head, and 0.216, 0.191, 0.187, 0.187, 0.191, 0.203 mm for the brain. The default of 20 sits at the brain minimum. One subject does not validate this setting.

## Rerun after the envelope change

Commit `24703c5` seals narrow openings into the head envelope, after [EXP-006](ernie-fresh-charm-surfaces.md) found open airways in fresh SimNIBS 4.6 labels. The results above stay as attempt 1. Rerunning the same commands on these supplied labels gave:

| Measure | Head | Brain |
| --- | --- | --- |
| Triangles | 450,954 (was 532,336) | 579,908, unchanged |
| Distance to exported label boundary: mean / p95 / max | 0.193 / 0.460 / 0.957 mm | 0.236 / 0.552 / 1.045 mm |
| Model to SimNIBS mesh: mean / p95 / max | 0.235 / 0.375 / 6.132 mm | 0.187 / 0.353 / 4.009 mm |
| SimNIBS mesh to model: mean / p95 / max | 8.436 / 46.669 / 73.053 mm | 1.743 / 5.865 / 17.187 mm |

Verification passed. The reverse head distance rose because this older mesh's skin tag also covers airway and sinus walls: 29.5% of its skin points are more than 2 mm from the sealed surface, and every one of them lies at least 2 voxels inside the sealed envelope. The other points average 0.209 mm. In the fresh SimNIBS 4.6 mesh the same share is 0%, so the sealed envelope matches the current tool's outer-skin definition.

## Limits

One healthy subject. Face coverage was not assessed. No opening in an independent viewer has been recorded yet, and no human has reviewed these surfaces.

## Related notes

[Export proposal](../decisions/003-export-route-proposal.md) · [Coordinates](../concepts/coordinates.md) · [Labels](../concepts/labels-and-face.md) · [Current state](../current.md)
