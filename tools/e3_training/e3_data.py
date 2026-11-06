"""Dataset003 adapter around E2's reviewed archive/grid/RAS helpers.

The private module copy leaves E2 behavior unchanged. Archive contents are never code.
"""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

DATASET = "Dataset003_E3Face"
DATASET_ID = "3"
LABELS = {"background": 0, "skin": 1, "skull": 2, "csf": 3,
          "gray_matter": 4, "white_matter": 5, "ignore": 6}
HERE = Path(__file__).resolve().parent
base_path = HERE / "e2_helpers.py"
if not base_path.is_file():
    base_path = HERE.parent / "e2_training/e2_helpers.py"
spec = importlib.util.spec_from_file_location("_e3_base_helpers", base_path)
_base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_base)
_base.DATASET, _base.DATASET_ID, _base.LABELS = DATASET, DATASET_ID, LABELS
require, sha256 = _base.require, _base.sha256
extract_handoff, write_ras_dataset, install_split = _base.extract_handoff, _base.write_ras_dataset, _base.install_split
dataset_fingerprint = _base.dataset_fingerprint


def verify_sidecar(path, expected):
    fields = Path(path).read_text(encoding="utf-8-sig").split()
    require(fields and fields[0].lower() == expected, "Archive SHA-256 sidecar differs from the reviewed E3 package.")


def validate_split(train, val, contract):
    require(len(train) == len(set(train)) and len(val) == len(set(val)), "Duplicate split entries.")
    require(sorted(train) == sorted(contract["train"]) and sorted(val) == sorted(contract["val"]), "Fixed E3 split changed.")
    copies = contract["copy_sources"]
    require(all(c == source + "w2" and source.startswith("IXI") for c, source in copies.items()), "Unexpected copy identifiers.")
    require(set(train) == set(contract["source_train"]) | set(copies), "Training entries differ from source people plus IXI copies.")
    require(set(copies.values()) == {c for c in contract["source_train"] if c.startswith("IXI")}, "Every IXI training case needs exactly one copy.")
    require(not set(contract["source_train"]) & set(val) and not set(train) & set(val), "Source-person training/validation leakage.")


def outside_acquisition(image):
    """Zero voxels connected to a volume border, with the preparer's 6-connectivity."""
    import numpy as np
    from scipy import ndimage
    components, _ = ndimage.label(image == 0)
    border = np.unique(np.concatenate([components[0].ravel(), components[-1].ravel(),
        components[:, 0].ravel(), components[:, -1].ravel(), components[:, :, 0].ravel(), components[:, :, -1].ravel()]))
    return np.isin(components, border[border > 0])


def array_grid_hash(values, image):
    """Decoded values/grid, not platform-specific gzip encoding."""
    import numpy as np
    h = hashlib.sha256()
    h.update(json.dumps({"shape": list(values.shape), "dtype": values.dtype.str,
                         "units": image.header.get_xyzt_units()[0]}, sort_keys=True).encode())
    h.update(np.asarray(image.affine, dtype="<f8").tobytes())
    h.update(values.tobytes(order="C"))
    return h.hexdigest()


