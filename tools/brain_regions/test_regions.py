import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import nibabel as nib
import numpy as np

import regions as rg

NAMES = ["unknown", "precentral", "rostralmiddlefrontal", "cuneus"]
CTAB = np.array([[25, 5, 25, 0, 0], [60, 20, 220, 0, 0], [75, 50, 125, 0, 0], [220, 180, 140, 0, 0]], np.int32)


def sphere_points(n, seed):
    v = np.random.default_rng(seed).normal(size=(n, 3))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def template_labels(points):
    """precentral where x > 0.3, rostral middle frontal where y > 0.3, cuneus where z < -0.5, else unknown."""
    labels = np.zeros(len(points), np.int32)
    labels[points[:, 2] < -0.5] = 3
    labels[points[:, 1] > 0.3] = 2
    labels[points[:, 0] > 0.3] = 1
    return labels


def write_gifti(path, points, triangles):
    image = nib.gifti.GiftiImage(darrays=[
        nib.gifti.GiftiDataArray(points.astype(np.float32), intent="NIFTI_INTENT_POINTSET"),
        nib.gifti.GiftiDataArray(triangles.astype(np.int32), intent="NIFTI_INTENT_TRIANGLE")])
    nib.save(image, str(path))


class RegionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.atlas = root / "templates"
        (self.atlas / "fsaverage_surf").mkdir(parents=True)
        (self.atlas / "fsaverage_atlases").mkdir()
        self.m2m = root / "m2m_test"
        (self.m2m / "surfaces").mkdir(parents=True)
        tri = np.array([[0, 1, 2], [1, 2, 3]])
        self.template = sphere_points(4000, 0)
        for hemi in rg.HEMISPHERES:
            write_gifti(self.atlas / "fsaverage_surf" / f"{hemi}.sphere.gii", 100 * self.template, tri)
            nib.freesurfer.write_annot(str(self.atlas / "fsaverage_atlases" / f"{hemi}.aparc_DK40.annot"),
                                       template_labels(self.template), CTAB, NAMES, fill_ctab=True)
        self.subject = sphere_points(600, 1)  # different vertices, unit radius like charm's sphere.reg
        for hemi in rg.HEMISPHERES:
            write_gifti(self.m2m / "surfaces" / f"{hemi}.sphere.reg.gii", self.subject, tri)
            write_gifti(self.m2m / "surfaces" / f"{hemi}.pial.gii", 70 * self.subject + [10, 0, 0], tri)

    def tearDown(self):
        self.tmp.cleanup()

    def test_labels_follow_the_nearest_template_vertex_across_radii(self):
        result = rg.subject_regions(self.m2m, "DK40", self.atlas)
        hemi = result.hemispheres[0]
        expected = template_labels(self.subject).astype(int)
        expected[expected == 0] = rg.UNKNOWN  # "unknown" is not cortex
        agreement = (hemi.labels == expected).mean()
        self.assertGreater(agreement, 0.95, "only vertices next to region borders may differ")
        np.testing.assert_allclose(hemi.points, 70 * self.subject + [10, 0, 0], atol=1e-4)
        self.assertEqual(hemi.names, NAMES)

    def test_non_cortex_entries_are_unlabeled_and_listed_regions_are_named(self):
        result = rg.subject_regions(self.m2m, "DK40", self.atlas)
        names = {name for _, _, name, _ in result.regions()}
        self.assertIn("Left precentral", names)
        self.assertIn("Right cuneus", names)
        self.assertFalse(any("unknown" in name for name in names))

    def test_target_highlight_colors_only_motor_and_dlpfc(self):
        result = rg.subject_regions(self.m2m, "DK40", self.atlas)
        hemi = result.hemispheres[0]
        colors = result.vertex_colors(hemi, highlight_targets=True)
        motor = hemi.labels == 1
        dlpfc = hemi.labels == 2
        other = hemi.labels == 3
        self.assertTrue((colors[motor] == rg.TARGET_COLORS["Motor cortex (M1)"]).all())
        self.assertTrue((colors[dlpfc] == rg.TARGET_COLORS["DLPFC (approx.)"]).all())
        self.assertTrue((colors[other] == rg.UNLABELED_COLOR).all())
        plain = result.vertex_colors(hemi)
        self.assertTrue((plain[other] == CTAB[3, :3]).all())

    def test_missing_cortex_or_atlas_is_explained(self):
        (self.m2m / "surfaces" / "rh.sphere.reg.gii").unlink()
        self.assertFalse(rg.has_cortex(self.m2m))
        with self.assertRaisesRegex(ValueError, "no charm cortical surfaces"):
            rg.subject_regions(self.m2m, "DK40", self.atlas)
        with self.assertRaisesRegex(ValueError, "Choose one of"):
            rg.subject_regions(self.m2m, "AAL", self.atlas)

    def test_atlas_folder_can_be_set_by_environment(self):
        with mock.patch.dict(os.environ, {rg.ATLAS_ENV: str(self.atlas)}):
            self.assertEqual(rg.find_atlas_dir(), self.atlas)
        with mock.patch.dict(os.environ, {rg.ATLAS_ENV: str(self.m2m)}):
            self.assertIsNone(rg.find_atlas_dir())

    def test_bundled_atlases_work_without_simnibs(self):
        self.assertTrue(rg.BUNDLE.is_file(), "data/fsaverage_atlases.npz must ship with the tool")
        with mock.patch.object(rg, "find_atlas_dir", return_value=None):
            self.assertEqual(rg.available_atlases(), ["DK40", "a2009s"])
            for hemi in rg.HEMISPHERES:
                sphere, labels, names, colors = rg.load_template(hemi, "DK40")
                self.assertEqual(sphere.shape, (163842, 3))
                np.testing.assert_allclose(np.linalg.norm(sphere, axis=1), 1, atol=1e-5)
                self.assertEqual(len(labels), 163842)
                self.assertIn("precentral", names)
                self.assertEqual(colors.shape, (len(names), 3))
            self.assertIn("G_precentral", rg.load_template("lh", "a2009s")[2])
            with self.assertRaisesRegex(ValueError, "HCP_MMP1 needs a SimNIBS 4 install"):
                rg.load_template("lh", "HCP_MMP1")
            result = rg.subject_regions(self.m2m, "DK40")  # synthetic subject, real bundled atlas
            self.assertEqual(len(result.hemispheres[0].labels), len(self.subject))

    def test_hcp_is_offered_only_with_simnibs(self):
        with mock.patch.object(rg, "find_atlas_dir", return_value=self.atlas):
            self.assertEqual(rg.available_atlases(), ["DK40", "a2009s", "HCP_MMP1"])

    def test_simnibs_install_layout_is_found_from_its_root(self):
        root = Path(self.tmp.name) / "SimNIBS-4.6"
        target = root / "simnibs_env/Lib/site-packages/simnibs/resources/templates/fsaverage_atlases"
        target.mkdir(parents=True)
        self.assertEqual(rg._templates_from_simnibs_root(root), target.parent)


if __name__ == "__main__":
    unittest.main()
