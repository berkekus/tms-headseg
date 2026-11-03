---
type: Decision
title: 'D-003: Generic Surface Export First'
description: A proposed export strategy with evidence required before acceptance.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
decision_id: D-003
decision_state: proposed
sources:
- id: roadmap
  resource: ../references/module-a-roadmap.md
  title: Roadmap export ordering, pp. 8–9
- id: direction
  resource: 002-downstream-independence.md
  title: Accepted downstream independence
---

# D-003: Generic Surface Export First

Decision state: **proposed**, not accepted.

## Proposal

First validate separate external-head and brain surfaces in a documented physical frame. Candidate formats are STL or PLY with an accompanying metadata record for units, coordinate convention, reference-image identity, and transforms. A labeled NIfTI output can preserve the source-grid relationship.

Keep optional volume meshing separate until a demonstrated requirement justifies its cost. The source roadmap prioritizes direct surfaces; current user direction requires independence from a particular output consumer.

## Evidence needed

Demonstrate overlay alignment, physical scale, left/right consistency, and usable surface quality. Document format limitations and stage timings. Then choose the first supported export contract in a reviewed decision.

## Evidence so far

`tools/headmodel` implements a candidate: `head` and `brain` surfaces in RAS millimetres, `labels.nii.gz` on the source grid, and `model.json` with frame, units, reference identity, cleanup volumes, warnings, timing, and software versions. Surface files declare `SPACE=RAS UNITS=mm`, the tag 3D Slicer reads from an STL header or PLY comment. [EXP-005](../experiments/ernie-surface-export.md) measured one real head.

Format limits observed while implementing: binary STL stores float32 coordinates, repeats vertices, and has only an 80-byte header, so it cannot carry the contract alone. PLY keeps shared vertices. Both rely on `model.json` for everything beyond the frame tag.

Still missing: an opening in an independent viewer, usable-surface review by a person, and team acceptance.

## Alternatives

A volume-mesh route may be useful for research interoperability but adds runtime and packaging questions. SimNIBS already provides a documented label-to-mesh tool; that alone does not prove the full project output contract.

## Related notes

[D-002](002-downstream-independence.md) · [Coordinates](../concepts/coordinates.md) · [SimNIBS](../references/simnibs.md) · [Acceptance](../acceptance.md)
