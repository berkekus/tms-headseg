---
type: Decision
title: 'D-004: Axis-Only Reversible Preprocessing'
description: A proposal to reorient without interpolation and leave resampling to nnU-Net, with evidence still needed.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-02T23:00:00+03:00'
decision_id: D-004
decision_state: proposed
sources:
- id: roadmap
  resource: ../references/module-a-roadmap-revised.md
  title: Reversible preprocessing, pp. 6–7
- id: spec
  resource: ../references/source-catalog.md#src-007-module-a-specification-revision
  title: Module A specification revision, section 4.1
- id: nnunet
  resource: ../references/nnunet.md
  title: nnU-Net reference
- id: contract
  resource: ../concepts/coordinates.md
  title: Coordinate contract v1
---

# D-004: Axis-Only Reversible Preprocessing

Decision state: **proposed**, not accepted. K3 proposed it on 2026-11-02 while implementing the geometry part of F3.

## Question

How do we meet "reversible preprocessing" so segmentation returns to the patient's own coordinates? SRC-007 section 4.1 says to reorient, resample to 1 mm, and map results back. The [nnU-Net note](../references/nnunet.md) says nnU-Net already preprocesses and asks us to justify any extra fixed-resolution resampling.

## Constraints

- Labels must return to the source grid without geometric drift.
- MultiAxial is RAS and IXI is PSR (K1 audit, unmerged branch). nnU-Net's default reader does not reorient, so the training set must share one axis order.
- NiBabel and SimpleITK read a file with conflicting qform and sform differently, and SimpleITK rejects a sheared sform without a qform. See the [measured behavior](../concepts/coordinates.md#measured-library-behavior).

## Options

| Option | For | Against |
| --- | --- | --- |
| A. Reorient and resample to 1 mm ourselves. | Follows the source text. | Second interpolation before nnU-Net's own; inverting it is lossy for labels. |
| B. Use nnU-Net's reorienting reader. | Little code. | Depends on a version not inspected; leaves the raw-file geometry ambiguity; training files stay in mixed axis order on disk. |
| C. Permute and flip axes ourselves, write one ITK-readable carrier, leave resampling to nnU-Net. | Exact inverse; removes the qform/sform ambiguity; handles sheared sources; independent of the nnU-Net version. | One more project step; K1 must apply it to IXI. |

## Proposal

Choose **C**. It is implemented in `headmodel.reversible` and tested on all 48 axis orientations with exact array equality.

## Consequences

- We add no resampling step of our own. This narrows SRC-007's "resample to 1 mm" to nnU-Net's internal behavior.
- Intensity correction stays outside this decision; it is not a geometry step.
- K1 applies `canonicalize` to IXI before E2. K2 runs inference through the carrier.

## Evidence needed before acceptance

- A nnU-Net 2.8.1 smoke prediction that returns on the input grid and passes `read_model_output`.
- One real non-RAS scan through the full path, checked against the source MRI.
- Team review, including K2 on the inference path.

## Related notes

[Coordinates](../concepts/coordinates.md) · [Roadmap](../roadmap.md) · [Alignment review](../reviews/roadmap-alignment.md) · [Questions](../questions.md)
