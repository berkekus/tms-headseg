---
type: Review
title: Revised Roadmap Alignment Review
description: Source-level improvements, remaining contradictions, and project-specific adaptation.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T14:40:39+03:00'
sources:
- id: revised
  resource: ../references/module-a-roadmap-revised.md
  title: Revised roadmap, SRC-005
- id: proposal
  resource: ../references/proposal-form.md
  title: Current five-page project proposal
- id: earlier
  resource: roadmap-review.md
  title: Earlier review findings
---

# Revised Roadmap Alignment Review

**Assessment:** substantially aligned with the project knowledge base and more precise than SRC-004. Import the new definitions as proposals; do not infer accepted targets, working code, or successful experiments. Page numbers below refer to the seventeen-page SRC-005 unless stated otherwise.

## Earlier findings: what changed in the source

| Earlier finding | Revised source evidence | Remaining work |
| --- | --- | --- |
| REV-02: blanket cleanup | pp. 10–11 distinguish tissues, preserve cavities, require exclusive labels and record volume changes. | Validate component removal, class priority, and surface changes; see ALIGN-04. |
| REV-03: coordinates | pp. 4–5 state RAS+/LPS, array order, units, conversion boundaries, and asymmetric checks. | Agree tolerances and actual-grid affine handling; see ALIGN-05. |
| REV-04: removed faces | pp. 9, 11 separate ignored annotations, visible missed anatomy, and irrecoverable removed anatomy. | Establish masks, detector performance, and intact-face validation; see ALIGN-02/03. |
| REV-05: failed cases | p. 14 retains failures, all-case Dice, and successful-only Dice; p. 7 limits pseudo-label rejection to training. | p. 16 still says to exclude failed cases from analysis; see ALIGN-01. |
| REV-06: training layout | pp. 8–9 correct validation placement, generated counts, training-only pseudo-labels, fixed splits, and conditional `3d_lowres`. | Verify actual releases and generated plans; p. 16's shorter fallback must retain that condition. |
| REV-07: timing and QC | pp. 2–3, 10, 12, 14 supply stage budgets, numerical QC goals, and validation-only threshold selection. | Ratify definitions, denominators, hardware, and timing boundaries. |
| REV-08: external dependency | pp. 13, 17 distinguish independent research acceptance from optional external integration. | Apply D-002 consistently to earlier milestones; external inventory cannot block our baseline. |
| REV-01, REV-09–11 | A CLI and own-model training remain central; UI/API and deployed dataflow are not allocated explicitly. | Current proposal requirements and the training-scope decision remain open. |

These are changes in the source proposal, not closed implementation findings. The [earlier review](roadmap-review.md) remains the historical record.

## Remaining issues and proposed handling

| ID | Source location | Issue | Handling needed before implementation/evaluation |
| --- | --- | --- | --- |
| ALIGN-01 | pp. 14 vs 16 | Complete test-case accounting conflicts with the risk-table instruction to exclude failed cases. | Preserve every test subject for every method. Record failures and conditional accuracy separately. Exclude bad pseudo-labels only from training; document reasons. |
| ALIGN-02 | p. 9 vs pp. 11–12, 14 | Internal validation uses only MultiAxial, whose face coverage is described as defaced; face-distance and face-QC gates need intact references. The separate cohort is only explicitly excluded from training. | Define an intact-face validation/calibration cohort and a separate untouched test cohort. Proposed minimum ten subjects applies to the latter; prove subject disjointness and prevent tuning on it. |
| ALIGN-03 | pp. 9, 11 | Zero-valued T1 voxels intersected with a head mask are only a proposed missing-face heuristic. A mask derived from remaining anatomy may exclude the removed region entirely. Zero intensity alone does not establish defacing. | Specify mask provenance, thresholds, manual annotation, and detector error rates. Distinguish cropping, missing annotations, true air, and removed anatomy; never claim recovery of the patient's removed face. |
| ALIGN-04 | pp. 10–12 | More than 2% volume change is a warning in the algorithm but a hard failure in F5 completion. Largest-component brain cleanup and fixed class priorities still can alter anatomy. | Decide warning vs gate, denominator, zero-volume handling, and class-specific tolerances. Validate against untouched labels, clinical cases, and face/brain surfaces; volume alone is insufficient. |
| ALIGN-05 | p. 5 vs p. 11 | Coordinate prose says source-T1 affine; the code applies the segmentation affine. They agree only after output has been restored to the source grid. | Use the affine of the actual mask grid, then recorded transforms if needed. Numerically check orientation, units, and the path back to source MRI. |
| ALIGN-06 | pp. 2–3, 12–14 | Thresholds exist, but Dice aggregation, absent/ignored labels, surface-distance definition, unavailable face references, and QC denominators remain unspecified. NIfTI-to-export and DICOM-to-usable-model timing have different boundaries. | Freeze the [measurement contract](../acceptance.md) before test access. Count no-output errors as failures and issue a visible error even when no confidence map exists. Never assign zero distance to missing surfaces. |
| ALIGN-07 | pp. 3, 14–17 vs proposal pp. 1, 3–5 | CLI/package completion does not demonstrate the required integrated local inspection, documented local API, usability, or local-only data/inference. | Schedule those work items and acceptance evidence explicitly. External viewer checks supplement application acceptance. |

These concerns are engineering judgments from comparing the supplied plans, not experimental findings. No detector, threshold, or cleanup policy is marked validated.

## What to carry forward

Use the revised F0–F9 plan, coordinate definitions, train/validation/test separation, class-specific cleanup proposal, face-reference plan, explicit failure accounting, and preregistration proposal. Keep generic exports and independent geometry acceptance. Keep application/API/local-processing requirements from SRC-001. Existing [Ernie baseline](../experiments/ernie-baseline.md) remains the next practical step and remains **not run**.

## Related notes

[Revised source](../references/module-a-roadmap-revised.md) · [Acceptance](../acceptance.md) · [Questions](../questions.md) · [Coordinates](../concepts/coordinates.md) · [Labels and facial coverage](../concepts/labels-and-face.md)
