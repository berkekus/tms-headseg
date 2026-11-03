---
type: Experiment
title: 'EXP-001: Ernie T1 Baseline'
description: Fresh SimNIBS 4.6 charm reconstruction of the public Ernie T1 on the K3 Windows machine, with runtime, memory, outputs, and geometry.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-03T12:30:00+03:00'
experiment_id: EXP-001
experiment_state: completed
sources:
- id: charm
  resource: https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html
  title: CHARM usage
- id: observations
  resource: ../references/session-observations.md
  title: Local sample inventory
---

# EXP-001: Ernie T1 Baseline

Experiment state: **completed**, attempt `exp001_ernie_t1`, run on 2026-11-03 on the K3 Windows machine. One subject, one attempt.

## Purpose

Learn MRI-to-model outputs, establish processing and geometry observations, and identify stages relevant to the project's software-independent export contract. One example cannot establish robustness on the intended population.

## Protocol

Configure `SIMNIBS_BIN` as the installed SimNIBS `bin` directory and `ERNIE_DATA` as the downloaded example root containing `org/` and `m2m_ernie/`. Use an absolute path for each. Confirm the new output directory does not already contain a previous run. Source files and the supplied reconstruction are references, not evidence from this experiment.

```bash
: "${SIMNIBS_BIN:?Set the absolute SimNIBS bin directory}"
: "${ERNIE_DATA:?Set the absolute example dataset directory}"
cd "$ERNIE_DATA"
test -x "$SIMNIBS_BIN/charm" || exit 1
test -f org/ernie_T1.nii.gz || exit 1
test ! -e m2m_exp001_ernie_t1 || { echo "Use a fresh run ID; output already exists."; exit 1; }
time "$SIMNIBS_BIN/charm" exp001_ernie_t1 org/ernie_T1.nii.gz
```

The distinct subject ID preserves the supplied `m2m_ernie/` example.[^charm]

## How it was run

The command above ran through the project's own launcher code, `Job` and `Runner` in `tools/charm_gui/runner.py`, from a small script kept with the data. On Windows that path resolves `charm.cmd` to SimNIBS's bundled Python, starts it in a Job Object, and streams the console to a log. The Job Object also reported the run's peak memory and CPU time. This is the first real CHARM run through the launcher code on Windows; the window itself and a packaged build were not used.

Another CPU-heavy desktop application ran on the machine during the whole run. Treat the runtime as an upper bound under load.

## Results

| Field | Value |
| --- | --- |
| Run ID | `exp001_ernie_t1`, first attempt |
| Tool version | SimNIBS 4.6.0, per the installed package and `charm_log.html` |
| Hardware | Windows 11, Intel Core i7-14700KF (28 logical processors), 31.8 GB RAM. charm's default `threads = 8` was used. |
| Input | `org/ernie_T1.nii.gz`, SHA-256 `27e33241fc7c44b42dd63d613e81cadaefdfad271fd7e844fea71d0db75942ad`; 256 × 256 × 208, 1 mm, PSR. T1 only, no T2. |
| Exit status | 0. Expected mesh and `final_tissues.nii.gz` present. |
| Wall-clock time | 1 h 16 min 29 s (charm log, 10:44:46–12:01:15); 4,600.6 s measured by the runner |
| CPU time | 6,562.6 s user and 739.9 s kernel across 25 processes; on average about 1.6 cores busy |
| Peak memory | 10.13 GB (9.44 GiB), peak committed memory of the whole process tree as reported by the Job Object |
| Output size | 730 MB for `m2m_exp001_ernie_t1/`, including a 179 MB mesh |
| Manual adjustments | None |

Stage times. The last three come from the charm log; the others are approximate, taken from output file times.

| Stage | Time |
| --- | --- |
| Affine registration and neck correction | about 1 min |
| Segmentation | about 15.5 min (10:45:45–11:01:20) |
| MNI transforms and label preparation | about 20 min |
| Surface creation | 11 min 45 s |
| Mesh preparation, meshing, post-processing | 4 min 47 s, 1 min 6 s, 21 min 42 s |

