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

Held-out subjects (10 `test_face`, 5 `calibration`) ran on the K1 desktop from 2026-11-03 23:13 to 2026-11-04 11:32: all 15 completed (39–56 min each). IXI111 first crashed in mmg3d (access violation while improving mesh quality, probably memory pressure from other jobs) and finished on retry. IXI130 was first skipped because its T2 qform/sform differ by 1.2e-3 (0.28 mm at the volume corner, a third of a voxel); K1 accepted it and it ran with `--forceqform` via `--accept-qform-diff`, recorded in its run record. QC by K1 with the same checks as the training pool: all 15 pass. Brain 961–1259 mL; labels on zero padding at most 17 mL, none beyond 5 mm and no brain or CSF there; detached bone in IXI204 and IXI312 (39 and 30 mL) is spine or jaw; IXI257's 467 mL CSF follows visible atrophy; the nose tip touches the field-of-view edge in IXI176, IXI286 (both `test_face`) and IXI303. These labels stay closed until the model is frozen. K2 runs its 15 training subjects with the same tool.

**K2 delivery (2026-11-04):** 15/15 subjects, zip hash and every per-subject checksum verified by K1; SimNIBS 4.6.0 on macOS with thread limits, 28–35 min each. K2 QC: 13 pass, IXI426 and IXI442 `check` because charm puts tissue on the T1's zero padding. K1 measured this on all 29 IXI subjects: IXI426 has 414 mL of extrapolated neck and scalp on inferior padding (338 mL more than 5 mm from any signal); every other subject has at most 21 mL, with at most 3.7 mL beyond 5 mm and no brain or CSF. **Rule adopted for E2:** labels on exactly-zero voxels connected to the volume border become background in `prepare_e2.py` (recorded per case as `padding_cleared_ml`). With that rule K1 accepted both `check` cases (`qc_K1_review_of_K2.csv`, outside Git). The same rule turns the defaced region of MultiAxial images into background, matching the Dataset001 labels.

**Decision (2026-11-04, team):** E2 uses charm labels only. The 54 MultiAxial E1 train/val cases are relabeled with charm (T1 only, on the Dataset001 images) so that IXI and MultiAxial share one GM/CSF convention; the MultiAxial test hold-out is not relabeled. Runs: K1 laptop parts 1/3 and 2/3 (36 cases); part 3/3 split into 9 on the K1 desktop after the held-out runs and 9 on K2 (`multiaxial_assignment_K2.csv`). After part 1/3 finished, part 2/3 was split as well: laptop 10, desktop 8 (totals: laptop 28, desktop 17, K2 9). Dataset assembly: `tools/nnunet_prep/prepare_e2.py` (`Dataset002_E2Charm`). Caveat: MultiAxial charm runs are T1-only, which NC033 suggests gives a weaker skull than T1+T2.

**MultiAxial desktop batch, 9 cases (2026-11-04, K1).** All 9 completed (37–72 min), affine difference 0 to the Dataset001 image. Labels on zero padding are eye and blood in the defaced orbit (5–13 mL), no brain. Against the Dataset001 reference (mapped, padding cleared, within 25 mm of the reference brain/CSF), mean Dice is 0.716–0.845. **Finding: charm labels chronic stroke lesions as white matter.** In GU016 and GU035 a 92–94 mL region with CSF-like T1 intensity (median 93 and 113; reference CSF 96 and 117, WM 282 and 311) is WM in charm and CSF in the reference; GU008 (19 mL) and NC004 (32 mL) show the same, smaller. charm's atlas has no lesion class. These four are QC `check` (not in E2 until the team decides); the other five pass. Training E2 on them would teach "lesion = WM", which matters for TMS fields in stroke patients. Options: (a) leave lesion cases out of E2; (b) use charm labels but set voxels to CSF where the reference says CSF and charm says WM or GM with CSF-like T1; (c) keep charm as is. The laptop's 36 cases will show the same effect, about 4 in 9 here.

