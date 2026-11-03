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

The `model_io.py` command line adds thirteen tests: RAS output, labels on the image grid, charm mapping before the move, trailing singleton axes, rejected grids and labels, no overwrite, no output inside Git, a rejected off-grid prediction, a sheared source, and a command-line round trip. Eleven injected defects were all caught. On real headers (2026-11-03), the public Ernie T1 (PSR, 256 × 256 × 208) and its EXP-001 charm labels went to RAS (208 × 256 × 256), SimpleITK read the prepared file at 1 mm spacing, and `restore` returned exactly the mapped labels with 0.0 mm corner disagreement. This was a file round trip with the labels standing in for a prediction; no model ran.

## Handoffs

| Role | What this asks for |
| --- | --- |
| K1 | Done on 2026-11-03, per the K1 log: `tools/nnunet_prep` writes `mm` units with coded qform and sform, and the rebuilt files pass `read_source` without warnings. The five sheared NYU source affines are kept in `original_affines.json`; NYU009 is one of them and sits in the test hold-out, so its millimetre metrics must use that saved affine. Pending: pass IXI scans (PSR) and their charm labels through `model_io.py prepare --label-scheme charm` before E2, so MultiAxial (RAS) and IXI share one axis order. The command exists from 2026-11-03 (see the [headmodel README](../../tools/headmodel/README.md)). |
| K2 | Run inference on `model_io.py prepare` output and bring results back with `model_io.py restore`. Confirm on a smoke run that nnU-Net 2.8.1 returns predictions on the input grid. Open gap (2026-11-03): the Workbench **04 E1 segmentation** tab and `demo.py predict` pass the MRI to nnU-Net as stored, so a PSR scan such as IXI or Ernie reaches the RAS-trained E1 in a different axis order. Whether this lowers E1's output is not measured; see the comparison proposed in [D-004](../decisions/004-reversible-preprocessing-proposal.md). |
| K4 | Compute millimetre metrics in world from source-grid labels, not from carrier files. |

MultiAxial's paper says RSA while file headers say RAS, and K1 follows the header. K1's left–right check supports it indirectly: lesion CSF lies on the header's left in 51 of 54 training and validation cases and on the right in none, as expected for aphasia-causing strokes (see the [data inventory](../references/datasets.md)). An anterior–superior swap, which RSA would imply, would be obvious in a viewer; one look at a case would close that question.

## Related notes

[Reversible preprocessing proposal](../decisions/004-reversible-preprocessing-proposal.md) · [Acceptance](../acceptance.md) · [Review](../reviews/roadmap-review.md) · [Ernie protocol](../experiments/ernie-baseline.md)

[^nib]: NiBabel coordinate-system documentation. [Open source](https://nipy.org/nibabel/coordinate_systems.html).
[^sitk]: SimpleITK orientation documentation. [Open source](https://simpleitk.org/doxygen/latest/html/classitk_1_1simple_1_1DICOMOrientImageFilter.html).
[^slicer]: Slicer coordinate-system documentation, section "Coordinate system convention in Slicer". [Open source](https://slicer.readthedocs.io/en/latest/user_guide/coordinate_systems.html).
[^nnunet-io]: `reader_writer_registry.py`, `simpleitk_reader_writer.py`, and `nibabel_reader_writer.py`, read from the `master` branch on 2026-11-02. [Open source](https://github.com/MIC-DKFZ/nnUNet/tree/master/nnunetv2/imageio).
