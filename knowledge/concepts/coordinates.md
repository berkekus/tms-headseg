---
type: Concept
title: Geometry and Coordinate Contract
description: Proposed coordinate contract v1, with measured library behavior, implemented checks, and team handoffs.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-02T23:00:00+03:00'
contract_state: proposed_v1
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
- id: slicer
  resource: https://slicer.readthedocs.io/en/latest/user_guide/coordinate_systems.html
  title: 3D Slicer coordinate systems
- id: nnunet-io
  resource: https://github.com/MIC-DKFZ/nnUNet/tree/master/nnunetv2/imageio
  title: nnU-Net image readers (master branch)
---

# Geometry and Coordinate Contract

Contract state: **proposed v1**, written by K3 on 2026-11-02. It is the coordinates handoff named in the [team plan](../team.md); the team has not accepted it yet. The rules are implemented and tested in [`tools/headmodel`](../../tools/headmodel/README.md). SRC-005 pp. 4–5 supplied the starting proposal: RAS+ millimetres, NIfTI affines, LPS at ITK boundaries, and NumPy `(z, y, x)` order from SimpleITK.[^nib][^sitk]

## Frames

| Name | Definition | Used by |
| --- | --- | --- |
| Source voxel | `(i, j, k)` array index in the input file, 0-based, at the voxel center. | Input files and restored labels. |
| World | RAS+ millimetres given by the source affine after unit normalization. | Everything in project code, and all exported geometry. |
| Canonical voxel | Source array with axes permuted and flipped toward RAS+, without interpolation. | Model input and output. An oblique scan keeps an oblique affine. |
| Model carrier | Canonical grid with an orthonormal affine that ITK can read. | The file nnU-Net sees. Never used for millimetre measurement. |
| ITK physical | LPS millimetres; arrays in `(k, j, i)` order. | Only at ITK boundaries, through `headmodel.frames`. |

## Rules

1. **World is RAS+ millimetres.** Convert to LPS only at an ITK boundary. RAS and LPS differ by the signs of the first two coordinates.
2. **Every writer states its geometry.** NIfTI files carry `mm` units and matching coded qform and sform. `headmodel.images.write_nifti` does this; the NiBabel default leaves the units unknown and omits the qform.
3. **Undefined geometry is rejected.** Unknown units, no coded form, a singular or non-finite affine, or non-finite voxels stop processing with a reason. Guessing millimetres is not allowed.
4. **The sform wins when both forms are coded, and disagreement is reported.** A difference above the world tolerance becomes a visible warning.
5. **Geometry travels with voxel indices.** Reorientation is an exact permutation and flip. Labels return to the source grid voxel for voxel, then the source affine maps them to world. This is why a carrier affine can be approximate without moving the result.
6. **Shear is preserved, not corrected.** A sheared source affine stays the world mapping. Only the carrier affine is replaced by the nearest rotation at the same spacing, and the source keeps a warning.
7. **ITK-based tools never read a raw source file.** They read the carrier, which has a single geometry. See the measured behavior below.
8. **A model output must stay on the carrier grid.** Shape and affine are checked; a mismatch is an error, not a resampling step.
9. **Mesh vertices come from the affine of the grid they were extracted on.** Marching cubes runs in voxel units, so spacing is applied exactly once. See ALIGN-05 in the [alignment review](../reviews/roadmap-alignment.md).
10. **Exports name their frame.** A file that carries geometry declares RAS and millimetres. 3D Slicer assumes LPS unless a file states otherwise, so an unlabeled RAS surface would open with its first two axes reversed.[^slicer]

## Measured library behavior

Observed on 2026-11-02 with SimpleITK 2.5.7 and NiBabel 5.4.2 on synthetic files. These are behavior observations, not evidence about any dataset.

| Case | NiBabel | SimpleITK |
| --- | --- | --- |
| qform and sform both coded and different | Uses the sform. | Uses the qform, so the same file has two world positions. |
| Sheared sform with a valid qform | Uses the sform. | Silently uses the qform. |
| Sheared sform, no coded qform | Reads it. | Rejects the file. This matches the five NYU cases K1 reported. |
| Writer defaults | Units unknown, qform code 0, sform code 2. | Units `mm`, qform and sform code 1. |

The nnU-Net `master` branch reads NIfTI through `SimpleITKIO`, which does not reorient. `SimpleITKIOWithReorient` and `NibabelIOWithReorient` exist as options. The installed 2.8.1 release was not inspected.[^nnunet-io]

## Tolerances

Proposed values, to be confirmed when real data is measured:

| Check | Tolerance |
| --- | --- |
| Reorientation round trip | Exact array equality. |
| Same voxel across libraries, or carrier vs model output | 0.01 mm at the image corners. |
| Shear flag | 0.001 in direction-cosine orthonormality, matching K1's threshold. |
| qform/sform disagreement warning | 0.01 mm at the image corners. |

## Implemented checks

`tools/headmodel` tests cover RAS/LPS round trips, one voxel read by both libraries on an oblique, non-unit, translated grid, ITK array order, all 48 axis orientations for exact restoration and world position, an asymmetric phantom whose ear and nose keep their sides, sheared sources through a real SimpleITK read and write, and rejected inputs. Seventeen deliberately injected geometry defects were all caught by the suite. These are synthetic checks; nothing here validates a real scan.

## Handoffs

| Role | What this asks for |
| --- | --- |
| K1 | Set `mm` units in `tools/nnunet_prep`, because MRI Workbench and `read_source` reject the current output. Pass IXI scans (PSR) through `canonicalize` before adding them to `Dataset001`, so MultiAxial (RAS) and IXI share one axis order in E2. Keep original affines for millimetre measurements of the five sheared NYU cases. Check whether any of them fall in the test hold-out. |
| K2 | Run inference on `write_model_input` output and bring results back with `read_model_output`. Confirm on a smoke run that nnU-Net 2.8.1 returns predictions on the input grid. |
| K4 | Compute millimetre metrics in world from source-grid labels, not from carrier files. |

K1's facts above come from its unmerged `feat/k1-data-intake` branch. MultiAxial's paper says RSA while file headers say RAS; K1 follows the header, and this still needs one anatomical check in a viewer.

## Related notes

[Reversible preprocessing proposal](../decisions/004-reversible-preprocessing-proposal.md) · [Acceptance](../acceptance.md) · [Review](../reviews/roadmap-review.md) · [Ernie protocol](../experiments/ernie-baseline.md)

[^nib]: NiBabel coordinate-system documentation. [Open source](https://nipy.org/nibabel/coordinate_systems.html).
[^sitk]: SimpleITK orientation documentation. [Open source](https://simpleitk.org/doxygen/latest/html/classitk_1_1simple_1_1DICOMOrientImageFilter.html).
[^slicer]: Slicer coordinate-system documentation, section "Coordinate system convention in Slicer". [Open source](https://slicer.readthedocs.io/en/latest/user_guide/coordinate_systems.html).
[^nnunet-io]: `reader_writer_registry.py`, `simpleitk_reader_writer.py`, and `nibabel_reader_writer.py`, read from the `master` branch on 2026-11-02. [Open source](https://github.com/MIC-DKFZ/nnUNet/tree/master/nnunetv2/imageio).