**Desktop, 8 more cases (2026-11-05, K1).** NC013, NC017, NC020, NC023, NC029, NYU002, NYU005, NYU008 completed (39–70 min), affine difference 0, mean Dice 0.780–0.840. NYU002 and NYU005 show the lesion effect (27–28 mL with CSF-like T1 labelled WM; visible next to the lateral ventricle in NYU005) and are `check`; the other six pass. Detached bone in NC017 (48 mL) and NC029 (26 mL) lies at neck level, spine or jaw. Desktop total: 17 cases, 6 `check` for lesions, 11 pass.

**All 54 MultiAxial cases delivered (2026-11-05, K1).** Desktop 17, laptop 28, K2 9 (macOS, 27–32 min); every case checked against the assignment (none missing, none duplicated) and every per-case checksum verified. QC by K1 with the same checks on all 54: affine difference 0, mean Dice 0.76–0.86, no brain labels on padding. Detached bone and soft tissue in several cases lie at neck level (about 100 mm below the brain centre), jaw or spine split off by defacing. **35 pass, 19 `check` for the lesion effect** (largest charm-WM-on-reference-CSF region at least 10 mL with T1 closer to CSF than to WM): desktop GU008, GU016, GU035, NC004, NYU002, NYU005; laptop GU010, GU012, GU015, GU017, GU025, GU032, NC008 (borderline), NC010, NC027; K2 GU039, NC024, NYU003, NYU010. NC011 has a large cystic lesion that charm labels CSF like the reference, so K1 overrides K2's `check` there. charm therefore handles fluid-filled cavities but not partly filled lesions. Sheets: `charm_MA/qc_K1.csv`, `charm_laptop_MA/qc_K1_laptop.csv`, `k2_delivery/MA_charm_20261104/qc_K1_review_of_K2_MA.csv` (outside Git). A pass-only Dataset002 (29 IXI + 35 MultiAxial = 64 cases, 50 train / 14 val) was built into `e2_pass_20261105` and passed `nnUNetv2_extract_fingerprint --verify_dataset_integrity`. The 19 lesion cases wait for the team's decision on options (a)–(c).

**Decision (2026-11-05): option (b), lesion rule.** `prepare_e2.csf_like_lesions` relabels CSF where the Dataset001 reference says CSF, charm says GM/WM, T1 is darker than midway between the case's reference CSF and GM medians, and the region survives a 2-voxel opening (thin sulcal differences stay charm) and is at least 1 mL. MultiAxial only (IXI has no reference); `lesion_csf_ml` per case in `e2_manifest.csv`. Effect: 10–124 mL in the 19 lesion cases; 0–22 mL in the other 35, where it fixes parts of enlarged lateral ventricles that charm labels GM/WM (NC017, GU027, GU041) and the margin of NC011's cyst; 17 cases unchanged. K1 reviewed the corrected labels of all 19 and passed them (`qc_K1_lesion_rule_20261105.csv`). Residual: lesion tissue with intermediate T1 (partly filled, not CSF-dark) stays WM, largest piece 13–20 mL in NC004, NYU003 and NC008 and at most 9 mL elsewhere. Full Dataset002 built with `--require-all` into `e2_full_20261105`: 83 cases (IXI 23 train / 6 val, MultiAxial 44 / 10). `nnUNetv2_plan_and_preprocess -d 2 -c 3d_fullres --verify_dataset_integrity` passed on the K1 desktop (1 mm, patch 160×128×112, batch 2). Handoff for K2: `handoff_k2_e2.zip` (1.09 GB, SHA256 `aa548971…`), raw dataset, split, manifest and `K2_BASLA_E2.md`; checked to contain no held-out or test case.

## Related notes

[Data inventory](../references/datasets.md) · [Start plan](../playbooks/module-a-kickoff.md) · [EXP-001](ernie-baseline.md)
