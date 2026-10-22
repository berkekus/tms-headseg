---
type: Roadmap
title: Implementation Roadmap
description: Source phase map, dependencies, and entry checks; no phase is marked complete.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: roadmap
  resource: references/module-a-roadmap.md
  title: Module A coding roadmap
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
---

# Implementation Roadmap

The source proposes twelve weeks and F0–F9. No start date, deadline, or assignment to a named team member is confirmed; weeks are relative planning units. No application phase is marked complete.[^roadmap]

| Phase | Source weeks | Intended output | Current evidence or prerequisite |
| --- | --- | --- | --- |
| F0 | 1 | Environment and baseline inventory. | Installation/sample presence observed; processing, timing, and geometry still to demonstrate. |
| F1 | 2–3 | Data inventory, label map, subject-level splits. | Confirm actual release contents, face coverage, and permitted use. |
| F2 | 3–5 | QC-screened pseudo-labels for additional MRI. | Start with three cases; scale only after reviewing output. Source target of at least 50 is provisional. |
| F3 | 3–4 | Reversible preprocessing and geometry checks. | Define image/label spaces and conversion boundaries first. |
| F4 | 5–7 | Initial segmentation models and validation results. | Fixed splits, validated labels, and suitable compute. |
| F5 | 8–9 | Clean external-head and brain surfaces. | Class-specific cleanup and a documented spatial contract. |
| F6 | 8–9 | QC score and interpretable reports. | Define unusable output and select thresholds on validation only. |
| F7 | Early spike, then 9–10 | Validated generic export workflow. | Adapt source-specific deployment steps to D-002; check geometry independently. |
| F8 | 10–11 | Reproducible comparisons and subgroup reports. | Lock test set and failure accounting. |
| F9 | 11–12 | Usable package, model card, docs, demo. | Clean-machine reproduction; UI demonstration also required by the proposal. |

## Missing work to schedule

The current proposal requires guided local inspection, a documented local API, and local handling/inference without patient-data uploads. The phase plan does not allocate clear UI/API work items or a local-dataflow acceptance check. Resolve this before treating twelve weeks as an agreed delivery commitment.[^proposal]

## Milestones adapted to current direction

1. Baseline can be reproduced and its output is aligned with the source MRI.
2. First model has validation results on a fixed split.
3. MRI-to-surface pipeline and software-independent export run reproducibly.
4. Local application and API demonstrate import, model inspection, and export with the required dataflow boundary; comparisons are reported.
5. Setup, limitations, evidence, and user documentation are complete.

These milestones are planning proposals. Record completion only with evidence in [experiments](experiments/index.md), and resolve concerns in the [review](reviews/roadmap-review.md).

[^roadmap]: Coding roadmap, pp. 1–12. This note is an adaptation, not a verbatim instruction list. [Open source](references/module-a-roadmap.md).
[^proposal]: Current proposal, pp. 1, 3, and 5. [Open source](references/proposal-form.md).
