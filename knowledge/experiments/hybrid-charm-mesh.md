---
type: Experiment
title: 'EXP-009: E2 Labels Through charm Meshing (Hybrid), NC023'
description: E2 labels replaced charm's label image and `charm --mesh` built a SimNIBS head mesh in 11.2 min (charm alone 46 min); closer to the MultiAxial reference than charm's own mesh on one case.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-06T02:30:00+03:00'
experiment_id: EXP-009
experiment_state: completed_one_case
sources:
- id: e2
  resource: e2-preliminary-training.md
  title: EXP-008, the E2 model whose validation prediction was meshed
- id: charm-help
  resource: 'charm --help, SimNIBS 4.6.0, K1 desktop (2026-11-06)'
  title: charm step options
- id: charm-doc
  resource: https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html
  title: charm documentation (SimNIBS 4.6.0)
- id: bs-msh
  resource: https://mailman.drcmr.dk/pipermail/simnibs-discuss/2023-January/000456.html
  title: simnibs-discuss, Brainsight developer on charm import (January 2023)
- id: bs-targets
  resource: https://mailman.drcmr.dk/pipermail/simnibs-discuss/2023-February/000503.html
  title: simnibs-discuss, importing Brainsight targets (February 2023)
- id: bs-vendor
  resource: https://www.neurocaregroup.com/technology/brainsight-tms
  title: Brainsight TMS product page (distributor)
---

# EXP-009: E2 Labels Through charm Meshing (Hybrid), NC023

Experiment state: **completed on one validation case** (2026-11-06, K1 desktop). Not repeated on other cases; the test set was not used.

## Question

Can our segmentation replace charm's segmentation step while charm's own meshing still produces a SimNIBS head mesh, and what do the meshing step and its time add over the surfaces our own tools build?

## Why it matters

Brainsight reportedly creates a project from charm's output mesh: it splits the mesh surfaces into its reconstruction list and loads the T1 and the MNI transform. It also runs SimNIBS simulations itself and shows the result as overlays. Targets can be exchanged as text files, where coordinate conventions need care.[^bs-msh][^bs-targets][^bs-vendor] These are mailing-list and distributor statements, not official documentation; the hospital's Brainsight version and workflow are unverified. If they hold, a charm-shaped `m2m_<ID>` folder is a route into the device without thresholding by hand.

## charm stage times (observed)

From `charm_log.html` of earlier full runs (SimNIBS 4.6.0, T1 only, 8 threads, K1 desktop):

| Case | Total | Surfaces (TopoFit) | Prepare mesh | Mesh | Post-process mesh | Registration + segmentation (remainder) |
| --- | --- | --- | --- | --- | --- | --- |
| GU008 | 40.6 min | 6:18 | 2:13 | 0:47 | 15:02 | about 16 min |
| NC023 | 46.2 min | 6:22 | 2:21 | 0:44 | 14:18 | about 22 min |

The charm documentation states that SimNIBS 4.6 reconstructs cortical surfaces with an implementation of the TopoFit network.[^charm-doc] `charm --help` lists separate steps (`--initatlas`, `--segment`, `--surfaces`, `--mesh`) and says a label image edited by hand can be meshed again with `charm subID --mesh`.[^charm-help] `--mesh` reads `label_prep/tissue_labeling_upsampled.nii.gz` (0.5 mm; NC023 424×552×552, RAS, uint16, charm IDs).

## Method

