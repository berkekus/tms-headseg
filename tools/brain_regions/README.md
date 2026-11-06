# Brain regions on the subject's cortex

`regions.py` labels each vertex of a subject's cortex with a brain atlas, so the 3D view can color regions and mark TMS targets. MRI Workbench uses it in **3D view → Brain regions**.

## How it works

charm writes each hemisphere's pial surface and its registration to the fsaverage sphere (`m2m_X/surfaces/{lh,rh}.pial.gii` and `{lh,rh}.sphere.reg.gii`, with the same vertex order).

| Atlas | Regions per hemisphere | Source | Where it comes from |
| --- | --- | --- | --- |
| `DK40` (default) | 34 | Desikan–Killiany (Desikan et al. 2006) | Bundled: `data/fsaverage_atlases.npz` |
| `a2009s` | 74 | Destrieux (Destrieux et al. 2009) | Bundled |
| `HCP_MMP1` | 180 | Glasser et al. 2016 | A SimNIBS 4 install only |

The bundle (3.4 MB) holds the fsaverage sphere directions and the DK40 and a2009s labels, colors and names. It lets the coloring work on a machine without SimNIBS. `build_atlas_bundle.py` regenerates it from a SimNIBS template folder; `data/ATLAS_NOTICE.md` lists the citations and the SHA-256 of every source file. HCP-MMP1 is not bundled, because it derives from Human Connectome Project data whose use terms each user must accept. It is offered only when SimNIBS 4 is found, or when `TMS_HEADSEG_ATLAS_DIR` points to SimNIBS's `resources/templates`.

Every subject vertex takes the label of the nearest fsaverage vertex on the unit sphere. Both spheres are normalized first, because charm's `sphere.reg` has radius 1 and fsaverage radius 100. Entries that are not cortex (`unknown`, `???`, `corpuscallosum`, `Medial_wall`) count as unlabeled and show gray.

TMS target groups (`TMS_TARGETS`):
- **Motor cortex (M1):** precentral (DK40), `G_precentral` (a2009s), area 4 (HCP).
- **DLPFC (approx.):** the middle frontal regions that hold BA 9/46. These are rostral and caudal middle frontal (DK40), `G_front_middle` (a2009s), and 46, 9-46d, a9-46v and p9-46v (HCP).

The DLPFC mark is an atlas approximation, not a stimulation target.

For HCP-MMP1, the SimNIBS templates are found next to the `charm` launcher, the same search the CHARM launcher uses.

```bash
python tools/brain_regions/regions.py m2m_SUBJECT --atlas DK40
```

## Measured (2026-11-06, K1 desktop)

On NC023 (charm 4.6 surfaces, 245,762 vertices per hemisphere), mapping DK40 to both hemispheres took 1.6 s. It found 34 regions per side, with 5% of vertices unlabeled (the medial wall). Motor cortex covered about 16,000 vertices per side. In Workbench, switching to HCP-MMP1 (360 regions) took 1.4 s. A render showed precentral directly in front of the central sulcus and middle frontal on the lateral frontal lobe. This is a visual check on one subject, not a validation of the atlas registration.

## Limits

- Only for folders with charm cortical surfaces: full charm runs and hybrid folders (EXP-009). E2-only results have no `sphere.reg` yet. The next step is to run SimNIBS's TopoFit surface step on E2 cases.
- The accuracy of the regions depends on charm's spherical registration. Large lesions or thick slices can shift region borders.
- Workbench draws regions on charm's pial surface, which lies on the gray matter surface. While regions show, the gray matter surface is hidden to avoid overlap.

## Tests

```bash
cd tools/brain_regions && python -m unittest -v
```

The tests build synthetic GIFTI spheres and FreeSurfer `.annot` atlases. They check nearest-vertex labels across different sphere radii, unlabeled non-cortex entries, region names, the target highlight colors, the error messages and the atlas search.
