---
type: Concept
title: Geometry and Coordinate Contract
description: Proposed invariants for voxel, physical, and export coordinates.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T14:40:39+03:00'
sources:
- id: nib
  resource: https://nipy.org/nibabel/coordinate_systems.html
  title: NiBabel coordinate systems
- id: sitk
  resource: https://simpleitk.org/doxygen/latest/html/classitk_1_1simple_1_1DICOMOrientImageFilter.html
  title: SimpleITK orientation conventions
- id: roadmap
  resource: ../references/module-a-roadmap-revised.md
  title: Revised roadmap, pp. 4–5, 7, 11
---

# Geometry and Coordinate Contract

The revised roadmap now proposes an explicit library-boundary contract. NiBabel uses RAS+ world coordinates; ITK/SimpleITK uses LPS conventions. Array reorientation and changing world-coordinate conventions are distinct operations.[^nib][^sitk]

## Latest source proposal

SRC-005 pp. 4–5 specifies world coordinates in millimetres/RAS+, voxel `(i, j, k)` positions through the NIfTI affine, LPS-to-RAS sign changes on the first two physical coordinates, and SimpleITK NumPy array order `(z, y, x)`. It prefers NIfTI file boundaries and centralizes in-memory conversions in one proposed module. These are proposed contracts, not implemented utilities.

## Contract to agree before implementation

- Name each reference grid and world frame, its units, origin, orientation, and array axis order.
- Preserve the original image identity and relevant spatial metadata, including how qform/sform disagreements are handled.
- Record reorientation, resampling, cropping, and any registration transformations; an original affine alone does not describe an arbitrary processing history.
- At library boundaries, establish which conversions file I/O already performs. Do not add a second manual flip blindly.
- Derive mesh vertices from the affine belonging to the actual segmentation grid. Do not apply voxel spacing twice.
- Publish an explicit frame/unit contract alongside generic surface exports; do not rely on an unnamed viewer convention.

The revised source example's `marching_cubes` followed by the segmentation's `apply_affine` is reasonable for a NiBabel array when spacing has not already been applied. Its prose also says to use the source T1 affine: that is valid only after restoring the mask to that source grid. Track the actual grid and transforms; see ALIGN-05 in the [alignment review](../reviews/roadmap-alignment.md).

## Proposed checks

The revised source explicitly proposes RAS/LPS round trips, cross-library agreement for the same voxel after expressing both physical positions in one convention, and preservation of an asymmetric side marker. Use non-unit spacing, translation, and a nontrivial orientation as well. Check numerical positions and source-MRI overlay. Agree error tolerances before calling the contract passed; none of these checks is recorded as executed.

## Related notes

[Acceptance](../acceptance.md) · [Review](../reviews/roadmap-review.md) · [Ernie protocol](../experiments/ernie-baseline.md)

[^nib]: NiBabel coordinate-system documentation. [Open source](https://nipy.org/nibabel/coordinate_systems.html).
[^sitk]: SimpleITK orientation documentation. [Open source](https://simpleitk.org/doxygen/latest/html/classitk_1_1simple_1_1DICOMOrientImageFilter.html).
