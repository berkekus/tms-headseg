---
type: Roadmap
title: Implementation Roadmap
description: Source phase map, dependencies, and entry checks; no phase is marked complete.
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

| Phase | Source weeks | Intended output | Current evidence or prerequisite |
| --- | --- | --- | --- |
| F0 | 1 | Environment and baseline inventory. | Installation/sample presence observed; processing, timing, and geometry still to demonstrate. |
| F1 | 2–3 | Data inventory, label map, subject-level splits. | Confirm actual release contents, face coverage, and permitted use. |
| F2 | 3–5 | QC-screened pseudo-labels for additional MRI. | Start with three cases; scale only after reviewing output. Source target of at least 50 is provisional. |
| F3 | 3–4 | Reversible preprocessing and geometry checks. | Define image/label spaces and conversion boundaries first. |
| F4 | 5–7 | Initial segmentation models and validation results. | Tissue validation uses MultiAxial; IXI pseudo-labels are training-only. Fixed E1–E3 splits, validated labels, and suitable compute remain prerequisites. |
| F5 | 8–9 | Clean external-head and brain surfaces. | Validate class-specific cleanup, label exclusivity, actual-grid affine handling, and missing-face flags. |
| F6 | 8–9 | QC score and interpretable reports. | Ratify bad-result definitions, supply eligible validation references, and freeze thresholds before testing. |
| F7 | Early spike, then 9–10 | Validated generic export workflow. | Adapt source-specific deployment steps to D-002; check geometry independently. |
| F8 | 10–11 | Reproducible comparisons and subgroup reports. | Lock tissue and intact-face test cohorts, independent references, all-case failure accounting, and repeated stage timing. |
| F9 | 11–12 | Usable package, model card, docs, demo. | Clean-machine reproduction; UI demonstration also required by the proposal. |

## Proposed team ownership

The [four-person team plan](team.md) records the latest role and weekly handoff proposal: K1 owns the data workstream (F1/F2), K2 preprocessing/model work (F3/F4), K3 coordinates/surfaces/generic export (F5/F7), and K4 quality/evaluation/delivery (F6/F8/F9), with shared F0 preparation. These are proposed role responsibilities, not named assignments or exclusive implementation boundaries.[^team]

Section 9.2 proposes four written interfaces by the end of relative week 2, backup pairs K1/K2 and K3/K4, weekly coordination, and milestone demos. Names, capacity, allocation, interface acceptance, and dates remain to agree. Application/API work remains unassigned; do not infer that K4 owns it.

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
[^team]: SRC-006 section 9.2, pp. 16–18. The surrounding technical plan is unchanged in extracted-text comparison. [Open source](references/module-a-roadmap-team-update.md).
