---
type: Project State
title: Current State
description: Start here for confirmed direction, evidence gaps, and the next useful action.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-23T10:06:38+03:00'
sources:
- id: session
  resource: references/session-observations.md
  title: User direction and local observations
- id: proposal
  resource: references/proposal-form.md
  title: Current five-page project proposal
- id: revised
  resource: references/module-a-roadmap-revised.md
  title: Revised seventeen-page roadmap
- id: team
  resource: references/module-a-roadmap-team-update.md
  title: Latest nineteen-page roadmap and expanded team proposal
---

# Current State

Last substantive update: 2026-11-02. Project stage: preparation; Module A start plan written, not started.

## Confirmed direction

- This knowledge base is entirely in English and lives beside the project in Git.
- Outputs and acceptance criteria are independent of any particular downstream application.
- Module A is the current implementation focus. Optional targeting work does not determine its completion.
- Preserve source claims, proposals, decisions, and measured results as distinct records.
- The user confirms a four-person team; member names, capacities, and final responsibilities are not yet recorded.

The first two choices come directly from the user; document review is not implied.[^session]

## Evidence available

- Five project PDF artifacts have been inspected and fingerprinted in the [source catalog](references/source-catalog.md), including the latest nineteen-page `tms-modul-a (1).pdf` (SRC-006).
- The current proposal is five pages and requires one local application, a documented local API, local inference/data handling, and interactive inspection. The coding roadmap primarily describes a CLI; UI/API and local-dataflow work remain to schedule.[^proposal]
- The revised roadmap clarifies coordinates, validation splits, class-specific cleanup, face coverage, numerical targets, and benchmark failures. These are source-level improvements, not approved thresholds or validated implementations. Remaining contradictions are recorded in the [alignment review](reviews/roadmap-alignment.md).[^revised]
- SRC-006 changes section 9.2: expanded roles, weekly work, interfaces, backups, and coordination rules. Surrounding extracted text matches SRC-005. The [team plan](team.md) captures the update as proposed/unassigned; UI/API ownership and workload balance remain open.[^team]
- A local SimNIBS 4.6 installation directory and the Ernie sample files were inspected. Successful execution has not been demonstrated in this session.[^session]
- A shared Qt desktop [CHARM launcher prototype](../tools/charm_gui/README.md) now targets macOS and Windows with input selection, fresh-job execution, live logs, cancellation, and result-opening controls. The macOS ARM64 app bundle built and passed a native startup check; installed CHARM help also exited successfully. The Windows process path passed its stand-in tests on 2026-11-02 after a job-creation fix; the Windows package and manual build workflow have not run. Process checks use stand-ins, not real MRI reconstruction.[^session]
- The [MRI Workbench prototype](../tools/mri_prototype/README.md) inspects MRI, opens SimNIBS folders and verified project exports, shows surfaces in 3D, and exports a model. On 2026-11-02 its checks and native 3D check passed on Windows with real Ernie data. It is a prototype, not the final application.
- K3 code in [`tools/headmodel`](../tools/headmodel/README.md) covers the [coordinate contract](concepts/coordinates.md), lossless reorientation, cleanup, surfaces, and generic export. [EXP-005](experiments/ernie-surface-export.md) ran it on one supplied real head; it shows alignment with the supplied mesh, not anatomical accuracy. The contract and D-004 are proposed, not accepted.
- [EXP-001](experiments/ernie-baseline.md) completed on 2026-11-03: a fresh SimNIBS 4.6 charm reconstruction of the Ernie T1 on the K3 Windows machine in 1 h 16 min, with outputs on the input grid. Running the K3 surface pipeline on those labels found that open airways entered the head surface; sealing narrow openings fixed it on this subject ([EXP-006](experiments/ernie-fresh-charm-surfaces.md)).
- No final Module A application or test-set evaluation has been established. [EXP-003](experiments/e1-multiaxial-100ep.md) reports a preliminary model with validation results only.[^session]
- The team's shared Drive archive packages the Module A core data (MultiAxial, SimNIBS samples, SynthStrip selection, 50-subject IXI subset) with checksums; access-controlled sets have no data. CT-paired skull datasets D14/D15 are missing from Drive; a [staging tool](../tools/data_staging/README.md) prepares them for manual upload. Nothing has been unpacked or audited in this project yet.[^data]
- The literature review (SRC-012), Module A literature candidates, snowball workbook, and the 14-page Module A specification revision (SRC-007) are now cataloged.[^data]

## Next useful action

Hold the kickoff in the [Module A start plan](playbooks/module-a-kickoff.md): record owners, start date, and GPU access; then unpack and audit D01/D04/D05/D06, upload D14/D15 to Drive, and run the [Ernie baseline](experiments/ernie-baseline.md) (still **not run**). The start gate at the end of relative week 2 lists the evidence that marks Module A as started.

For K3: run the surface pipeline on model predictions once K2's checkpoint is available, check the 8 mm envelope seal on more subjects, open an export in 3D Slicer, and get team review of the [coordinate contract](concepts/coordinates.md), whose handoffs ask K1 to state units and share one axis order, and K2 to confirm the model path.

## Decisions and unresolved work

- [Accepted project direction](decisions/index.md): repository knowledge and downstream independence.
- [Open questions](questions.md): interaction scope, data, geometry, metrics, compute, ownership, and dates.
- [Team workstreams](team.md): four-person role proposal and handoffs; source assignment cells are empty.
- [Latest alignment review](reviews/roadmap-alignment.md): source-level corrections and remaining issues; the [earlier review](reviews/roadmap-review.md) preserves SRC-004 history.
- [Requirements](scope.md) and [acceptance definitions](acceptance.md): source-backed intentions, with provisional targets explicitly marked.

## Reading budget

Read this page and [the map](index.md), then the notes relevant to the task. No full-vault loading or chronological chat dumps are needed. Update this page when the next action, confirmed direction, or evidence changes; preserve experiment details in the experiment note.

[^session]: See the session observation record for the evidence and its limits. [Open source](references/session-observations.md).
[^proposal]: Current proposal, pp. 1, 3, and 5; see its source note and checksum. [Open source](references/proposal-form.md).
[^revised]: Revised roadmap, pp. 2–5, 8–14, and 17. [Open source](references/module-a-roadmap-revised.md).
[^team]: Latest roadmap, section 9.2, pp. 16–18; source comparison and fingerprint are in its reference note. [Open source](references/module-a-roadmap-team-update.md).
[^data]: [Data inventory](references/datasets.md), [Drive archive](references/team-drive.md), and [source catalog](references/source-catalog.md) entries SRC-007–SRC-012, recorded 2026-11-02.
