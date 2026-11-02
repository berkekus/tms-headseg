---
type: Reference
title: Shared Drive Data Archive
description: Layout, verification scope, unpacking procedure, and missing items of the team's Google Drive data archive.
status: draft
generated:
  by: claude/opus-5.5
  at: '2026-11-02T18:00:00+03:00'
source_id: SRC-011
sources:
- id: drive
  resource: https://drive.google.com/drive/folders/1JlxZ5EOhOxTCys5m_hkdfT97lMSGgx5K
  title: Team Drive folder "TMS" (link-shared listing read 2026-11-02)
---

# Shared Drive Data Archive

The team keeps literature PDFs and downloaded data in a link-shared Google Drive folder. The listing and guide files below were read on 2026-11-02 through the public folder view; nothing was downloaded beyond the small guide/JSON files, and no package was unpacked or verified by us.[^drive]

## Layout

```text
TMS/
└── Makaleler/                     83 numbered literature PDFs (two files share the name 80.pdf)
    └── data/
        ├── 00_Envanter_ve_Kullanim_Rehberi/
        │   ├── 00_BURADAN_BASLA.txt            start guide (2026-10-23)
        │   ├── KAYNAK_DURUM_LISTESI.json       current status per D/K item
        │   ├── SON_KONTROL_KAYDI.json          last verification record (2026-10-23)
        │   └── Veri_ve_Arac_Envanteri.xlsx     inventory copy (status cells outdated)
        ├── 01_Veri_Setleri/   D01–D13, one folder each
        └── 02_Kod_ve_Araclar/ K01–K10, one folder each
```

Module A folder IDs: D01 `17QEqu2TAgsMxKHVaRq9BJ1RPd0HmwII9`, D04 `1E4ETdnke4KFCHofhDOACuvuPeZQ58CdY`, D05 `1IFVqzzkxfrpJn5doqHjIkkLJsNVo5NB2`, D06 `1AtZRVkdXdwpTyHs5IomR2rORgeQe57Re`, K02 GRACE `1wVis0i8JBVximWRgE4oGtxfuZJJ3E0HT`. Datasets folder `01_Veri_Setleri`: `1CObGPbWqJ85xTOQRL2MYkwGNhOt982zS`.

## What the archive states about itself

- Usable image data: D01, D02, D03, D04, D05, D06, D08, D11. D10 is metadata only. D07, D09, D12, D13 contain only a guide (access or version choice pending).
- Code: K01–K10 source archives, not installed or run. GRACE weights are deliberately absent (redistribution forbidden).
- The JSON status list is the current record; blank status cells in the Excel copy are outdated.
- Verification scope (2026-10-23): Drive names, sizes, and package counts were matched against package manifests; this was not a fresh download of every archive. Data packages carry SHA-256; code packages only size and ZIP CRC checks.
- Downloading does not grant unlimited redistribution; licenses differ per source.

Module A sizes: D01 736,566,931 bytes; D04 1,765,898,921; D05 1,029,282,654; D06 742,813,927 (≈4.3 GB together, before unpacking).

## Unpacking procedure

Download every ZIP of a folder plus `paket_manifest.json` and `PAKETLERI_AC.py` into one local folder outside the Git repository. Run `python PAKETLERI_AC.py` with Python 3.11+; it checks SHA-256, then extracts into `acilmis_dosyalar/` and rejoins `.birlesecek` parts (required for D04). Stop and re-download on any missing package or checksum error. Do not rename files.

## Missing from the archive (to add)

| Proposed folder | Action | Mirror allowed? |
| --- | --- | --- |
| `D14_Paired_Head_CT_MRI` | `tools/data_staging/stage_open_datasets.py stage D14` (participants.xlsx + cerebrovascular subset, 4.4 GB). | Yes, CC BY-NC 4.0 with attribution, non-commercial. |
| `D15_SynthRAD2023_Beyin_MR_BT` | `stage D15` (Task1.zip, 14.5 GB). | Yes, CC BY-NC 4.0. |
| `D16_SynthRAD2025_Bas_Boyun_MR_BT` | Optional `stage D16` (14.9 GB); low priority. | Centers A/B/C/E only; never center D. |
| `D17_CERMEP_IDB_MRXFDG` | Guide-only folder recording the access request. | No; access-committee data. |
| `D18_SHARM` | Guide-only until the figshare license is read. | Unknown. |
| `D19_DBB`, `D20_Head_Model_Population` | Guide-only until host and license are verified. | Unknown. |
| `K11_nnUNet`, `K12_SimNIBS_4_6` | Record pinned versions instead of mirroring; install from official sources. | Not needed. |

Uploads must be done by a team member with Drive write access; this session had no Drive write connector. See the [staging tool](../../tools/data_staging/README.md).

## Related notes

[Data inventory](datasets.md) · [Start plan](../playbooks/module-a-kickoff.md) · [Source catalog](source-catalog.md)

[^drive]: Folder listings of `TMS`, `Makaleler`, `data`, and all D/K subfolders; full text of `00_BURADAN_BASLA.txt`, `KAYNAK_DURUM_LISTESI.json`, `SON_KONTROL_KAYDI.json`, D01/D04/D05/D06/D07/D09/D10/D12/D13/K02 guides, and the D01/D06 manifests, read 2026-11-02. [Open folder](https://drive.google.com/drive/folders/1JlxZ5EOhOxTCys5m_hkdfT97lMSGgx5K).
