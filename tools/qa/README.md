# Demo QA baseline

K4 owns the integrated report, acceptance evidence and follow-up defects. Component
owners keep their existing tests. This runner aggregates those checks without real
MRI, GPU training, CHARM reconstruction or model inference.

The aggregate includes E2 handoff/geometry checks as `e2-handoff`. Passing them
does not establish that E2 weights or an inference runtime are installed, or that
a real E2 prediction has completed on this machine.

## First run on Windows

From the repository root:

```powershell
python -m venv tools/qa/.venv
tools/qa/.venv/Scripts/python.exe -m pip install --upgrade pip
tools/qa/.venv/Scripts/python.exe -m pip install -r tools/qa/requirements.txt
tools/qa/.venv/Scripts/python.exe tools/qa/run_checks.py --temp-root C:\Projects\tms-qa-temp
```

On macOS/Linux use `tools/qa/.venv/bin/python` instead and omit `--temp-root` if the
OS temp directory is outside Git. The default report location is
`outputs/qa/<UTC timestamp>/`. Keep reports local and ignored. Check the directory
with `git check-ignore outputs/qa/example/report.md` before adding anything to Git.
An explicit `--out` must be a new private/local directory. No result directory is
overwritten. No packages are installed by the runner itself.

If your user home directory is itself a Git checkout, the normal Windows temp
directory is also inside Git. Geometry/data tools correctly refuse outputs there.
Use a scratch root outside **every** checkout, for example on this machine:

```powershell
tools/qa/.venv/Scripts/python.exe tools/qa/run_checks.py --temp-root C:\Projects\tms-qa-temp
```

The runner creates that directory if needed, while individual tests clean their
own temporary subdirectories. It does not delete the scratch root or change any
data-protection rule. A bad/inaccessible temp location is reported as BLOCKED.

The core requirements intentionally exclude desktop libraries. To enable the two
desktop suites, install the project's existing desktop requirements into this same
environment and rerun:

```powershell
tools/qa/.venv/Scripts/python.exe -m pip install -r tools/mri_prototype/requirements.txt
tools/qa/.venv/Scripts/python.exe tools/qa/run_checks.py --temp-root C:\Projects\tms-qa-temp
```

Each suite runs in a separate process. JSON and Markdown record commit, branch,
dirty-worktree state, interpreter, platform, imported dependency versions, duration,
counts, skipped reasons and logs. The report identifies failures separately from
dependencies that prevent execution. Inspect failures before making code changes.

Exit codes: `0` all selected suites pass without skips; `1` a failure/crash/timeout;
`2` blocked, no discovered tests or incomplete skipped coverage. A dependency or skip
does not count as a pass. Expected failures are reported by unittest. A scoped run
only establishes the selected suites, not the entire demo.

Examples:

```powershell
tools/qa/.venv/Scripts/python.exe tools/qa/run_checks.py --temp-root C:\Projects\tms-qa-temp --suite launcher-inputs --suite e1-demo
$env:TEMP='C:\Projects\tms-qa-temp'
$env:TMP='C:\Projects\tms-qa-temp'
tools/qa/.venv/Scripts/python.exe -m unittest discover -s tools/qa -p test_run_checks.py -v
```

## Ten manual demo acceptance scenarios

Run these on the actual presentation machine with agreed demo assets. Record each
as NOT RUN, PASS, FAIL or BLOCKED, with actual date, tester, commit, asset identifier,
expected/observed behavior, evidence and defect/retest reference. A unit-test pass
does not fill a manual result. Store recordings and case paths outside Git; use
non-sensitive asset identifiers in shared notes.

| ID | Requirement | Action and expected result | Needed evidence |
| --- | --- | --- | --- |
| DEMO-01 | REQ-01,09 | Start Workbench from the documented environment. The window opens and controls respond. | Actual machine/environment and startup result. |
| DEMO-02 | REQ-01,04 | Open the agreed T1 MRI. Three slice views load and navigate; no stale previous-case display. | Input identifier and slice-view evidence. |
| DEMO-03 | REQ-01,07 | Select an invalid/non-3D/corrupt input. A clear error appears; the app remains usable and stale data clears. | Error and successful recovery. |
| DEMO-04 | REQ-03,04 | Open the saved E1 or E2 prediction paired with its matching MRI. Overlay and all expected tissue controls work. | Matching asset IDs, model version and overlay. |
| DEMO-05 | REQ-02,04 | Rotate/zoom the 3D output and change tissue visibility/opacity. MRI plane alignment remains inspectable. | Native screen recording. |
| DEMO-06 | REQ-05,07 | Try a mismatched grid or unknown units. Record actual refusal/warning and any explicit assumption; do not declare physical geometry verified from appearance. | Geometry values, message and behavior. |
| DEMO-07 | REQ-05,06 | Export an eligible result with declared units and verify/reopen it using an independent reader. | Export manifest and verification result. |
| DEMO-08 | REQ-04 | Exercise a controlled stand-in start/cancel/failure path. No duplicate job or active child remains. Do not interrupt a teammate's real batch. | Status/log and process-exit evidence. |
| DEMO-09 | REQ-09 | Disconnect network for the saved-result path. Open local saved report/3D backup on the presentation machine. | Offline rehearsal result. This is not proof of no network transmission (REQ-11). |
| DEMO-10 | REQ-04,08 | Rehearse the complete agreed presentation path with a timer and recovery plan. | Actual duration, tested commit/assets, open defects and fallback. |

Choose saved-output presentation for the first rehearsal. Real inference, if wanted,
is a separately agreed run with checkpoint, input, budget and logs. A fresh training
run is not a demo prerequisite. Hold-out data must not be opened for rehearsal.

## Blockers and closure

Current demo assets, presentation machine and final demo path need the component owners'
confirmation before manual acceptance. Missing desktop dependencies block those
suites until installed; offscreen checks still do not prove native rendering.

For every defect record reproduction steps, expected/actual outcome, affected
commit, severity based on impact, owner agreed with the component developer,
fix reference and retest. Close this QA task when the report is reproducible and
the manual results/blockers are honestly recorded. Demo release acceptance is a
separate decision after the necessary checks and rehearsal.

Sources: [project requirements](../../knowledge/scope.md),
[acceptance definitions](../../knowledge/acceptance.md),
[Workbench](../mri_prototype/README.md), [E1 demo](../e1_training/DEMO.md).

Keep personal findings and generated reports under ignored `outputs/`. Share only
the minimal reproduction and relevant evidence when coordinating an actual defect.

## Repeated real E2 CPU timing

`benchmark_inference.py` is a separate opt-in benchmark, not part of CI or the
synthetic runner. It starts three new real CPU predictions sequentially through
the desktop verification helper. From the repository root, use:

```text
<qa-python> tools/qa/benchmark_inference.py --desktop-python <desktop-python> --python <inference-python> --model <E2-model-folder> --mri <public-T1.nii.gz> --output <new-folder-outside-Git> --repeats 3
```

Keep both Python environments separate. Outputs must be new and outside every
Git checkout. The script records protocol/hardware, every attempt and log,
per-repeat CSV and successful-only medians with failure counts. It does not
install packages, train, overwrite results or compare accuracy. Model preparation,
prediction/restoration and desktop/report/3D total have distinct timing boundaries;
the first two are included in the total. Processes reload the model each time;
OS cache and background load are uncontrolled. See the
[K4 timing experiment](../../knowledge/experiments/k4-inference-timing.md).
