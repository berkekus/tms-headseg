import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mesh_viewer import MeshView, region_triangles, regions_module  # noqa: E402

rg = regions_module()


def fake_regions():
    """Two hemispheres of four vertices: precentral (motor), cuneus and medial wall."""
    names = ["unknown", "precentral", "cuneus"]
    colors = np.array([[25, 5, 25], [60, 20, 220], [220, 180, 140]], np.uint8)
    triangles = np.array([[0, 1, 2], [2, 3, 0]])
    hemis = []
    for name, x in (("lh", -40.0), ("rh", 40.0)):
        points = np.array([[x, 0, 0], [x, 10, 0], [x, 10, 10], [x, 0, 10]], float)
        hemis.append(rg.Hemisphere(name, points, triangles, np.array([1, 1, 2, rg.UNKNOWN]), names, colors))
    return rg.CortexRegions("DK40", hemis)


class RegionViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = MeshView()
        self.view.regions_supported = True

    def test_support_depends_on_model_kind_cortex_and_atlas(self):
        self.view.update_region_support(SimpleNamespace(kind="e1", directory=Path(".")))
        self.assertFalse(self.view.region_atlas.isEnabled())
        self.assertIn("AI segmentations", self.view.region_hint.text())
        with tempfile.TemporaryDirectory() as tmp:
            surfaces = Path(tmp) / "surfaces"
            surfaces.mkdir()
            model = SimpleNamespace(kind="simnibs", directory=Path(tmp))
            self.view.update_region_support(model)
            self.assertIn("no charm cortical surfaces", self.view.region_hint.text())
            for hemi in rg.HEMISPHERES:
                (surfaces / f"{hemi}.pial.gii").touch()
                (surfaces / f"{hemi}.sphere.reg.gii").touch()
            hcp = self.view.region_atlas.model().item(self.view.region_atlas.findData("HCP_MMP1"))
            dk40 = self.view.region_atlas.model().item(self.view.region_atlas.findData("DK40"))
            with mock.patch.object(rg, "find_atlas_dir", return_value=None):  # no SimNIBS on this machine
                self.view.update_region_support(model)
                self.assertTrue(self.view.region_atlas.isEnabled())
                self.assertTrue(dk40.isEnabled())
                self.assertFalse(hcp.isEnabled())
                self.assertIn("HCP-MMP1 needs SimNIBS", self.view.region_hint.text())
            with mock.patch.object(rg, "find_atlas_dir", return_value=Path(tmp)):
                self.view.update_region_support(model)
                self.assertTrue(hcp.isEnabled())

    def test_list_names_regions_and_marks_tms_targets(self):
        self.view.set_regions(fake_regions())
        items = [self.view.region_list.item(i).text() for i in range(self.view.region_list.count())]
        self.assertEqual(len(items), 4)  # precentral and cuneus, both sides
        self.assertIn("Left precentral · Motor cortex (M1)", items)
        self.assertIn("Right cuneus", items)
        self.assertTrue(self.view.region_list.isEnabled())

    def test_hiding_a_region_drops_its_triangles(self):
        regions = fake_regions()
        self.view.set_regions(regions)
        item = next(self.view.region_list.item(i) for i in range(self.view.region_list.count())
                    if self.view.region_list.item(i).text().startswith("Left precentral"))
        item.setCheckState(Qt.CheckState.Unchecked)
        self.assertIn(("lh", 1), self.view.hidden_regions)
        lh, rh = regions.hemispheres
        self.assertEqual(region_triangles(lh, self.view.hidden_regions).tolist(), [False, True])
        self.assertEqual(region_triangles(rh, self.view.hidden_regions).tolist(), [True, True])
        self.view.set_all_regions(True)
        self.assertFalse(self.view.hidden_regions)

    def test_gray_matter_surface_is_hidden_while_regions_show_and_restored_after(self):
        brain = QCheckBox()
        brain.setChecked(True)
        self.view.checks[2] = brain
        self.view.presets = {"brain": 2}
        self.view.set_regions(fake_regions())
        self.assertFalse(brain.isChecked())
        self.view.preset(True)  # the Brain button must not bring the overlapping surface back
        self.assertFalse(brain.isChecked())
        self.view.set_regions(None)
        self.assertTrue(brain.isChecked())

    def test_click_point_names_the_nearest_region_or_nothing(self):
        self.view.set_regions(fake_regions())
        self.assertEqual(self.view.region_at(np.array([-40.5, 0.5, 0.0])), "Left precentral · Motor cortex (M1)")
        self.assertEqual(self.view.region_at(np.array([41.0, 10.0, 10.0])), "Right cuneus")
        self.assertIn("medial wall", self.view.region_at(np.array([40.0, 0.0, 10.0])))
        self.assertIsNone(self.view.region_at(np.array([0.0, 0.0, 0.0])))

    def test_a_pick_names_the_region_and_reports_it(self):
        self.view.set_regions(fake_regions())
        picked = []
        self.view.region_picked.connect(picked.append)
        point = np.array([-40.0, 0.0, 0.0])
        self.view.show_pick(point, self.view.region_at(point))
        self.assertEqual(picked, ["Left precentral · Motor cortex (M1)"])
        self.assertEqual(self.view.region_picked_label.text(), "Left precentral · Motor cortex (M1)")
        self.view.set_regions(None)
        self.assertEqual(self.view.region_picked_label.text(), "Click the cortex to name a region.")

    def test_choosing_an_atlas_requests_it_and_off_clears(self):
        requested = []
        self.view.regions_requested.connect(requested.append)
        self.view.region_atlas.setCurrentIndex(self.view.region_atlas.findData("HCP_MMP1"))
        self.view.region_atlas.setCurrentIndex(0)
        self.assertEqual(requested, ["HCP_MMP1", ""])

    def test_highlight_uses_target_colors(self):
        regions = fake_regions()
        colors = regions.vertex_colors(regions.hemispheres[0], highlight_targets=True)
        self.assertEqual(tuple(colors[0]), rg.TARGET_COLORS["Motor cortex (M1)"])
        self.assertEqual(tuple(colors[2]), rg.UNLABELED_COLOR)


if __name__ == "__main__":
    unittest.main()
