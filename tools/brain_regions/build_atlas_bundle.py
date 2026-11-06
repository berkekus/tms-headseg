"""Pack the FreeSurfer fsaverage atlases (DK40, a2009s) into one small file that ships with the repository.

Run once from a machine with SimNIBS 4 installed; the output lets regions.py work without SimNIBS:

    python tools/brain_regions/build_atlas_bundle.py <SimNIBS .../simnibs/resources/templates>

HCP-MMP1 is not packed: it derives from Human Connectome Project data under the HCP data use terms.
"""
import argparse
import hashlib
from datetime import date
from pathlib import Path

import nibabel as nib
import numpy as np

BUNDLED = ("DK40", "a2009s")
HERE = Path(__file__).resolve().parent
BUNDLE = HERE / "data" / "fsaverage_atlases.npz"
NOTICE = HERE / "data" / "ATLAS_NOTICE.md"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(templates):
    templates = Path(templates)
    arrays, sources = {}, []
    for hemi in ("lh", "rh"):
        sphere = templates / "fsaverage_surf" / f"{hemi}.sphere.gii"
        points = np.asarray(nib.load(str(sphere)).darrays[0].data, np.float64)
        arrays[f"{hemi}_sphere"] = (points / np.linalg.norm(points, axis=1, keepdims=True)).astype(np.float32)
        sources.append(sphere)
        for atlas in BUNDLED:
            annot = templates / "fsaverage_atlases" / f"{hemi}.aparc_{atlas}.annot"
            labels, ctab, names = nib.freesurfer.read_annot(str(annot))
            if len(labels) != len(points):
                raise ValueError(f"{annot.name} does not match {sphere.name}")
            arrays[f"{hemi}_{atlas}_labels"] = labels.astype(np.int16)
            arrays[f"{hemi}_{atlas}_colors"] = np.asarray(ctab[:, :3], np.uint8)
            arrays[f"{hemi}_{atlas}_names"] = np.array([n.decode() if isinstance(n, bytes) else str(n) for n in names])
            sources.append(annot)
    BUNDLE.parent.mkdir(exist_ok=True)
    np.savez_compressed(BUNDLE, **arrays)
    rows = "\n".join(f"| `{p.parent.name}/{p.name}` | `{sha256(p)}` |" for p in sources)
    NOTICE.write_text(f"""# Atlas data notice

`fsaverage_atlases.npz` holds, for each hemisphere, the fsaverage sphere vertex directions (unit length) and the
per-vertex labels, colors and names of two FreeSurfer cortical parcellations. It was generated on {date.today()} by
`build_atlas_bundle.py` from the SimNIBS 4 template folder; nothing else was changed.

| Atlas | Reference |
| --- | --- |
| DK40 (FreeSurfer `aparc`, Desikan–Killiany) | Desikan RS et al. An automated labeling system for subdividing the human cerebral cortex on MRI scans into gyral based regions of interest. NeuroImage 31(3):968–980, 2006. |
| a2009s (FreeSurfer `aparc.a2009s`, Destrieux) | Destrieux C, Fischl B, Dale A, Halgren E. A sulcal depth-based anatomical parcellation of the cerebral cortex. HBM 2009, poster 541; NeuroImage 53(1):1–15, 2010. |

The fsaverage surfaces and both parcellations are distributed with FreeSurfer
(https://surfer.nmr.mgh.harvard.edu/fswiki/CorticalParcellation) and with SimNIBS. Cite the references above when
using them. HCP-MMP1 (Glasser et al. 2016) is deliberately not included: it derives from Human Connectome Project
data whose use terms require acceptance by each user.

Source files (SHA-256):

| File | SHA-256 |
| --- | --- |
{rows}
""", encoding="utf-8")
    return BUNDLE


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("templates", type=Path, help="SimNIBS resources/templates folder")
    out = build(parser.parse_args().templates)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB) and {NOTICE.name}")


if __name__ == "__main__":
    main()
