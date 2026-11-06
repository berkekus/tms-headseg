"""Label a subject's cortex with a brain atlas, for colored 3D views.

charm writes each hemisphere's pial surface and its registration to the fsaverage sphere
(`surfaces/{lh,rh}.pial.gii`, `{lh,rh}.sphere.reg.gii`, same vertex order). Each subject vertex takes
the label of the nearest fsaverage vertex on the unit sphere, so the atlas follows the subject's own folding.

DK40 and a2009s ship with this tool (`data/fsaverage_atlases.npz`, see data/ATLAS_NOTICE.md), so no SimNIBS
install is needed. HCP_MMP1 is read from a SimNIBS 4 install only, because its data use terms do not allow
us to redistribute it.

    python tools/brain_regions/regions.py m2m_SUBJECT [--atlas DK40]
"""
import argparse
import glob
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.spatial import cKDTree

ATLASES = ("DK40", "a2009s", "HCP_MMP1")
BUNDLED_ATLASES = ("DK40", "a2009s")
BUNDLE = Path(__file__).resolve().parent / "data" / "fsaverage_atlases.npz"
HEMISPHERES = ("lh", "rh")
HEMISPHERE_NAMES = {"lh": "Left", "rh": "Right"}
UNKNOWN = -1
ATLAS_ENV = "TMS_HEADSEG_ATLAS_DIR"

# Atlas regions that approximate common TMS targets. DLPFC has no single atlas region; these are the
# middle frontal regions that contain BA 9/46 in the usual definitions, so the mark is approximate.
TMS_TARGETS = {
    "DK40": {"Motor cortex (M1)": ("precentral",),
             "DLPFC (approx.)": ("rostralmiddlefrontal", "caudalmiddlefrontal")},
    "a2009s": {"Motor cortex (M1)": ("G_precentral",),
               "DLPFC (approx.)": ("G_front_middle",)},
    "HCP_MMP1": {"Motor cortex (M1)": ("4",),
                 "DLPFC (approx.)": ("46", "9-46d", "a9-46v", "p9-46v")},
}
TARGET_COLORS = {"Motor cortex (M1)": (226, 74, 74), "DLPFC (approx.)": (245, 166, 35)}
# Atlas entries that are not cortical regions (medial wall, corpus callosum) count as unlabeled.
NOT_CORTEX = {"unknown", "Unknown", "???", "corpuscallosum", "Medial_wall"}
UNLABELED_COLOR = (170, 170, 170)


@dataclass
class Hemisphere:
    name: str
    points: np.ndarray
    triangles: np.ndarray
    labels: np.ndarray                        # per vertex: index into names, UNKNOWN if none
    names: list = field(default_factory=list)
    colors: np.ndarray = None                 # per name, RGB uint8


@dataclass
class CortexRegions:
    atlas: str
    hemispheres: list
    surface: str = "pial"

    def regions(self):
        """(hemisphere, label, display name, RGB) for every region present on the surface."""
        found = []
        for hemi in self.hemispheres:
            for label in np.unique(hemi.labels):
                if label != UNKNOWN:
                    found.append((hemi.name, int(label), display_name(hemi, int(label)),
                                  tuple(int(c) for c in hemi.colors[label])))
        return found

    def target_of(self, hemi, label):
        """The TMS target group a region belongs to, or None."""
        name = hemi.names[label] if label != UNKNOWN else None
        for target, members in TMS_TARGETS.get(self.atlas, {}).items():
            if name in members:
                return target
        return None

    def vertex_colors(self, hemi, highlight_targets=False):
        """Per-vertex RGB: atlas colors, or the two TMS target groups on a neutral cortex."""
        colors = np.empty((len(hemi.labels), 3), np.uint8)
        known = hemi.labels != UNKNOWN
        colors[~known] = UNLABELED_COLOR
        if not highlight_targets:
            colors[known] = hemi.colors[hemi.labels[known]]
            return colors
        colors[known] = UNLABELED_COLOR
        for label in np.unique(hemi.labels[known]):
            target = self.target_of(hemi, int(label))
            if target:
                colors[hemi.labels == label] = TARGET_COLORS[target]
        return colors


def display_name(hemi, label):
    return f"{HEMISPHERE_NAMES[hemi.name]} {hemi.names[label]}"


def _templates_from_simnibs_root(root):
    patterns = ("simnibs_env/Lib/site-packages/simnibs/resources/templates",
                "simnibs_env/lib/python3*/site-packages/simnibs/resources/templates")
    for pattern in patterns:
        for found in sorted(glob.glob(str(Path(root) / pattern))):
            if (Path(found) / "fsaverage_atlases").is_dir():
                return Path(found)
    return None


def find_atlas_dir():
    """SimNIBS's template folder (with fsaverage_atlases and fsaverage_surf), or None."""
    if os.environ.get(ATLAS_ENV):
        path = Path(os.environ[ATLAS_ENV])
        return path if (path / "fsaverage_atlases").is_dir() else None
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "charm_gui"))
    from installation import find_charm
    charm = find_charm()
    return _templates_from_simnibs_root(Path(charm).parents[1]) if charm else None


