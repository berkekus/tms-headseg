# TMS HeadSeg

**Module A: Fast Head Model Generation for TMS Neuronavigation**

TMS HeadSeg is a research prototype plan for generating a patient-specific head model from a routine T1-weighted MRI. Module A connects AI-assisted segmentation, surface generation, interactive inspection, and software-independent export. The module roadmap proposes a trained nnU-Net segmenter; the exact implementation and training scope remain planning decisions.

The document describes a planned system. This repository currently contains no application code, trained weights, datasets, or dependency manifests. Performance figures below are provisional targets, not achieved results. All outputs require clinician review; the system is not for autonomous clinical decisions.

The latest received nineteen-page roadmap, [SRC-006](knowledge/references/module-a-roadmap-team-update.md), expands the [four-person team proposal](knowledge/team.md). Its technical text outside section 9.2 matches the earlier seventeen-page SRC-005 after normalization. The [alignment review](knowledge/reviews/roadmap-alignment.md) retains remaining gaps; source roles and targets do not establish team approval or named assignments.

## Project knowledge

Start with the [knowledge map](knowledge/index.md) and [current state](knowledge/current.md). The English knowledge base records source revisions, requirements, decisions, open questions, and experiment evidence. Follow the [Obsidian setup guide](knowledge/playbooks/obsidian-setup.md) to open the same files as a vault.

## Module A scope

Module A is a standalone head-modeling deliverable. It covers:

- T1 MRI import, including DICOM-to-NIfTI conversion.
- Six-class tissue segmentation.
- Face-inclusive skin and brain surface generation.
- Guided local inspection alongside source MRI, including 3D rotation and zoom within one application.
- A documented local API for model preparation and export.
- Local patient-image/model handling and AI inference without uploads to external services.
- Automated quality checks and low-confidence warnings.
- Software-independent surface export, with optional reference-tool meshing.
- Evaluation on held-out subjects, including lesion cases where data allow.

Module A does **not** include landmark detection (Module B), TMS target selection (Module C), electric-field calculation, changes to external navigation applications, or other system integration work (Module D). It produces model inputs for existing navigation software.

## Planned workflow

```text
T1 MRI (DICOM or NIfTI)
  -> convert, reorient, resample to 1 mm, correct intensity variation
  -> nnU-Net tissue segmentation
  -> skin and brain surface extraction and cleanup
  -> confidence, tissue-volume, and mesh-integrity checks
  -> low confidence: warn operator; otherwise inspect and export models
```

Preprocessing must preserve the original image geometry and map outputs back into the patient's coordinate system. Coordinate and orientation checks are required throughout the pipeline; a misplaced or mirrored surface can make a model unusable for navigation.

### Segmentation labels

The model will assign each voxel to one of six classes:

1. Air
2. Skin
3. Skull
4. Cerebrospinal fluid (CSF)
5. Gray matter
6. White matter

Skin surface must include available facial anatomy to support subsequent head-to-image alignment. Skull and CSF labels support accurate tissue boundaries even though electric-field modeling is outside this module.

### Surface generation and quality control

Generate face-inclusive skin and brain meshes from eligible inputs. Cleanup rules must be class-specific and validated; component removal, hole filling, and smoothing can alter anatomy. A proposed quality score combines model confidence with tissue-volume and surface-integrity checks. Results below a calibrated threshold must be flagged for operator review rather than exported without a visible warning.

## Model export

The project is independent of a particular downstream application. Define outputs through their geometry, units, coordinate convention, and alignment with the source MRI.

Separate external-head and brain surfaces in `.stl` or `.ply`, accompanied by explicit spatial metadata, are candidate initial exports. Validate scale, orientation, and overlay alignment in an independent viewer before accepting an export contract. Keep the segmentation and reference-image identity available for traceability.

SimNIBS remains an optional baseline, pseudo-labeling tool, and label-to-mesh reference. A volume-mesh route is optional and requires a demonstrated use case and runtime budget. The final export strategy remains a [proposed decision](knowledge/decisions/003-export-route-proposal.md).

## Planned tools

| Component | Planned tools |
| --- | --- |
| Main language and segmentation | Python, nnU-Net, PyTorch |
| MRI conversion and preprocessing | dcm2niix, nibabel, SimpleITK |
| Surface extraction and export | scikit-image, PyVista/VTK |
| Pseudo-labels, benchmark, SimNIBS route | SimNIBS/charm |
| Visual inspection | 3D Slicer |
| Comparison methods | charm, SPM12, GRACE, and another documented reference workflow when available |

These are proposed tools, not installed dependencies. GRACE is reserved for research comparison in the module specification; do not make deployment depend on its weights or license.

## Data plan

Use public datasets for development. Keep all splits subject-level, distribute acquisition centers across splits, and do not use the held-out test set for tuning.

The descriptions below summarize the module plan. Actual release contents, selected counts, and face coverage remain subject to the [data inventory](knowledge/references/datasets.md).

| Dataset | Planned role | Notes from the module specification |
| --- | --- | --- |
| MultiAxial | Primary labeled training, validation, and test data | About 64 T1 scans across healthy and clinical cases, three centers, and six labels. Faces are defaced, so this dataset alone cannot teach face-skin segmentation. |
| IXI | Add healthy-subject and scanner diversity | About 600 unlabeled scans; selected cases may be labeled with charm for training. Verify face coverage and label mapping before use. |
| SynthStrip | Robustness evaluation | 622 scans with brain masks; labels do not match the six-class scheme. |
| SimNIBS “ernie” sample | Early timing and generic export/geometry test | Use to verify project structure and coordinate alignment. |
| Hospital T1 scans | Optional real-world evaluation | The plan proposes 5–10 scans, only after ethics approval and applicable KVKK/privacy requirements. The core module does not depend on hospital access. |

