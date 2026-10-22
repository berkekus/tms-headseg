---
type: Concept
title: Labels and Facial Coverage
description: A proposed six-class schema with unresolved mappings and missing-anatomy limits.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T14:40:39+03:00'
sources:
- id: roadmap
  resource: ../references/module-a-roadmap-revised.md
  title: Revised roadmap label and postprocessing proposal
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

The revised source adds `ignore: 6` for unknown/removed-face annotations (pp. 8–9). It is a training-annotation marker, not a seventh anatomical output class or evidence that missing anatomy can be recovered. Its proposed zero-intensity/head-mask heuristic needs a separately defined mask and manual validation; see ALIGN-03 in the [alignment review](../reviews/roadmap-alignment.md).

## Facial coverage is an input property

Distinguish intact anatomy, cropped anatomy, defaced anatomy, missing annotations, and a model prediction that misses visible anatomy. A threshold-based correction can only use boundaries still present in the image; it cannot recover a removed patient's actual face.

Eligible brain evaluation and facial-surface evaluation need separate coverage/reference rules. Explicitly mask unknown annotation areas where justified. Screen pseudo-labels before adding them to training and keep reference-method failures visible in benchmark reports.

SRC-005 p. 11 proposes automatic defacing detection and a visible face-incomplete status, with no claim of a recovered actual face. Detection accuracy is unmeasured. Distinguish a partial observed head surface from a face suitable for registration. SRC-005 p. 14 proposes at least ten intact-face evaluation subjects and skin references manually corrected independently of charm. Separate face-validation/calibration subjects from the untouched test cohort; see [acceptance](../acceptance.md).

## Cleanup is not class-neutral

A largest-component rule may discard valid disconnected anatomy. Filling all holes in each tissue mask can fill regions belonging to other tissues. The revised proposal is class-specific:[^roadmap]

| Mask | SRC-005 pp. 10–11 proposal |
| --- | --- |
| Whole-head union | Largest component and hole filling for the external envelope. |
| Skin | No standalone hole filling; derive consistently from head and internal tissues. |
| Skull | No hole filling; remove only small islands and preserve natural openings. |
| CSF | No largest-component reduction; remove only tiny islands. |
| Brain union (GM + WM) | Largest component, without filling ventricles or lesion cavities. |
| GM and WM individually | Only small-island removal. |

Island thresholds are proposed in cubic millimetres. Merge into mutually exclusive labels, record per-class volumes before/after, and inspect anatomy and surface distances. Whole-head union must contain only the mapped anatomical classes, never an annotation-ignore region. Class priority must not conceal conflicting labels. The 2% volume-change warning vs hard gate remains unresolved. Validate every operation, especially brain component removal, before adoption.

## Related notes

[Datasets](../references/datasets.md) · [nnU-Net](../references/nnunet.md) · [Review](../reviews/roadmap-review.md)

[^roadmap]: Revised coding roadmap, pp. 8–12. Proposed operations require validation; source-level correction does not establish implementation correctness. [Open source](../references/module-a-roadmap-revised.md).
