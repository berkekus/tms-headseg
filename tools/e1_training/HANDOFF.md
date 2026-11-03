# E1 model handoff

This folder contains the code used to prepare, train and demonstrate the preliminary E1 model. It is separate from `tools/mri_prototype` and `tools/charm_gui`. Reusing the model does not require another training run.

The Workbench's **04 E1 segmentation** tab now calls this same prediction CLI in a separate inference environment and automatically opens successful new output. See the [desktop inference guide](../mri_prototype/INFERENCE.md). The header action **Open E1 segmentation…** continues to open a saved prediction.

## Files in Git

| Task | Files |
| --- | --- |
| Start or resume training | `E1_Colab.ipynb`, `README.md` |
| Custom trainer | `trainers.py` |
| Training environment | `requirements-colab.txt`, `requirements-colab.lock.txt` |
| Audit/package the original handoff | `audit_handoff.py`, `prepare_bundle.py`, `handoff_contract.json` |
| Inspect a completed result or run new inference | `E1_Demo.ipynb`, `DEMO.md`, `demo.py` |
| Display segmentation surfaces | `surface_view.py`, `surface_controls.js` |
| Rebuild clean notebooks | `build_notebook.py`, `build_demo_notebook.py` |

The notebooks embed their reviewed helpers. Existing uploaded copies do not update when repository files change; upload a regenerated notebook when adopting changes. Both notebooks are committed without execution outputs. Training and live inference require explicit flags.

## Files kept in Drive

Keep the entire completed `TMS_E1/runs/E1_L4_001` directory, not only its checkpoint:

```text
TMS_E1/
├── handoff_k2_e1.zip
└── runs/E1_L4_001/
    └── Dataset001_MultiAxial/
        └── nnUNetTrainer_E1Preliminary__nnUNetPlans__3d_fullres/
            ├── plans.json
            ├── dataset.json
            └── fold_0/
                ├── checkpoint_final.pth
                ├── checkpoint_best.pth
                ├── training_log_*.txt
                └── validation/
                    ├── summary.json
                    └── *.nii.gz
```

Retain the run's environment, session, split/contract and other metadata alongside these outputs. Five-epoch pilots are separate experiments; do not substitute their checkpoints. Only fold 0 was trained. MRI volumes, weights, archives and generated MRI-containing reports are not committed.

## Trainer needed to load the checkpoint

Data preparation alone does not need this trainer. Standard nnU-Net checkpoint loading, inference or training continuation needs its recorded class, `nnUNetTrainer_E1Preliminary`.

1. Use a separate Python 3.11 environment with nnU-Net **2.8.1** and PyTorch **2.6.0**. The Colab lock is for Linux/CUDA; do not apply it to macOS or install it into SimNIBS's Python.
2. Locate the active environment's nnU-Net package:

   ```bash
   python -c "from pathlib import Path; import nnunetv2; print(Path(nnunetv2.__file__).parent)"
   ```

3. Copy this folder's `trainers.py` into that package as `training/nnUNetTrainer/variants/training_length/nnUNetTrainer_E1.py`. If that file already exists, compare before replacing it. Both supplied notebooks handle this registration; the demo CLI also registers the trainer when needed.
4. Keep `plans.json`, `dataset.json` and `fold_0/checkpoint_final.pth` together. Follow [DEMO.md](DEMO.md) for saved-result viewing or explicitly enabled new inference.

The trainer subclasses nnU-Net's standard 100-epoch trainer, seeds initialization with 42 and saves each completed epoch. It does not define a different network architecture. The same file also contains the separate five-epoch pilot class.

Verified final checkpoint SHA-256:

```text
678867420134d54b31a9975f2c2d1a34b57b8369aef5692fa64f97a8980a531b
```

## Result and limits

The completed model used one T1 channel, `3d_fullres`, 44 training subjects and the fixed 10-subject validation split. Labels are 0 background, 1 skin, 2 skull, 3 CSF, 4 gray matter, 5 white matter; these IDs must not be interpreted as SimNIBS tissue IDs.

Mean validation Dice was **0.8715520701436821** against the handoff references. This is not a held-out test result. Original label semantics and geometry remain qualified in [the detailed experiment record](../../knowledge/experiments/e1-preparation.md); [the team result note](../../knowledge/experiments/e1-multiaxial-100ep.md) records the same model. The original training handoff's unknown spatial units differ from later team preparation copies with explicit units; this folder never rewrites originals.

The 3D demo produces approximate display surfaces, not a simulation-ready FEM mesh. Local CPU inference and synthetic geometry/control checks completed; interactive browser/Colab rehearsal remains separate. No desktop E1 integration is included.
