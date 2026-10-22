---
type: Data Inventory
title: Data and Baseline Inventory
description: Candidate datasets and methods, with availability and annotation limits kept explicit.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: module
  resource: module-a-spec.md
  title: Module A source plan, pp. 6–9
- id: multi
  resource: https://arxiv.org/abs/2501.18716
  title: MultiAxial model/data release paper
- id: ixi
  resource: https://brain-development.org/ixi-dataset/
  title: Official IXI dataset
- id: grace-code
  resource: https://github.com/lab-smile/GRACE/blob/main/LICENSE
  title: GRACE code license
- id: grace-weights
  resource: https://github.com/lab-smile/GRACE/blob/main/MODEL_LICENSE
  title: GRACE weights license
---

# Data and Baseline Inventory

This is a candidate inventory, not evidence that datasets have been downloaded, cleared, split, or labeled. Only the Ernie sample's local presence is recorded.

| Resource | Proposed role | Evidence and open checks |
| --- | --- | --- |
| SimNIBS Ernie sample | Learn input/output and establish geometry/runtime baseline. | Locally present. Supplied mesh is not a new experiment result. Sample README records CC BY-NC 4.0. |
| MultiAxial release | Labeled training and difficult-anatomy evaluation. | Module document proposes about 64 subjects; published study describes 98 MRIs overall. Cohort size, public release size, subjects, and scans must be distinguished by an actual manifest.[^multi] |
| IXI | Candidate additional images for screened pseudo-labels. | Official site provides nearly 600 healthy-subject MR images and T1/T2 downloads. Check each selected scan's coverage and terms.[^ixi] |
| SynthStrip | Brain-mask robustness checks. | Module document proposes it. Six-tissue or facial-surface ground truth is not established by a brain mask. Actual selected release remains unverified. |
| Later institutional data | Optional independent evaluation. | No acquisition or access is assumed; core development uses public data. |

## Label and face audit

For every selected case record a non-identifying case ID, source release, checksum, subject grouping, center where available, shape/spacing, geometry, reference labels, face coverage, and assigned split. An anonymized subject ID can still link repeated scans: split by subject, not filename.

Defaced examples can support eligible brain tests but cannot establish accuracy for missing facial anatomy. Reference-method labels used for training must not be treated as independent proof of matching that method.

## Baseline and model terms

The plan considers CHARM, GRACE, and optionally SPM12. Record failure cases and hardware alongside their conditional accuracy. GRACE source code has an MIT license, while its supplied weights have separate research-use, production, and redistribution restrictions. Code licensing does not establish permission to package the weights.[^grace-code][^grace-weights]

## Related notes

[Source catalog](source-catalog.md) · [Label contract](../concepts/labels-and-face.md) · [Acceptance](../acceptance.md)

[^multi]: MultiAxial paper abstract; it does not establish the contents of a selected downloadable subset. [Open source](https://arxiv.org/abs/2501.18716).
[^ixi]: Official IXI data page. [Open source](https://brain-development.org/ixi-dataset/).
[^grace-code]: GRACE repository LICENSE. [Open source](https://github.com/lab-smile/GRACE/blob/main/LICENSE).
[^grace-weights]: GRACE repository MODEL_LICENSE; inspect the exact model/release terms before use. [Open source](https://github.com/lab-smile/GRACE/blob/main/MODEL_LICENSE).
