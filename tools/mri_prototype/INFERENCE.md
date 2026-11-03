# Run our E1 model in MRI Workbench

The **04 E1 segmentation** tab creates a new prediction from MRI using the existing E1 model. The header's **Open E1 segmentation…** action opens an already-saved prediction. Training and CHARM remain separate actions.

## First run

1. Start Workbench as described in [README.md](README.md), then open **04 E1 segmentation**.
2. Select **Inference Python**, the executable inside a separate Python 3.11 environment containing nnU-Net 2.8.1, torch 2.6.0 and the [E1 demo dependencies](../e1_training/DEMO.md). The existing local demo environment is prefilled if found beside this checkout. Keep its virtual-environment executable path; selecting the base interpreter or SimNIBS Python will not provide the same environment. No installation/download happens automatically.
3. Select your trusted **trained model folder**, containing `plans.json`, `dataset.json` and `fold_0/checkpoint_final.pth`. The known local demo model is prefilled if available. See the [model handoff](../e1_training/HANDOFF.md).
4. Select **Source T1 MRI** and an existing **Output parent folder** outside Git and outside the model directory. An MRI opened in the inspection tab fills this input too.
5. Keep **CPU** and mirror augmentation off for the initial Mac workflow. CUDA requires an independently configured NVIDIA inference environment. Mirror augmentation is optional and slower; the original full validation used it, so the default CPU demo has a different inference setting. For original handoff MRIs with unknown header units, explicitly enable **Use handoff mm assumption for unknown MRI units**. This workflow accepts mm or that explicit provisional assumption; other units need an independently prepared mm-space copy. Original files stay unchanged.
6. Click **Generate E1 segmentation**. A separate owned process runs the reviewed `demo.py predict` CLI. Qt remains responsive, the log is retained on disk, and elapsed time is shown. No completion percentage is fabricated.
7. On success, the new prediction opens automatically in **03 3D model**, with the matching MRI and overlays also available in **01 Inspect MRI**. A failed run never falls back to an old prediction. A failed display load is distinguished from a completed inference.

**Cancel inference** stops the owned process tree and preserves partial output. Closing an active run asks whether to stop it and waits for cleanup. Import, K3 export, CHARM and E1 inference cannot run simultaneously. The K3 project-model import/export path remains available after the inference ends; E1 display does not automatically run cleanup or change its geometry/export contract.

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

The direct E1 3D scene uses approximate display surfaces, not a simulation-ready tetrahedral FEM mesh. Its unit/anatomical limitations remain visible. K3's strict geometry/export requirements are not bypassed by the inference unit opt-in.

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
