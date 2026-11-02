# Dataset staging for the team Drive

Downloads openly licensed datasets that are missing from the team Drive archive and packages each one in the archive's folder style (`00_OKU_BENI.txt` guide + `kaynak_manifest.json` with SHA-256). A team member with Drive write access then uploads the folder to `data/01_Veri_Setleri`.

| ID | Folder | Default download | License |
| --- | --- | --- | --- |
| D14 | `D14_Paired_Head_CT_MRI` | `participants.xlsx` + `cerebrovascular-disease.zip` (4.4 GB) | CC BY-NC 4.0 |
| D15 | `D15_SynthRAD2023_Beyin_MR_BT` | `Task1.zip` (14.5 GB; brain + pelvis) | CC BY-NC 4.0 |
| D16 | `D16_SynthRAD2025_Bas_Boyun_MR_BT` | `synthRAD2025_Task1_Train.zip` (14.9 GB), low priority | CC BY-NC 4.0 for centers A/B/C/E; never upload center D |

Access-controlled datasets (ATLAS, HCP, ADNI, CERMEP) are deliberately not supported: their terms do not allow re-hosting.

## Use

Requires Python 3.9+ and no extra packages. Use a staging folder **outside** this repository.

```bash
python tools/data_staging/stage_open_datasets.py list                 # live file sizes from Zenodo
python tools/data_staging/stage_open_datasets.py stage D14 D15 --out D:/tms-staging
python tools/data_staging/stage_open_datasets.py stage D14 --all-files --out D:/tms-staging   # all 40 GB
```

Downloads resume after interruption. Each file is checked against the MD5 published by Zenodo; a mismatch stops the run.

## Tests

```bash
cd tools/data_staging && python -m unittest -v
```

The tests use synthetic bytes and make no network calls.

See [knowledge/references/team-drive.md](../../knowledge/references/team-drive.md) for the archive layout and the full list of items still missing.
