"""E2 Colab helpers: check K1's handoff, put every case in one axis order, build training commands.

Importing this module never starts training. Functions that read NIfTI import nibabel lazily, so the
archive checks also run in Colab's own kernel.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

DATASET = "Dataset002_E2Charm"
DATASET_ID = "2"
LABELS = {"background": 0, "skin": 1, "skull": 2, "csf": 3, "gray_matter": 4, "white_matter": 5}
TRAINERS = ("nnUNetTrainer_E2Smoke", "nnUNetTrainer_E2Preliminary")
MAX_ARCHIVE_BYTES = 20_000_000_000
GRID_ATOL_MM = 1e-3


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _layout(names):
    """Where dataset.json and splits_final.json sit inside the archive (a top folder is allowed)."""
    marker = f"nnUNet_raw/{DATASET}/dataset.json"
    found = [name for name in names if name == marker or name.endswith("/" + marker)]
    require(len(found) == 1, f"Arşivde tam bir tane {marker} olmalı; bulunan: {len(found)}.")
    prefix = found[0][: -len(marker)]
    preferred = f"{prefix}nnUNet_preprocessed/{DATASET}/splits_final.json"
    splits = [preferred] if preferred in names else [n for n in names if PurePosixPath(n).name == "splits_final.json"]
    require(len(splits) == 1, f"Arşivde tek bir splits_final.json bulunmalı; bulunan: {len(splits)}.")
    return {"dataset": f"{prefix}nnUNet_raw/{DATASET}", "raw": f"{prefix}nnUNet_raw", "splits": splits[0]}


def extract_handoff(archive_path, destination, expected_sha256):
    """Extract K1's archive once, after its SHA-256 matches the published value; return its layout."""
    archive_path, destination = Path(archive_path), Path(destination).resolve()
    digest = sha256(archive_path)
    require(digest == expected_sha256, f"Arşivin SHA-256 değeri yayımlanan pakete uymuyor: {digest}")
    marker, layout_file = destination / ".archive_sha256", destination / ".layout.json"
    if destination.exists():
        require(marker.is_file() and marker.read_text().strip() == digest,
                "Bu klasör başka bir arşivden açılmış. Yeni bir hedef klasör seç.")
        layout = json.loads(layout_file.read_text())
        return {key: destination / value for key, value in layout.items()}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        # Archives made by Windows PowerShell 5.1 store "\" separators; read them as "/".
        entries = [(info, info.filename.replace("\\", "/")) for info in infos]
        files = [(info, name) for info, name in entries if not name.endswith("/")]
        names = [name for _, name in files]
        require(len(names) == len(set(names)), "Arşivde aynı yol iki kez geçiyor.")
        require(sum(info.file_size for info in infos) <= MAX_ARCHIVE_BYTES, "Arşiv beklenenden çok büyük.")
        for info, name in entries:
            path = PurePosixPath(name)
            require(not path.is_absolute() and ".." not in path.parts and ":" not in name,
                    f"Güvensiz arşiv yolu: {info.filename}")
            require(not stat.S_ISLNK(info.external_attr >> 16), f"Arşivde bağlantı (symlink) var: {info.filename}")
        layout = _layout(names)
        with tempfile.TemporaryDirectory(prefix="e2-extract-", dir=destination.parent) as folder:
            temporary = Path(folder) / "content"
            for info, name in files:
                output = temporary / name
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, output.open("xb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
            (temporary / ".archive_sha256").write_text(digest + "\n")
            (temporary / ".layout.json").write_text(json.dumps(layout, indent=2) + "\n")
            temporary.rename(destination)
    return {key: destination / value for key, value in layout.items()}


def _cases(dataset):
    return sorted(p.name[: -len("_0000.nii.gz")] for p in (Path(dataset) / "imagesTr").glob("*_0000.nii.gz"))


def dataset_fingerprint(dataset, splits):
    """One hash over every file name and content in the dataset folder plus the split."""
    dataset = Path(dataset)
    lines = [f"{sha256(path)}  {path.relative_to(dataset).as_posix()}"
             for path in sorted(p for p in dataset.rglob("*") if p.is_file())]
    lines.append(f"{sha256(splits)}  splits_final.json")
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def audit(dataset, splits, contract):
    """Technical checks against the contract; returns a report. Not an anatomical review."""
    import nibabel as nib
    import numpy as np

    dataset, splits = Path(dataset), Path(splits)
    for name in ("imagesTs", "labelsTs"):
        require(not (dataset / name).exists(), f"Test klasörü eğitim paketine girmemeli: {name}")
    metadata = json.loads((dataset / "dataset.json").read_text())
    require(metadata.get("labels") == LABELS, "Etiket sözleşmesi 0–5 (deri, kafatası, BOS, GM, WM) değil.")
    require(metadata.get("channel_names") == {"0": "T1"}, "Tek T1 kanalı bekleniyordu.")
    require(metadata.get("file_ending") == ".nii.gz", ".nii.gz dosyaları bekleniyordu.")
    folds = json.loads(splits.read_text())
    require(len(folds) == 1 and set(folds[0]) == {"train", "val"}, "Tek bir sabit train/val bölmesi bekleniyordu.")
    train, val = folds[0]["train"], folds[0]["val"]
    require(sorted(train) == sorted(contract["train"]) and sorted(val) == sorted(contract["val"]),
            "Bölme, K1'in atamasından hesaplanan listeyle aynı değil.")
    require(not set(train) & set(val), "Bir vaka hem eğitimde hem doğrulamada.")
    cases = set(train) | set(val)
    require(metadata.get("numTraining") == len(cases), "dataset.json numTraining bölmeyle uyuşmuyor.")
    images = {p.name for p in (dataset / "imagesTr").iterdir()}
    labels = {p.name for p in (dataset / "labelsTr").iterdir()}
    require(images == {f"{case}_0000.nii.gz" for case in cases}, "imagesTr'de eksik, fazla ya da yanlış adlı dosya var.")
    require(labels == {f"{case}.nii.gz" for case in cases}, "labelsTr'de eksik, fazla ya da yanlış adlı dosya var.")
    report = {"dataset": DATASET, "train_count": len(train), "validation_count": len(val), "cases": [],
              "axis_codes": {}, "warnings": []}
    for case in sorted(cases):
        image = nib.load(dataset / "imagesTr" / f"{case}_0000.nii.gz")
        label = nib.load(dataset / "labelsTr" / f"{case}.nii.gz")
        require(image.ndim == 3 and label.shape == image.shape, f"{case}: 3B görüntü ve aynı boyutta etiket bekleniyordu.")
        require(np.allclose(image.affine, label.affine, rtol=0, atol=GRID_ATOL_MM), f"{case}: görüntü ve etiket aynı ızgarada değil.")
        values = np.asanyarray(label.dataobj)
        require(np.all(values == np.round(values)), f"{case}: etiketler tam sayı değil.")
        present = sorted(int(v) for v in np.unique(values))
        require(set(present) <= set(LABELS.values()), f"{case}: 0–5 dışında etiket var: {present}")
        require(np.isfinite(np.asanyarray(image.dataobj)).all(), f"{case}: görüntüde sonlu olmayan değer var.")
        codes = "".join(nib.aff2axcodes(image.affine))
        report["axis_codes"][codes] = report["axis_codes"].get(codes, 0) + 1
        report["cases"].append({"case": case, "split": "train" if case in train else "val", "shape": list(image.shape),
                                "axis_codes": codes, "units": image.header.get_xyzt_units()[0],
                                "zooms": [round(float(z), 4) for z in image.header.get_zooms()[:3]],
                                "labels_present": present})
    if len(report["axis_codes"]) > 1:
        report["warnings"].append(f"Vakalar farklı eksen sıralarında saklanmış: {report['axis_codes']}. "
                                  "nnU-Net görüntüyü döndürmez.")
    report["dataset_sha256"] = dataset_fingerprint(dataset, splits)
    report["split_sha256"] = sha256(splits)
    return report


def _to_ras(path, out_path):
    """Permute and flip axes toward RAS without interpolation; returns the source axis codes."""
    import nibabel as nib
    from nibabel import orientations
    import numpy as np

    image = nib.load(path)
    data = np.asanyarray(image.dataobj)
    transform = orientations.io_orientation(image.affine)
    moved = orientations.apply_orientation(data, transform).copy()
    affine = image.affine @ orientations.inv_ornt_aff(transform, data.shape)
    result = nib.Nifti1Image(moved, affine)
    result.set_data_dtype(data.dtype)
    result.set_sform(affine, code=1)
    result.set_qform(affine, code=1)
    result.header.set_xyzt_units(image.header.get_xyzt_units()[0])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(result, str(out_path))
    return "".join(nib.aff2axcodes(image.affine)), transform.tolist()


def write_ras_dataset(dataset, raw_out):
    """Copy the dataset into raw_out with every image and label in RAS order; returns the change log.

    Voxel values are never interpolated: each case is an exact axis permutation and flip of the original,
    and the world position of every voxel is unchanged."""
    dataset, target = Path(dataset), Path(raw_out) / DATASET
    require(not target.exists(), f"{target} zaten var; yeni bir klasör seç.")
    partial = Path(raw_out) / f".partial_{DATASET}"
    if partial.exists():  # left by an interrupted run; never used for training
        shutil.rmtree(partial)
    changes = {}
    for case in _cases(dataset):
        image_codes, transform = _to_ras(dataset / "imagesTr" / f"{case}_0000.nii.gz",
                                         partial / "imagesTr" / f"{case}_0000.nii.gz")
        label_codes, label_transform = _to_ras(dataset / "labelsTr" / f"{case}.nii.gz", partial / "labelsTr" / f"{case}.nii.gz")
        require(image_codes == label_codes and transform == label_transform, f"{case}: görüntü ve etiket aynı dönüşümü almadı.")
        changes[case] = {"source_axis_codes": image_codes, "to_ras": transform}
    shutil.copyfile(dataset / "dataset.json", partial / "dataset.json")
    partial.rename(target)
    return changes


def install_split(splits, preprocessed):
    target = Path(preprocessed) / DATASET / "splits_final.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        require(json.loads(target.read_text()) == json.loads(Path(splits).read_text()),
                "Kayıtlı bölme farklı; üzerine yazılmıyor.")
    else:
        shutil.copyfile(splits, target)
    return sha256(target)


