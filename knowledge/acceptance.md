---
type: Evaluation Plan
title: Acceptance and Measurement Definitions
description: Distinguish proposed thresholds, product acceptance, and measured evidence.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T14:40:39+03:00'
sources:
- id: module
  resource: references/module-a-spec.md
  title: Module A concept specification
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
- id: roadmap
  resource: references/module-a-roadmap-revised.md
  title: Revised Module A coding roadmap, SRC-005
---

# Acceptance and Measurement Definitions

No project performance measurements are recorded yet. The latest source proposes the targets below; team approval and final measurement definitions are not recorded.[^roadmap] Receipt of a revised PDF does not freeze an experiment protocol.

## Latest numerical proposal: SRC-005

| Item | Current proposal | Definition still needed |
| --- | --- | --- |
| End-to-end GPU runtime | At most 60 seconds, NIfTI input through export; report preprocessing, inference, surfaces, QC, and export separately. | Hardware, warm/cold loading, report-generation inclusion, batch size, failures, and timing implementation. DICOM conversion and operator interaction need separate workflow timing. |
| End-to-end CPU runtime | Report separately; at most 10 minutes is informational. | Same boundaries and hardware record; not a mandatory GPU-equivalent gate. |
| Tissue Dice | Skin at least 0.90; brain union (GM + WM) at least 0.90; WM at least 0.85; GM at least 0.80; skull at least 0.75; CSF at least 0.70. Include all test cases. | Per-subject aggregation and cohort summaries, absent/ignored labels, background exclusion, and eligible reference regions. Brain union is an additional metric, not a seventh model class. |
| Whole-head skin surface distance | Mean at most 1.5 mm. | Symmetric vs directed mean, surface sampling/weighting, anatomical boundaries, missing outputs, and separate HD95 definition. |
| Face/ear skin surface distance | Mean at most 2.0 mm on eligible intact-face subjects. | Fixed regional masks/landmarks, independent references, and distinct calibration/test cohorts. |
| Failure rate | At most 5%; report for every method. | Explicit unusable-output adjudication, denominator, and exclusion rules fixed before testing. |
| QC recall | At least 80% of bad results flagged. | Bad-result labels, no-output alerts, per-case denominator, uncertainty, and subgroup reporting. |
| QC false-alarm rate | At most 20% of good results flagged. | Define as flagged good cases divided by all good cases; not the fraction of alerts that are wrong. Freeze threshold using validation only. |
| Difficult anatomy | Compare against reference methods on clinical subgroups. | Subgroup definitions and predeclared meaning of non-inferior performance. |
| Operator benefit | Reduce preparation time and manual steps. | Same scans and tasks; separate operator interaction time from compute time. |
| Usability | Guided, learnable local inspection and export. | Record task completion, time, errors, repeated-attempt learnability, and perceived ease of use, as required by proposal p. 5. |

SRC-005 pp. 2–3 supplies the numerical targets; pp. 13–14 supplies measurement procedures. Operator benefit and usability remain proposal requirements, not new numerical thresholds. Earlier SRC-002 proposed mean Dice at least 0.85 and skin distance under 2 mm without these regional/per-class distinctions.[^module] Preserve those as historical targets; do not mix them with the new proposal as simultaneous acceptance gates.

### Preregistration and intermediate gates

- SRC-005 proposes freezing thresholds before viewing test results, with at most one documented validation-driven revision before testing. Record the versioned protocol and rationale; this has not happened yet.
- F4 proposes per-tissue validation Dice meeting the final targets or falling no more than 0.03 below them, and GPU inference at most 30 seconds. This intermediate inference budget does not establish the 60-second end-to-end target.
- F5 proposes a warning above 2% tissue-volume change, but also a completion gate allowing no tissue above 2%. The policy, denominator, and class-specific tolerances remain unresolved; see ALIGN-04 in the [alignment review](reviews/roadmap-alignment.md).

### QC reference labels

The proposed bad-result rule is: any tissue Dice below its target minus 0.05, face/ear mean distance above 3 mm, or no output (SRC-005 p. 3). Ratify boundary comparisons and how the brain-union metric participates. Define eligibility when a region/reference is unavailable; missing facial anatomy must remain visibly flagged rather than being assigned a passing face score.

Calibration needs both good and bad validation cases with suitable references. Report recall and false alarms per corruption type and on the untouched test set. If no threshold satisfies both targets on validation, record the unmet target; do not search test results for a replacement. A no-output case must trigger a pipeline error/alert even when entropy cannot be computed.

## Geometry and functional acceptance

- Source MRI, segmentation, and surfaces retain documented physical scale and alignment.
- Synthetic asymmetric fixtures check orientation and left/right consistency; measure coordinate errors, not just appearance.
- Source-image and model inspection, rotation/zoom, and export are demonstrated within the local application.[^proposal]
- The local API has a documented request/result/error contract and checks for representative and invalid inputs.[^proposal]
- Patient images, derived models, and AI inference remain local; the deployed workflow is checked for external transmission of those artifacts.[^proposal]
- Exports have a documented coordinate/unit contract and align in an independent viewer. Acceptance does not depend on a named downstream product.
- Cropped or defaced inputs cannot silently count as valid full-face reconstructions.
- An unsuccessful case remains in failure-rate reporting. Accuracy among completed cases is identified as conditional accuracy.

## Evaluation boundaries

Training and validation may guide design; held-out test results must not guide postprocessing, QC thresholds, or model selection. E1–E3 comparisons use the same validation and test subjects. SRC-005 proposes MultiAxial-only tissue validation and training-only IXI pseudo-labels. Dataset identities, releases, and disjoint subject lists remain to verify.

Use expert-corrected tissue labels for tissue accuracy. SRC-005 proposes at least ten intact-face subjects not used for training, with threshold-derived skin references manually corrected in 3D Slicer and independent of charm. Reserve an untouched face test cohort and a separate calibration cohort; the source has not fully specified this split. Record reference-maker/reviewer protocol and regional masks before comparison. Pseudo-labels are not independent ground truth for accuracy claims.

Retain every benchmark subject for every method. The source requests failure rate, all-case Dice (no output receives zero), and successful-only Dice. Decide how unusable-but-present outputs and absent reference classes contribute before testing. Missing-surface distances are unavailable plus a recorded failure, never zero. Rejection of corrupt pseudo-labels from training does not authorize removing benchmark failures.

The revised roadmap proposes three timing repeats on the same documented hardware, reporting the median, separate CPU/GPU results, stage totals, clinical/healthy and center subgroups, and paired E1–E3 comparisons. Specify handling of repeated failures and model loading as part of the protocol. Store commands, settings, input identifiers, and output paths in each [experiment](experiments/index.md); do not fill a result cell with a target.

## Related notes

[Scope](scope.md) · [Latest alignment review](reviews/roadmap-alignment.md) · [Open questions](questions.md)

[^module]: Module A specification, pp. 7–9; thresholds are described as provisional. [Open source](references/module-a-spec.md).
[^proposal]: Current proposal, pp. 1, 3, and 5. [Open source](references/proposal-form.md).
[^roadmap]: Revised coding roadmap, pp. 2–3, 10–14, and 17. Numbers are starting proposals, not accepted or achieved results. [Open source](references/module-a-roadmap-revised.md).
