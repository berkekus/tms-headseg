# Knowledge Update Log

## 2026-11-02

- **Windows launcher fix (K3)**: Running the suites on Windows for the first time showed that every launcher job failed at Job Object creation. Fixed the call and the log-handle leak it exposed; recorded the checks as OBS-08 in [session observations](references/session-observations.md). No real CHARM run or Windows package is claimed.
- **Team rebalance**: At the user's request, replaced the SRC-006 role table in [team workstreams](team.md) with a rebalanced proposal (dataset builder → K1, preprocessing geometry → K3, timing → K4, inference API → K2 after the model freeze, viewer/UI → K3, K1 test custodian, shared packaging, rotating report coordination). The SRC-006 version is kept for provenance. Updated the [start plan](playbooks/module-a-kickoff.md) and [roadmap](roadmap.md) accordingly. Team acceptance and names remain pending.
- **Data and start plan**: Cataloged SRC-007 (`docs/roadmap.pdf`, 14-page Module A specification), SRC-008–010 (inventory, Module A literature, snowball workbooks), SRC-011 (shared Drive archive), and SRC-012 (literature review; the SLR copy is a duplicate). Rewrote the [data inventory](references/datasets.md) from the Drive control records and official pages (D14 license corrected to CC BY-NC 4.0; IXI overlap across D05/D06/SHARM noted). Added the [Drive archive note](references/team-drive.md), [literature map](references/module-a-literature.md), and the [Module A start plan](playbooks/module-a-kickoff.md); added data-informed updates to the [roadmap](roadmap.md); added Q-18–Q-20. Added `tools/data_staging/` to stage D14–D16 for manual Drive upload (unit tests pass; nothing downloaded or uploaded). No run, audit, or assignment is claimed.

## 2026-10-30

- **Desktop portability**: The user approved one shared Qt launcher for Windows and macOS. Added Windows launcher resolution, Job Object process ownership, portable log streaming, packaging/runtime isolation, and a manual desktop build workflow. The macOS app built and passed a native startup check. Windows execution/build and real reconstruction remain unverified; no workflow was run or release published. Details are in [launcher usage](../tools/charm_gui/README.md) and [session observations](references/session-observations.md).
- **Preparation tool**: Added an in-repository [CHARM launcher prototype](../tools/charm_gui/README.md) at the user's request for review before committing. Recorded native-window startup and successful CHARM help invocation separately from stand-in lifecycle checks. Updated [session observations](references/session-observations.md) and [current state](current.md); no full reconstruction, benchmark, final Module A delivery, or team assignment is claimed. [EXP-001](experiments/ernie-baseline.md) remains not run.

## 2026-10-23

- **Team update**: Compared the nineteen-page `tms-modul-a (1).pdf` with SRC-005 and cataloged it as [SRC-006](references/module-a-roadmap-team-update.md). Extracted text outside section 9.2 is unchanged after normalization. Added [team workstreams](team.md), relative weekly handoffs, proposed interfaces/backups, and remaining allocation/test-access questions. Four-person team size is user-confirmed; role names, dates, and operating rules remain unassigned/proposed. Existing targets and experiment states are unchanged.

## 2026-10-22

- **Revised roadmap**: Imported fingerprinted seventeen-page `tms-modul-a.pdf` as [SRC-005](references/module-a-roadmap-revised.md); retained SRC-004. Added the [alignment review](reviews/roadmap-alignment.md), latest proposed measurement definitions, class-specific cleanup/face handling, and calibration questions. No threshold approval, implementation, or experiment success is implied.
- **Creation**: Established the English project knowledge base with [source fingerprints](references/source-catalog.md), requirements, references, concepts, templates, and navigation.
- **Direction**: Recorded [repository knowledge](decisions/001-repository-knowledge.md) and [downstream independence](decisions/002-downstream-independence.md) from explicit user requests.
- **Review**: Recorded the current five-page proposal's application and API requirements and the coding roadmap's [unresolved issues](reviews/roadmap-review.md).
- **Source revision**: Final fingerprint checking detected a new five-page proposal under the same filename. Imported local API/local-processing requirements and retained the earlier four-page fingerprint in the [catalog](references/source-catalog.md).
- **Protocol**: Created [EXP-001](experiments/ernie-baseline.md) as not run. No benchmark or model result is claimed.