def audit(dataset, splits, contract):
    import nibabel as nib
    import numpy as np
    dataset, splits = Path(dataset), Path(splits)
    split = json.loads(splits.read_text(encoding="utf-8"))[0]
    validate_split(split["train"], split["val"], contract)
    report = _base.audit(dataset, splits, contract)
    manifest_path = splits.parent / "e3_manifest.csv"
    if "manifest_sha256" in contract:
        require(sha256(manifest_path) == contract["manifest_sha256"], "E3 manifest hash changed.")
    with manifest_path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    manifest = {r["case_id"]: r for r in rows}
    require(len(manifest) == len(rows) == len(split["train"] + split["val"])
            and set(manifest) == set(split["train"] + split["val"]), "Manifest cases differ from the split.")
    copies = contract["copy_sources"]
    semantic = {}
    for case in split["train"] + split["val"]:
        source = copies.get(case, case)
        row = manifest[case]
        is_train = case in split["train"]
        require(row["source_case"] == source and row["split"] == ("train" if is_train else "val")
                and row["source"] == ("IXI" if source.startswith("IXI") else "MultiAxial")
                and int(row["weight_copy"]) == (2 if case in copies else 1), f"{case}: manifest identity mismatch.")
        if case in copies:
            for folder, ending in (("imagesTr", "_0000.nii.gz"), ("labelsTr", ".nii.gz")):
                require(sha256(dataset / folder / (case + ending)) == sha256(dataset / folder / (source + ending)),
                        f"{case}: weighted copy differs from its source.")
            continue
        image = nib.load(dataset / "imagesTr" / f"{case}_0000.nii.gz")
        label = nib.load(dataset / "labelsTr" / f"{case}.nii.gz")
        values = np.asanyarray(label.dataobj)
        image_values = np.asanyarray(image.dataobj)
        semantic[case] = [array_grid_hash(image_values, image), array_grid_hash(values, label)]
        require(image.header.get_xyzt_units()[0] == "mm" and np.isfinite(image.affine).all()
                and abs(np.linalg.det(image.affine[:3, :3])) > 1e-8, f"{case}: invalid physical geometry.")
        if is_train:
            mask = outside_acquisition(image_values)
            require(np.array_equal(mask, values == 6), f"{case}: ignore mask differs from border-connected zero image voxels.")
            ml = float(np.count_nonzero(mask)) * float(np.prod(label.header.get_zooms()[:3])) / 1000
            require(abs(ml - float(row["ignore_ml"])) <= .11, f"{case}: ignored volume differs from manifest.")
        else:
            require(not np.any(values == 6), f"Validation {case} contains ignore voxels.")
    for case, source in copies.items():semantic[case] = semantic[source]
    semantic_payload = {"pairs": semantic, "split": split,
                        "metadata": json.loads((dataset / "dataset.json").read_text())}
    report["semantic_dataset_sha256"] = hashlib.sha256(json.dumps(semantic_payload, sort_keys=True).encode()).hexdigest()
    report.update({"unique_training_subjects": len(contract["source_train"]), "weighted_copies": len(copies),
                   "sampling": "uniform_over_entries", "ignore_label": 6})
    return report


def preview(dataset, cases, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    import nibabel as nib
    import numpy as np
    colors = ListedColormap([(0, 0, 0, 0), (.99, .65, .52, .45), (1, .94, .70, .5),
                             (.4, .64, 1, .5), (.65, .32, .8, .5), (.9, .9, .9, .5)])
    fig, axes = plt.subplots(len(cases), 3, figsize=(12, 3.6 * len(cases)), squeeze=False)
    for row, case in enumerate(cases):
        a = np.asanyarray(nib.load(Path(dataset) / "imagesTr" / f"{case}_0000.nii.gz").dataobj)
        b = np.asanyarray(nib.load(Path(dataset) / "labelsTr" / f"{case}.nii.gz").dataobj)
        for axis in range(3):
            index = [slice(None)] * 3;index[axis] = a.shape[axis] // 2
            plane, labels = a[tuple(index)].T, b[tuple(index)].T
            axes[row, axis].imshow(plane, cmap="gray", origin="lower")
            axes[row, axis].imshow(np.ma.masked_where(labels == 6, labels), cmap=colors, vmin=0, vmax=5, origin="lower")
            axes[row, axis].set_title(f"{case} / axis {axis}; ignore hidden")
            axes[row, axis].axis("off")
    fig.tight_layout();fig.savefig(destination, dpi=130);plt.close(fig)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dataset003 E3 audit and lossless RAS preparation.")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("audit")
    for name in ("dataset", "splits", "contract", "out"):check.add_argument(name, type=Path)
    ras = commands.add_parser("ras")
    for name in ("dataset", "raw_out", "out"):ras.add_argument(name, type=Path)
    view = commands.add_parser("preview")
    view.add_argument("dataset", type=Path);view.add_argument("out", type=Path);view.add_argument("cases", nargs="+")
    args = parser.parse_args()
    if args.command == "audit":
        report = audit(args.dataset, args.splits, json.loads(args.contract.read_text()))
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"{report['train_count']} entries / {report['unique_training_subjects']} people train; {report['validation_count']} validation; {report['axis_codes']}")
    elif args.command == "ras":
        changes = write_ras_dataset(args.dataset, args.raw_out)
        args.out.write_text(json.dumps(changes, indent=2) + "\n", encoding="utf-8")
        print(f"RAS preparation complete: {len(changes)} entries.")
    else:
        preview(args.dataset, args.cases, args.out);print(args.out)


if __name__ == "__main__":main()
