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

Header update (2026-11-03): output files now state `mm` units with qform = sform (code 1), as the K3 coordinate contract requires; the first build left units unknown and K3's `read_source` rejected it. A rebuild into `C:\Users\Berke\tms-data\nnunet_mm` was checked against the first build: all 136 files have identical voxels and affines, so the model K2 trained on the first build (`handoff_k2.zip`) is unaffected. `original_affines.json` stores the source affines of the five sheared NYU cases; **NYU009 is in the test hold-out**, so its millimetre metrics must use that source affine.

Known caveats:
- Label mapping from the release labels is inferred (intensity + overlay check); the paper lists the seven classes but not their numeric values and does not contradict the mapping. Air cavities (release label 1) are merged into background. No `ignore` label for the removed face yet (Q-16).
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

## E2: charm labels (`prepare_e2.py`, decided 2026-11-04)

E2 trains on charm 4.6.0 labels only, so the sulcal GM/CSF boundary follows one convention (EXP-002, NC033).

| Source | Cases | charm input | Split |
| --- | --- | --- | --- |
| IXI (D06), cohort `train` | 29 (K1 14 + K2 15) | T1+T2 | 2 val per site (seed 42), rest train |
| MultiAxial (D01), E1 train/val | 54 | T1 only, the Dataset001 image | E1 split kept (44 / 10) |

Never included: IXI `test_face`, `calibration`, `excluded_d05`, and the MultiAxial test hold-out. A case enters only if its delivery checksums match, `run.json` reports a completed SimNIBS 4.6.0 run, and its QC row says `pass` (`fail`/`check` never enter; `--allow-unchecked` admits only rows with no QC yet). Labels use `headmodel.labels.CHARM_TO_PROJECT` (blood → CSF). Labels on exactly-zero voxels connected to the volume border (padding, defacing) become background, because charm extrapolates tissue there (IXI426: 414 mL); `e2_manifest.csv` records `padding_cleared_ml` per case. Later `--qc` sheets override earlier ones, so a K1 review can turn K2's `check` into `pass`. Output: `Dataset002_E2Charm` plus `e2_manifest.csv`.

```powershell
python tools/nnunet_prep/prepare_e2.py `
    --deliver <tms-data>\charm_K1\deliver_K1 <K2 deliver_K2> <MultiAxial deliver folders> `
    --qc <qc_K1.csv> <qc_K2.csv> <MultiAxial qc sheets> `
    --ixi-images <tms-data>\D06\acilmis_dosyalar `
    --ma-images <tms-data>\nnunet_mm\nnUNet_raw\Dataset001_MultiAxial\imagesTr `
    --out <new folder> --require-all
nnUNetv2_plan_and_preprocess -d 2 -c 3d_fullres --verify_dataset_integrity -np 1
```

Preview (2026-11-04): all 29 IXI cases (23 train, 6 val) built with image/label affine difference 0; the 14-case preview passed `nnUNetv2_extract_fingerprint --verify_dataset_integrity`. The full build waits for the 54 MultiAxial charm runs.

Pass-only build (2026-11-05): all 54 MultiAxial runs delivered and verified. 19 are QC `check` because charm labels partly filled stroke lesions as WM (EXP-002). The other 35 plus all 29 IXI cases (64; 50 train, 14 val) were built into `e2_pass_20261105` and passed `--verify_dataset_integrity`. `--require-all` waits for the team's lesion decision.

Lesion rule (decided 2026-11-05, option b): for MultiAxial cases, regions that the Dataset001 reference labels CSF, that charm labels GM or WM, and that are CSF-dark on T1 become CSF when they are thick (survive a 2-voxel opening) and at least 1 mL (`csf_like_lesions`). Thin sulcal differences keep charm's convention. The reference is read from `labelsTr` next to `--ma-images` (or `--ma-labels`); `e2_manifest.csv` records `lesion_csf_ml`. The full build (`e2_full_20261105`, 83 cases, `--require-all`) adds the QC sheet `qc_K1_lesion_rule_20261105.csv` after the other sheets.

## Tests

```bash
cd tools/nnunet_prep && python -m unittest -v
```
