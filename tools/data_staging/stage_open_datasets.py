"""Stage openly licensed datasets in the team Drive folder layout.

The shared Drive archive keeps one folder per dataset (``D01_...``) with a
``00_OKU_BENI.txt`` guide and a checksum manifest. This tool downloads the
selected Zenodo files for datasets that are not yet in the Drive, verifies
them against the MD5 published by Zenodo, records SHA-256 values, and writes
the guide and manifest. Upload the resulting folder to
``data/01_Veri_Setleri`` in the team Drive by hand.

Only datasets whose stated license allows non-commercial sharing with
attribution are listed here. Access-controlled datasets (ATLAS, HCP, ADNI,
CERMEP, SynthRAD2025 center D) must not be mirrored.

Usage:
    python stage_open_datasets.py list
    python stage_open_datasets.py stage D14 --out <staging dir> [--all-files]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ZENODO_API = "https://zenodo.org/api/records/{record}"
CHUNK = 1024 * 1024

DATASETS: dict[str, dict] = {
    "D14": {
        "folder": "D14_Paired_Head_CT_MRI",
        "title": "A Paired Head CT-MRI Dataset for Cross-Modality Image Synthesis",
        "record": "17486320",
        "files": ["participants.xlsx", "cerebrovascular-disease.zip"],
        "optional": ["meningioma.zip", "vestibular-schwannoma.zip", "pituitary-tumor.zip"],
        "license": "CC BY-NC 4.0 (Zenodo kaydi)",
        "module": "A",
        "purpose": "BT'den turetilmis kafatasi referansi: modelimiz ve charm icin "
        "ortak kafatasi testi.",
        "notes": "120 ameliyat oncesi hasta, ince kesit BT + MR. MR sekansi (kontrastli "
        "T1 olabilir) ve yuz durumu kayitta belirtilmemis; ilk 3 vakada kontrol edin. "
        "Hazir etiket yok; kafatasi BT'den esiklemeyle cikarilir. Once "
        "serebrovaskuler alt grup (4,4 GB) indirilir.",
    },
    "D15": {
        "folder": "D15_SynthRAD2023_Beyin_MR_BT",
        "title": "SynthRAD2023 Grand Challenge dataset (training data)",
        "record": "7260705",
        "files": ["Task1.zip"],
        "optional": ["synthRAD2023_dataset_article.pdf"],
        "license": "CC BY-NC 4.0 (Zenodo kaydi)",
        "module": "A",
        "purpose": "Cok merkezli ek BT dogrulamali kafatasi referansi.",
        "notes": "Task1.zip beyin ve pelvis MR-BT ciftlerini birlikte icerir; yalniz beyin "
        "kullanilir. Beyin hastalarinda yuz silinmis. Merkez B ve C'nin bazi MR'lari "
        "gadolinyum kontrastli; merkez A kontrastsiz. Yuz/kulak degerlendirmesinde "
        "kullanilamaz.",
    },
    "D16": {
        "folder": "D16_SynthRAD2025_Bas_Boyun_MR_BT",
        "title": "SynthRAD2025 Grand Challenge dataset (training, public centers)",
        "record": "15373853",
        "files": ["synthRAD2025_Task1_Train.zip"],
        "optional": [],
        "license": "CC BY-NC 4.0 (merkez A, B, C, E). Merkez D sinirli lisans: "
        "Drive'a KOPYALANMAZ.",
        "module": "A",
        "purpose": "Kafatasi tabani icin ek BT referansi (dusuk oncelik).",
        "notes": "Bas-boyun gorus alani kafa tepesini kapsamayabilir; yuz silinmis. "
        "Arsiv bas-boyun, toraks ve karin bolgelerini birlikte icerir. Merkez D "
        "verisi arsivdeyse Drive'a yuklemeden once cikarin.",
    },
}


def fetch_record(record: str) -> dict:
    with urllib.request.urlopen(ZENODO_API.format(record=record), timeout=60) as resp:
        return json.load(resp)


def record_files(record_json: dict) -> dict[str, dict]:
    """Map file name to size, md5 and download URL from a Zenodo record."""
    files = {}
    for item in record_json.get("files", []):
        checksum = item.get("checksum", "")
        files[item["key"]] = {
            "bytes": int(item["size"]),
            "md5": checksum.split(":", 1)[1] if checksum.startswith("md5:") else None,
            "url": item["links"]["self"],
        }
    return files


def file_digests(path: Path) -> tuple[str, str]:
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            md5.update(block)
            sha.update(block)
    return md5.hexdigest(), sha.hexdigest()


def download(url: str, target: Path, expected_bytes: int) -> None:
    """Download with resume support; skips files that are already complete."""
    have = target.stat().st_size if target.exists() else 0
    if have == expected_bytes:
        return
    if have > expected_bytes:
        target.unlink()
        have = 0
    request = urllib.request.Request(url)
    if have:
        request.add_header("Range", f"bytes={have}-")
    with urllib.request.urlopen(request, timeout=120) as resp:
        if have and resp.status != 206:
            have = 0  # Server ignored the range; start over.
        with target.open("ab" if have else "wb") as out:
            done = have
            for block in iter(lambda: resp.read(CHUNK), b""):
                out.write(block)
                done += len(block)
                print(f"\r  {target.name}: {done / 1e9:.2f} / {expected_bytes / 1e9:.2f} GB",
                      end="", flush=True)
    print()


def readme_text(dataset_id: str, spec: dict, names: list[str], today: str) -> str:
    return "\n".join([
        f"{dataset_id} — {spec['title']}",
        "",
        "KAPSAM: Acik lisansli kaynak dosyalari (degistirilmeden)",
        "",
        spec["notes"],
        "",
        f"PROJE MODULU: {spec['module']}",
        f"AMAC: {spec['purpose']}",
        "",
        f"KAYNAK: https://zenodo.org/records/{spec['record']}",
        f"LISANS NOTU: {spec['license']}",
        "",
        "DOSYALAR: " + ", ".join(names),
        "",
        "KULLANIM",
        "Dosyalari indirin ve kaynak_manifest.json icindeki SHA256 degerleriyle "
        "karsilastirin. MD5 degerleri Zenodo'nun yayimladigi degerlerle eslesti.",
        "",
        f"HAZIRLAMA TARIHI: {today}",
        "Kaynak dosyalarin icerikleri degistirilmedi.",
        "",
    ])


def stage(dataset_id: str, out_root: Path, all_files: bool) -> Path:
    spec = DATASETS[dataset_id]
    available = record_files(fetch_record(spec["record"]))
    wanted = spec["files"] + (spec["optional"] if all_files else [])
    missing = [name for name in wanted if name not in available]
    if missing:
        raise SystemExit(f"{dataset_id}: not in Zenodo record {spec['record']}: {missing}")

    folder = out_root / spec["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    entries = []
    for name in wanted:
        info = available[name]
        target = folder / name
        download(info["url"], target, info["bytes"])
        md5, sha = file_digests(target)
        if info["md5"] and md5 != info["md5"]:
            raise SystemExit(f"{name}: MD5 mismatch ({md5} != {info['md5']}); delete and retry")
        entries.append({"name": name, "bytes": info["bytes"], "md5": md5, "sha256": sha})

    today = dt.date.today().isoformat()
    manifest = {
        "id": dataset_id,
        "source_record": f"https://zenodo.org/records/{spec['record']}",
        "license": spec["license"],
        "files": entries,
        "prepared_at": today,
    }
    (folder / "kaynak_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / "00_OKU_BENI.txt").write_text(
        readme_text(dataset_id, spec, [e["name"] for e in entries], today), encoding="utf-8")
    return folder


def list_datasets() -> None:
    for dataset_id, spec in DATASETS.items():
        print(f"{dataset_id}  {spec['folder']}  (zenodo {spec['record']}, {spec['license']})")
        try:
            available = record_files(fetch_record(spec["record"]))
        except OSError as exc:
            print(f"    record unavailable: {exc}")
            continue
        for name in spec["files"] + spec["optional"]:
            info = available.get(name)
            tag = "default " if name in spec["files"] else "optional"
            size = f"{info['bytes'] / 1e9:7.2f} GB" if info else "  MISSING"
            print(f"    [{tag}] {size}  {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="show datasets and live Zenodo file sizes")
    stage_cmd = sub.add_parser("stage", help="download and package one or more datasets")
    stage_cmd.add_argument("ids", nargs="+", choices=sorted(DATASETS))
    stage_cmd.add_argument("--out", type=Path, required=True)
    stage_cmd.add_argument("--all-files", action="store_true",
                           help="also download optional archives")
    args = parser.parse_args(argv)

    if args.command == "list":
        list_datasets()
        return 0
    for dataset_id in args.ids:
        print(f"Staging {dataset_id} ...")
        print(f"  ready for upload: {stage(dataset_id, args.out, args.all_files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
