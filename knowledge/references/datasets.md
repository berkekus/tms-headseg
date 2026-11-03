---
type: Data Inventory
title: Data and Baseline Inventory
description: Dataset roles for Module A, the shared Drive archive state, licenses, face coverage, and leakage risks.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-02T18:00:00+03:00'
sources:
- id: inventory
  resource: source-catalog.md#src-008-data-and-tool-inventory-workbook
  title: Team data and tool inventory workbook, SRC-008
- id: drive
  resource: team-drive.md
  title: Shared Drive archive snapshot, SRC-011
- id: spec
  resource: source-catalog.md#src-007-module-a-specification-revision
  title: Module A specification revision, SRC-007, pp. 6–8
- id: multi
  resource: https://arxiv.org/abs/2501.18716
  title: MultiAxial model/data release paper
- id: ixi
  resource: https://brain-development.org/ixi-dataset/
  title: Official IXI dataset
- id: grace-weights
  resource: https://github.com/lab-smile/GRACE/blob/main/MODEL_LICENSE
  title: GRACE weights license
- id: zenodo-d14
  resource: https://zenodo.org/records/17486320
  title: Paired Head CT-MRI dataset record
- id: zenodo-d15
  resource: https://zenodo.org/records/7260705
  title: SynthRAD2023 training data record
- id: zenodo-d16
  resource: https://zenodo.org/records/14918089
  title: SynthRAD2025 dataset record
- id: sharm
  resource: https://arxiv.org/abs/2309.06677
  title: SHARM paper (arXiv v1)
---

# Data and Baseline Inventory

Updated 2026-11-02 from the team inventory workbook (SRC-008), the shared Drive archive (SRC-011), and official dataset pages read on that date. "In Drive" means the archive's own control record lists the packages; it does not mean anyone has unpacked, audited, split, or labeled the data in this project. No dataset audit has been recorded yet.[^inventory][^drive]

IDs D01–D17 follow the team workbook and Drive folder names. D18+ are new Module A candidates from the literature workbook (SRC-009) and are numbered here for the first time.

## Module A datasets

