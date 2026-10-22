---
type: Playbook
title: Open This Knowledge Base in Obsidian
description: Use the existing repository files as a vault without a second note copy.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: storage
  resource: https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data
  title: Obsidian Markdown/vault storage
- id: links
  resource: https://help.obsidian.md/Linking+notes+and+files/Internal+links
  title: Obsidian standard Markdown links
---

# Open This Knowledge Base in Obsidian

1. In Obsidian choose **Open folder as vault** and select this repository's `knowledge` directory.
2. Open `index.md`, then `current.md`.
3. In **Settings → Files and links**, disable **Use Wikilinks** so newly created links use ordinary Markdown paths. Enable automatic link updates when renaming files.
4. Use links, backlinks, search, and Graph view to navigate; the notes remain editable through any text editor.

Obsidian stores notes as local Markdown and its vault settings in `.obsidian/`. That local directory is ignored by the repository; no plugin installation is required.[^storage][^links]

## Collaboration

Pull other contributors' changes before editing shared notes and review overlapping changes. Git remains the sharing mechanism; opening the folder does not itself publish anything. Prefer editing the relevant topic note over repeatedly appending to the same shared current-state page. Do not keep a second independently edited vault copy of these notes.

Store internal attachments only when appropriate to share and actually referenced. Source PDF summaries are linked through the [catalog](../references/source-catalog.md); the original project PDFs are currently external artifacts.

## Related notes

[Map](../index.md) · [Maintenance](knowledge-maintenance.md) · [Decision D-001](../decisions/001-repository-knowledge.md)

[^storage]: Official Obsidian storage documentation. [Open source](https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data).
[^links]: Official Obsidian internal-link documentation. [Open source](https://help.obsidian.md/Linking+notes+and+files/Internal+links).
