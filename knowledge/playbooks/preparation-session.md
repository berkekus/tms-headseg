---
type: Playbook
title: First Preparation Session
description: A bounded pre-implementation session that produces evidence and resolves scope.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T14:40:39+03:00'
sources:
- id: proposal
  resource: ../references/proposal-form.md
  title: Current proposal workflow and evaluation
- id: roadmap
  resource: ../references/module-a-roadmap-revised.md
  title: Revised roadmap preparation phase
---

# First Preparation Session

## Inputs

[Current state](../current.md), [requirements](../scope.md), [latest alignment review](../reviews/roadmap-alignment.md), and the locally available Ernie sample.

## Suggested sequence

1. Inspect supplied MRI, segmentation report, and surfaces. Record what each file represents.
2. Agree which input, output, local API boundary, and inspection journey the first application should support. Keep unresolved choices in the question register.
3. When processing is authorized, execute the separate [Ernie baseline](../experiments/ernie-baseline.md) and capture evidence.
4. Examine geometry and output quality before choosing a meshing/export implementation.
5. Confirm available training compute and inspect one candidate labeled dataset before allocating a full training phase.

## Useful output

A recorded baseline attempt, a source/output inventory, an agreed or explicitly open local interface/dataflow boundary, and updated next actions. Planning notes must not mark a run, dataset audit, or phase complete merely because its instructions exist.

## Discussion prompts

Which manual preparation actions are repeated? Which defects make a surface unusable? Which source anatomy is visible? Which outputs can be checked independently? What minimum integrated inspection satisfies the proposal? Record concrete examples without personal or patient identifiers.

## Related notes

[Open questions](../questions.md) · [Acceptance](../acceptance.md) · [Export proposal](../decisions/003-export-route-proposal.md)