1. Copied `charm_MA/m2m_NC023` (694 MB) to `tms-data/hybrid_NC023_20261106/m2m_NC023`; the original stays untouched.
2. Took the E2 validation prediction `fold_0/validation/NC023.nii.gz` from `E2_L4_001` (same grid as the copy's `T1.nii.gz`).
3. Mapped project IDs to charm IDs (skin→5 scalp, skull→7 compact bone, CSF→3, GM→2, WM→1) and moved the labels to the 0.5 mm grid by trilinear interpolation of each class mask and arg-max. The grid relation was exactly scale 0.5, offset −0.25 voxel. charm's file was saved as `charm_tissue_labeling_upsampled.nii.gz` next to the copy; volumes are in `conversion.json`. Script: one-off, outside Git.
4. Ran `charm NC023 --mesh` in the copy (default `settings.ini`, 8 threads).
5. Built surfaces from the same prediction with our tools only: `tools/headmodel/build_model.py` (T1 from `nnunet_mm`, output `tms-data/e2_model_NC023_20261106`).
6. Scored `final_tissues.nii.gz` (written by charm from each mesh) against the MultiAxial reference labels, after mapping charm IDs to project IDs.
7. Rendered the gray-matter (tag 1002) and skin (tag 1005) mesh surfaces, and our `brain.stl`/`head.stl`, from identical cameras.

## Results

| | charm alone | Hybrid (E2 + `charm --mesh`) | E2 + `headmodel` |
| --- | --- | --- | --- |
| Time | 46.2 min | about 1 min E2 + 11.2 min meshing | about 1 min E2 + 8 s surfaces |
| Output | Tetrahedral mesh, 161 MB | Tetrahedral mesh, 2.26 M tetrahedra, 89 MB | Two closed surfaces (head 473 k, brain 517 k triangles) |
| Meshing timings | see table above | prepare 2:13, mesh 0:32, post-process 7:47 | — |

Dice against the MultiAxial reference labels (labels written back from each mesh):

| | Skin | Skull | CSF | GM | WM |
| --- | --- | --- | --- | --- | --- |
| charm mesh | 0.671 | 0.741 | 0.694 | 0.825 | 0.890 |
| Hybrid mesh | 0.832 | 0.823 | 0.756 | 0.839 | 0.893 |

Hybrid against charm's mesh labels: skin 0.738, skull 0.849, CSF 0.854, GM 0.929, WM 0.956.

Visual comparison (K1 review of rendered images, NC023):

- **Hybrid vs charm:** brain surfaces look nearly the same; the hybrid gray matter has fewer triangles (204 k vs 284 k) and slightly softer gyri. On the skin, charm filled the defaced face region with a nose, eyes and lips from its atlas; the hybrid keeps the defacing cut. The real face is unknown, so the atlas face is invented anatomy. Part of charm's lower skin and skull Dice comes from this.
- **E2 + `headmodel` vs hybrid:** gyri are in the same places and slightly sharper in ours. Ours includes the brainstem and upper spinal cord, because our brain surface is the GM+WM envelope while the hybrid view shows only the GM tag. Ours has one thin spur near the left temporal pole, which looks like a small mislabeled structure. Our skin shows concentric terraces on the vertex: 1 mm voxel steps that the current smoothing leaves. The hybrid skin is smooth, because charm meshes at 0.5 mm and smooths the skin.

## Interpretation

For navigation, charm's mesh step adds mainly a smooth skin surface, at a cost of about 11 minutes. The tetrahedral mesh matters for E-field simulation, which Brainsight can run itself. Upsampling our labels to 0.5 mm with soft class interpolation before surface extraction, more skin smoothing and small-island removal could give a similar skin in seconds. That is a hypothesis, not a measurement. Such changes belong to `tools/headmodel` (K3). Separately, K3 added optional display smoothing to Workbench ([E2 handoff review](e2-handoff-review.md#slicer-style-surface-smoothing)); that changes the display only, not exported surfaces.

## Limits

- One case only, a defaced MultiAxial subject. Skin Dice includes the defacing difference.
- The copied folder still holds charm's own `toMNI/` transforms, `surfaces/` (TopoFit) and segmentation files. A pipeline that skips charm's segmentation must produce the MNI transform itself and run `charm --surfaces` (or an equivalent) separately.
- Our labels have five tissues. The hybrid mesh has no eyes, blood vessels, spongy bone or muscle. This should not affect navigation surfaces but changes E-field conductivities.
- The reference labels are semi-manual (automated first pass, then expert correction), not ground truth.
- Brainsight's import of a hybrid folder was not tested.

## Next

- Ask at the hospital: Brainsight version, whether a project is created from a SimNIBS/charm mesh, whether surfaces alone suffice, and which files it reads.
- Measure faster meshing settings (`threads`, `mmg_noinsert`, `smooth_steps`, `skin_care`, element sizes) against the default hybrid mesh: time, element count, surface distance.
- Try 0.5 mm soft upsampling and skin smoothing in our own surface export, and measure the skin against the hybrid.
- Repeat on more validation cases. Build the MNI transform without charm's segmentation step.

## Related notes

[EXP-008](e2-preliminary-training.md) · [E2 handoff review](e2-handoff-review.md) · [EXP-005](ernie-surface-export.md) · [Coordinates](../concepts/coordinates.md)

[^charm-help]: `charm --help` output, SimNIBS 4.6.0 on the K1 desktop, read 2026-11-06.
[^charm-doc]: [charm documentation](https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html), SimNIBS 4.6.0, read 2026-11-06.
[^bs-msh]: [simnibs-discuss, January 2023](https://mailman.drcmr.dk/pipermail/simnibs-discuss/2023-January/000456.html): the Brainsight developer on creating a project from charm's mesh and on the simulate workflow. Search summary; the full thread was not read.
[^bs-targets]: [simnibs-discuss, February 2023](https://mailman.drcmr.dk/pipermail/simnibs-discuss/2023-February/000503.html): importing Brainsight targets; coordinate convention issues. Search summary.
[^bs-vendor]: [Brainsight TMS product page](https://www.neurocaregroup.com/technology/brainsight-tms) (distributor): E-field modelling integrated via SimNIBS, results imported for visualisation.
