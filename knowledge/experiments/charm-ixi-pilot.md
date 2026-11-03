---
type: Experiment
title: 'EXP-002: charm Pilot on IXI Subjects'
description: Pilot charm runs on three non-overlapping IXI subjects to measure runtime and assess pseudo-label quality; one of three completed.
status: draft
generated:
  by: claude/sonnet-5.5
  at: '2026-11-02T21:00:00+03:00'
experiment_id: EXP-002
experiment_state: partially_run
sources:
- id: datasets
  resource: ../references/datasets.md
  title: IXI audit and D05/D06 overlap
- id: charm
  resource: https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html
  title: CHARM usage
---

# EXP-002: charm Pilot on IXI Subjects

Experiment state: **partially run (1 of 3 subjects)**. Purpose: measure charm runtime on the training machine and judge whether its labels are usable as pseudo-labels (training only) before scaling to about 50 subjects.

## Plan

Subjects chosen from D06 by the [IXI audit](../references/datasets.md): intact face, ears, and vertex in the field of view, not among the six subjects shared with D05. One per site: IXI045 (Guys), IXI095 (HH), IXI294 (IOP). Planned variants: T1+T2 for all three (best teacher quality) and optionally IXI045 T1-only to see what T2 contributes.

## Run record

| Field | IXI045 (T1+T2) | IXI095 | IXI294 |
| --- | --- | --- | --- |
| Status | **Completed** | Not run | Not run |
| Tool version | SimNIBS 4.6.0 (from `charm_log.html`) | | |
| Hardware | K1 Windows machine, 8 threads set by charm, 15.8 GB RAM | | |
| Command | `charm IXI045 IXI045-Guys-0713-T1.nii.gz IXI045-Guys-0713-T2.nii.gz` | | |
| Wall-clock | ≈ 66 min (log start 19:23:39, last report file 20:29:17) | | |
| Per-stage time | Not recorded as such; file times: registration done 19:23, segmentation 19:36, label prep 19:45, surfaces 19:55, mesh 20:28 | | |
| Peak memory | Not measured | | |
| Outputs | `.msh` (171 MB), `final_tissues.nii.gz`, `final_tissues_LUT.txt`, `charm_report.html`, log | | |
| Exit status | Outputs complete; no error observed (log tail shows normal mesh steps) | | |

Outputs stay outside Git (`C:\Users\Berke\tms-data\charm_pilot\m2m_IXI045`).

## Observations (IXI045)

- `final_tissues.nii.gz` is on the input T1 grid (256×256×150, about 0.94×0.94×1.2 mm, PSR) with a trailing singleton dimension. Pseudo-labels therefore align directly with the original T1; loaders must squeeze the fourth dimension.
- Labels present: 1 white matter 587 ml, 2 gray matter 648 ml, 3 CSF 279 ml, 5 scalp 1705 ml, 6 eyeballs 11 ml, 7 compact bone 447 ml, 8 spongy bone 70 ml, 9 blood 39 ml, 10 muscle 2 ml. Labels 4 (generic bone), 11 (cartilage), and 12 (fat) do not occur in this output.
- A mid-sagittal, coronal, and axial overlay check showed anatomically plausible tissue boundaries (scalp/soft tissue, skull, CSF, GM, WM, sagittal sinus as blood). This is one subject and a visual impression only, not a quantitative or expert assessment.
- Most soft tissue, including jaw and tongue regions, is labeled "Scalp" (5); muscle is nearly absent.

## Mapping to project classes (`9 → CSF` accepted, PR #5; the rest proposed)

| charm label | Project class |
| --- | --- |
| 0 outside | 0 background |
| 1 WM | 5 white matter |
| 2 GM | 4 gray matter |
| 3 CSF | 3 CSF |
| 4, 7, 8 bone | 2 skull |
| 5 scalp, 10 muscle, 11 cartilage, 12 fat | 1 skin/soft tissue |
| 9 blood | 3 CSF (changed from skin on 2026-11-03; see the evidence below) |
| 6 eyeballs | 3 CSF (the MultiAxial paper relabels eye contents as CSF; confirm) |

Open points: where blood vessels and dural sinuses should go, whether air cavities exist in charm's output (no separate label), and whether the sites' T1 contrasts change quality. Decide with the label-mapping review (Q-05).

**Evidence on the mapping (2026-11-03, K1).** E1 (trained on MultiAxial only) was run on IXI045 and on the public Ernie Extended T1, and its labels were cross-tabulated against raw charm labels within 25 mm of charm's brain/CSF (neck and face excluded). The same pattern appears in both subjects:

| charm voxels | E1 calls them | IXI045 | Ernie |
| --- | --- | --- | --- |
| 9 blood (mostly dural sinuses here) | CSF | 61% | 62% |
| 3 CSF | gray matter | 23% | 14% |
| 7 compact bone | CSF | 8% | 13% |
| 6 eyeballs | CSF | 93% | 46% (53% soft tissue) |

