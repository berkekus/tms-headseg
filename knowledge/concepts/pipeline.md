---
type: Concept
title: Modeling Pipeline
description: Software-independent stage boundaries and proposed data exchange contracts.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: proposal
  resource: ../references/proposal-form.md
  title: Current project proposal
- id: module
  resource: ../references/module-a-spec.md
  title: Module A concept specification
---

# Modeling Pipeline

Proposed flow: MRI import → validated image/geometry → segmentation → surfaces → QC and inspection → documented export. These are planned boundaries, not implemented packages.[^proposal][^module]

| Stage | Input and output contract to establish |
| --- | --- |
| Import | Accepted T1/DICOM subset, selected series, original image metadata, and clear rejection reasons. |
| Preprocessing | Image and labels with explicit reference grids, units, and recorded transformations. |
| Segmentation | Semantic integer label map, optional probabilities, label schema, and model/version identifier. |
| Surface generation | Separate head and brain surfaces in a named physical frame; cleanup settings and defects recorded. |
| QC / application | Guided local image/surface inspection and warnings; confidence is evidence to interpret, not an automatic correctness guarantee. |
| Local API | Document model-preparation and export operations, result/error behavior, and representative/invalid-input checks. |
| Export | Geometry, coordinate convention, units, reference-image identity, and output metadata. |

Keep computational stages callable separately for reproducibility. The application must also demonstrate the source proposal's integrated inspection workflow. A command-line interface alone does not resolve that requirement.

The exact UI toolkit, local API interface, primary output formats, model training requirement, and supported scan range remain open. The source requires patient images, derived models, and inference to remain local without external uploads. Direct surface files are a proposed first route, not an accepted implementation choice. Downstream product-specific project structures are not a core requirement.

## Related notes

[Scope](../scope.md) · [Coordinates](coordinates.md) · [Labels](labels-and-face.md) · [Export proposal](../decisions/003-export-route-proposal.md)

[^proposal]: Current proposal, pp. 1, 3–5. [Open source](../references/proposal-form.md).
[^module]: Module A concept specification, pp. 4–5. [Open source](../references/module-a-spec.md).
