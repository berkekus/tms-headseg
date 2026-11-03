"""Create training-only voxel-plane previews; never modifies source NIfTI files."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import nibabel as nib
import numpy as np

from audit_handoff import DATASET, LABELS


def create_preview(root, destination):
    import json
    root, destination = Path(root), Path(destination)
    train = json.loads((root / "splits_final.json").read_text())[0]["train"]
    selected = [next(case for case in train if case.startswith(center)) for center in ("GU", "NC", "NYU")]
    selected += [case for case in ("NYU003", "NYU006", "NYU007", "NYU008") if case in train and case not in selected]
    colors = [(0, 0, 0, 0), (.99, .65, .52, .45), (1, .94, .70, .5), (.4, .64, 1, .5), (.65, .32, .8, .5), (.9, .9, .9, .5)]
    figure, axes = plt.subplots(len(selected), 3, figsize=(12, len(selected) * 3.5), squeeze=False)
    dataset = root / "nnUNet_raw" / DATASET
    for row, case in enumerate(selected):
        image = nib.as_closest_canonical(nib.load(dataset / "imagesTr" / f"{case}_0000.nii.gz"))
        labels = nib.as_closest_canonical(nib.load(dataset / "labelsTr" / f"{case}.nii.gz"))
        data = image.get_fdata(dtype=np.float32, caching="unchanged")
        target = np.asanyarray(labels.dataobj)
        low, high = np.percentile(data[data > 0], [.5, 99.5])
        for column, axis in enumerate((2, 1, 0)):
            index = data.shape[axis] // 2
            plane = np.flipud(np.take(data, index, axis).T)
            mask = np.flipud(np.take(target, index, axis).T)
            ax = axes[row, column]
            ax.imshow(plane, cmap="gray", vmin=low, vmax=high)
            ax.imshow(mask, cmap=ListedColormap(colors), vmin=0, vmax=5, interpolation="nearest")
            ax.set_title(f"{case} · axis {axis}, voxel {index}")
            ax.axis("off")
    figure.suptitle("E1 provisional label mapping — voxel-plane QC, not physical-space validation", fontsize=13)
    figure.legend(handles=[Patch(color=colors[label][:3], label=f"{label}: {name}") for name, label in LABELS.items() if label],
                  loc="lower center", ncol=5)
    figure.tight_layout(rect=(0, .025, 1, .97))
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=130)
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    create_preview(args.handoff, args.out)