Outputs, kept outside Git in `ERNIE_DATA/m2m_exp001_ernie_t1/`:

| File | SHA-256 |
| --- | --- |
| `final_tissues.nii.gz` | `16aff060162be6cb48bd7c120463dfd0fbdb4cf17c12d0ba0e481dbfd849fe6d` |
| `exp001_ernie_t1.msh` | `447188e3aa30a6954a526dd933f2abb9493c704ac7064c5fa322ea16a26ffbba` |
| `T1.nii.gz` | `003fd89606002aede4d8eccfbd4be9fb5b6d4dc7c1b7b22b2613c06422150d2a` |
| `final_tissues_LUT.txt` | `23cb2c01031db512a659a95567cac834289ab3286057c63b73e9eaa544816534` |

## Geometry

- `final_tissues.nii.gz` and the `T1.nii.gz` that charm writes are on the input grid exactly: same shape, same PSR affine, 0.0 mm difference at the corners, no header warnings from `read_source`. The written T1 has different voxel values from the input; charm processes the image, so do not use it as a byte copy of the source.
- The new mesh's skin spans the same superior-inferior range as the labels (z from −128.7 to 99.9 mm against −128.6 to 99.4 mm).
- MRI Workbench opened the new folder natively on Windows and `check_3d.py` passed, including MRI-plane registration.
- Surface-level agreement with the project pipeline is in [EXP-006](ernie-fresh-charm-surfaces.md).

## Agreement with the supplied model

Dice between the new labels and the supplied `m2m_ernie` labels, after the proposed charm mapping: skin 0.939, skull 0.887, CSF 0.824, gray matter 0.938, white matter 0.966. This is an observation, not an accuracy measure: the supplied model came from charm 3.2.4.dev with FreeSurfer-assisted surfaces, and neither is ground truth.

## Comparisons that do not transfer

The supplied model's log reports 2 h 29 min on its author's machine with that older pipeline. K1's charm run on IXI045 took about 66 minutes with T1 and T2 on another machine ([EXP-002](charm-ixi-pilot.md)). Different subjects, inputs, versions, and machines make neither a benchmark for this run.

## The November 2 Mac run

The Mac reconstruction mentioned in `tools/mri_prototype/README.md` is recorded in Mert's [EXP-002 thread-limit note](ernie-thread-limits.md). Its launcher log (SHA-256 `9a6a6455892cba09180a033cec8210f5be176fdf72ccf8c19fb1063b230ee7ec`) was read on 2026-11-03.

| | Mac run, 2026-11-02 | This run |
| --- | --- | --- |
| Machine | M4 Pro, macOS | i7-14700KF, Windows 11 |
| Inputs | T1 and T2 | T1 only |
| OpenBLAS and OpenMP threads | Limited to 1 by the launcher | Not limited |
| Other load | Not recorded | Another CPU-heavy application |
| Surface creation | 6 min 42 s | 11 min 45 s |
| Mesh preparation, meshing, post-processing | 1 min 49 s, 1 min 0 s, 10 min 44 s | 4 min 47 s, 1 min 6 s, 21 min 42 s |
| Total | 40 min 17 s | 1 h 16 min 29 s |

The Mac run was faster despite also processing T2. Machine, thread limits, and concurrent load all differ, so this comparison does not identify the cause. Both logs show the same NumPy `matmul` runtime warnings. The launcher now applies the thread limits on Windows too, since the K3 branch merged them, so a repeat on an otherwise idle machine would separate load from the thread setting.

## Related notes

[Current state](../current.md) · [SimNIBS reference](../references/simnibs.md) · [Local observations](../references/session-observations.md) · [Coordinates](../concepts/coordinates.md) · [EXP-005](ernie-surface-export.md)

[^charm]: Official CHARM usage supports a chosen subject identifier and T1-only input. [Open source](https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html).
