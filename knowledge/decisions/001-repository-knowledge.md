---
type: Decision
title: 'D-001: Shared Repository Knowledge'
description: Accepted location, language, and lightweight authoring approach.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
decision_id: D-001
decision_state: accepted
sources:
- id: session
  resource: ../references/session-observations.md
  title: User direction and observed local state
---

# D-001: Shared Repository Knowledge

Decision state: **accepted by explicit user direction**. This written record itself has not received a separate human review.

## Choice

Keep the project knowledge base in `knowledge/` inside the existing repository. Use English Markdown, standard relative links, and minimal OKF v0.2 metadata. Obsidian is an optional editor/viewer over the same files.

## Basis and consequences

The user requested a second brain before implementation and selected English. Repository storage makes changes inspectable alongside project work. Notes remain usable through ordinary editors and file search. Each task should load an index and the relevant notes, not the full corpus.

Keep scientific results linked to evidence, source snapshots identified, and proposed decisions visibly separate from accepted ones. Raw MRI, large model artifacts, private transcripts, and machine-specific editor state are not knowledge-note content.

## Related notes

[Session direction](../references/session-observations.md) · [Maintenance](../playbooks/knowledge-maintenance.md) · [Obsidian setup](../playbooks/obsidian-setup.md)
