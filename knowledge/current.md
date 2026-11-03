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

Last substantive update: 2026-11-03. Project stage: preliminary E1 validation and baseline exploration.

## Confirmed direction

- This knowledge base is entirely in English and lives beside the project in Git.
- Outputs and acceptance criteria are independent of any particular downstream application.
- Module A is the current implementation focus. Optional targeting work does not determine its completion.
- Preserve source claims, proposals, decisions, and measured results as distinct records.
- The user confirms a four-person team; member names, capacities, and final responsibilities are not yet recorded.
- The user now identifies model training as their workstream and requested E1 preparation from the supplied K2 handoff; this does not assign the remaining team roles.

The first two choices come directly from the user; document review is not implied.[^session]

## Evidence available

- Five project PDF artifacts have been inspected and fingerprinted in the [source catalog](references/source-catalog.md), including the latest nineteen-page `tms-modul-a (1).pdf` (SRC-006).
- The current proposal is five pages and requires one local application, a documented local API, local inference/data handling, and interactive inspection. The coding roadmap primarily describes a CLI; UI/API and local-dataflow work remain to schedule.[^proposal]
- The revised roadmap clarifies coordinates, validation splits, class-specific cleanup, face coverage, numerical targets, and benchmark failures. These are source-level improvements, not approved thresholds or validated implementations. Remaining contradictions are recorded in the [alignment review](reviews/roadmap-alignment.md).[^revised]
- SRC-006 changes section 9.2: expanded roles, weekly work, interfaces, backups, and coordination rules. Surrounding extracted text matches SRC-005. The [team plan](team.md) captures the update as proposed/unassigned; UI/API ownership and workload balance remain open.[^team]
- A local SimNIBS 4.6 installation and public Ernie inputs have been inspected. Earlier T1-plus-T2 trials stalled with OpenBLAS errors; a child-thread-limited retry completed on 2026-11-02 with new mesh, labels, and report.[^session]
- A shared Qt desktop [CHARM launcher prototype](../tools/charm_gui/README.md) now targets macOS and Windows with input selection, fresh-job execution, live logs, cancellation, and result-opening controls. The macOS ARM64 app bundle built and passed a native startup check; installed CHARM help also exited successfully. Windows-specific launch/cancellation code and a manual build workflow exist but have not run on Windows. Process checks use stand-ins, not real MRI reconstruction. The user requested review before committing.[^session]
- No final Module A application or accepted model/test performance has been established. A preliminary E1 model now has a completed 100-epoch run and fixed ten-case validation result in [EXP-003](experiments/e1-preparation.md); label and geometry limitations remain. The completed CHARM run is separate reference-tool evidence.[^session]
- [EXP-002](experiments/ernie-thread-limits.md) records the stopped October 30 attempt and the completed November 2 T1-plus-T2 retry. CHARM reported 40:17 runtime and finished at 14:36:57 +03:00; expected outputs are present and the label volume reads. Neither prior OpenBLAS memory error nor thread-limit warning recurred; numerical runtime warnings remain. Anatomical quality and generic export geometry still need review. Nineteen launcher checks passed and one native Windows check was skipped.

- The fetched team records now document the MultiAxial and IXI audits, a completed IXI045 CHARM pilot, and the same preliminary E1 result in [the team experiment record](experiments/e1-multiaxial-100ep.md). The [updated preparation tool](../tools/nnunet_prep/README.md) writes explicit millimetre units and coded transforms in new copies and preserves original sheared NYU affines. These new preparation records do not retroactively change the original handoff bytes used for our training/demo. CT-paired skull datasets D14/D15 still require staging/upload; the literature/specification sources are cataloged.[^data]

## Next useful action

E1 source, clean notebooks and dependencies are collected under `tools/e1_training/`; teammates should use the [model handoff guide](../tools/e1_training/HANDOFF.md) and retain the whole Drive model folder. The user requested local commits only. Data, checkpoints and generated reports remain outside Git.

