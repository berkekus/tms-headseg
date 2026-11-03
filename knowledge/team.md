---
type: Team Plan
title: Four-Person Team Workstreams
description: Rebalanced K1–K4 role proposal, 12-week handoffs, interfaces, backups, and unresolved allocation; SRC-006 version kept for provenance.
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

## Rebalanced role proposal (2026-11-02)

This section is the **recommended working version**. It was proposed in a planning session with the user on 2026-11-02 to fix three gaps in SRC-006: the local application/API had no owner, K4 was overloaded, and no test custodian was named. It also spreads K2's work so the model role is not a single point of failure and does not idle after the model freeze. The team has not yet accepted it; names remain unassigned.[^rebalance]

| Role | Core responsibility | Suggested experience | Named owner |
| --- | --- | --- | --- |
| K1 — Data | F1/F2: Drive intake and audit, IXI deduplication, source-label mappings, subject splits, **nnU-Net raw dataset conversion**, charm pseudo-labels and screening, removed-face masks, intact-face references, CT-skull data preparation. **Test custodian.** Co-runs E2 (pseudo-label experiment) with K2. | Careful data handling and long-running Linux jobs. | Berke (user-confirmed 2026-11-02) |
| K2 — Model | F4: GPU environment, nnU-Net training, E1–E3 experiments, model records. After the model freeze (≈ week 8): **local inference API** (model loading, packaging, error/progress behavior) and the model card. | Strongest PyTorch/ML experience. | Unassigned |
| K3 — Geometry and interface | Coordinate-contract stewardship, **F3 geometry part** (reorientation, resampling, and their exact inversion), Ernie baseline, F5 surfaces/cleanup, F7 generic export, **application viewer/UI** for guided inspection. | 3D geometry experience. | Unassigned |
| K4 — Quality and evaluation | Repository/test infrastructure, metrics interface, F6 QC, **stage and inference timing measurements**, comparators (charm 4.6, GRACE, SPM12, SIAM if released), F8 frozen evaluation and CT-skull subgroup. | Software engineering, reproducibility, test discipline. | Unassigned |

Shared: F0 preparation (all), F9 packaging (K3 + K4), final report coordination (rotating; each role writes its own section).

### Changes from SRC-006

| Work item | SRC-006 | Rebalanced | Reason |
| --- | --- | --- | --- |
| nnU-Net dataset builder | K2 | K1 | K1 already owns labels and splits; removes a handoff. |
| Reversible preprocessing (geometry) | K2 | K3 | Coordinate steward owns orientation/inversion. |
| Inference timing | K2 | K4 | One owner for all timing measurements. |
| Local inference API | none | K2 (after week 8) | Uses K2's free capacity after model freeze; needs model knowledge. |
| Application viewer/UI | none | K3 | Displays surfaces and coordinates; a CHARM launcher prototype exists. |
| Test custodian | none | K1 | Must not be the person tuning the model or QC. |
| Packaging, report coordination | K4 | K3 + K4; rotating | K4 overload. |

The source additionally assigns external-system inventory and visits to K3. Under accepted D-002, those activities are outside core completion and do not block the independent baseline or export contract.[^direction]

### Expected load by period (estimate)

| Role | Weeks 1–4 | Weeks 5–7 | Weeks 8–12 |
| --- | --- | --- | --- |
| K1 | High | Medium | Low–medium |
| K2 | Medium | High (mostly GPU wait) | Medium (API, model card) |
| K3 | Medium | Medium | High (export, viewer) |
| K4 | Medium | Medium | High (QC, evaluation) |

The main remaining bottleneck is GPU access, not people: with one GPU, E1–E3 run sequentially (Q-07).

## Rebalanced weekly handoffs

| Weeks | K1 — Data | K2 — Model | K3 — Geometry/interface | K4 — Quality/evaluation |
| --- | --- | --- | --- | --- |
| 1–2 | Unpack and audit Drive data (D01/D04/D05/D06); stage D14/D15; start case manifest. | GPU environment; nnU-Net install; smoke run on a few cases. | EXP-001 Ernie baseline; output and geometry inventory. | Repository/test scaffolding; metrics interface draft; GRACE setup. |
| 3–4 | Label maps, IXI deduplication, subject splits, nnU-Net raw dataset; charm 3-case pilot then batch. | Training configuration; E1 (MultiAxial only) started. | Reversible preprocessing and coordinate checks; first Ernie surface extraction. | Synthetic fixtures, development regression cohort, consistency checks. |
| 5–7 | Screen pseudo-labels; co-run E2 with K2; intact-face reference masks; CT-skull preparation. | E1–E3 experiments. | Class-specific cleanup; visible vs removed face handling; generic surface exports. | QC/uncertainty experiments; corrupted-input cases; comparators; inference timing. |
| 8–9 | Comparator test predictions held under custodian rule. | Improve on training/validation only; freeze model; start local inference API. | Export scale/alignment/orientation validation; application viewer. | Calibrate QC on validation only; record frozen threshold. |
| 10–11 | Release test data only after freeze; subgroup reports; dataset documentation. | Inference API complete; model card. | Viewer integrated with API; geometry acceptance documentation. | Frozen evaluation incl. CT-skull subgroup; tables/figures; stage timing. |
| 12 | Data section. | Model section. | Geometry/interface section. | Evaluation section; packaging with K3. |

