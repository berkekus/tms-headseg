# Run our E1 or E2 model in MRI Workbench

The **04 E1 / E2 segmentation** tab creates a new prediction using the selected model version. The header's **Open E1 / E2 segmentation…** action opens an already-saved prediction.

## E2 model selection

Select **E2** under **Model version**, then choose the completed E2 model directory with `plans.json`, `dataset.json` and `fold_0/checkpoint_final.pth`. Each version remembers its selected folder during the session. The supplied `Downloads/E2_L4_001` model is offered when present. Click **Generate E2 segmentation** to run it locally.

E2 rebuilds the reviewed standard architecture from its plans, loads the epoch-100 weights strictly and manually initializes nnU-Net. The original E2 notebook and custom trainer source are optional for this inference route. MRI headers must declare millimetre units. K3's `headmodel.model_io` prepares a lossless RAS copy and restores predicted labels to the input grid. The run retains `model_input_0000.nii.gz`, `geometry.json` and `prediction_model.nii.gz` alongside the final source-grid `prediction.nii.gz`. E1 retains its existing loading and stored-axis behavior.

For an E1/E2 comparison, use the same MRI and mirror-augmentation setting. A validation score against E2's CHARM-based labels measures agreement with that reference. The E1 and E2 cohort scores use different references and cohort sizes.

## First run

1. Start Workbench as described in [README.md](README.md), then open **04 E1 / E2 segmentation** and select **E1** for the original model workflow.
2. Select **Inference Python**, the executable inside a separate Python 3.11 environment containing nnU-Net 2.8.1, torch 2.6.0 and the [E1 demo dependencies](../e1_training/DEMO.md). The existing local demo environment is prefilled if found beside this checkout. Keep its virtual-environment executable path; selecting the base interpreter or SimNIBS Python will not provide the same environment. No installation/download happens automatically.
3. Select your trusted **trained model folder**, containing `plans.json`, `dataset.json` and `fold_0/checkpoint_final.pth`. The known local demo model is prefilled if available. See the [model handoff](../e1_training/HANDOFF.md).
4. Select **Source T1 MRI** and an existing **Output parent folder** outside Git and outside the model directory. An MRI opened in the inspection tab fills this input too.
5. Keep **CPU** and mirror augmentation off for the initial Mac workflow. CUDA requires an independently configured NVIDIA inference environment. Mirror augmentation is optional and slower; the original full validation used it, so the default CPU demo has a different inference setting. For original handoff MRIs with unknown header units, explicitly enable **Use handoff mm assumption for unknown MRI units**. This workflow accepts mm or that explicit provisional assumption; other units need an independently prepared mm-space copy. Original files stay unchanged.
6. Click **Generate E1 segmentation**. A separate owned process runs the reviewed `demo.py predict` CLI. Qt remains responsive, the log is retained on disk, and elapsed time is shown. No completion percentage is fabricated.
7. On success, the new prediction opens automatically in **03 3D model**, with the matching MRI and overlays also available in **01 Inspect MRI**. A failed run never falls back to an old prediction. A failed display load is distinguished from a completed inference.

**Cancel inference** stops the owned process tree and preserves partial output. Closing an active run asks whether to stop it and waits for cleanup. Import, K3 export, CHARM and E1 inference cannot run simultaneously. The K3 project-model import/export path remains available after the inference ends; E1 display does not automatically run cleanup or change its geometry/export contract.

## Surface display detail

In **03 3D model**, choose **Surface detail · voxel step**, then **Apply surface settings**. **Auto** keeps the fast bounded preview. Explicit **4**, **2** and **1 voxel** settings rebuild the surfaces at the selected sampling step. A smaller step retains more of the original label detail and uses more rendering memory. The step is measured in source voxels, with their existing spacing.

The update uses the saved prediction and preserves the camera and tissue visibility/opacity. MRI slices, labels and inference outputs remain unchanged. Explicit choices have an eight-million-triangle limit. If exceeded, an error asks for a coarser step while retaining the previous model. This control applies to E1/E2 predictions; imported meshes keep their supplied geometry.

**Surface smoothing · Slicer method** controls a display-only Windowed Sinc filter. **0** shows the raw surface. **0.50** uses Slicer's default factor mapping (40 iterations, passband 0.01). Start with **1 voxel** and **0.50** for a detailed smooth view. Higher factors can remove small features. The filter runs in label voxel space before applying the world affine, matching Slicer's treatment of anisotropic spacing. The underlying triangulation remains our existing marching-cubes extraction. This reproduces Slicer's smoothing settings rather than guaranteeing identical meshes from different conversion algorithms. [Slicer conversion implementation](https://github.com/Slicer/Slicer/blob/main/Libs/vtkSegmentationCore/vtkBinaryLabelmapToClosedSurfaceConversionRule.cxx).

## Outputs and provenance

Each run has a new UTC-stamped ID; existing runs and model files are never overwritten:

```text
OUTPUT_PARENT/
├── e1.RUN_ID.TIMESTAMP.launcher.log
├── RUN_ID.desktop.json
└── RUN_ID/
    ├── prediction.nii.gz
    ├── status.json
    └── report/
        ├── report.html
        ├── report.json
        └── comparison.png
```

The desktop record captures input/model/runtime paths, exact command, device, mirror augmentation, unit opt-in, four math-library threads, elapsed time, exit code and final outcome. It is the cancellation record when a terminated child retains an incomplete `running` status. The child report contains model hashes and measured model-load/prediction timings. No reference is supplied by the desktop form, so no case Dice or new cohort score is claimed.

The MRI reaches the model in its stored axis order. E1 was trained on RAS-stored MultiAxial scans, so a PSR scan such as IXI or Ernie arrives in a different order; the effect is unmeasured, and `tools/headmodel/model_io.py` offers the reversible alternative (see the open gap in the [coordinate contract](../../knowledge/concepts/coordinates.md)). The direct E1 3D scene uses approximate display surfaces, not a simulation-ready tetrahedral FEM mesh. Its unit/anatomical limitations remain visible. K3's strict geometry/export requirements are not bypassed by the inference unit opt-in.

## Developer interfaces

- `InferenceJob` captures immutable settings and creates the existing prediction CLI command.
- `InferenceRunner` reuses the launcher's process ownership, logging and cancellation; E1 uses its own log prefix and four child math-library threads. CHARM retains its original prefix, one-thread defaults and the K3 Windows job-object fix.
- `InferencePanel.completed(job)` fires only after successful exit plus completed status, prediction and report files. The Workbench worker then loads `job.prediction` and selects the 3D tab.
- `Window.run_task(function, callback, failure="Could not load: ", on_error=None)` preserves K3's positional failure-prefix interface while allowing a display-specific error callback.

Run synthetic UI/process checks from repository root with the prototype environment:

```bash
tools/mri_prototype/.venv/bin/python -m unittest discover -s tools/mri_prototype -q
```

The optional native check below performs a **new CPU inference**, not a quick saved-result preview. It can take several minutes and saves screenshots plus a verification record outside Git:

```bash
tools/mri_prototype/.venv/bin/python tools/mri_prototype/check_inference.py \
  --python /outside/git/e1-env/bin/python \
  --model /outside/git/completed_e1_model \
  --mri /outside/git/GU011_0000.nii.gz \
  --output /outside/git/existing_output_parent --assume-mm
```

Omit `--assume-mm` for known-mm inputs. Actual execution evidence and platform limitations belong in [EXP-003](../../knowledge/experiments/e1-preparation.md); synthetic checks alone do not prove successful model inference.