The [MRI Workbench](../tools/mri_prototype/README.md) now also opens paired MRI/E1 predictions as slice overlays and native 3D tissue surfaces, alongside existing SimNIBS model import. GU011 native rotation, tissue controls, linked MRI planes and reopening passed; 29 prototype checks passed. Unknown original MRI units require an explicit display-only assumption and remain marked unverified. Desktop nnU-Net inference is still absent. The earlier source sync/review found that connection missing; the user subsequently approved this display extension. The user subsequently reported a successful manual 3D trial and requested committing and pushing this extension; the earlier three commits had already been pushed through `ab89d23`. Detailed evidence is in [EXP-003](experiments/e1-preparation.md).

The user also approved a 3D display extension. The updated [demo notebook](../tools/e1_training/E1_Demo.ipynb) now generates rotatable tissue surfaces with visibility/opacity controls, presets and camera reset, followed by the existing 2D comparisons. Recorded GU011 geometry contains all five tissues (348,104 display triangles at a 3-voxel sampling step); scores and source labels are unchanged. The HTML bundles its JavaScript for offline viewing. Thirty-seven tests pass, including geometry and Node-based control logic, and a static gray-matter preview was inspected. Interactive browser/WebGL/Colab behavior still needs rehearsal. Reload the new notebook and run its environment cell; old uploaded notebooks do not update automatically. No SimNIBS/FEM volume-mesh adaptation has been performed.

The user approved a Friday E1 demonstration while waiting for E2 data. The [demo notebook and guide](../tools/e1_training/DEMO.md) now support saved-result presentation and explicitly enabled new inference, with offline HTML/PNG/JSON outputs. Actual local CPU inference of GU011 completed with the trained final checkpoint: 2.06 seconds to load and 561.18 seconds for preprocessing/prediction/export with TTA off; case macro-Dice 0.810074. The original cohort score is unchanged. Recorded reports need no GPU. Rehearse the new notebook in Colab before relying on live GPU inference; that path has not been executed. Do not start another training run for the demonstration. Team handoff uses the whole `E1_L4_001` folder plus the demo tools/custom trainer; optional five-epoch pilot folders remain separate. Detailed evidence is in [EXP-003](experiments/e1-preparation.md).

The separate L4 100-epoch preliminary E1 model (`E1_L4_001`) completed after checkpoint recovery. The user's final console log shows resumed epochs 14–99, `Training done.`, all ten fixed validation predictions, `Validation complete`, foreground mean Dice **0.8715520701436821**, and successful subprocess completion in 237.4 minutes for that resumed invocation. [EXP-003](experiments/e1-preparation.md) preserves the full evidence and earlier GPU comparisons. The optional completion cell reached its success/release-request branch; actual runtime release and stopped billing are unverified. If a runtime is still allocated, release it after confirming outputs. The supplied validation JSON now matches the fixed ten-case split and its Dice arithmetic checks out. Per-class mean Dice: skin 0.9550, skull 0.8479, CSF 0.7950, gray matter 0.8632, white matter 0.8966. GU011 has the lowest case macro-Dice (0.8103), with gray matter 0.7501 and CSF 0.7283. The supplied GU011 prediction now matches the original voxel grid and all JSON voxel counts/Dice exactly. Limited orthogonal/axial overlays show tissue-boundary and fine-structure differences; relative to the provisional reference, CSF label volume is 12.69% lower, gray matter 11.75% lower, and skull 9.88% higher. The prediction declares millimetres but original spatial units remain unknown. Next inspect additional validation cases and label provenance/anatomy before attributing these differences solely to training length or choosing a longer run. Preserve the whole trainer output folder with its custom trainer/environment information for inference. The final checkpoint has now been downloaded, archive-checked, deserialized, and used in real CPU inference; it confirms epoch 100 and fold 0. Original label semantics, anatomical quality, spatial units, affine provenance, and missing defacing masks remain unresolved; this is a provisional validation result, not held-out test success or accepted E1/Module A completion. No further long training is scheduled.

Review the report, MRI tissue boundaries, and new mesh from [EXP-002](experiments/ernie-thread-limits.md); record geometry and anatomical findings separately from execution success. The separate [T1-only baseline](experiments/ernie-baseline.md) remains **not run**; Windows execution also remains unverified.

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
