---
type: Question Register
title: Open Questions
description: An actionable register of missing decisions without inventing owners or results.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T14:40:39+03:00'
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
---

# Open Questions

All entries below are open. Ownership is unassigned unless a person accepts it. The independent-output direction is already recorded in [D-002](decisions/002-downstream-independence.md); it is not an open dependency.

SRC-005 supplies more precise proposals for Q-04–06 and Q-08; these now need ratification and evidence rather than an initial numerical suggestion. See the [alignment review](reviews/roadmap-alignment.md).

| ID | Question | Evidence needed to close it | Priority |
| --- | --- | --- | --- |
| Q-01 | What guided local application and inspection scope satisfies the current proposal? | Agreed user journey, UI boundary, and acceptance demonstration. | Before architecture |
| Q-02 | Which input subset and export formats are first supported? | Example inputs/outputs, units, coordinate convention, failure behavior. | Before interfaces |
| Q-03 | Which dataset release and subset are available? | Actual manifest, checksums, subject/scan counts, source and terms. | Before training |
| Q-04 | Which examples contain an intact face and suitable reference geometry? | Per-case inspection, independent skin references, fixed face/ear regions, and the proposed minimum ten untouched test subjects. | Before face claims |
| Q-05 | What is the source-specific label mapping? | Reviewed tables covering internal air, outside background, extra tissues, unknown voxels, and lesion treatment. | Before training |
| Q-06 | Are the SRC-005 per-class, regional, runtime, failure, and QC targets accepted, and how are they computed? | Ratified acceptance protocol: aggregation, absent/ignored labels, surface metrics, denominators, hardware, loading and timing boundaries; freeze before test access. | Before benchmarking |
| Q-07 | Which compute environment is available for training? | Device, VRAM/RAM, access, budget, and package versions; distinguish training from the required local inference environment. Local Apple Silicon is not evidence of NVIDIA/CUDA access. | Before training |
| Q-08 | Which revised cleanup and QC rules preserve anatomy? | Validate tissue-specific rules and label priority; settle the 2% warning vs gate, failure annotations, no-output behavior, and locked thresholds. | Before evaluation |
| Q-09 | Where will the team retrieve original project documents? | Shared source location and revision/approval identifiers. Filenames and hashes alone do not grant access. | During onboarding |
| Q-10 | Who owns each workstream, and what dates are agreed? | Named ownership, actual start/deadline, review cadence. Source four-person plan is a proposal. | Before scheduling |
| Q-11 | Is training a new model required, or is integration of an existing model acceptable? | Advisor/team scope decision; broader proposal says AI-assisted segmentation while module plan proposes own training. | Before allocating compute |
| Q-12 | Where is the literature review and its source inventory? | Original report and citation table; do not treat reported review counts as independently audited. | Before literature claims |
| Q-13 | What exactly does the documented local API expose? | Choose callable vs local-service interface, operation/result/error schemas, and progress/cancellation behavior. | Before interfaces |
| Q-14 | What deployment boundary demonstrates local-only patient-data handling and inference? | Document data/model flows, storage/logging, and a verification method for external transmission. | Before packaging |
| Q-15 | Which intact-face subjects support validation and QC calibration without contaminating the face test set? | Separate training, calibration, and untouched test manifests; independent regional references. Resolve MultiAxial-only validation vs face-specific gates. | Before tuning face/QC rules |
| Q-16 | How are removed-face regions identified for ignored annotations and runtime flags? | Defined mask provenance, manually reviewed labels, detection protocol, and measured false-intact/false-defaced rates; zero intensity alone is insufficient evidence. | Before face handling |

Resolution rule: record evidence in a reference or experiment, write a decision if a choice is made, then update this register and [current state](current.md). A chat suggestion alone does not close a technical question.
