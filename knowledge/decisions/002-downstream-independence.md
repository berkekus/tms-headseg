---
type: Decision
title: 'D-002: Downstream Independence'
description: Accepted requirement to avoid dependence on a particular external application.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
decision_id: D-002
decision_state: accepted
sources:
- id: session
  resource: ../references/session-observations.md
  title: User direction and observed local state
---

# D-002: Downstream Independence

Decision state: **accepted by explicit user direction** on 2026-10-22.

## Choice

Define the project through MRI input, reconstructed geometry, inspection, QC, and documented outputs. Do not make scope, acceptance, or open questions depend on the identity/version of an external application.

## Consequences

- Generic export formats, coordinate conventions, units, and source-image alignment form the output contract.
- Tool-specific deployment assumptions in older source plans are not adopted.
- SimNIBS remains a candidate baseline and meshing/reference tool, not a required consumer of project outputs.
- Independent viewers may validate geometry; a particular consumer integration is not required for core completion.
- Exact generic output formats still need a recorded implementation decision.

## Related notes

[Session direction](../references/session-observations.md) · [Requirements](../scope.md) · [Export proposal](003-export-route-proposal.md)
