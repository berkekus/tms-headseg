---
type: Playbook
title: Module A Start Plan
description: Everything needed to start Module A now — decisions, access, environment, data intake, labels, splits, baselines, first-two-week work, and the start gate.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-02T18:00:00+03:00'
plan_state: proposed_not_started
sources:
- id: data
  resource: ../references/datasets.md
  title: Data inventory updated from the Drive archive
- id: drive
  resource: ../references/team-drive.md
  title: Shared Drive archive, SRC-011
- id: spec
  resource: ../references/source-catalog.md#src-007-module-a-specification-revision
  title: Module A specification revision, SRC-007
- id: roadmap
  resource: ../references/module-a-roadmap-revised.md
  title: Revised coding roadmap, SRC-005
- id: team
  resource: ../team.md
  title: Four-person workstream proposal, SRC-006
- id: literature
  resource: ../references/module-a-literature.md
  title: Module A literature map
---

# Module A Start Plan

Plan state: **proposed, not started.** Weeks are relative to an agreed start date, which is not yet recorded. Roles K1–K4 follow the [team proposal](../team.md); no person is assigned. Nothing below is complete until evidence is recorded in an experiment or reference note.

## 1. Where we start (2026-11-02)

| Available now | Missing |
| --- | --- |
| Drive archive with Module A data D01 MultiAxial, D04 SimNIBS samples, D05 SynthStrip selection, D06 IXI 50-subject subset (≈4.3 GB packed, SHA-256 manifests). | Named owners, start date, compute access, and the train-our-own-model decision. |
| SimNIBS 4.6 installation and Ernie sample on one machine; CHARM launcher prototype. | Any recorded run: [EXP-001](../experiments/ernie-baseline.md) is **not run**. |
| Revised roadmap, acceptance proposals, open-question register, literature workbooks. | Unpacked/audited data, case manifest, label map, splits, training environment. |
| Staging tool for missing open datasets. | CT-derived skull datasets (D14, D15) in Drive. |

## 2. Kickoff decisions (before week 1)

