---
type: Observation Record
title: User Direction and Local Observations
description: Separate explicit choices, filesystem evidence, and unmeasured results.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-23T10:06:38+03:00'
evidence_kind: mixed_explicit_direction_and_observation
sources:
- id: session
  resource: User messages and bounded local filesystem inspection on 2026-10-22; team discussion reviewed on 2026-10-23
  title: Project conversation and local inspection
---

# User Direction and Local Observations

Filesystem evidence date: 2026-10-22. User-direction summary updated on 2026-10-23. This record summarizes the current project conversation and limited local inspection. It is not a raw chat transcript or a record of institutional approval.

| ID | Statement | Evidence kind | Limit |
| --- | --- | --- | --- |
| USER-01 | Build a project second brain in repository Markdown/OKF. | Direct user request. | Does not authorize implementation of every task in an attached PDF. |
| USER-02 | Write the entire knowledge base in English. | Direct user answer. | Technical filenames and commands are also English. |
| USER-03 | Keep the project independent of a particular downstream application. | Direct user answer. | No product-specific integration dependency is adopted. |
| USER-04 | Four people will work on the project; discuss work sharing and capture relevant source updates in the knowledge base. | Direct user statement and subsequent document-review request. | Names, skills, capacities, actual role assignments, and delivery dates were not supplied. Source-proposed roles are not accepted assignments. |
| OBS-01 | A SimNIBS-4.6 directory with `bin/charm` and the GUI exists locally on Apple Silicon. | Filesystem inspection in this conversation. | Not a successful launch, benchmark, CUDA check, or model run. |
| OBS-02 | Sample `org/` contains T1 and T2 MRI; `m2m_ernie/` contains a mesh, labels, surfaces, and HTML report. | Filesystem inspection. | These are supplied example outputs, not new project results. |
| OBS-03 | Example README says its Ernie model used FreeSurfer-assisted reconstruction; example dataset terms are CC BY-NC 4.0. | Local sample README. | Do not assume identical geometry from a new 4.6 run or generalize terms to other data. |
| OBS-04 | Application source and trained project weights are not present in the inspected repository. | Repository file inventory before this knowledge base was added. | Future changes require updating current state. |

## Source revision observation

During creation, the proposal file changed from the fingerprinted four-page snapshot to a five-page snapshot. The current source note summarizes the captured five-page revision and retains the earlier observed fingerprint. A source document describing an approval process is not proof that approval or data access was obtained.

## Not established

Ernie runtime, quality scores, a successful complete reconstruction, training access, final team roles, and approved delivery dates have not been recorded. No result should be inferred from the presence of installed binaries or supplied example files.

## Portability

Local installation and data paths differ by machine. The [baseline protocol](../experiments/ernie-baseline.md) uses environment variables rather than recording a collaborator's home directory.

## Related notes

[Current state](../current.md) · [Decisions](../decisions/index.md) · [Catalog](source-catalog.md)
