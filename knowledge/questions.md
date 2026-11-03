---
type: Question Register
title: Open Questions
description: An actionable register of missing decisions without inventing owners or results.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-23T10:06:38+03:00'
sources:
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
- id: module
  resource: references/module-a-spec.md
  title: Module A concept specification
- id: roadmap
  resource: references/module-a-roadmap-revised.md
  title: Revised Module A coding roadmap
- id: team
  resource: references/module-a-roadmap-team-update.md
  title: Expanded team plan, SRC-006
---

# Open Questions

All entries below are open. Ownership is unassigned unless a person accepts it. The independent-output direction is already recorded in [D-002](decisions/002-downstream-independence.md); it is not an open dependency.

SRC-005 supplies more precise proposals for Q-04–06 and Q-08; these now need ratification and evidence rather than an initial numerical suggestion. See the [alignment review](reviews/roadmap-alignment.md).

SRC-006 expands the [team proposal](team.md), but leaves named assignments empty. The team size is confirmed as four; assignment, capacity, dates, and acceptance of its operating rules remain open.

| ID | Question | Evidence needed to close it | Priority |
| --- | --- | --- | --- |
| Q-01 | What guided local application and inspection scope satisfies the current proposal? | Agreed user journey, UI boundary, and acceptance demonstration. | Before architecture |
| Q-02 | Which input subset and export formats are first supported? | Example inputs/outputs, units, coordinate convention, failure behavior. | Before interfaces |
| Q-03 | Which dataset release and subset are available? | Actual manifest, checksums, subject/scan counts, source and terms. Partial evidence (2026-11-02): the Drive archive lists D01, D04, D05, D06 with package checksums and licenses ([inventory](references/datasets.md)); unique-subject counts and label values still need an audit of the unpacked data. | Before training |
| Q-04 | Which examples contain an intact face and suitable reference geometry? | Per-case inspection, independent skin references, fixed face/ear regions, and the proposed minimum ten untouched test subjects. | Before face claims |
| Q-05 | What is the source-specific label mapping? | Reviewed tables covering internal air, outside background, extra tissues, unknown voxels, and lesion treatment. | Before training |
| Q-06 | Are the SRC-005 per-class, regional, runtime, failure, and QC targets accepted, and how are they computed? | Ratified acceptance protocol: aggregation, absent/ignored labels, surface metrics, denominators, hardware, loading and timing boundaries; freeze before test access. | Before benchmarking |
| Q-07 | Which compute environment is available for training? | Device, VRAM/RAM, access, budget, and package versions; distinguish training from the required local inference environment. Local Apple Silicon is not evidence of NVIDIA/CUDA access. Observed 2026-11-02: the K1 Windows machine reports an NVIDIA GeForce RTX 4070 (12 GB) via `nvidia-smi`; PyTorch 2.6 + CUDA 12.4 reports `cuda.is_available() == True` on it, nnU-Net 2.8.1 is installed and preprocessing ran, but training speed is untested; C: has ~55 GB free. Colab Pro (A100) is the proposed fallback. | Before training |
| Q-08 | Which revised cleanup and QC rules preserve anatomy? | Validate tissue-specific rules and label priority; settle the 2% warning vs gate, failure annotations, no-output behavior, and locked thresholds. | Before evaluation |
| Q-09 | Where will the team retrieve original project documents? | Shared source location and revision/approval identifiers. Filenames and hashes alone do not grant access. | During onboarding |
| Q-10 | Who accepts the K1–K4 workstreams and backups, and what dates/capacities are agreed? | Named owners/backups, weekly availability, workload review, explicit application/API/local-dataflow ownership, interface acceptance, actual start/deadline, and review cadence. SRC-006 is a proposal with empty assignment cells. | Before scheduling |
| Q-11 | Is training a new model required, or is integration of an existing model acceptable? | Advisor/team scope decision; broader proposal says AI-assisted segmentation while module plan proposes own training. | Before allocating compute |
| Q-12 | Where is the literature review and its source inventory? | Report supplied as SRC-012 (`docs/literature-review.md`), plus Module A candidates and snowball workbooks (SRC-009/010) and 83 PDFs in Drive. Remaining: full-text decisions for A01–A50 and an audit of the reported counts. | Before literature claims |
| Q-13 | What exactly does the documented local API expose? | Choose callable vs local-service interface, operation/result/error schemas, and progress/cancellation behavior. | Before interfaces |
| Q-14 | What deployment boundary demonstrates local-only patient-data handling and inference? | Document data/model flows, storage/logging, and a verification method for external transmission. | Before packaging |
| Q-15 | Which intact-face subjects support validation and QC calibration without contaminating the face test set? | Separate training, calibration, and untouched test manifests; independent regional references. Resolve MultiAxial-only validation vs face-specific gates. | Before tuning face/QC rules |
| Q-16 | How are removed-face regions identified for ignored annotations and runtime flags? | Defined mask provenance, manually reviewed labels, detection protocol, and measured false-intact/false-defaced rates; zero intensity alone is insufficient evidence. | Before face handling |
| Q-17 | Who controls held-out test access while comparator runs and model improvement overlap? | Agreed custodian/access rule; freeze model, cleanup, QC, and metric settings before viewing test predictions/scores. Keep development regression subjects separate from the held-out benchmark. | Before test processing |
| Q-18 | How are CT-paired datasets (D14–D17) used? | Decide evaluation-only vs partial skull supervision; CT-to-MR registration method; skull threshold rule; handling of contrast-enhanced or defaced MRIs; subgroup reporting. Inspect three cases per set first. | Before F8 protocol freeze |
| Q-19 | Who uploads new datasets to Drive, and what may be mirrored? | Named person with Drive write access; per-dataset license check. Open CC BY-NC sets (D14, D15, D16 A/B/C/E) may be mirrored with attribution; access-controlled sets (D07, D09, D13, D17, SynthRAD2025 center D) may not. | Before data intake |
| Q-20 | Is SHARM (196 IXI subjects, 15 tissues) usable as extra labeled training data? | Its data license and face handling; label mapping to six classes; overlap with other IXI subjects in the splits. | Before E1–E3 data freeze |

Resolution rule: record evidence in a reference or experiment, write a decision if a choice is made, then update this register and [current state](current.md). A chat suggestion alone does not close a technical question.
