---
type: Project State
title: Current State
description: Start here for confirmed direction, evidence gaps, and the next useful action.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: session
  resource: references/session-observations.md
  title: User direction and local observations
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
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

- Three project PDFs have been inspected and fingerprinted in the [source catalog](references/source-catalog.md).
- The current proposal is five pages and requires one local application, a documented local API, local inference/data handling, and interactive inspection. The coding roadmap primarily describes a CLI; UI/API and local-dataflow work remain to schedule.[^proposal]
- A local SimNIBS 4.6 installation directory and the Ernie sample files were inspected. Successful execution has not been demonstrated in this session.[^session]
- No application source, trained project model, evaluation result, or implementation completion has been established.

## Next useful action

Follow the [Ernie baseline protocol](experiments/ernie-baseline.md): inspect the supplied model, run a separate T1-only reconstruction when authorized, and record elapsed time, logs, outputs, and observed defects. Its current state is **not run**, not successful.

## Decisions and unresolved work

- [Accepted project direction](decisions/index.md): repository knowledge and downstream independence.
- [Open questions](questions.md): interaction scope, data, geometry, metrics, compute, ownership, and dates.
- [Roadmap review](reviews/roadmap-review.md): technical concerns that are not resolved by importing the PDF.
- [Requirements](scope.md) and [acceptance definitions](acceptance.md): source-backed intentions, with provisional targets explicitly marked.

## Reading budget

Read this page and [the map](index.md), then the notes relevant to the task. No full-vault loading or chronological chat dumps are needed. Update this page when the next action, confirmed direction, or evidence changes; preserve experiment details in the experiment note.

[^session]: See the session observation record for the evidence and its limits. [Open source](references/session-observations.md).
[^proposal]: Current proposal, pp. 1, 3, and 5; see its source note and checksum. [Open source](references/proposal-form.md).
