---
type: Reference
title: Module A Literature Map
description: Which literature candidates inform each Module A phase, and which claims still need full-text checks.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-02T18:00:00+03:00'
sources:
- id: candidates
  resource: source-catalog.md#src-009-module-a-literature-candidates-workbook
  title: Module A literature candidates workbook, SRC-009 (A01–A50)
- id: snowball
  resource: source-catalog.md#src-010-snowball-workbook
  title: Snowball workbook, SRC-010 (#113–#132)
- id: review
  resource: source-catalog.md#src-012-systematic-literature-review
  title: Systematic literature review, SRC-012
---

# Module A Literature Map

The team's Module A search (SRC-009) lists 50 candidates (A01–A50) with suggested decisions; the snowball sheet (SRC-010) adds #113–#132 to the main review (SRC-012). Status and reviewer columns are empty: no candidate has a recorded full-text decision. Many results are filled from abstracts and many authors/DOIs are marked "to verify". Treat every number below as a workbook claim until the full text is checked.[^candidates]

## By phase

| Phase | Candidates to read first | What they give the plan |
| --- | --- | --- |
| F1 data | A02 MultiAxial, A05 SHARM, A32 DBB, A47 head-model population, A29 MIDA | Main labels; extra labeled/pseudo-labeled sources; distorted-anatomy test set; detailed non-brain reference. |
| F2 pseudo-labels | A09 charm, A18 subcutaneous fat (SimNIBS 4.6), A47 | Teacher choice: use charm from SimNIBS 4.6, not older headreco. |
| F3–F4 models | A01 GRACE, A06 SIAM, A07 SynthSeg, A25 synthetic stroke, A04 ForkNet, A40 calibration | Comparators; synthetic-training alternative; scanner shift; Dice+CE vs calibration. |
| Skull accuracy | A13 CT-label MRI skull (DSC 0.864 on MRI), A14 CT-like bone from T1, A19 skull assessment, A21/A22 pseudo-CT | Motivates the CT-derived skull track (D14–D17) and its metrics. |
| F5 surfaces | A43 TopoFit, A44–A46 | Only needed if brain surfaces show topology defects. |
| F6 QC | A27 Bayesian QuickNAT, A37 failure-detection benchmark, A38 QC as failure detection, A39 SegQC, A41 corruption types/severities | Image-level failure score, evaluation by catch/false-alarm rates, corrupted-input set design. |
| F8 evaluation | A28 Metrics Reloaded, A34/A35 test-time and few-shot adaptation | Metric choice rationale; scanner-adaptation experiments. |
| F9 delivery | A42 regulatory lifecycle; standards sheet (IEC 62304, ISO 14971, IEC 62366-1, MDR Rule 11, KVKK) | Lightweight traceability and risk records; awareness only, not certification scope. |

## Points that affect decisions

- **SIAM (A06, 2026 preprint)** segments 16 head structures from synthetic training on six templates and was evaluated on 301 scans. It is the strongest direct competitor and should be a comparator if its code/weights are released; check before F4 freezes comparators.
- **charm version matters (A18).** Comparisons and teacher labels should use SimNIBS 4.6, which includes the improved skull segmentation; record the exact version.
- **QC is a failure detector (A38, A37).** Report catch rate and false-alarm rate at a frozen threshold, not only correlation with Dice. This matches the revised roadmap's QC acceptance.
- **Literature counter-view (#56).** One reviewed study argues that segmentation-free head models can be more accurate in tumor patients; mention it in discussion.
- **Out of Module A scope:** A49/A50 (facial landmarks, Module B), #113–#129 navigation/targeting work (Modules B–D).

## Related notes

[Data inventory](datasets.md) · [Start plan](../playbooks/module-a-kickoff.md) · [Acceptance](../acceptance.md)

[^candidates]: `docs/ModulA_Literatur_Adaylari.xlsx`, sheets 1_ModulA_Adaylar and 2_Notlar; `docs/snowball.xlsx`; `docs/literature-review.md` sections 8–10. [Catalog](source-catalog.md).
