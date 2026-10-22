---
type: Evaluation Plan
title: Acceptance and Measurement Definitions
description: Distinguish proposed thresholds, product acceptance, and measured evidence.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: module
  resource: references/module-a-spec.md
  title: Module A concept specification
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
- id: roadmap
  resource: references/module-a-roadmap.md
  title: Module A coding roadmap
---

# Acceptance and Measurement Definitions

No project performance measurements are recorded yet. Source documents propose targets; the team has not confirmed all numerical definitions.[^module]

| Item | Current proposal | Definition still needed |
| --- | --- | --- |
| End-to-end runtime | Under 60 seconds on GPU. | Exact input/output boundaries, hardware, warm/cold model loading, and whether conversion/report/export are included. |
| Tissue Dice | Mean at least 0.85. | Foreground classes, per-subject aggregation, background exclusion, and handling of absent/unknown labels. |
| Skin surface distance | Under 2 mm. | Symmetric mean vs another statistic; report HD95 separately. Specify face-region coverage. |
| Difficult anatomy | Compare against reference methods on clinical subgroups. | Subgroup definitions and predeclared meaning of non-inferior performance. |
| QC | Identify unusable results. | Failure annotation protocol, sensitivity/recall, false-alarm rate, and a locked threshold. |
| Operator benefit | Reduce preparation time and manual steps. | Same scans and tasks; separate operator interaction time from compute time. |
| Usability | Guided, learnable local inspection and export. | Record task completion, time, errors, repeated-attempt learnability, and perceived ease of use, as required by proposal p. 5. |

## Geometry and functional acceptance

- Source MRI, segmentation, and surfaces retain documented physical scale and alignment.
- Synthetic asymmetric fixtures check orientation and left/right consistency; measure coordinate errors, not just appearance.
- Source-image and model inspection, rotation/zoom, and export are demonstrated within the local application.[^proposal]
- The local API has a documented request/result/error contract and checks for representative and invalid inputs.[^proposal]
- Patient images, derived models, and AI inference remain local; the deployed workflow is checked for external transmission of those artifacts.[^proposal]
- Exports have a documented coordinate/unit contract and align in an independent viewer. Acceptance does not depend on a named downstream product.
- Cropped or defaced inputs cannot silently count as valid full-face reconstructions.
- An unsuccessful case remains in failure-rate reporting. Accuracy among completed cases is identified as conditional accuracy.

## Evaluation boundaries

Training and validation may guide design; held-out test results must not guide postprocessing, QC thresholds, or model selection. E1–E3 comparisons use the same held-out subjects. Reference-method pseudo-labels are not independent ground truth for accuracy claims.

The roadmap proposes repeated timing on documented hardware, tissue metrics, surface distances, and subgroup analysis.[^roadmap] Store commands, settings, input identifiers, and output paths in each [experiment](experiments/index.md); do not fill a result cell with a target.

## Related notes

[Scope](scope.md) · [Review](reviews/roadmap-review.md) · [Open questions](questions.md)

[^module]: Module A specification, pp. 7–9; thresholds are described as provisional. [Open source](references/module-a-spec.md).
[^proposal]: Current proposal, pp. 1, 3, and 5. [Open source](references/proposal-form.md).
[^roadmap]: Coding roadmap, pp. 9–12; measurement details require reconciliation with this note. [Open source](references/module-a-roadmap.md).
