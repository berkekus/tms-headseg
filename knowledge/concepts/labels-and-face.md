---
type: Concept
title: Labels and Facial Coverage
description: A proposed six-class schema with unresolved mappings and missing-anatomy limits.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: roadmap
  resource: ../references/module-a-roadmap.md
  title: Roadmap label and postprocessing proposal
- id: module
  resource: ../references/module-a-spec.md
  title: Module specification face-coverage discussion, pp. 6–7
---

# Labels and Facial Coverage

The source proposes the following project labels. Numeric values are a candidate schema from the roadmap, not a mapping validated against any selected release.[^roadmap]

| Proposed value | Proposed meaning | Open definition |
| --- | --- | --- |
| 0 | Background / air | Specify outside background vs internal air and unannotated regions. |
| 1 | Skin / external soft tissue | Define handling of fat, muscle, eyes, and other source tissues. |
| 2 | Skull | Define merged vs separate source bone classes. |
| 3 | CSF | Document source coverage and lesion-related conventions. |
| 4 | Gray matter | Document anatomical scope. |
| 5 | White matter | Document anatomical scope. |

Use one reviewed mapping per source schema, with an explicit project target schema. Reject unexpected labels rather than silently assigning background. Image and reference label geometry must match.

## Facial coverage is an input property

Distinguish intact anatomy, cropped anatomy, defaced anatomy, missing annotations, and a model prediction that misses visible anatomy. A threshold-based correction can only use boundaries still present in the image; it cannot recover a removed patient's actual face.

Eligible brain evaluation and facial-surface evaluation need separate coverage/reference rules. Explicitly mask unknown annotation areas where justified. Screen pseudo-labels before adding them to training and keep reference-method failures visible in benchmark reports.

## Cleanup is not class-neutral

A largest-component rule may discard valid disconnected anatomy. Filling all holes in each tissue mask can fill regions belonging to other tissues. Tune class-specific operations on validation data and check label exclusivity and spatial plausibility after processing.[^roadmap]

## Related notes

[Datasets](../references/datasets.md) · [nnU-Net](../references/nnunet.md) · [Review](../reviews/roadmap-review.md)

[^roadmap]: Coding roadmap, pp. 6–8; definitions and blanket cleanup rules require review. [Open source](../references/module-a-roadmap.md).
