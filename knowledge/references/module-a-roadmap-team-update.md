---
type: Reference
title: Module A Roadmap Team Update
description: Nineteen-page revision with an expanded four-person work-sharing section.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-23T10:06:38+03:00'
source_id: SRC-006
source_pages: 19
source_sha256: 17e66a62d5a9e9b68982d6d9fe1a17a87288418da805ff064520b9e5e7dfb906
approval_state: not_recorded
sources:
- id: SRC-006
  resource: 'User-provided PDF: tms-modul-a (1).pdf; SHA-256 17e66a62d5a9e9b68982d6d9fe1a17a87288418da805ff064520b9e5e7dfb906'
  title: Module A Roadmap Team Update
- id: previous
  resource: module-a-roadmap-revised.md
  title: Previous seventeen-page roadmap, SRC-005
---

# Module A Roadmap Team Update

Received on 2026-10-23. This is a nineteen-page revision of the previously inspected seventeen-page [SRC-005](module-a-roadmap-revised.md), not a separate project plan. The PDF export metadata is dated 2026-10-22; neither export nor receipt establishes approval.

## What changed

The extracted text before section 9.2 and from section 9.3 onward matches SRC-005 after removing repeated page headers, page-number footers, and whitespace. The changed text is section 9.2, expanded from a short role table into a detailed team proposal. Role and schedule tables on pp. 16–17 were also inspected visually; the assigned-person cells are empty.

| Pages | Content and revision significance |
| --- | --- |
| 1–15 and start of 16 | Existing F0–F9 plan, numerical proposals, geometry, training, cleanup, QC, evaluation, packaging, and test strategy; no extracted-text change before section 9.2. |
| 16–18, section 9.2 | Expanded K1–K4 responsibilities and suggested profiles; week-by-week work; four interfaces proposed for the end of week 2; backup pairings, review, meetings, demos, and report ownership. |
| 18, section 9.3 | Existing risk table, now on a later page. The failed-case exclusion contradiction remains. |
| 18–19, section 9.4 | Existing separate research and external-integration completion criteria; no extracted-text change. |

## Interpretation

- [Team workstreams](../team.md) is the canonical English adaptation of the new section. All K1–K4 person assignments, backup assignments, dates, and operating rules remain proposed.
- The user has confirmed a four-person team. This does not name the members or accept the PDF's proposed distribution.
- Keep [D-002](../decisions/002-downstream-independence.md): adapt the surface/export role to independent geometry and generic outputs. External-system activities in the source are not prerequisites for core work.
- Numeric targets and technical procedures are unchanged, so their existing [acceptance definitions](../acceptance.md) and [alignment concerns](../reviews/roadmap-alignment.md) still apply. Earlier page citations remain explicitly tied to SRC-005.
- The new schedule still leaves application/UI, local API, and deployed local-dataflow work without explicit owners. A proposed quality/evaluation role is not evidence those requirements have been allocated.
- Importing the source does not configure branch protection, install hooks, run tests, assign people, create issues, or authorize model runs.

## Related notes

[Source catalog](source-catalog.md) · [Team workstreams](../team.md) · [Roadmap](../roadmap.md) · [Alignment review](../reviews/roadmap-alignment.md)
