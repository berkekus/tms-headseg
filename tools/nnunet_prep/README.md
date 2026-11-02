# MultiAxial → nnU-Net preparation (K1 → K2 handoff)

`prepare_multiaxial.py` splits MultiAxial (D01) by subject and writes an nnU-Net v2 raw dataset. Outputs live **outside** the repository (default used so far: `C:\Users\Berke\tms-data\nnunet`).

## What was built (2026-11-02, K1 machine)

| Item | Value |
| --- | --- |
| Split | 44 train / 10 val / 10 test, seed 42, stratified by center. Test = 2 GU + 2 NC + 2 NYU clinical + healthy `subj1–4`. |
| nnU-Net dataset | `Dataset001_MultiAxial`: 54 cases (train+val), channel `T1`, labels 0 background, 1 skin, 2 skull, 3 CSF, 4 gray matter, 5 white matter. |
| Fixed split | `nnUNet_preprocessed/Dataset001_MultiAxial/splits_final.json` (one entry, so fold `0` = our split). |
| Test hold-out | `test_holdout/` (10 defaced cases, 4 intact-face twins of `subj1–4`) is **not** part of the nnU-Net dataset. Held by K1; do not open it while tuning. |
| Plan | `3d_fullres`, 1 mm spacing, patch 128×160×112, batch 2 (nnU-Net 2.8.1). `3d_lowres` dropped by nnU-Net (image sizes too similar). |
| Preprocessed | 54 cases, 1.1 GB. |

Known caveats:
- Label mapping from the release labels is inferred (intensity + overlay check), not documented by the data release. Air cavities (release label 1) are merged into background. No `ignore` label for the removed face yet (Q-16).
- Five NYU cases (NYU003/006/007/008/009) have a sheared sform that ITK-based readers reject. Their affine was replaced by the nearest rotation in the nnU-Net copies; `split_manifest.csv` flags them (`affine_orthonormalized`). Do not use these cases' converted affines for physical-space (mm) checks.
- This machine has 15.8 GB RAM: use one preprocessing worker and keep `nnUNet_n_proc_DA` at 4 or lower.

## Run training (PowerShell)

```powershell
$env:nnUNet_raw          = "C:\Users\Berke\tms-data\nnunet\nnUNet_raw"
$env:nnUNet_preprocessed = "C:\Users\Berke\tms-data\nnunet\nnUNet_preprocessed"
$env:nnUNet_results      = "C:\Users\Berke\tms-data\nnunet\nnUNet_results"
$env:nnUNet_n_proc_DA    = "4"
$nn = "C:\Users\Berke\tms-data\venv-nnunet\Scripts"

# 1) Smoke run: measure epoch time (not a result)
& "$nn\nnUNetv2_train.exe" 1 3d_fullres 0 -tr nnUNetTrainer_5epochs

# 2) Preliminary model, 100 epochs (resume after an interruption with --c)
& "$nn\nnUNetv2_train.exe" 1 3d_fullres 0 -tr nnUNetTrainer_100epochs
```

`C:\Users\Berke\tms-data\venv-nnunet` was created with `--system-site-packages` to reuse the installed PyTorch 2.6 + CUDA 12.4 (RTX 4070, 12 GB). Use a new results folder or `-tr` variant for every experiment so runs do not overwrite each other.

## Rebuild from scratch

```bash
python tools/nnunet_prep/prepare_multiaxial.py <D01 acilmis_dosyalar> --out <dir>
nnUNetv2_plan_and_preprocess -d 1 -c 3d_fullres --verify_dataset_integrity -np 1
```

## Tests

```bash
cd tools/nnunet_prep && python -m unittest -v
```