No work is marked started or complete. Phase completion is still governed by each phase's evidence gate.

## Original SRC-006 proposal (provenance)

SRC-006 section 9.2 proposed: K1 F1/F2 data work; K2 F3/F4 including reversible preprocessing, nnU-Net dataset/split generation, E1–E3, and inference timing; K3 coordinates, F5 surfaces, F7 export; K4 infrastructure, F6 QC, F8 comparisons, F9 packaging and report coordination. The rebalanced version above keeps this structure and moves only the items in the change table.[^team-source]

## Interfaces proposed by the end of week 2

| Interface | Responsible role and consumers | Written handoff |
| --- | --- | --- |
| Data | K1 → K2 | nnU-Net raw dataset layout, file names, source/target labels, split-manifest schema. |
| Model output | K2 → K3/K4 | Segmentation, probability maps, naming; link the shared grid/frame contract. |
| Inference API (by week 8) | K2 → K3 | Call/service shape, inputs, outputs, errors, progress and cancellation (Q-13). |
| Coordinates | K3 → all | Shared coordinate contract; K3 reviews code that changes geometry. |
| Metrics | K4 → all | Evaluation-function inputs, outputs, units, and failure representation. |

These are **proposed handoffs**, not contracts already written or accepted. The [coordinate](concepts/coordinates.md) and [measurement](acceptance.md) notes supply the current draft definitions.

## Proposed collaboration rules

- Backup role pairings: K1 ↔ K2 and K3 ↔ K4. Named backups and capacity are still unassigned.
- Another team member reviews each pull request; review rotation gives everyone exposure to adjacent work.
- Hold a weekly progress/blocker discussion and short demos around relative weeks 2, 5, 9, and 11.
- Each person writes the report section for their role; consistency coordination rotates (rebalanced proposal; SRC-006 gave it to K4). Every contributor still owns evidence and documentation for their work.

These rules are imported proposals, not newly configured repository policy. The PDF adds no automatic commit/push rule.

## Allocation issues to settle

1. **Application ownership:** the rebalanced proposal gives the local inference API to K2 and the viewer/UI to K3. Usability evaluation and the local-only dataflow check still need an owner (suggested: K4, as evaluation work).[^proposal]
2. **Workload and backup capacity:** the rebalanced proposal moves packaging and report coordination off K4. Still check member availability before promising dates. K3's coordinate stewardship needs a reviewer from K4 (backup pair).
3. **Test access:** the rebalanced proposal names K1 as custodian. Precomputing comparator predictions is not leakage, but viewing them to tune the model is. Freeze model, cleanup, QC, and metric settings before unblinding test results. The development regression cohort must not be the held-out benchmark.
4. **Face references:** K1's intact-face set needs distinct calibration and untouched test subjects; the source's expanded responsibilities do not resolve ALIGN-02.
5. **Team acceptance:** record skills, weekly capacity, chosen owners/backups, approved interfaces, and an agreed start before converting this source proposal into individual commitments.

These are review recommendations, not additional source requirements or accepted assignments. Track unresolved choices in [Q-10 and Q-17](questions.md).

## Related notes

[Source revision](references/module-a-roadmap-team-update.md) · [Roadmap](roadmap.md) · [Start plan](playbooks/module-a-kickoff.md) · [Current state](current.md) · [Alignment review](reviews/roadmap-alignment.md)

[^rebalance]: Planning session with the user, 2026-11-02: the user asked whether K2 was overloaded and could be split; the recommendation was to redistribute K2 sub-tasks rather than assign two people. Team acceptance is pending (Q-10).

[^team-source]: SRC-006 section 9.2, pp. 16–18. Role/profile and weekly tables begin on p. 16; interfaces and backup pairs appear on p. 17; review/meeting/report rules continue on p. 18. [Open source](references/module-a-roadmap-team-update.md).
[^user]: User explicitly stated that four people will work on the project; names and final allocation were not supplied. [Direction record](references/session-observations.md).
[^direction]: Accepted D-002 keeps core outputs and acceptance independent of any named downstream application. [Decision](decisions/002-downstream-independence.md).
[^proposal]: Current five-page proposal, pp. 1, 3–5, requires the local application/API and local data/inference boundary. [Open source](references/proposal-form.md).