| Decision | Proposed default | Closes | Notes |
| --- | --- | --- | --- |
| Owners, backups, weekly hours, start date | Fill K1–K4 using the [rebalanced roles](../team.md#rebalanced-role-proposal-2026-11-02); backup pairs K1↔K2, K3↔K4 | Q-10 | Rebalanced roles give the inference API to K2 (after week 8) and the viewer/UI to K3. |
| Train our own model? | Yes: nnU-Net v2 trained on MultiAxial + charm pseudo-labels | Q-11 | GRACE weights cannot be packaged; SRC-007 §8.1 gives this rationale. |
| Target labels | 0 background/air, 1 skin, 2 skull, 3 CSF, 4 GM, 5 WM; `ignore` 6 for unknown/removed-face regions only | Q-05 (partly) | See [labels and face](../concepts/labels-and-face.md). |
| Training compute | NVIDIA GPU ≥8 GB (12 GB+ preferred): university server, TRUBA, or Colab | Q-07 | Name the account holder and confirm with a test job. charm needs a multi-core CPU with ≥16 GB RAM. |
| Test custodian | K1 holds the test manifest and releases test data only after settings freeze | Q-17 | K1 does not tune the model or QC thresholds. |
| First supported input/output | Input: one T1 MRI (NIfTI or DICOM via dcm2niix). Output: label map in source space + skin and brain surfaces + QC report | Q-02 | Export formats per [D-003 proposal](../decisions/003-export-route-proposal.md). |
| Data storage | One shared local/server path outside Git; no patient data in cloud services | Q-14 | `.gitignore` already blocks NIfTI and `m2m_*` outputs. |
| CT skull track | Add D14 (cerebrovascular subset) and D15 now; D16 optional | Q-18 | Evaluation only; see section 6. |

## 3. Access requests (week 1, long lead time)

None of these blocks the core plan; submit early only if the team wants the data.

| Request | Purpose | Note |
| --- | --- | --- |
| Hospital ethics committee + KVKK | Optional 5–10 real-world T1 test (SRC-007 §5.1) | Downstream-independent completion does not depend on it (D-002). |
| CERMEP-IDB-MRXFDG (D17) request form | Healthy CT-derived skull reference | Do not mirror to Drive. |
| ATLAS v2.0 DUA (D07) | Lesion test | Optional. |
| HCP (D09), ADNI (D13) | Extra cohorts | ADNI approval is slow; keep off the critical path. |
| GRACE weights (official release) | Research-only comparator | Each user downloads; never redistribute. |

## 4. Environment (F0, weeks 1–2)

| Component | Purpose | Check to record |
| --- | --- | --- |
| Python 3.11+ | Project code; Drive unpack tool requires ≥3.11 | `python --version` |
| PyTorch with CUDA | Training/inference on the GPU machine | `torch.cuda.is_available()`, GPU name, VRAM |
| nnU-Net v2 (pinned version) | Segmentation training | `nnUNet_raw`, `nnUNet_preprocessed`, `nnUNet_results` set; smoke run |
| SimNIBS 4.6 (charm) | Teacher labels, comparator, format reference | `charm --version`; EXP-001 timing |
| dcm2niix, nibabel, SimpleITK | Input conversion and geometry | Version list |
| scikit-image, PyVista/VTK | Surface extraction/export | Version list |
| 3D Slicer | Visual inspection | Version |

Storage: ≈4.3 GB packed for D01/D04/D05/D06, 4.4 GB for D14's subset, 14.5 GB for D15, plus unpacked data, charm outputs, and nnU-Net preprocessing. Measure actual per-subject charm output size in EXP-001 before sizing the pseudo-label run. Record every version in the experiment note that first uses it.

## 5. Data intake and audit (F1, weeks 1–2; K1)

1. Download D01, D04, D05, D06 from Drive with their `paket_manifest.json` and `PAKETLERI_AC.py`; unpack outside the repository; keep the checksum log ([procedure](../references/team-drive.md)).
2. Stage D14 and D15 with `tools/data_staging/stage_open_datasets.py` and upload them to `data/01_Veri_Setleri` (needs a team member with Drive write access). Add guide-only folders for D17–D20.
3. Build one case manifest with the fields listed in the [data inventory](../references/datasets.md#label-and-face-audit). Keep the manifest with the data; commit only its schema and a non-identifying summary.
4. **MultiAxial:** count unique subjects (group the four control variants), centers (GU, NC, NYU), clinical vs healthy, label values actually present, image/label geometry match, and defaced extent.
5. **IXI:** face and ear inside the field of view per subject, T1/T2 pairing, and the union of IXI IDs across D05, D06, and (if used) SHARM; deduplicate before any split.
6. **SynthStrip:** confirm 131 cases; mark IXI cases; ASL/FSM cases are robustness-only.
7. **CT-paired sets:** on three cases each, record MR sequence and contrast, face status, field of view (skull vertex present?), and whether CT and MR are already registered.

Exit: counts and audit findings recorded; [Q-03](../questions.md) updated with evidence.

## 6. Label mapping (F1, weeks 2–3; K1 with K2 review)

| Source | Mapping task |
| --- | --- |
| MultiAxial (D01) | Read actual label values; map skin/scalp, skull, CSF, GM, WM; map air cavity and extracephalic air to 0; decide lesion voxels. |
| charm 4.6 teacher labels | Read the tissue lookup table shipped with the installed version; map extra tissues (fat, muscle, eyes, vessels, compact/spongy bone) to the six classes with a written rule per tissue. |
| SHARM (D18, if licensed) | Map its 15 tissues; check face handling. |
| SynthStrip (D05) | No tissue mapping; brain mask only. |
| CT-paired (D14–D16) | Skull from CT threshold after registration; every other voxel `ignore`. Evaluation first; partial supervision only by later decision. |

Exit: one reviewed table per source; a loader test rejects unexpected label values.

## 7. Splits (F1, weeks 3–4; K1, custodian)

- **MultiAxial:** subject-level, about 44 train / 10 validation / 10 test (SRC-007 §5.1), stratified by center and clinical/healthy; control variants stay together. Adjust numbers to the audited count.
- **IXI with charm labels:** training only, except two disjoint intact-face cohorts drawn from other IXI subjects: validation/calibration and an untouched test of at least ten subjects (SRC-005 proposal; Q-15).
- **SynthStrip ASL/FSM:** robustness test only. **CT-paired:** skull test only.
- Write `splits_final.json` for nnU-Net and a separate test manifest held by the custodian. Freeze after review.

## 8. Baseline runs (F0/F2, weeks 1–3)

| Run | Owner role | Purpose | Record |
| --- | --- | --- | --- |
| EXP-001 Ernie charm, T1 only | K3 | Runtime, outputs, geometry reference | Existing protocol |
| Proposed EXP-002: charm 4.6 on 3 IXI subjects | K1 | Pilot pseudo-labels; review before scaling to ~50 | New experiment note |
| Proposed EXP-003: GRACE on 3 MultiAxial cases | K4 | Comparator plumbing; research use only | New experiment note |
| Proposed EXP-004: nnU-Net smoke run | K2 | Pipeline/GPU check on a few cases and epochs; not a result | New experiment note |

charm takes about 1–2 hours per subject (SRC-007); about 50 IXI subjects is a 50–100 CPU-hour batch. Schedule overnight runs only after the 3-case review.

## 9. Repository and interfaces (weeks 1–2; K4 with all)

- Proposed package layout, test runner, and CI for pure-Python checks; data never committed.
- Coordinate utilities and checks per the [coordinate contract](../concepts/coordinates.md) (K3 reviews geometry code).
- Draft the four interfaces by the end of week 2: data incl. nnU-Net raw layout (K1→K2), model output (K2→K3/K4), coordinates (K3→all), metrics incl. timing (K4→all). The inference API interface (K2→K3) follows by week 8.

## 10. First two weeks by role (rebalanced proposal)

Roles follow the [rebalanced team proposal](../team.md#rebalanced-role-proposal-2026-11-02); the full 12-week handoff table is there.

| Role | Week 1 | Week 2 |
| --- | --- | --- |
| K1 Data (test custodian) | Download/unpack D01, D04, D05, D06; stage/upload D14, D15; start manifest | MultiAxial and IXI audit; IXI dedupe; charm 3-case pilot started; draft nnU-Net raw dataset layout |
| K2 Model | GPU access and environment; nnU-Net install | Smoke run; training configuration draft |
| K3 Geometry/interface | EXP-001 Ernie run and output inventory | Coordinate checks on Ernie; reversible-preprocessing design; first surface extraction attempt |
| K4 Quality/eval | Repository/test scaffolding | Metrics and timing interface draft; GRACE setup; synthetic fixtures |

## 11. Start gate (end of week 2)

- [ ] Owners, backups, hours, and start date recorded (Q-10).
- [ ] GPU access confirmed with a test job (Q-07).
- [ ] D01/D04/D05/D06 unpacked with checksum logs.
- [ ] D14/D15 in Drive, or an explicit decision to skip.
- [ ] Case manifest with audited counts (Q-03).
- [ ] Label map v1 drafted for MultiAxial and charm.
- [ ] Split proposal written (frozen after review).
- [ ] EXP-001 run recorded with timing and observed defects.
- [ ] charm 3-case IXI pilot reviewed.
- [ ] nnU-Net smoke run recorded.
- [ ] Four interfaces drafted.
- [ ] Optional access requests submitted or declined.

## 12. After the gate (weeks 3–12)

Follow the [roadmap](../roadmap.md): F2 scaled pseudo-labels, F3 preprocessing, F4 experiments E1 (MultiAxial only), E2 (+ screened IXI charm labels), E3 (face weighting), F5 surfaces, F6 QC, F7 export, F8 frozen evaluation including the CT-skull subgroup and comparators (charm 4.6, GRACE, SPM12, SIAM if available), F9 delivery. Literature to read per phase is in the [literature map](../references/module-a-literature.md).

## Start risks

| Risk | Mitigation |
| --- | --- |
| MultiAxial is defaced, so faces are not learned from it | Intact faces come from IXI; face cohorts are disjoint. |
| IXI subjects leak across D05, D06, SHARM | Deduplicate by IXI ID before splitting. |
| charm runtime limits pseudo-label count | Pilot 3, then overnight batches; reduce count if needed (SRC-007 §8.1). |
| CT-paired MRIs are contrast-enhanced or defaced | Record per case; report as a separate subgroup. |
| Non-commercial licenses (D01, D04, D14–D16) | Research use only; record in the model card. |
| No GPU by week 2 | Escalate; Colab fallback for the smoke run only. |

## Related notes

[Roadmap](../roadmap.md) · [Data inventory](../references/datasets.md) · [Drive archive](../references/team-drive.md) · [Team](../team.md) · [Questions](../questions.md) · [Acceptance](../acceptance.md)
