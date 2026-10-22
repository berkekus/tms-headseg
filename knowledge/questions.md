---
type: Question Register
title: Open Questions
description: An actionable register of missing decisions without inventing owners or results.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
- id: module
  resource: references/module-a-spec.md
  title: Module A concept specification
- id: roadmap
  resource: references/module-a-roadmap.md
  title: Module A coding roadmap
---

# Open Questions

All entries below are open. Ownership is unassigned unless a person accepts it. The independent-output direction is already recorded in [D-002](decisions/002-downstream-independence.md); it is not an open dependency.

| ID | Question | Evidence needed to close it | Priority |
| --- | --- | --- | --- |
| Q-01 | What guided local application and inspection scope satisfies the current proposal? | Agreed user journey, UI boundary, and acceptance demonstration. | Before architecture |
| Q-02 | Which input subset and export formats are first supported? | Example inputs/outputs, units, coordinate convention, failure behavior. | Before interfaces |
| Q-03 | Which dataset release and subset are available? | Actual manifest, checksums, subject/scan counts, source and terms. | Before training |
| Q-04 | Which examples contain an intact face and suitable reference geometry? | Per-case coverage inspection and face-region reference protocol. | Before face claims |
| Q-05 | What is the source-specific label mapping? | Reviewed tables covering internal air, outside background, extra tissues, unknown voxels, and lesion treatment. | Before training |
| Q-06 | What exactly do the 60 s, Dice, and 2 mm targets mean? | Agreed definitions in acceptance note; hardware and timing boundaries. | Before benchmarking |
| Q-07 | Which compute environment is available for training? | Device, VRAM/RAM, access, budget, and package versions; distinguish training from the required local inference environment. Local Apple Silicon is not evidence of NVIDIA/CUDA access. | Before training |
| Q-08 | Which cleanup and QC rules preserve anatomy? | Validation comparisons, failure annotations, and locked thresholds. | Before evaluation |
| Q-09 | Where will the team retrieve original project documents? | Shared source location and revision/approval identifiers. Filenames and hashes alone do not grant access. | During onboarding |
| Q-10 | Who owns each workstream, and what dates are agreed? | Named ownership, actual start/deadline, review cadence. Source four-person plan is a proposal. | Before scheduling |
| Q-11 | Is training a new model required, or is integration of an existing model acceptable? | Advisor/team scope decision; broader proposal says AI-assisted segmentation while module plan proposes own training. | Before allocating compute |
| Q-12 | Where is the literature review and its source inventory? | Original report and citation table; do not treat reported review counts as independently audited. | Before literature claims |
| Q-13 | What exactly does the documented local API expose? | Choose callable vs local-service interface, operation/result/error schemas, and progress/cancellation behavior. | Before interfaces |
| Q-14 | What deployment boundary demonstrates local-only patient-data handling and inference? | Document data/model flows, storage/logging, and a verification method for external transmission. | Before packaging |

Resolution rule: record evidence in a reference or experiment, write a decision if a choice is made, then update this register and [current state](current.md). A chat suggestion alone does not close a technical question.
