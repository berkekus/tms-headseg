---
type: Review
title: Roadmap Review and Unresolved Conflicts
description: Technical review findings retained separately from source requirements and decisions.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T14:40:39+03:00'
sources:
- id: roadmap
  resource: ../references/module-a-roadmap.md
  title: Coding roadmap
- id: proposal
  resource: ../references/proposal-form.md
  title: Current project proposal
- id: holes
  resource: https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.binary_fill_holes.html
  title: SciPy binary_fill_holes
---

# Roadmap Review and Unresolved Conflicts

These findings record the earlier twelve-page SRC-004 and its conflicts with other requirements. They are engineering review judgments, not proof of an implementation defect. The seventeen-page SRC-005 addresses several concerns at source level; use the [revised alignment review](roadmap-alignment.md) for their current disposition. None is marked implemented or experimentally resolved by document import.

| ID | Source location | Concern | Resolution evidence |
| --- | --- | --- | --- |
| REV-01 | Proposal pp. 1, 5; roadmap pp. 2, 10 | Proposal requires integrated image/model inspection; roadmap delivery centers on a CLI. | Allocate an application/UI work item and demo criteria. |
| REV-02 | Roadmap p. 7 | Blanket largest-component and hole-filling rules can remove anatomy or create overlapping tissues. | Class-specific validation and label-exclusivity checks. |
| REV-03 | Roadmap pp. 3, 5, 8–9 | RAS language and saved affine do not fully define cross-library spatial transformations. | Explicit coordinate contract and asymmetric numeric round-trip checks. |
| REV-04 | Module specification pp. 6–7; roadmap pp. 7–8 | Completing a missed prediction is different from recovering anatomy removed from MRI. | Per-case coverage audit and separate eligible face/brain evaluation. |
| REV-05 | Roadmap p. 12 | Excluding failed reference-method cases from benchmark analysis creates selection bias. | Include every test case in outcome accounting; report failures separately from conditional accuracy. |
| REV-06 | Roadmap pp. 6–7 | Dataset counts, custom validation split, and optional low-resolution configuration need exact handling. | Inventory-derived counts, fixed E1–E3 splits, inspected plans. |
| REV-07 | Roadmap pp. 7–10 | Fast model inference does not establish fast end-to-end processing; QC success is qualitative. | Stage timing and predeclared QC/failure definitions. |
| REV-08 | Roadmap pp. 9, 12 | Source acceptance alternates between required external validation and documenting its absence. | Apply the current software-independent acceptance contract; do not inherit product-specific gates. |
| REV-09 | Current proposal vs earlier module plan | AI-assisted reconstruction does not necessarily imply mandatory from-scratch model training. | Advisor/team decision about required scientific contribution and acceptable reuse. |
| REV-10 | Current proposal pp. 3–5 vs roadmap | Documented local API and guided application requirements lack explicit work items. | Define API/UI contracts and schedule implementation and acceptance evidence. |
| REV-11 | Current proposal pp. 3–5 vs older compute suggestions | Training resources and deployment must not be conflated; patient artifacts and inference must stay local. | Define eligible training data/compute separately from deployed inference and inspect dataflow. |

REV-02 follows the documented binary hole-filling behavior and the fact that separate tissue masks can enclose other tissue regions.[^holes] REV-03 and REV-06 are supported by the linked coordinate and nnU-Net references. A source-specific deployment dependency has been removed from current project direction by D-002; generic geometry acceptance is still to define.

## Related notes

[Scope](../scope.md) · [Acceptance](../acceptance.md) · [Coordinates](../concepts/coordinates.md) · [nnU-Net](../references/nnunet.md) · [Questions](../questions.md)

[^holes]: SciPy documents filling enclosed holes in binary masks; anatomical suitability is an engineering question for validation. [Open source](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.binary_fill_holes.html).
