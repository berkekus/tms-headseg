"""Visualization geometry and control logic, without training or a browser."""

import importlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest

import numpy as np

try:
    surface_view = importlib.import_module("surface_view")
except ModuleNotFoundError:
    surface_view = None


class SurfaceViewTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(surface_view, "3D surface-view implementation is missing")
        self.labels = np.zeros((10, 11, 12), dtype=np.uint8)
        self.labels[2:6, 3:7, 1:5] = 4

    def test_surface_vertices_use_source_affine_without_changing_labels(self):
        before = self.labels.copy()
        affine = np.eye(4)
        affine[:3, 3] = [10, 20, 30]
        surfaces = surface_view.extract_surfaces(self.labels, affine, step_size=1)
        self.assertEqual([s["label"] for s in surfaces], [4])
        mesh = surfaces[0]
        np.testing.assert_allclose(mesh["vertices"].min(0), [11.5, 22.5, 30.5])
        np.testing.assert_allclose(mesh["vertices"].max(0), [15.5, 26.5, 34.5])
        self.assertTrue(np.isfinite(mesh["vertices"]).all())
        self.assertTrue(np.all((mesh["faces"] >= 0) & (mesh["faces"] < len(mesh["vertices"]))))
        np.testing.assert_array_equal(before, self.labels)

    def test_padding_closes_a_surface_touching_volume_boundary(self):
        self.labels[:3, :3, :3] = 1
        surfaces = surface_view.extract_surfaces(self.labels, np.eye(4), step_size=1)
        skin = next(s for s in surfaces if s["label"] == 1)
        faces = skin["faces"]
        edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
        _, counts = np.unique(edges, axis=0, return_counts=True)
        self.assertTrue(np.all(counts == 2))

    def test_small_tissue_is_not_silently_dropped(self):
        labels = np.zeros((9, 9, 9), dtype=np.uint8)
        labels[5, 5, 5] = 3
        surfaces = surface_view.extract_surfaces(labels, np.eye(4), step_size=2)
        self.assertEqual([s["label"] for s in surfaces], [3])
        self.assertGreater(len(surfaces[0]["faces"]), 0)

    def test_unsupported_labels_and_excessive_geometry_are_rejected(self):
        invalid = self.labels.copy()
        invalid[0, 0, 0] = 6
        with self.assertRaisesRegex(ValueError, "labels"):
            surface_view.extract_surfaces(invalid, np.eye(4))
        with self.assertRaisesRegex(ValueError, "complex"):
            surface_view.extract_surfaces(self.labels, np.eye(4), max_faces=1)

    def test_viewer_has_offline_library_controls_and_visualization_metadata(self):
        names = {1: "Deri", 2: "Kafatası", 3: "CSF", 4: "Gri cevher", 5: "Beyaz cevher"}
        fragment, metadata = surface_view.make_view(self.labels, np.eye(4), names)
        self.assertTrue(metadata["visualization_only"])
        self.assertFalse(metadata["fem_mesh"])
        self.assertEqual(metadata["labels"], [4])
        self.assertGreater(metadata["triangles"], 0)
        self.assertTrue('id="e1-surface-plot"' in fragment)
        self.assertTrue('data-surface-index="0"' in fragment)
        self.assertTrue('data-opacity-index="0"' in fragment)
        self.assertTrue('data-surface-preset="brain"' in fragment)
        self.assertTrue("Plotly.newPlot" in fragment)
        self.assertTrue("<script src=" not in fragment)
        self.assertTrue("SimNIBS/FEM" in fragment)

    def test_control_events_change_visibility_opacity_and_camera(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is unavailable for the JavaScript control test")
        script = Path(surface_view.__file__).with_name("surface_controls.js").read_text()
        fixture = r'''
const vm = require('vm');
const calls = [];
const element = dataset => ({dataset, checked:true, value:'100', disabled:true, handlers:{},
  addEventListener(name, fn) {this.handlers[name] = fn;}});
const checks = [element({surfaceIndex:'0', surfaceLabel:'1'}), element({surfaceIndex:'1', surfaceLabel:'4'})];
const ranges = [element({opacityIndex:'0'}), element({opacityIndex:'1'})];
const buttons = ['brain','head','all','reset'].map(p => element({surfacePreset:p}));
const status = {textContent:''};
const graph = {on(){}};
const document = {getElementById: id => id === 'e1-surface-plot' ? graph : status,
 querySelectorAll: selector => selector === '[data-surface-index]' ? checks : selector === '[data-opacity-index]' ? ranges : buttons};
const Plotly = {restyle:(...args)=>calls.push(['restyle',...args.slice(1)]), relayout:(...args)=>calls.push(['relayout',...args.slice(1)])};
vm.runInNewContext(SOURCE, {document, Plotly});
checks[0].checked=false; checks[0].handlers.change();
ranges[1].value='37'; ranges[1].handlers.input();
buttons[1].handlers.click();
buttons[3].handlers.click();
process.stdout.write(JSON.stringify({calls, enabled:checks.every(e=>!e.disabled), status:status.textContent}));
'''
        result = subprocess.run([node, "-e", fixture.replace("SOURCE", json.dumps(script))],
                                text=True, capture_output=True, check=True)
        result = json.loads(result.stdout)
        self.assertTrue(result["enabled"])
        self.assertEqual(result["calls"][0], ["restyle", {"visible": False}, [0]])
        self.assertEqual(result["calls"][1], ["restyle", {"opacity": .37}, [1]])
        self.assertTrue(any(call[0] == "relayout" for call in result["calls"]))


if __name__ == "__main__":
    unittest.main()
