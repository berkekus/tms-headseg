---
type: Project State
title: Current State
description: Start here for confirmed direction, evidence gaps, and the next useful action.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T14:40:39+03:00'
sources:
- id: session
  resource: references/session-observations.md
  title: User direction and local observations
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
- id: revised
  resource: references/module-a-roadmap-revised.md
  title: Revised seventeen-page roadmap
---

# Current State

Last substantive update: 2026-10-22. Project stage: preparation and baseline exploration.

## Confirmed direction

- This knowledge base is entirely in English and lives beside the project in Git.
- Outputs and acceptance criteria are independent of any particular downstream application.
- Module A is the current implementation focus. Optional targeting work does not determine its completion.
- Preserve source claims, proposals, decisions, and measured results as distinct records.

The first two choices come directly from the user; document review is not implied.[^session]

## Evidence available

- Four project PDFs have been inspected and fingerprinted in the [source catalog](references/source-catalog.md), including the newly received seventeen-page `tms-modul-a.pdf` (SRC-005).
- The current proposal is five pages and requires one local application, a documented local API, local inference/data handling, and interactive inspection. The coding roadmap primarily describes a CLI; UI/API and local-dataflow work remain to schedule.[^proposal]
- The revised roadmap clarifies coordinates, validation splits, class-specific cleanup, face coverage, numerical targets, and benchmark failures. These are source-level improvements, not approved thresholds or validated implementations. Remaining contradictions are recorded in the [alignment review](reviews/roadmap-alignment.md).[^revised]
- A local SimNIBS 4.6 installation directory and the Ernie sample files were inspected. Successful execution has not been demonstrated in this session.[^session]
- No application source, trained project model, evaluation result, or implementation completion has been established.

## Next useful action

Follow the [Ernie baseline protocol](experiments/ernie-baseline.md): inspect the supplied model, run a separate T1-only reconstruction when authorized, and record elapsed time, logs, outputs, and observed defects. Its current state is **not run**, not successful.

## Decisions and unresolved work

- [Accepted project direction](decisions/index.md): repository knowledge and downstream independence.
- [Open questions](questions.md): interaction scope, data, geometry, metrics, compute, ownership, and dates.
- [Latest alignment review](reviews/roadmap-alignment.md): source-level corrections and remaining issues; the [earlier review](reviews/roadmap-review.md) preserves SRC-004 history.
- [Requirements](scope.md) and [acceptance definitions](acceptance.md): source-backed intentions, with provisional targets explicitly marked.

## Reading budget

Read this page and [the map](index.md), then the notes relevant to the task. No full-vault loading or chronological chat dumps are needed. Update this page when the next action, confirmed direction, or evidence changes; preserve experiment details in the experiment note.

[^session]: See the session observation record for the evidence and its limits. [Open source](references/session-observations.md).
[^proposal]: Current proposal, pp. 1, 3, and 5; see its source note and checksum. [Open source](references/proposal-form.md).
[^revised]: Revised roadmap, pp. 2–5, 8–14, and 17. [Open source](references/module-a-roadmap-revised.md).