| ID | Dataset | Module A role | In Drive (2026-10-23 record) | Face | License / access |
| --- | --- | --- | --- | --- | --- |
| D01 | MultiAxial v2 (Kaggle) | Main labeled train/validation/test data; lesion robustness. | Yes: 10 packages, 0.74 GB, SHA-256 per package. | Defaced | CC BY-NC-SA 4.0 per Drive guide. |
| D04 | SimNIBS examples v4.1 + Ernie Extended | Output-format and geometry reference; local charm timing. | Yes: 39 packages, 1.77 GB. | Intact (sample) | Ernie Extended CC BY-NC 4.0; other packages per archive notes. |
| D05 | SynthStrip v1.5 selection | Domain-shift robustness: 131 adult T1 (ASL 43, FSM 38, IXI 50) with image, brain mask, and labels. | Yes: 13 packages, 1.03 GB; source SHA-256 matched. | Not defaced | IXI part CC BY-SA; rest CC BY 4.0. |
| D06 | IXI subset | Teacher pseudo-label pool, intact-face cohort, T1 vs T1+T2 comparison. | Partial: 50 of 393 paired T1/T2 subjects (100 NIfTI), evenly spaced IDs IXI002–IXI442; not random. | Not defaced | CC BY-SA 3.0. |
| D07 | ATLAS v2.0 | Lesion test (optional). | No data; DUA pending. | To check | ICPSR DUA. Do not mirror. |
| D09 | HCP Young Adult | Large healthy cohort (optional). | No data; account needed. | Not defaced | HCP terms. Do not mirror. |
| D10 | UPenn-GBM | Pathology test (optional). | Metadata only; MRI ≈69 GB via Aspera. | To check | TCIA terms. Skull-stripped versions unusable for heads. |
| D12 | OASIS | Age diversity (optional). | No data; version undecided. | Intact | Terms prohibit face reconstruction: no face surfaces. |
| D13 | ADNI | Older-adult test (optional). | No data; application needed. | Phases 1–3 intact; ADNI-4 defaced | Long approval: keep off the critical path. |
| D14 | Paired Head CT-MRI | CT-derived skull reference for our model and charm. | **No** — staging script ready. | Not stated | **CC BY-NC 4.0** (the workbook's "CC BY 4.0" is wrong). 120 patients, 40.1 GB; cerebrovascular subset 4.4 GB. |
| D15 | SynthRAD2023 brain MR-CT | Multi-center CT-derived skull reference. | **No** — staging script ready. | Defaced (brain) | CC BY-NC 4.0. 180 brain training pairs in Task1.zip (14.5 GB, includes pelvis). Some center B/C MRIs contrast-enhanced. |
| D16 | SynthRAD2025 head-and-neck | Skull-base CT reference (low priority). | **No** — staging script ready. | Defaced | Centers A/B/C/E CC BY-NC 4.0; center D challenge-only: never mirror. |
| D17 | CERMEP-IDB-MRXFDG | Healthy CT-derived skull reference; MPRAGE close to routine T1. | No; request form. | To check | Access committee approval. Do not mirror. |
| D18 | SHARM | Candidate extra labeled training data: 196 IXI subjects, 15 tissues (.mat, 7.62 GB on figshare). | No — license not stated; check before mirroring. | IXI source not defaced; model face handling not stated | Not stated. |
| D19 | DBB distorted brain benchmark | Extra distorted-anatomy test (paediatric, 37 T1, 6 classes). | No | To check | Not verified (publisher page unreadable). |
| D20 | Head models population (Sci Data 2025) | Candidate pseudo-labels from SimNIBS headreco models. | No | To check | Not verified (publisher login wall). |

D02, D03 (landmarks/registration), D08 (TMS motor mapping), and D11 (UNITE) are in Drive but serve other modules; they are not Module A inputs. Hospital MRI remains optional, needs ethics approval and KVKK compliance, and does not gate core completion under [D-002](../decisions/002-downstream-independence.md).

## Facts that change the plan

- **MultiAxial audit (observed 2026-11-02, K1, unpacked D01).** `tools/data_audit/audit_multiaxial.py` found 68 T1/label pairs, all in RAS orientation with image and label geometry matching: 64 defaced `Anonymized_Subjects` (GU 28, NC 22, NYU 10, plus `subj1–4`) and 4 `Control_Subjects` (`subj1–4`, the **non-defaced variants of the same four healthy people**). `Metadata.csv` lists the same 64 IDs exactly (age 30–85, mean 59.7; 46 male, 17 female, 1 unspecified). So there are **64 unique subjects (60 clinical, 4 healthy) across 3 centers**, and the four intact-face variants are the only intact-face MultiAxial data. Labels are 0–6 in every case; by T1 intensity and a visual overlay check they are 0 outside air, 1 air cavity, 2 gray matter, 3 white matter, 4 CSF, 5 skull, 6 skin/soft tissue. The paper lists the seven classes (background/extracephalic air, air cavities, WM, GM, CSF, bone, non-brain soft tissue) but states **no numeric values**; this mapping rests on mean T1 intensity (value 3 brightest, value 2 intermediate) and an overlay check (value 2 follows the cortical ribbon, value 3 the deep core). It does not contradict the paper. The Kaggle demo notebook may state the numbers (not read). Spacing is 1 mm except two cases at 1×0.977×0.977; matrix sizes vary widely (e.g. 196×270×270, 192×256×256, 212×276×276); T1 dtypes are mixed (int16 59, float32 5, uint8 4). The control labels differ from their defaced twins in skin, skull, and air-cavity voxels (face restored). Raw outputs stay outside the repository.
- **MultiAxial paper facts (J Med Imaging 2025, full text read 2026-11-02).** The study has 98 T1 MRIs from four institutions: 4 healthy (3T Siemens), 50 chronic-aphasia stroke patients (Georgetown 28, UNC 22), 34 disorders-of-consciousness patients (Paris), and 10 apraxia/stroke patients (NYU). The release has 64 subjects = 98 − 34, so **the 34 Paris patients are not in the public release** (consistent with our GU 28 + NC 22 + NYU 10 + 4 healthy). Released data are defaced MRIs with labels version 2 (AFNI deface; the paper also evaluates reface) plus originals of the healthy subjects; all scans are 1 mm isotropic (two files show 0.977 mm spacing). Labels were semi-manual: automated first pass (SPM8 or MultiPriors), then manual correction. The data statement says images are in "RSA" orientation, while file headers read RAS; geometry in this project follows the header affine. **Left-right check (2026-11-03, K1):** in the 54 train/validation subjects (test set not used), CSF volume, which fills chronic stroke lesions, lies mostly on the header's left side (x below the brain's median x) in 51 cases and mostly on the right in none (median left share 0.62; GU 23/26, NC 20/20, NYU 8/8). Aphasia-causing strokes are predominantly left-hemispheric, so this supports the header's left-right direction; a flipped header would show the opposite. It is indirect evidence, not a marker-based check. The paper states the data and model are released under CC BY-NC-SA 4.0, matching the Drive guide. The 61 clinical MRIs cited by the literature workbook differ from the 60 found here and are unverified.
- **MultiAxial counts (before the audit).** The Drive guide says the archive contains anonymised images plus separate variants of four controls: file count is not subject count. SRC-007 proposes 64 subjects (4 healthy, 60 clinical) from three centers (GU, NC, NYU) split ~44/10/10. The paper describes 98 MRIs overall and the literature workbook cites 61 released clinical MRIs. Only a manifest built from the unpacked archive settles the count.[^multi]
- **IXI subset audit (observed 2026-11-02, K1, unpacked D06; `tools/data_audit/audit_ixi.py`).** All 100 files match their manifest SHA-256. 50 subjects from three sites (T1: Guys 29, HH 14, IOP 7). T1 is sagittal (PSR) at about 0.94×0.94×1.2 mm (a few 1.25 mm), T2 axial (LAS) with different matrix sizes, so **T1 and T2 are not on the same grid**; no affine shear. Edge-contact screening on T1: head touches the neck edge in 49/50 (expected), the vertex in 0/50, and the nose side only in IXI442 (2.2% of that face, nose tip nearly at the edge; IXI417 also close), ears in 3 cases marginally. T2 vertex is cut in 23/50 (T2 is secondary). A sagittal/axial visual check of four cases showed intact nose, lips, and jaw: faces are not defaced. This is a screening aid, not a full face-quality audit.
- **IXI overlap D05 vs D06 (measured).** D05's 50 IXI T1 scans (IXI numbers 002, 012–022, 134–143, 230–234, 266–278, 397–401, 518–528, 553) share **6 subjects with D06**: IXI002, IXI020, IXI139, IXI230, IXI276, IXI401. Together the two sets cover 94 unique IXI subjects. D05 is a domain-robustness test set, so those six subjects must not enter training or pseudo-label training via D06.
- **IXI appears in three places.** D05 contains 50 IXI subjects, D06 another selection of 50, and D18 (SHARM) 196 IXI subjects. Any IXI ID may appear in more than one source. Deduplicate on IXI subject ID before splitting, and assign each IXI subject to exactly one split.
- **SynthStrip labels 100–105 are not tissue classes.** Use D05 for brain-mask and robustness checks only, never as six-tissue ground truth.
- **CT-derived skull is a new validation track.** D14–D17 give skull references independent of charm; they have no ready labels and are not T1-only clinical inputs. Use them for skull evaluation (and possibly partial skull supervision with all other voxels ignored). Contrast-enhanced or defaced inputs must be reported as such.
- **Only IXI gives intact faces with open access in the archive.** The intact-face validation/calibration and test cohorts (Q-04, Q-15) must come from distinct IXI subjects (D06 or a larger IXI download), not from D01, D14 (unknown), D15, or D16.
- **GRACE weights are not in Drive.** Their license forbids redistribution; each user downloads them from the official release for research comparison only.[^grace-weights]