Reading: (1) MultiAxial convention treats intracranial blood as CSF, so the proposed `9 blood → skin` is inconsistent with the training labels; **proposed change: 9 → CSF** for E2 pseudo-labels. The same row lives in K3's `tools/headmodel/labels.py` (`CHARM_TO_PROJECT`); at the user's direction it now maps `9 → 3 (CSF)` there too (K3, 2026-11-03), so surfaces and E2 pseudo-labels share one table. The rest of the mapping stays proposed. (2) E1 places the GM/CSF boundary into sulcal CSF and the CSF/skull boundary into the inner table, which matches the lost folding and thin skull seen in its surfaces. Whether this is MultiAxial's labeling convention or model error is not yet separable: charm is being run on the MultiAxial training case NC033 (smallest CSF volume among GU/NC training cases) so that charm and the semi-manual reference can be compared on the same scan. E1 is not ground truth, and E1 errors and convention differences are mixed in this table.

**Same-scan comparison, NC033 (2026-11-03).** charm 4.6.0 ran T1-only on the MultiAxial training case NC033 (38.8 min, exit 0) and was compared voxel-wise with the semi-manual reference on the same grid, within 25 mm of the reference brain/CSF:

- Folding ratio of the brain surface (same K3 surface code): reference **1.76** (1233 cm²), charm **2.38** (1640 cm²). 24% of charm CSF is reference GM, and reference GM is larger (549 vs 481 mL). The MultiAxial reference fills sulcal CSF with GM, so the smooth E1 cortex is inherited from the training labels, not mainly a model error.
- Skull: the reference has more skull than charm (443 vs 403 mL); 15% of charm CSF is reference skull. E1's thin skull on IXI045 and Ernie therefore does not come from this convention; it is more likely a generalization error. Caveat: charm ran T1-only here (no T2), which weakens its skull.
- Blood (26 mL): reference CSF 39%, skull 33%, skin 23%. `9 → CSF` is the plurality and raises mean Dice only from 0.794 to 0.796; low impact either way.
- Mean Dice charm vs reference, five tissues: 0.794 (skin 0.853, skull 0.779, CSF 0.672, GM 0.794, WM 0.872).

Consequence for E2: MultiAxial and charm labels follow different GM/CSF conventions. Training on both mixes conflicting targets at the sulcal boundary. The team must choose a target convention (charm is closest to what SimNIBS meshing expects), for example by relabeling the MultiAxial training cases with charm as well. One subject, a stroke patient, and a T1-only charm run: this is direction, not a measured population effect.

## Batch run, K1 training pool (2026-11-03)

All 14 K1 training subjects of [ixi_assignment.csv](../../tools/charm_batch/ixi_assignment.csv) have charm 4.6.0 labels (T1+T2), delivered with checksums. Twelve ran through `tools/charm_batch` with math-library threads limited to 1: six on the K1 desktop (51–80 min each) and six on a second K1 laptop (48–52 min each). IXI045 and IXI294 are the hand-run pilots (66 and 40 min, no thread limits). `--forceqform` was needed for 8 of 14 because of rounding-level qform/sform differences. A full `m2m` folder is about 0.75 GB, not 0.25 GB.

QC by K1 (six T1 overlay slices per subject plus volume and connectivity checks; not an expert read of every slice): all 14 pass. Brain 935–1284 mL, every main tissue present, stray islands under 0.1 mL, no CSF touching scalp above the brain centre. Detached bone of 33–46 mL in five subjects is the cervical spine or jaw, not a skull gap. IXI103 (occiput) and IXI195, IXI417 (nose tip) touch the field-of-view edge. Results are in `qc_K1.csv` outside Git.

## Next

Held-out subjects (10 `test_face`, 5 `calibration`) run on the K1 desktop from 2026-11-03 23:13. K2 runs its 15 training subjects with the same tool.

**K2 delivery (2026-11-04):** 15/15 subjects, zip hash and every per-subject checksum verified by K1; SimNIBS 4.6.0 on macOS with thread limits, 28–35 min each. K2 QC: 13 pass, IXI426 and IXI442 `check` because charm puts tissue on the T1's zero padding. K1 measured this on all 29 IXI subjects: IXI426 has 414 mL of extrapolated neck and scalp on inferior padding (338 mL more than 5 mm from any signal); every other subject has at most 21 mL, with at most 3.7 mL beyond 5 mm and no brain or CSF. **Rule adopted for E2:** labels on exactly-zero voxels connected to the volume border become background in `prepare_e2.py` (recorded per case as `padding_cleared_ml`). With that rule K1 accepted both `check` cases (`qc_K1_review_of_K2.csv`, outside Git). The same rule turns the defaced region of MultiAxial images into background, matching the Dataset001 labels.

**Decision (2026-11-04, team):** E2 uses charm labels only. The 54 MultiAxial E1 train/val cases are relabeled with charm (T1 only, on the Dataset001 images) so that IXI and MultiAxial share one GM/CSF convention; the MultiAxial test hold-out is not relabeled. Runs: K1 laptop parts 1/3 and 2/3, K1 desktop part 3/3 after the held-out runs. Dataset assembly: `tools/nnunet_prep/prepare_e2.py` (`Dataset002_E2Charm`). Caveat: MultiAxial charm runs are T1-only, which NC033 suggests gives a weaker skull than T1+T2.

## Related notes

[Data inventory](../references/datasets.md) · [Start plan](../playbooks/module-a-kickoff.md) · [EXP-001](ernie-baseline.md)
