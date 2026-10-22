---
type: Concept
title: Geometry and Coordinate Contract
description: Proposed invariants for voxel, physical, and export coordinates.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: nib
  resource: https://nipy.org/nibabel/coordinate_systems.html
  title: NiBabel coordinate systems
- id: sitk
  resource: https://simpleitk.org/doxygen/latest/html/classitk_1_1simple_1_1DICOMOrientImageFilter.html
  title: SimpleITK orientation conventions
- id: roadmap
  resource: ../references/module-a-roadmap.md
  title: Roadmap, pp. 3, 5, 8–9
---

# Geometry and Coordinate Contract

The roadmap's RAS/affine rule needs an explicit library-boundary contract. NiBabel uses RAS+ world coordinates; ITK/SimpleITK uses LPS conventions. Array reorientation and changing world-coordinate conventions are distinct operations.[^nib][^sitk]

## Contract to agree before implementation

- Name each reference grid and world frame, its units, origin, orientation, and array axis order.
- Preserve the original image identity and relevant spatial metadata, including how qform/sform disagreements are handled.
- Record reorientation, resampling, cropping, and any registration transformations; an original affine alone does not describe an arbitrary processing history.
- At library boundaries, establish which conversions file I/O already performs. Do not add a second manual flip blindly.
- Derive mesh vertices from the affine belonging to the actual segmentation grid. Do not apply voxel spacing twice.
- Publish an explicit frame/unit contract alongside generic surface exports; do not rely on an unnamed viewer convention.

The source example's `marching_cubes` followed by `apply_affine` is reasonable for a NiBabel array when spacing has not already been applied. Its surrounding interfaces still need verification.

## Proposed checks

Use an asymmetric synthetic object with known physical landmarks, non-unit spacing, translation, and a nontrivial orientation. Check numerical positions after round trips and inspect alignment against MRI. Agree error tolerances before calling the contract passed.

## Related notes

[Acceptance](../acceptance.md) · [Review](../reviews/roadmap-review.md) · [Ernie protocol](../experiments/ernie-baseline.md)

[^nib]: NiBabel coordinate-system documentation. [Open source](https://nipy.org/nibabel/coordinate_systems.html).
[^sitk]: SimpleITK orientation documentation. [Open source](https://simpleitk.org/doxygen/latest/html/classitk_1_1simple_1_1DICOMOrientImageFilter.html).
