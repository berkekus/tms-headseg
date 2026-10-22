---
type: Playbook
title: Maintaining Project Knowledge
description: Authoring and retrieval rules that keep evidence current without loading every note.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: okf
  resource: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md
  title: OKF v0.2 specification
---

# Maintaining Project Knowledge

## Read

Start at [the map](../index.md) and [current state](../current.md), then follow task-relevant links. Search a topic or ID when needed. Do not preload every source, meeting, or experiment.

## Record

Give each note one purpose. Use full English prose, stable filenames, and ordinary relative Markdown links. Each concept has YAML `type`, `title`, `description`, and a lifecycle `status`; source-backed claims carry `sources` and page/section references where available. Root `index.md` declares OKF 0.2; reserved indexes and logs follow their own minimal structure.[^okf]

Lifecycle status is not evidence strength. A drafted requirement, accepted choice, observed filesystem fact, and measured result must be identified in the body or purpose-specific state field. Do not invent a human verification event. Add formal `verified` metadata only when verification actually occurred, following the spec.

## Update after meaningful work

- New source: record artifact identity/revision and create a concise source note.
- New observation: state what was inspected and what it does not establish.
- New experiment: capture command, inputs, environment, logs, outputs, and measurements; record failures.
- New choice: update a decision record with who accepted it and the actual evidence; proposals remain proposed.
- Changed next action or confirmed scope: update current state and linked requirements.
- Source conflict: retain both claims with provenance and resolve explicitly; file recency alone is not approval.

Keep one canonical location for each detailed record; index/state pages summarize and link. Add a brief entry to [the log](../log.md) for substantive knowledge changes. Preserve prior experiment attempts rather than overwriting results.

## Check before sharing

Check frontmatter, relative links, source references, state labels, and consistency between current state and the decision register. A future source edit should not silently overwrite the fingerprint of a previously cited artifact. Keep raw scans, large weights, private transcripts, and local editor state outside tracked notes.

## Templates

[Reference](../templates/reference.md) · [Decision](../templates/decision.md) · [Experiment](../templates/experiment.md)

[^okf]: Official Open Knowledge Format v0.2 specification; this project adds lightweight conventions and does not require an OKF runtime service. [Open source](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md).
