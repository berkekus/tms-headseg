---
type: Experiment
title: Supplied Dataset003 E3 handoff review
description: Technical inspection of the actual E3 ZIP, including ignore labels, duplicated IXI training entries and fixed validation references.
status: draft
experiment_state: completed_technical_review_only
sources:
- id: supplied
  resource: session
  title: User-supplied handoff_e3.zip on 2026-11-06
- id: preparer
  resource: https://github.com/berkekus/tms-headseg/commit/bfbb98d
  title: E3 preparation code fetched from origin/main
- id: e2
  resource: e2-handoff-review.md
  title: Retained E2 final validation evidence
---

# Supplied E3 handoff review

**Subsequent update:** the [Dataset003 notebook adaptation](e3-dataset003-training.md)
is now prepared and locally checked. References below to a necessary adaptation
describe the initial review state; no GPU training has started.

The user asked whether the newly downloaded data should be uploaded to Drive.
The package is **Dataset003_E3Face**, not the E2 archive assumed by the earlier
[sampler-only E3 preparation](e3-face-weighted-training.md). The previous notebook
does not support this package and must not be used for the intended E3 run.

## Identity and layout

- Supplied folder: `Downloads/drive-download-20261106T160737Z-1-001/`.
- `handoff_e3.zip`: 1,479,086,849 bytes; SHA-256
  `c12f5fb233d829d20bdcc112e412a1eb9fe17158a4a56377cec3e1951eba7698`.
  The companion `.sha256` matches. This is an integrity check, not independent
  authentication of the supplied checksum.
- 216 archive entries, 106 T1/label pairs, one dataset JSON, one fixed split,
  one 106-row manifest and the supplied `BASLA_E3.md`.
- 90 training entries: 44 MultiAxial + 46 IXI entries. There are only 67 distinct
  training people: the same 23 IXI people each have a byte-identical `w2` copy.
- 16 validation people: the same six IXI and ten MultiAxial IDs as E2.
  Total distinct people: 83. Source-person train/validation overlap: none.
- Underlying train/validation lists match the E2 contract exactly. Test/calibration
  subjects are absent. The source person, cohort, copy index and split in every
  manifest row match the actual entries.

## Technical checks and reference comparison

All ZIP members were fully read/extracted with CRC verification. There were no
duplicate archive paths, unsafe paths or symlinks. Every expected image and label
is present. All 83 distinct pairs were read; shapes and affines align, MRI values
are finite and labels are integer-valued. All spatial units are millimetres.
Storage remains mixed: 54 MultiAxial RAS and 29 IXI PSR cases; training needs the
same lossless RAS preparation as E2.

Training labels permit 0–6. `ignore: 6` is **not a seventh predicted tissue**: it
marks exactly-zero image voxels connected to the volume boundary. That rule matches
all 67 distinct training subjects and the manifest's ignored-volume measurements.
All 23 copied image/label pairs match their originals byte-for-byte. Validation
labels contain only 0–5, with no ignore voxels.

Each supplied validation label was losslessly reoriented to RAS and compared with
the retained real E2 validation prediction. All five classes' TP/FP/FN/TN reproduce
the recorded E2 metrics on **all 16 cases**. The original E2 reference files were not
available for direct byte hashing; do not call this independent byte-identity proof.

No technical failures remain in the corrected audit. The initial check incorrectly
expected every zero voxel to be ignored; the actual preparer excludes enclosed
zero-valued components. That initial report is retained separately and the final
audit verifies the precise border-connected rule.

Evidence lives outside Git at
`training-runs/e3-data-audit-20261106-0eb37kl5/audit.json` and the extracted package.
No supplied Markdown commands were executed; `BASLA_E3.md` was treated as source
material. The upstream preparer at `bfbb98d` was read, not executed. Anatomical
accuracy and live nnU-Net preprocessing/training were not established by this review.

## Upload and training consequences

The ZIP and companion SHA file can be uploaded together to the team's Drive, for
example `My Drive/TMS_E3/`. Upload the existing ZIP intact. A training notebook must
still verify the mounted copy's SHA before extraction.

The notebook needs Dataset003, the supplied archive hash and 90/16 entry lists,
ignore-label support, source-group-safe split checks and RAS preparation. Sampling
should be **uniform across the 90 entries**: the data already implements the IXI
weight of 2. Adding the previous custom sampler would double-weight those cases.
Ignore masking plus case duplication means this E3 changes two training factors;
it is not the previous one-variable sampling-only experiment.

The preparer also proposes clearing predictions outside acquisition at inference.
That operation must be recorded and comparison settings matched; it was not applied
or validated by this review. Face-calibration surface references and any acceptance
criteria remain separate from the observed technical checks. No training started.