def training_command(executable, trainer, fold_directory, resume=False):
    require(trainer in TRAINERS, "Beklenmeyen E2 eğiticisi.")
    folder = Path(fold_directory)
    if resume:
        checkpoints = [folder / f"checkpoint_{name}.pth" for name in ("final", "latest", "best")]
        checkpoint = next((path for path in checkpoints if path.is_file()), None)
        require(checkpoint is not None, "Devam istendi ama checkpoint yok; sessizce baştan başlatılmıyor.")
        require(not (folder / "validation/summary.json").is_file(),
                "Bu çalışmanın doğrulaması bitmiş; sonuçlara bak ya da yeni deney kimliği kullan.")
        require(zipfile.is_zipfile(checkpoint), "Checkpoint eksik ya da beklenmeyen biçimde.")
        with zipfile.ZipFile(checkpoint) as archive:
            require(archive.testzip() is None, "Checkpoint bütünlük kontrolünden geçmedi.")
    else:
        require(not folder.exists(), "Çalışma klasörü var. Devam seçeneğini ya da yeni deney kimliğini kullan.")
    return [str(executable), DATASET_ID, "3d_fullres", "0", "-tr", trainer, "-device", "cuda"] + (["--c"] if resume else [])


def validation_complete(fold_directory, expected_cases):
    """True only when the final 3d_fullres validation covered every validation case."""
    summary = Path(fold_directory) / "validation" / "summary.json"
    if not summary.is_file():
        return False
    metrics = json.loads(summary.read_text())
    return len(metrics.get("metric_per_case", [])) == expected_cases


