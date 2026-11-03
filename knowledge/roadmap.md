---
type: Roadmap
title: Implementation Roadmap
description: Source phase map, data-informed updates, and entry checks; links the Module A start plan; no phase is marked complete.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-23T10:06:38+03:00'
sources:
- id: roadmap
  resource: references/module-a-roadmap-revised.md
  title: Revised Module A coding roadmap, SRC-005
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
- id: team
  resource: references/module-a-roadmap-team-update.md
  title: Latest nineteen-page roadmap, SRC-006
---

# Implementation Roadmap

The technical phase plan below follows SRC-005. The latest received source, SRC-006, keeps that text and expands section 9.2 with four-person work sharing. No start date, deadline, or assignment to a named team member is confirmed; weeks are relative planning units. No application phase is marked complete.[^roadmap][^team]

**To start Module A, follow the [Module A start plan](playbooks/module-a-kickoff.md)**: kickoff decisions, access requests, environment, data intake, label mapping, splits, baseline runs, first-two-week work per role, and the start gate.

| Phase | Source weeks | Intended output | Current evidence or prerequisite |
| --- | --- | --- | --- |
| F0 | 1 | Environment and baseline inventory. | Installation/sample presence observed; processing, timing, and geometry still to demonstrate. GPU access and pinned versions not yet recorded. |
| F1 | 2–3 | Data inventory, label map, subject-level splits. | Drive holds D01 MultiAxial, D04 SimNIBS samples, D05 SynthStrip (131 T1), and a 50-subject IXI subset with checksums; none unpacked or audited by us. Count unique MultiAxial subjects, deduplicate IXI IDs across D05/D06/SHARM, check faces, and write label maps.[^data] |
| F2 | 3–5 | QC-screened pseudo-labels for additional MRI. | Teacher is charm from SimNIBS 4.6. Start with three IXI cases; scale only after review. Drive has 50 IXI subjects; about 50 is the provisional source target, 393 paired subjects exist in the downloaded source part. |
| F3 | 3–4 | Reversible preprocessing and geometry checks. | Proposed [contract v1](concepts/coordinates.md) and lossless reorientation exist in `tools/headmodel`, tested on synthetic data ([D-004](decisions/004-reversible-preprocessing-proposal.md)). `model_io.py prepare`/`restore` round-tripped the real Ernie T1 and labels exactly. A real model round trip is still needed, and E1 inference does not use the carrier yet (effect unmeasured). |
| F4 | 5–7 | Initial segmentation models and validation results. | Tissue validation uses MultiAxial; IXI pseudo-labels are training-only. Fixed E1–E3 splits, validated labels, and suitable compute remain prerequisites. Optional extra labeled source: SHARM (license unverified). |
| F5 | 8–9 | Clean external-head and brain surfaces. | Proposed cleanup and surfaces exist; [EXP-005](experiments/ernie-surface-export.md) measured one supplied head; the airway seal was checked on Ernie ([EXP-006](experiments/ernie-fresh-charm-surfaces.md)) and the MNI152 example ([EXP-007](experiments/mni152-envelope-seal.md)). Still validate them on model predictions and clinical cases. Missing-face detection is not implemented. |
| F6 | 8–9 | QC score and interpretable reports. | Ratify bad-result definitions, supply eligible validation references, and freeze thresholds before testing. Evaluate QC as failure detection (catch and false-alarm rates). |
| F7 | Early spike, then 9–10 | Validated generic export workflow. | Candidate export and independent verification exist; [D-003](decisions/003-export-route-proposal.md) stays proposed. VTK readers accept the files, but no independent viewer has opened them yet. The Workbench exports SimNIBS folders, project labels, and E1 predictions with stated units. |
| F8 | 10–11 | Reproducible comparisons and subgroup reports. | Lock tissue and intact-face test cohorts, independent references, all-case failure accounting, and repeated stage timing. New: CT-derived skull subgroup (D14/D15, not yet in Drive) and SIAM as a comparator if released. |
| F9 | 11–12 | Usable package, model card, docs, demo. | Clean-machine reproduction; UI demonstration also required by the proposal. Model card must state non-commercial data licenses. |

