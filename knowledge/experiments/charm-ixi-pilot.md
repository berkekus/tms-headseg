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

## Proposed mapping to project classes (not accepted)

| charm label | Project class |
| --- | --- |
| 0 outside | 0 background |
| 1 WM | 5 white matter |
| 2 GM | 4 gray matter |
| 3 CSF | 3 CSF |
| 4, 7, 8 bone | 2 skull |
| 5 scalp, 10 muscle, 11 cartilage, 12 fat, 9 blood | 1 skin/soft tissue |
| 6 eyeballs | 3 CSF (the MultiAxial paper relabels eye contents as CSF; confirm) |

Open points: where blood vessels and dural sinuses should go, whether air cavities exist in charm's output (no separate label), and whether the sites' T1 contrasts change quality. Decide with the label-mapping review (Q-05).

## Next

Run IXI095 and IXI294, optionally the T1-only variant of IXI045, then compare runtimes across sites and review the reports before any batch run. Per-subject output is about 0.25 GB, and runtime of roughly 1.1 h per subject puts 50 subjects at about 55 hours.

## Related notes

[Data inventory](../references/datasets.md) · [Start plan](../playbooks/module-a-kickoff.md) · [EXP-001](ernie-baseline.md)
