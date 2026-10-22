---
type: Requirements
title: Project Scope and Requirements
description: Traceable modeling requirements with explicit module boundaries and a pending UI decision.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
sources:
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
- id: module
  resource: references/module-a-spec.md
  title: Module A concept specification
- id: direction
  resource: decisions/002-downstream-independence.md
  title: Accepted software-independent output direction
---

# Project Scope and Requirements

Goal: reduce operator preparation time and manual corrections when constructing patient-specific brain and external-head surfaces from structural MRI. The engineering scope connects import, model creation, inspection, and spatially consistent export.[^proposal]

These are requirements extracted from project documents, not claims that a feature exists or that the documents have received formal approval.

| ID | Requirement | Source and proposed evidence |
| --- | --- | --- |
| REQ-01 | Import MRI and reject unusable inputs clearly. | Proposal p. 5; document accepted inputs and failure cases. |
| REQ-02 | Produce brain and external-head surfaces, including the facial region where the input contains it. | Proposal pp. 1, 5; inspect surfaces separately. |
| REQ-03 | Use AI-assisted segmentation. | Proposal p. 5; record model/version and reference labels. The module plan proposes a six-class nnU-Net model. |
| REQ-04 | Provide guided local inspection alongside source images, 3D rotation/zoom, clear processing feedback, and consistent controls. | Proposal pp. 1, 3, 5; task-based demonstration in one application. |
| REQ-05 | Preserve orientation, physical scale, and source-image alignment through export. | Proposal p. 5; numerical and visual geometry checks. |
| REQ-06 | Provide software-independent exports with an explicit coordinate and unit contract. | User direction; see D-002. |
| REQ-07 | Provide meaningful QC information and warnings. | Module specification pp. 4–5; evaluate against a defined failure set. |
| REQ-08 | Evaluate quality, runtime, memory, failures, operator time, and manual interventions. | Proposal p. 5; see acceptance definitions. |
| REQ-09 | Deliver reproducible setup, tests, and user documentation. | Proposal p. 5 and roadmap pp. 10–12. |
| REQ-10 | Expose a documented local API for model preparation and export. | Proposal pp. 3–5; verify representative and invalid inputs. |
| REQ-11 | Keep patient images, derived models, and AI inference local without external uploads. | Proposal pp. 3–5; inspect the deployed dataflow and check representative executions. |

## Boundaries

Module A includes preparation, segmentation, reconstruction, inspection, QC, and export. Automatic landmark detection and target selection are separate modules. Electric-field calculation and clinical treatment decisions are outside this core implementation. The proposal's optional peak mapping must not delay core delivery.[^module]

## Unresolved implementation choices

The current roadmap's CLI is useful for reproducibility but does not on its own demonstrate REQ-04. UI framework, local API interface, deployment/dataflow boundary, supported input subset, final export formats, and exact label mapping remain decisions to make. Existing tool names in source documents describe candidate components, not mandatory application dependencies.

## Related notes

[Acceptance](acceptance.md) · [Roadmap](roadmap.md) · [Pipeline](concepts/pipeline.md) · [Questions](questions.md) · [Downstream independence](decisions/002-downstream-independence.md)

[^proposal]: Current project proposal, pp. 1–5; source note below. [Open source](references/proposal-form.md).
[^module]: Module A concept specification, pp. 1, 4–5, 11. [Open source](references/module-a-spec.md).