def experiment_id_ok(value):
    return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value) is not None


def preview(dataset, cases, destination):
    """Mid-plane overlays drawn in voxel order, so differently stored cases look different here."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    import nibabel as nib
    import numpy as np

    colors = ListedColormap([(0, 0, 0, 0), (.99, .65, .52, .45), (1, .94, .70, .5), (.4, .64, 1, .5),
                             (.65, .32, .8, .5), (.9, .9, .9, .5)])
    figure, axes = plt.subplots(len(cases), 3, figsize=(12, 3.6 * len(cases)), squeeze=False)
    for row, case in enumerate(cases):
        image = nib.load(Path(dataset) / "imagesTr" / f"{case}_0000.nii.gz")
        data = np.asanyarray(image.dataobj).astype(np.float32)
        label = np.asanyarray(nib.load(Path(dataset) / "labelsTr" / f"{case}.nii.gz").dataobj)
        low, high = np.percentile(data[data > 0], [1, 99]) if (data > 0).any() else (0, 1)
        for axis in range(3):
            index = [slice(None)] * 3
            index[axis] = data.shape[axis] // 2
            ax = axes[row, axis]
            ax.imshow(np.rot90(data[tuple(index)]), cmap="gray", vmin=low, vmax=high)
            ax.imshow(np.rot90(label[tuple(index)]), cmap=colors, vmin=0, vmax=5, interpolation="nearest")
            ax.set_title(f"{case} · {''.join(nib.aff2axcodes(image.affine))} · eksen {axis}", fontsize=9)
            ax.axis("off")
    figure.tight_layout()
    figure.savefig(destination, dpi=90)
    plt.close(figure)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="E2 handoff checks for the Colab notebook.")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("audit")
    check.add_argument("dataset", type=Path)
    check.add_argument("splits", type=Path)
    check.add_argument("contract", type=Path)
    check.add_argument("out", type=Path)
    ras = commands.add_parser("ras")
    ras.add_argument("dataset", type=Path)
    ras.add_argument("raw_out", type=Path)
    ras.add_argument("out", type=Path)
    view = commands.add_parser("preview")
    view.add_argument("dataset", type=Path)
    view.add_argument("out", type=Path)
    view.add_argument("cases", nargs="+")
    args = parser.parse_args()
    if args.command == "audit":
        report = audit(args.dataset, args.splits, json.loads(args.contract.read_text()))
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"{report['train_count']} eğitim / {report['validation_count']} doğrulama; eksen sıraları: {report['axis_codes']}")
    elif args.command == "ras":
        changes = write_ras_dataset(args.dataset, args.raw_out)
        args.out.write_text(json.dumps(changes, indent=2) + "\n")
        moved = sorted(case for case, change in changes.items() if change["source_axis_codes"] != "RAS")
        print(f"RAS'a çevrilen vaka: {len(moved)} / {len(changes)}")
    else:
        preview(args.dataset, args.cases, args.out)
        print(args.out)


if __name__ == "__main__":
    main()