## Label and face audit

For every selected case record a non-identifying case ID, source release, checksum, subject grouping, center, shape/spacing, orientation, reference labels, face coverage, contrast, and assigned split. An anonymized subject ID can still link repeated scans: split by subject, not filename.

Defaced examples can support eligible brain tests but cannot establish accuracy for missing facial anatomy. Reference-method labels used for training must not be treated as independent proof of matching that method.

## Baseline and comparator terms

The plan compares against charm (SimNIBS 4.6, which includes the subcutaneous-fat skull improvement), GRACE, SPM12, and optionally SIAM. GRACE code is MIT; its weights are research-only and non-redistributable. Record failure cases and hardware alongside conditional accuracy.

## Related notes

[Shared Drive archive](team-drive.md) · [Module A literature](module-a-literature.md) · [Start plan](../playbooks/module-a-kickoff.md) · [Label contract](../concepts/labels-and-face.md) · [Acceptance](../acceptance.md)

[^inventory]: Team workbook `docs/Veri_ve_Arac_Envanteri.xlsx`, sheets 1–3. Its grey cells are unverified by its own note. [Catalog entry](source-catalog.md).
[^drive]: Drive guides and control records dated 2026-10-22/23: `00_BURADAN_BASLA.txt`, `KAYNAK_DURUM_LISTESI.json`, `SON_KONTROL_KAYDI.json`, and per-dataset `00_OKU_BENI.txt`. [Archive note](team-drive.md).
[^multi]: MultiAxial paper abstract; it does not establish the contents of the downloaded subset. [Open source](https://arxiv.org/abs/2501.18716).
[^grace-weights]: GRACE MODEL_LICENSE and the Drive K02 guide. [Open source](https://github.com/lab-smile/GRACE/blob/main/MODEL_LICENSE).