## Data-informed updates (2026-11-02)

The team's data inventory, Module A literature workbook, and the shared Drive archive change the plan in five ways. These are planning changes, not results.[^data]

1. **Data is closer than the plan assumed.** The Module A core sets (D01, D04, D05, D06) are already packaged in Drive with SHA-256 manifests, so F1 starts with unpacking and auditing, not searching.
2. **Faces come only from IXI.** MultiAxial, SynthRAD, and likely the CT-paired sets are defaced. Intact-face calibration and test cohorts must be disjoint IXI subjects.
3. **IXI leakage risk.** IXI subjects appear in D05, D06, and SHARM; split by IXI subject ID across all sources.
4. **New CT-derived skull track.** D14 (Paired Head CT-MRI, CC BY-NC 4.0) and D15 (SynthRAD2023 brain) give skull references independent of charm. They are added to F8 as an evaluation subgroup; they are staged with `tools/data_staging/` but not yet uploaded.
5. **Comparators and teacher version.** Use SimNIBS 4.6 charm (improved skull segmentation) as teacher and comparator; add SIAM if its code/weights are released. GRACE stays research-only.

## Proposed team ownership

The [four-person team plan](team.md) records a rebalanced role proposal (2026-11-02) built on SRC-006: K1 data, nnU-Net dataset conversion, pseudo-labels, and test custody (F1/F2); K2 training and E1–E3 (F4), then the local inference API after the model freeze; K3 coordinates, reversible preprocessing geometry, surfaces, export, and the application viewer (F3/F5/F7); K4 infrastructure, QC, timing, comparators, and frozen evaluation (F6/F8). F0 is shared; F9 packaging is K3 + K4. These are proposed role responsibilities, not named assignments or exclusive implementation boundaries.[^team]

Backup pairs remain K1/K2 and K3/K4, with weekly coordination and milestone demos. Names, capacity, interface acceptance, and dates remain to agree. Usability evaluation and the local-only dataflow check still need an owner.

## Missing work to schedule

The current proposal requires guided local inspection, a documented local API, and local handling/inference without patient-data uploads. The revised phase plan still does not allocate clear UI/API work items or a local-dataflow acceptance check. It also needs an intact-face validation/calibration cohort distinct from the proposed minimum-ten-subject face test cohort. Resolve these before treating twelve weeks as an agreed delivery commitment.[^proposal]

For our project, F0 begins with the independent environment/Ernie baseline; external-system inventory is not a prerequisite under D-002. SRC-005's separate research acceptance supports this adaptation. The old roadmap remains available as [SRC-004](references/module-a-roadmap.md).

## Milestones adapted to current direction

1. Baseline can be reproduced and its output is aligned with the source MRI.
2. First model has validation results on a fixed split.
3. MRI-to-surface pipeline and software-independent export run reproducibly.
4. Local application and API demonstrate import, model inspection, and export with the required dataflow boundary; comparisons are reported.
5. Setup, limitations, evidence, and user documentation are complete.

These milestones are planning proposals. Record completion only with evidence in [experiments](experiments/index.md), and resolve concerns in the [alignment review](reviews/roadmap-alignment.md).

[^roadmap]: Revised coding roadmap, pp. 1–17. This note adapts the source to accepted project direction; it is not a verbatim instruction list. [Open source](references/module-a-roadmap-revised.md).
[^proposal]: Current proposal, pp. 1, 3, and 5. [Open source](references/proposal-form.md).
[^data]: [Data inventory](references/datasets.md), [Drive archive](references/team-drive.md), and [literature map](references/module-a-literature.md), updated 2026-11-02 from SRC-008–SRC-011.
[^team]: SRC-006 section 9.2, pp. 16–18. The surrounding technical plan is unchanged in extracted-text comparison. [Open source](references/module-a-roadmap-team-update.md).
