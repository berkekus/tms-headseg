# TMS HeadSeg

**AI-assisted 3D brain and face modeling for TMS planning**

TMS HeadSeg is a proposed software system for creating patient-specific 3D brain and face models from MR images. Its core goal is to bring image import, segmentation, surface reconstruction, interactive inspection, and model export into one workflow that can support preparation for an existing neuronavigation system.

This repository is an early project scaffold. It does not yet contain an implementation or a selected software stack.

## Project goals

The core project will:

- Import and inspect MR images.
- Segment brain and face anatomy.
- Reconstruct patient-specific 3D surfaces.
- Provide interactive 3D visualization for model inspection.
- Export reconstructed models for use in the existing neuronavigation workflow.
- Preserve image and model coordinates throughout processing, visualization, and export.

The project aims to reduce manual model-preparation effort. It is a planning and modeling tool; it is not described as a diagnostic system or a source of clinical decisions.

## Planned workflow

```text
MR image
   -> import and validation
   -> brain and face segmentation
   -> 3D surface reconstruction
   -> interactive inspection
   -> model export
```

The proposal does not specify supported MR formats, export formats, or the neuronavigation system's interface. These need to be selected and documented during implementation.

## Scope

### Core deliverable

The project is considered complete when the MR-to-3D modeling workflow is implemented and evaluated:

1. MR image import.
2. Automatic brain and face reconstruction.
3. Interactive model inspection.
4. Model export.
5. Testing and project documentation.

### Optional extension

AI-assisted peak mapping and candidate stimulation-target suggestions may be added to the reconstructed brain model for user review. This work is optional and will be evaluated separately; the core deliverable does not depend on it.

## Data and evaluation

Development and initial evaluation will use publicly available imaging datasets. The core workflow should not depend on access to hospital data.

Evaluation should use subject-level test splits to avoid leakage between training and test subjects. Depending on available reference annotations, planned measures include:

- Segmentation Dice score and surface error.
- Reconstruction quality.
- Processing runtime.
- MR import, model viewing, and export functionality.

If the optional target-suggestion extension is implemented, evaluate it separately from the core modeling workflow.

## Engineering challenges

- MR scan quality and anatomy can vary.
- Some scans may not include complete face coverage.
- Public datasets may have limited labels.
- Surface reconstruction must remain usable for inspection and export.
- Image, model, visualization, and exported coordinates must stay consistent.

Use suitable public datasets and reference methods to manage these risks. The core project can proceed without hospital access.

## Development setup

No application dependencies, runtime, or launch commands are defined yet. Add installation and run instructions after selecting the implementation stack and adding the application entry point.

Clone the repository:

```bash
git clone https://github.com/berkekus/tms-headseg.git
cd tms-headseg
```

The clone configures `origin` to the GitHub repository and tracks its default branch. A typical feature-branch workflow:

```bash
git pull --ff-only
git switch -c feature/short-description
# Make and commit changes
git push -u origin feature/short-description
```

Pushing requires GitHub authentication and write access to the repository. Use the project's agreed branch and review process when one is established.

## Project status

Initial repository setup. Application code, dependency manifests, dataset configuration, and automated evaluation are not present yet.

## References

1. Kim et al. (2016). *Neuronavigation-guided rTMS for Aphasia*. [doi:10.3791/53345](https://doi.org/10.3791/53345).
2. Ronneberger et al. (2015). *U-Net: Convolutional Networks for Biomedical Image Segmentation*. [arXiv:1505.04597](https://arxiv.org/abs/1505.04597).
3. [SimNIBS documentation](https://simnibs.github.io/simnibs/), referenced in the proposal for TMS coil-position optimization.
