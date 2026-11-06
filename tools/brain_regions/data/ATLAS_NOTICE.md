# Atlas data notice

`fsaverage_atlases.npz` holds, for each hemisphere, the fsaverage sphere vertex directions (unit length) and the
per-vertex labels, colors and names of two FreeSurfer cortical parcellations. It was generated on 2026-11-06 by
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
| `fsaverage_surf/lh.sphere.gii` | `d1e949329f687657f471d9cbdbe8c29d9676d5f4ca2be527be8fafc7357d8f19` |
| `fsaverage_atlases/lh.aparc_DK40.annot` | `39b1acde9a32b4227631eb51cbcd8dff84e2138c57bf9f96d74026f2c17f1480` |
| `fsaverage_atlases/lh.aparc_a2009s.annot` | `8ce931d3c87d9dfd369ac739fa32c04ab9b8335afab0e6d77f569b43d8c0b70e` |
| `fsaverage_surf/rh.sphere.gii` | `d1e949329f687657f471d9cbdbe8c29d9676d5f4ca2be527be8fafc7357d8f19` |
| `fsaverage_atlases/rh.aparc_DK40.annot` | `6a326aed325d313e6e0d10f67630efcd8d3b8343c50d3e108e005f626614badb` |
| `fsaverage_atlases/rh.aparc_a2009s.annot` | `f0de8093fc336ddea7fdefde91449f552accdb198dd51a559718262adf317aac` |
