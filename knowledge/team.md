---
type: Team Plan
title: Four-Person Team Workstreams
description: Source-proposed responsibilities, weekly handoffs, backup coverage, and unresolved allocation.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-23T10:06:38+03:00'
assignment_state: proposed_unassigned
sources:
- id: team-source
  resource: references/module-a-roadmap-team-update.md
  title: SRC-006, section 9.2, pp. 16–18
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page application proposal
- id: direction
  resource: decisions/002-downstream-independence.md
  title: Accepted downstream independence
- id: user
  resource: references/session-observations.md
  title: Explicit four-person team direction
---

# Four-Person Team Workstreams

**Confirmed:** the user states that four people will work on the project. **Proposed:** the responsibilities and schedule below come from SRC-006 section 9.2. Its person-assignment cells are empty; no member, backup person, workload capacity, start date, or deadline is assigned here. Weeks are relative planning units.[^team-source][^user]

## Role proposal

| Role | Proposed core responsibility | Suggested experience in the source | Named owner |
| --- | --- | --- | --- |
| K1 — Data | F1/F2: inventory, source-label mappings, subject splits, pseudo-label screening, removed-face annotation masks, and intact-face evaluation references. | Careful data handling and management of long-running Linux jobs. | Unassigned |
| K2 — Model | F3/F4: reversible preprocessing, nnU-Net dataset/split generation, E1–E3 training and inference experiments, and model records. | Strongest PyTorch/ML experience in the team. | Unassigned |
| K3 — Surfaces and export | Coordinate-contract stewardship, F5 surfaces/cleanup, F7 generic export and independent alignment checks. | 3D geometry experience. | Unassigned |
| K4 — Quality and evaluation | Repository/test infrastructure, F6 QC, F8 metrics/comparisons, F9 packaging and report coordination. | Software engineering, reproducibility, and test discipline. | Unassigned |

The source additionally assigns external-system inventory and visits to K3. Under accepted D-002, those activities are outside core completion and do not block the independent baseline or export contract. The role table above is an explicit adaptation, not a literal reproduction.[^direction]

## Proposed weekly handoffs

| Weeks | K1 — Data | K2 — Model | K3 — Surfaces/export | K4 — Quality/evaluation |
| --- | --- | --- | --- | --- |
| 1–2 | Obtain candidate data and audit actual contents. | Establish compute and try a small nnU-Net example. | Reconstruct/inspect Ernie and inventory geometry/output files independently. | Prepare repository/test infrastructure and metric interfaces. |
| 3–4 | Subject splits, source-label mapping, initial IXI pseudo-labels, reviewed face masks. | Preprocessing, nnU-Net dataset builder, and custom validation splits. | Coordinate utilities/checks and first Ernie surface extraction. | Synthetic fixtures, development regression cohort, and consistency checks. |
| 5–7 | Screen pseudo-labels and prepare independent intact-face reference masks. | E1–E3 experiments and inference timing. | Validate tissue-specific cleanup, distinguish visible vs removed faces, and build generic surface exports. | QC/uncertainty experiments, corrupted-input development cases, and eligible research comparators. |
| 8–9 | Generate reference-method test predictions under the test-access policy below. | Improve models using training/validation only. | Validate generic export scale, alignment, and orientation; assess optional meshing separately. | Calibrate QC on validation only and record the frozen threshold. |
| 10–11 | Subgroup reports and dataset documentation. | Freeze the final model/settings before test-result access and prepare the model card. | Document independent geometry acceptance and end-to-end stage timing; optional external checks remain separate. | Run frozen evaluation and generate reproducible tables/figures. |
| 12 | Write the data section. | Write the model section. | Write the geometry/export section. | Package, document, and coordinate the final report. |

The source schedule shifts some surface/QC work earlier than the phase chart. Treat it as overlapping preparation, with phase completion still governed by its evidence-based gate. The sequence and workload require team review; no work is marked started or complete.

## Interfaces proposed by the end of week 2

| Interface | Responsible role and consumers | Written handoff |
| --- | --- | --- |
| Data | K1 → K2 | File names, source/target labels, split-manifest schema. |
| Model output | K2 → K3/K4 | Segmentation, probability maps, naming; link the shared grid/frame contract. |
| Coordinates | K3 → all | Shared coordinate contract; K3 reviews code that changes geometry. |
| Metrics | K4 → all | Evaluation-function inputs, outputs, units, and failure representation. |

These are **proposed handoffs**, not contracts already written or accepted. The [coordinate](concepts/coordinates.md) and [measurement](acceptance.md) notes supply the current draft definitions.

## Proposed collaboration rules

- Backup role pairings: K1 ↔ K2 and K3 ↔ K4. Named backups and capacity are still unassigned.
- Another team member reviews each pull request; review rotation gives everyone exposure to adjacent work.
- Hold a weekly progress/blocker discussion and short demos around relative weeks 2, 5, 9, and 11.
- Each person writes the report section for their role; K4 coordinates consistency. Every contributor still owns evidence and documentation for their work.

These rules are imported proposals, not newly configured repository policy. The PDF adds no automatic commit/push rule.

## Allocation issues to settle

1. **Application ownership:** guided MRI/model inspection, the local API, usability evaluation, and local-only deployed dataflow have no explicit owner in section 9.2. Allocate them before accepting the team plan; do not silently add them all to K4.[^proposal]
2. **Workload and backup capacity:** K4 spans infrastructure, QC, comparisons, delivery, and report coordination. Check member availability and redistribute concrete tasks before promising dates. Coordinate stewardship by K3 also needs a workable backup/review path.
3. **Test access:** the source schedules comparator predictions on test subjects while model improvement is ongoing. Precomputing predictions is not itself leakage, but viewing them to tune the model is. Designate a custodian/access rule; freeze model, cleanup, QC, and metric settings before unblinding test results. The development regression cohort must not be the held-out benchmark.
4. **Face references:** K1's intact-face set needs distinct calibration and untouched test subjects; the source's expanded responsibilities do not resolve ALIGN-02.
5. **Team acceptance:** record skills, weekly capacity, chosen owners/backups, approved interfaces, and an agreed start before converting this source proposal into individual commitments.

These are review recommendations, not additional source requirements or accepted assignments. Track unresolved choices in [Q-10 and Q-17](questions.md).

## Related notes

[Source revision](references/module-a-roadmap-team-update.md) · [Roadmap](roadmap.md) · [Current state](current.md) · [Alignment review](reviews/roadmap-alignment.md)

[^team-source]: SRC-006 section 9.2, pp. 16–18. Role/profile and weekly tables begin on p. 16; interfaces and backup pairs appear on p. 17; review/meeting/report rules continue on p. 18. [Open source](references/module-a-roadmap-team-update.md).
[^user]: User explicitly stated that four people will work on the project; names and final allocation were not supplied. [Direction record](references/session-observations.md).
[^direction]: Accepted D-002 keeps core outputs and acceptance independent of any named downstream application. [Decision](decisions/002-downstream-independence.md).
[^proposal]: Current five-page proposal, pp. 1, 3–5, requires the local application/API and local data/inference boundary. [Open source](references/proposal-form.md).
