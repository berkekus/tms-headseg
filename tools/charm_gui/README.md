# CHARM Launcher

A small Qt desktop window for running an installed SimNIBS CHARM on macOS and Windows. One shared codebase lives in this repository as a preparation tool. The interface runs on your computer without a browser tab, localhost server, or hosted service. It is not the final Module A application, a new segmenter, or a replacement for anatomy review.

Windows-specific execution and packaging are implemented but have not yet been run on a Windows machine. The macOS app has been built and startup-checked on Apple Silicon; one fresh public Ernie T1-plus-T2 reconstruction completed on 2026-11-02. Anatomical accuracy and external viewer opening remain unverified.

## Desktop packages

Install [SimNIBS](https://simnibs.github.io/simnibs/build/html/installation/simnibs_installer.html) separately on each computer. The launcher package includes its own Python/Qt runtime, so teammates using a built package do not need a separate Python installation for the launcher.

- **macOS:** extract the macOS ZIP, then open `CHARM Launcher.app`. A local ARM64 build is in `dist/`. The build is ad-hoc signed, not Apple-notarized.
- **Windows:** extract the Windows ZIP and open `CHARM Launcher/CHARM Launcher.exe`. Keep the entire folder, including `_internal`, together. A Windows build must be produced on Windows; no Windows executable has been produced on this Mac.

These are development packages, not signed public installers. Each OS needs its own build; the ZIP is not a universal executable. Windows x64 and Apple Silicon macOS are the intended first targets. Windows ARM and Linux are not established targets.

## Setup

For development or running directly from source, install SimNIBS separately and Python 3.11 or newer. From the repository root, create an isolated environment.

**macOS:**

```bash
python3 -m venv tools/charm_gui/.venv
tools/charm_gui/.venv/bin/python -m pip install -r tools/charm_gui/requirements.txt
tools/charm_gui/.venv/bin/python tools/charm_gui/app.py
```

**Windows PowerShell:**

```powershell
py -3 -m venv tools/charm_gui/.venv
& tools/charm_gui/.venv/Scripts/python.exe -m pip install -r tools/charm_gui/requirements.txt
& tools/charm_gui/.venv/Scripts/python.exe tools/charm_gui/app.py
```

PySide6 Essentials supplies the interface; Windows additionally uses `pywin32` for process-tree control. Do not install these into SimNIBS's bundled Python environment. MATLAB, MATLAB Runtime, and Brainstorm are not required.

If using `uv`, dependency installation can instead use:

```bash
uv venv tools/charm_gui/.venv --python python3
uv pip install --python tools/charm_gui/.venv/bin/python -r tools/charm_gui/requirements.txt
```

## Create a model

1. Select a T1 NIfTI image (`.nii` or `.nii.gz`). Optionally select T2. CHARM uses T2 to improve skull segmentation; this launcher does not convert DICOM.
2. Choose an existing output folder outside any Git checkout. Use the folder chooser to create a dedicated local folder if desired.
3. Choose a new subject ID. Only letters, numbers, underscores and hyphens are accepted; begin with a letter or number. The model will be created at `OUTPUT/m2m_SUBJECT/`.
4. Check the detected CHARM launcher: `SimNIBS-4.6/bin/charm` on macOS or `SimNIBS-4.6/bin/charm.cmd` on Windows. You can choose another installation explicitly. Discovery checks PATH and common install folders; custom installations may require selection.
5. Press **Create head model**. Live output and elapsed time appear. No completion percentage is estimated.
6. After completion, open the HTML report and inspect tissue boundaries. **Open 3D mesh** launches the adjacent SimNIBS Gmsh launcher, or the system's `.msh` handler if unavailable. The report opens in the default browser; the launcher itself stays a desktop window.

The launcher runs `charm SUBJECT T1 [T2]` with separate arguments and the chosen output folder as its working directory. On Windows, it reads the standard generated `.cmd` wrapper and invokes its bundled Python and script directly, preserving `-E -u`; image paths never pass through a command shell. Modified/arbitrary batch wrappers are rejected. Moved or broken SimNIBS installations must be repaired or reselected.

It never uses `--forcerun`. Existing `m2m_SUBJECT` paths are rejected, including partial outputs. Input checks cover readable files and extensions, not image content or suitability.

**Cancel:** macOS stops the process group, escalating after two seconds if children resist stopping. Windows terminates a Job Object containing the process tree; the process starts suspended and joins the job before it can create children. Closing the Windows job also stops surviving children if the parent already exited. Closing the window during a run offers to cancel first. Partial files remain for inspection; use a new subject ID for a retry. Resume and automatic deletion are intentionally omitted.

Full console output goes directly to a unique `charm.SUBJECT.TIMESTAMP.launcher.log` in the output folder. The window tails that file and retains up to 10,000 lines, avoiding platform-specific pipe modes. Logs can contain local paths and scan information; keep them with the local data. CHARM also writes its own reports and logs.

### OpenBLAS threading workaround

Following repeated stalled Ernie trials with OpenBLAS thread-metadata and memory-unallocation errors on the development M4 Pro, launcher-started CHARM jobs now receive `OPENBLAS_NUM_THREADS=1`, `OPENBLAS_DEFAULT_NUM_THREADS=1`, and `OMP_NUM_THREADS=1`. These values override inherited values only for that child job and are printed at the beginning of its log. System settings and installed SimNIBS packages are not changed. OpenMP limits can also affect other OpenMP code; record these settings when comparing runtimes. One capped Ernie T1-plus-T2 run completed in 40:17 without the prior OpenBLAS memory/thread-metadata messages; this does not establish general reliability or anatomical accuracy.

The installed OpenBLAS runtime reported one thread in a small diagnostic with these settings. NumPy 2.3.0 on the development M4 also emitted `matmul` warnings for a correct identity-matrix result; that diagnostic does not establish the correctness of segmentation calculations. Warnings are not suppressed. See the [experiment record](../../knowledge/experiments/ernie-thread-limits.md) and [OpenBLAS runtime controls](https://www.openmathlib.org/OpenBLAS/docs/runtime_variables/).

A zero exit code plus the expected `.msh` and `final_tissues.nii.gz` files counts as a completed job. This is an output-presence check, not an anatomical, numerical, or clinical quality check. Failed or incomplete runs show an explicit status.

## Try Ernie

Click **Use Ernie example…**. It looks for `~/Downloads/simnibs4_examples/org/ernie_T1.nii.gz` and the optional `ernie_T2.nii.gz`; otherwise choose the example root folder. It fills the input fields and a fresh subject ID. It does not start CHARM or load the supplied `m2m_ernie` as a new result.

For a prefilled preview:

```bash
tools/charm_gui/.venv/bin/python tools/charm_gui/app.py --ernie
```

Clear T2 for a T1-only experiment. Keep inputs, supplied example outputs, and new reconstruction outputs separate. One Ernie T1-plus-T2 run on the development M4 Pro with the above limits reported 40:17. Treat this as a single observed reference-tool runtime, not a speed target, general benchmark, or T1-only result.

## Checks and current limits

```bash
tools/charm_gui/.venv/bin/python -m unittest discover -s tools/charm_gui -v
```

On Windows, replace `tools/charm_gui/.venv/bin/python` with `tools/charm_gui/.venv/Scripts/python.exe` in the commands above, including the `--ernie` preview command. Run PowerShell commands with `&` as in setup.

Checks use temporary stand-in executables and do not require SimNIBS. They cover input validation, existing models, Git output rejection, paths containing shell characters, output streaming before exit, failed/incomplete jobs, successful output detection, tree cancellation, standard Windows wrapper parsing, packaging environment isolation, and the Qt start/finish workflow. The Windows-only job cleanup check is skipped on macOS.

On 2026-10-30, the source preview opened using ARM64 Python 3.14.7 and PySide6 Essentials 6.12.0. The installed SimNIBS 4.6 `charm --help` exited successfully. The macOS desktop package built with PyInstaller 6.22.3 and its native startup check exited successfully. On 2026-11-02, a new public Ernie T1-plus-T2 run completed with mesh, labels, and report present; its label volume was successfully read. Anatomy, coordinate acceptance, external viewer opening, and Windows execution remain unverified. Restricted agent execution blocks macOS GUI services and CHARM's local MPI socket; normal desktop execution is separate from those restrictions.

Before declaring the Windows version ready, run the tests on Windows, open the packaged application, select an installed SimNIBS, reconstruct a fresh public Ernie case, cancel a separate trial, and check reports and Gmsh opening. Do not substitute the supplied Ernie model for a newly generated result.

No embedded 3D viewer, job queue, advanced CHARM settings, project-model training, local API, or automatic QC is included. CHARM's defaults and runtime requirements still apply.

## Build desktop packages

Build on the target operating system. From the repository root on macOS:

```bash
tools/charm_gui/.venv/bin/python -m pip install -r tools/charm_gui/requirements-build.txt
tools/charm_gui/.venv/bin/python tools/charm_gui/build.py
```

On Windows PowerShell:

```powershell
& tools/charm_gui/.venv/Scripts/python.exe -m pip install -r tools/charm_gui/requirements-build.txt
& tools/charm_gui/.venv/Scripts/python.exe tools/charm_gui/build.py
```

Packages appear under `tools/charm_gui/dist/`. macOS archives use `ditto` to preserve bundle links. Build caches, environments, and binaries are ignored by Git. SimNIBS and MRI files are not bundled.

The repository also includes a manually triggered [Build CHARM launcher workflow](../../.github/workflows/charm-launcher.yml). Once this workflow is pushed and available on GitHub, run it from Actions to test and package on Windows x64 and macOS ARM64. It uploads ZIP artifacts for 14 days and does not publish a release. It has not been run in this session. CI uses stand-ins; real SimNIBS checks still require installed SimNIBS and public sample data.

`--smoke-test` opens the native window and exits automatically without starting a job, for checking the packaged application. Packaging removes bundled Qt library/plugin paths from external-process environments; Windows also temporarily restores the system DLL search path when spawning external programs.

## Files

- `app.py`: native window, file selection, job state, and result opening.
- `runner.py`: validation, safe process arguments, streaming logs, and cancellation.
- `installation.py`: install discovery, standard wrapper resolution, and external-runtime isolation.
- `windows_process.py`: Windows Job Object ownership, suspended startup, and process cleanup.
- `build.py`: per-platform desktop package and ZIP creation.
- `test_runner.py`, `test_app.py`, and `test_simnibs.py`: focused checks.
- `PLAN.md`: bounded prototype scope and implementation checklist.

References: [CHARM documentation](https://simnibs.github.io/simnibs/build/html/documentation/command_line/charm.html), [Qt for Python setup](https://doc.qt.io/qtforpython-6/gettingstarted.html), [SimNIBS-generated launcher source](https://github.com/simnibs/simnibs/blob/v4.6.0/simnibs/cli/postinstall_simnibs.py), [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects), [PyInstaller external-process requirements](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application).