def available_atlases():
    """Atlases usable on this machine: the bundled ones, plus HCP_MMP1 when SimNIBS 4 is installed."""
    found = [atlas for atlas in BUNDLED_ATLASES if BUNDLE.is_file()]
    if find_atlas_dir() is not None:
        found += [atlas for atlas in ATLASES if atlas not in found]
    return found


@lru_cache(maxsize=1)
def _bundle():
    with np.load(BUNDLE) as data:
        return {key: data[key] for key in data.files}


def load_template(hemi, atlas, atlas_dir=None):
    """fsaverage sphere (unit vectors), per-vertex labels, region names and RGB colors for one hemisphere."""
    if atlas_dir is None and atlas in BUNDLED_ATLASES and BUNDLE.is_file():
        data = _bundle()
        return (data[f"{hemi}_sphere"].astype(float), data[f"{hemi}_{atlas}_labels"].astype(np.int64),
                [str(name) for name in data[f"{hemi}_{atlas}_names"]], data[f"{hemi}_{atlas}_colors"])
    atlas_dir = Path(atlas_dir) if atlas_dir else find_atlas_dir()
    if atlas_dir is None:
        raise ValueError(f"{atlas} needs a SimNIBS 4 install (or {ATLAS_ENV}); "
                         f"{' and '.join(BUNDLED_ATLASES)} work without it.")
    sphere, _ = read_surface(atlas_dir / "fsaverage_surf" / f"{hemi}.sphere.gii")
    labels, ctab, names = nib.freesurfer.read_annot(str(atlas_dir / "fsaverage_atlases" / f"{hemi}.aparc_{atlas}.annot"))
    if len(labels) != len(sphere):
        raise ValueError(f"{hemi}: atlas and fsaverage sphere do not match.")
    return (sphere, np.asarray(labels, np.int64), [n.decode() if isinstance(n, bytes) else str(n) for n in names],
            np.asarray(ctab[:, :3], np.uint8))


def cortex_files(m2m):
    surfaces = Path(m2m) / "surfaces"
    return {hemi: (surfaces / f"{hemi}.pial.gii", surfaces / f"{hemi}.sphere.reg.gii") for hemi in HEMISPHERES}


def has_cortex(m2m):
    return all(pial.is_file() and sphere.is_file() for pial, sphere in cortex_files(m2m).values())


def read_surface(path):
    image = nib.load(str(path))
    points = next((a.data for a in image.darrays if a.intent == nib.nifti1.intent_codes["NIFTI_INTENT_POINTSET"]), None)
    triangles = next((a.data for a in image.darrays if a.intent == nib.nifti1.intent_codes["NIFTI_INTENT_TRIANGLE"]), None)
    if points is None or triangles is None:  # some writers leave intents unset
        points, triangles = image.darrays[0].data, image.darrays[1].data
    return np.asarray(points, float), np.asarray(triangles, np.int64)


def _unit(points):
    return points / np.linalg.norm(points, axis=1, keepdims=True)


def map_labels(subject_sphere, template_sphere, template_labels):
    """Label of the nearest template vertex on the unit sphere, for each subject vertex."""
    _, nearest = cKDTree(_unit(template_sphere)).query(_unit(subject_sphere))
    return np.asarray(template_labels)[nearest]


def subject_regions(m2m, atlas="DK40", atlas_dir=None):
    if atlas not in ATLASES:
        raise ValueError(f"Choose one of {', '.join(ATLASES)}.")
    if not has_cortex(m2m):
        raise ValueError(f"{Path(m2m).name} has no charm cortical surfaces (surfaces/lh.pial.gii, lh.sphere.reg.gii).")
    hemispheres = []
    for hemi, (pial, sphere) in cortex_files(m2m).items():
        points, triangles = read_surface(pial)
        subject_sphere, _ = read_surface(sphere)
        if len(subject_sphere) != len(points):
            raise ValueError(f"{hemi}: pial and sphere.reg have different vertex counts.")
        template_sphere, labels, names, colors = load_template(hemi, atlas, atlas_dir)
        subject_labels = map_labels(subject_sphere, template_sphere, labels)
        subject_labels[np.isin(subject_labels, [i for i, n in enumerate(names) if n in NOT_CORTEX])] = UNKNOWN
        hemispheres.append(Hemisphere(hemi, points, triangles, subject_labels, names, colors))
    return CortexRegions(atlas, hemispheres)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("m2m", type=Path)
    parser.add_argument("--atlas", choices=ATLASES, default="DK40")
    args = parser.parse_args()
    result = subject_regions(args.m2m, args.atlas)
    for hemi in result.hemispheres:
        known = hemi.labels != UNKNOWN
        print(f"{hemi.name}: {len(hemi.points):,} vertices, {len(np.unique(hemi.labels[known]))} regions, "
              f"{100 * (~known).mean():.1f}% unlabeled")
    for target, members in TMS_TARGETS[args.atlas].items():
        counts = {h.name: int(np.isin(h.labels, [i for i, n in enumerate(h.names) if n in members]).sum())
                  for h in result.hemispheres}
        print(f"{target}: {counts} vertices")


if __name__ == "__main__":
    main()
