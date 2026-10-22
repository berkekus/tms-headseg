---
type: Reference
title: Module A Revised Coding Roadmap
description: Seventeen-page planning revision, its additions, and limits on adoption.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T14:40:39+03:00'
source_id: SRC-005
source_pages: 17
source_sha256: 3d0c8ea550db65bc28012057894e0fa8df7c426742617e9f4791d9e8eddd2eea
approval_state: not_recorded
sources:
- id: SRC-005
  resource: 'User-provided PDF: tms-modul-a.pdf; SHA-256 3d0c8ea550db65bc28012057894e0fa8df7c426742617e9f4791d9e8eddd2eea'
  title: Module A Revised Coding Roadmap
---

# Module A Revised Coding Roadmap

Received on 2026-10-22. This seventeen-page proposal expands the [earlier twelve-page roadmap](module-a-roadmap.md). It supplies clearer engineering and evaluation definitions; receipt does not establish team approval, completed implementation, or measured performance.

| Pages | Relevant content |
| --- | --- |
| 1–3 | F0–F9 over twelve proposed weeks; numerical acceptance proposals and a pre-test threshold-freezing rule. |
| 4–5 | RAS+ world millimetres, NIfTI affine, SimpleITK LPS and array order, centralized conversions, and three coordinate checks. |
| 6–7 | Subject/center/coverage inventory, fixed splits, screened pseudo-labels for training only, reversible preprocessing, and stage timing. |
| 8–10 | nnU-Net internal validation layout, inventory-derived counts, `ignore: 6`, training-only IXI, fixed E1–E3 comparisons, conditional low-resolution configuration, and a proposed 30-second inference budget. |
| 10–11 | Class-specific cleanup, volume-change checks, exclusive labels, distinct visible-vs-removed face handling, and surface generation. |
| 12 | Entropy and geometric QC, validation-only threshold calibration, corruption-specific evaluation, and per-case HTML reports. |
| 13–14 | Independent geometry acceptance, expert-corrected tissue references, a separate intact-face cohort, complete failure accounting, repeated stage timing, and paired comparisons. |
| 14–17 | CLI/container packaging, reproducibility records, proposed tests and workstreams, risks, and separate research vs external-integration completion criteria. |

## Interpretation for this project

- Numerical targets remain proposals. [Acceptance](../acceptance.md) records the latest values and remaining measurement decisions; earlier values remain attributable to SRC-002.
- Keep the user-approved [downstream independence](../decisions/002-downstream-independence.md). Product-specific inventory, import, and external-system milestones in the source do not become core prerequisites.
- The research completion criteria fit our independent-output direction. The five-page proposal still additionally requires the local application, local API, and local data/inference boundary.
- Repository rename, package layout, tooling, branch policies, environments, and twelve-week assignments remain suggestions. No such changes were executed during document import.
- Several earlier concerns are addressed in the revised text, but contradictions and validation gaps remain. Use the [alignment review](../reviews/roadmap-alignment.md) before applying examples.

## Related notes

[Source catalog](source-catalog.md) · [Phase map](../roadmap.md) · [Acceptance](../acceptance.md) · [Earlier review](../reviews/roadmap-review.md)