The proposed initial split uses roughly 44 MultiAxial subjects for training and 10 each for validation and test, plus a small IXI training subset labeled by charm. Final counts and dataset terms must be checked before data preparation. Test subjects must remain isolated from training and model selection.

### Face-coverage strategy

Check facial coverage per case. Image-based boundary extraction can use only anatomy still present in the scan. Defaced or cropped examples cannot establish the quality of missing patient-specific facial anatomy. Evaluate suitable face-preserved data separately, subject to data terms.

## Evaluation plan and provisional targets

Report results per tissue and subject, and separate lesion cases and acquisition centers. Compare against charm, SPM12, and GRACE on the same test subjects; compare with another documented preparation workflow where available. GRACE remains a research-only comparator per the module plan.

| Measure | Proposal in SRC-005, unchanged in SRC-006; not approved or achieved |
| --- | --- |
| End-to-end runtime | GPU at most 60 seconds, NIfTI input through export; report stages separately. CPU at most 10 minutes is informational. |
| Dice | Skin and brain union at least 0.90; WM 0.85; GM 0.80; skull 0.75; CSF 0.70. Include all test cases. |
| Skin-surface distance | Whole-head mean at most 1.5 mm; intact-face/ear regional mean at most 2.0 mm. |
| Failure rate | At most 5%; report every comparison method's failures. |
| Quality control | Recall at least 80%; false-alarm rate at most 20%; calibrate on validation and freeze before testing. |
| Export validity | Geometry opens with documented scale, orientation, and source-image alignment in an independent viewer |

See [acceptance and measurement definitions](knowledge/acceptance.md) for source pages, earlier targets, failure accounting, timing boundaries, and unresolved metric choices. The revised plan proposes at least ten intact-face evaluation subjects with manually corrected skin references independent of charm. Keep face calibration separate from untouched test subjects. Report clinical/healthy and center subgroups alongside averages. UI/API, usability, and local-processing acceptance remain required beyond CLI delivery.

## Risks and safeguards

- **Defaced faces:** test both face-surface completion strategies; never assume body-surface quality from brain-only scores.
- **Lesions and scan variability:** evaluate clinical cases and centers separately; augment training data and compare with charm.
- **Label mismatch:** define and freeze a six-class mapping between MultiAxial and charm labels before combining data.
- **Coordinate errors:** preserve transforms, check orientation at every stage, and visually verify output on the “ernie” integration case.
- **Limited GPU or storage:** the plan recommends an NVIDIA GPU with at least 8 GB VRAM (12 GB or more preferred), 16 GB RAM for charm workloads, and tens of GB of storage. University GPU resources, TRUBA, or Colab are proposed alternatives.
- **Ethics and privacy:** use public data for core development. Use hospital scans only after required approvals.
- **Integration uncertainty:** validate generic image/surface alignment early; define the export contract before committing to a meshing route.

## Proposed 12-week sequence

1. **Weeks 1–2:** verify charm runtime and exported geometry; obtain sample data; begin ethics review.
2. **Weeks 3–4:** build preprocessing, label mapping, and subject-level splits; start IXI pseudo-labeling.
3. **Weeks 5–7:** train baseline nnU-Net, then evaluate the value of IXI pseudo-labels.
4. **Weeks 8–9:** implement surfaces, face-skin completion, and quality checks.
5. **Week 10:** verify the generic export contract and run benchmark comparisons.
6. **Week 11:** run hospital-data evaluation only if approval is available; finish ablations.
7. **Week 12:** report results and prepare delivery.

## Development setup

No runtime or launch commands exist yet. Add installation, inference, training, and evaluation instructions when the code and dependency versions are committed. The planned stack above does not imply that dependencies are installed.

Clone the repository:

```bash
git clone https://github.com/berkekus/tms-headseg.git
cd tms-headseg
```

The clone configures `origin` and tracks the remote default branch. A typical feature-branch workflow:

```bash
git pull --ff-only
git switch -c feature/short-description
# Make and commit changes
git push -u origin feature/short-description
```

Pushing requires GitHub authentication and repository write access.

## References

1. [Project source catalog](knowledge/references/source-catalog.md), including the current proposal and Module A planning documents.
2. Puonti O. et al. “Accurate and robust whole-head segmentation from magnetic resonance images for individualized head modeling.” *NeuroImage*. 2020;219:117044. [doi:10.1016/j.neuroimage.2020.117044](https://doi.org/10.1016/j.neuroimage.2020.117044).
3. Birnbaum AM. et al. “Full-head segmentation of MRI with abnormal brain anatomy: model and data release.” *Journal of Medical Imaging*. 2025;12(5):054001. [doi:10.1117/1.JMI.12.5.054001](https://doi.org/10.1117/1.JMI.12.5.054001).
4. Stolte SE. et al. “Precise and rapid whole-head segmentation from magnetic resonance images of older adults using deep learning (GRACE).” *Imaging Neuroscience*. 2024. [GRACE repository](https://github.com/lab-smile/GRACE).
5. Isensee F. et al. “nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation.” *Nature Methods*. 2021;18:203–211. [nnU-Net repository](https://github.com/MIC-DKFZ/nnUNet).
6. Hoopes A. et al. “SynthStrip: skull-stripping for any brain image.” *NeuroImage*. 2022;260:119474.
7. Nieminen AE. et al. “Accuracy and precision of navigated transcranial magnetic stimulation.” *Journal of Neural Engineering*. 2022. [doi:10.1088/1741-2552/aca71a](https://doi.org/10.1088/1741-2552/aca71a).
