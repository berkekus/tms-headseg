---
type: Experiment
title: 'EXP-001: Ernie T1 Baseline'
description: A ready-to-follow baseline protocol; no run or measured result is claimed.
status: draft
generated:
  by: codex/gpt-6
  at: '2026-10-22T13:41:29+03:00'
experiment_id: EXP-001
experiment_state: not_run
sources:
- id: charm
  resource: https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html
  title: CHARM usage
- id: observations
  resource: ../references/session-observations.md
  title: Local sample inventory
---

# EXP-001: Ernie T1 Baseline

Experiment state: **not run**. Presence of supplied outputs is not a completed experiment. Update this state only when logs and outputs establish what happened.

## Purpose

Learn MRI-to-model outputs, establish processing and geometry observations, and identify stages relevant to the project's software-independent export contract. One example cannot establish robustness on the intended population.

## Before running

Configure `SIMNIBS_BIN` as the installed SimNIBS `bin` directory and `ERNIE_DATA` as the downloaded example root containing `org/` and `m2m_ernie/`. Use an absolute path for each. Confirm the new output directory does not already contain a previous run.

Inspect `m2m_ernie/charm_report.html`, the original T1, and the supplied mesh first. Source files and supplied reconstruction are references, not evidence from EXP-001.

## Proposed command

```bash
: "${SIMNIBS_BIN:?Set the absolute SimNIBS bin directory}"
: "${ERNIE_DATA:?Set the absolute example dataset directory}"
cd "$ERNIE_DATA"
test -x "$SIMNIBS_BIN/charm" || exit 1
test -f org/ernie_T1.nii.gz || exit 1
test ! -e m2m_exp001_ernie_t1 || { echo "Use a fresh run ID; output already exists."; exit 1; }
time "$SIMNIBS_BIN/charm" exp001_ernie_t1 org/ernie_T1.nii.gz
```

This protocol is not an automatic instruction to run a long job. Obtain the current user's authorization for execution when a task requests only reading or planning. The distinct subject ID preserves the supplied `m2m_ernie/` example.[^charm]

## Record after execution

| Field | Current value |
| --- | --- |
| Run ID | Planned: EXP-001; use a unique attempt ID for reruns. |
| Tool/runtime version | Installation directory observed as 4.6; executable version not yet captured. |
| Hardware and resource settings | Not recorded. |
| Input SHA-256 and image geometry | Not captured for a run. |
| Command and configuration | Proposed above; not executed by this protocol's creation. |
| Exit status, log, and report | Not available. |
| Wall-clock and per-stage time | Not measured. |
| Peak memory | Not measured. |
| Image/surface alignment and defects | Not assessed for a new reconstruction. |
| Manual adjustments | Not observed. |

Store large artifacts outside Git and record their location/identity. Add representative non-identifying evidence only where appropriate. The sample README says its supplied model used a different, FreeSurfer-assisted reconstruction; exact mesh equality is not an acceptance criterion.

## Related notes

[Current state](../current.md) · [SimNIBS reference](../references/simnibs.md) · [Local observations](../references/session-observations.md) · [Coordinates](../concepts/coordinates.md)

[^charm]: Official CHARM usage supports a chosen subject identifier and T1-only input. [Open source](https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html).
