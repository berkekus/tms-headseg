"""Synthetic behavior checks; no patient data, GPU, model download, or training."""

import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import nibabel as nib
import numpy as np

try:
    demo = importlib.import_module("demo")
except ModuleNotFoundError:
    demo = None


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(demo, "E1 demo implementation is missing")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.array = (np.indices((8, 9, 10)).sum(0) % 6).astype(np.uint8)
        self.mri = self.save("mri.nii.gz", np.indices(self.array.shape).sum(0).astype(np.float32))
        self.ref = self.save("reference.nii.gz", self.array)
        self.pred = self.save("prediction.nii.gz", self.array)

    def save(self, name, array, affine=None, units="unknown"):
        path = self.root / name
        image = nib.Nifti1Image(array, np.eye(4) if affine is None else affine)
        image.header.set_xyzt_units(units)
        nib.save(image, path)
        return path

    def test_metrics_are_recomputed_and_background_excluded(self):
        values = self.array.copy()
        index = tuple(np.argwhere(values == 3)[0])
        values[index] = 2
        self.save("prediction.nii.gz", values)
        result = demo.compare_volumes(self.mri, self.pred, self.ref)
        csf_count = int((self.array == 3).sum())
        self.assertAlmostEqual(result["per_label"]["3"]["dice"], 2 * (csf_count - 1) / (2 * csf_count - 1))
        self.assertEqual(set(result["per_label"]), {str(x) for x in range(1, 6)})
        self.assertTrue(result["warnings"])

    def test_no_reference_means_no_accuracy_score(self):
        result = demo.compare_volumes(self.mri, self.pred)
        self.assertIsNone(result["case_mean_dice"])
        self.assertIsNone(result["per_label"])

    def test_shifted_grid_is_rejected(self):
        affine = np.eye(4)
        affine[0, 3] = 1
        self.save("prediction.nii.gz", self.array, affine)
        with self.assertRaisesRegex(ValueError, "grid"):
            demo.compare_volumes(self.mri, self.pred, self.ref)

    def test_known_incompatible_units_are_rejected(self):
        self.save("mri.nii.gz", self.array.astype(np.float32), units="meter")
        self.save("prediction.nii.gz", self.array, units="mm")
        with self.assertRaisesRegex(ValueError, "units"):
            demo.compare_volumes(self.mri, self.pred)

    def test_invalid_labels_and_nonfinite_mri_are_rejected(self):
        values = self.array.astype(np.float32)
        values[0, 0, 0] = 2.5
        self.save("prediction.nii.gz", values)
        with self.assertRaisesRegex(ValueError, "labels"):
            demo.compare_volumes(self.mri, self.pred)
        self.save("prediction.nii.gz", self.array)
        values[0, 0, 0] = np.nan
        self.save("mri.nii.gz", values)
        with self.assertRaisesRegex(ValueError, "finite"):
            demo.compare_volumes(self.mri, self.pred)

    def test_report_is_offline_and_explicitly_recorded(self):
        before = {p: p.read_bytes() for p in (self.mri, self.ref, self.pred)}
        out = self.root / "report"
        demo.make_report(self.mri, self.pred, out, reference=self.ref)
        result = json.loads((out / "report.json").read_text())
        self.assertEqual(result["mode"], "recorded")
        self.assertEqual(result["case_mean_dice"], 1)
        self.assertIsNone(result["timing"])
        self.assertTrue(result["surface_view"]["visualization_only"])
        html = (out / "report.html").read_text()
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("Kaydedilmiş tahmin", html)
        self.assertTrue('<script src=' not in html, "Report must bundle its viewer library")
        self.assertGreater((out / "comparison.png").stat().st_size, 1000)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        with self.assertRaisesRegex(ValueError, "exists"):
            demo.make_report(self.mri, self.pred, out, reference=self.ref)

    def test_e2_report_has_correct_experiment_without_e1_cohort_claim(self):
        out = self.root / "e2_report"
        demo.make_report(self.mri, self.pred, out, experiment="E2")
        result = json.loads((out / "report.json").read_text())
        self.assertEqual(result["experiment"], "E2")
        page = (out / "report.html").read_text()
        self.assertIn("E2 ön model", page)
        self.assertNotIn("E1 ön model", page)
        self.assertNotIn("44 eğitim", page)

    def test_saved_e2_report_cli_forwards_experiment(self):
        arguments = ["demo.py", "report", "--mri", str(self.mri),
                     "--recorded-prediction", str(self.pred), "--out", str(self.root / "report"),
                     "--experiment", "E2"]
        with patch("sys.argv", arguments), patch.object(demo, "make_report", return_value="report.html") as report:
            demo.main()
        self.assertEqual(report.call_args.kwargs["experiment"], "E2")

    def test_recorded_report_cannot_claim_live_timing(self):
        with self.assertRaisesRegex(ValueError, "timing"):
            demo.make_report(self.mri, self.pred, self.root / "report", timing={"prediction_seconds": 1})

    def test_report_without_reference_has_no_disagreement_claim(self):
        out = self.root / "without_reference"
        demo.make_report(self.mri, self.pred, out)
        page = (out / "report.html").read_text()
        self.assertTrue("Referans yok; bu MRI için Dice hesaplanmadı." in page, "Missing no-reference explanation")
        self.assertTrue("Turuncu:" not in page, "Disagreement legend requires a reference")

    def test_reference_and_prediction_cannot_be_same_file(self):
        with self.assertRaisesRegex(ValueError, "same file"):
            demo.compare_volumes(self.mri, self.ref, self.ref)

    def test_model_requires_metadata_and_intact_checkpoint(self):
        model = self.root / "model"
        model.mkdir()
        with self.assertRaisesRegex(ValueError, "dataset.json"):
            demo.validate_model(model)
        (model / "dataset.json").write_text(json.dumps({"labels": demo.LABELS, "channel_names": {"0": "T1"}, "file_ending": ".nii.gz"}))
        (model / "plans.json").write_text(json.dumps({"configurations": {"3d_fullres": {}}}))
        (model / "fold_0").mkdir()
        checkpoint = model / "fold_0/checkpoint_final.pth"
        checkpoint.write_bytes(b"incomplete")
        with self.assertRaisesRegex(ValueError, "checkpoint"):
            demo.validate_model(model)
        with zipfile.ZipFile(checkpoint, "w") as archive:
            archive.writestr("fixture", "not model weights; only container validation is tested")
        result = demo.validate_model(model)
        self.assertEqual(len(result["checkpoint_sha256"]), 64)
        self.assertEqual(result["fold"], 0)

    def test_model_with_wrong_label_mapping_is_rejected(self):
        model = self.root / "model"
        model.mkdir()
        (model / "dataset.json").write_text(json.dumps({"labels": {"background": 0, "brain": 1}}))
        with self.assertRaisesRegex(ValueError, "labels"):
            demo.validate_model(model)

    def test_inference_cannot_write_inside_model_directory(self):
        model = self.root / "model"
        with self.assertRaisesRegex(ValueError, "outside"):
            demo.predict(model, self.mri, model / "new_output")

    def test_notebook_is_standalone_and_does_not_train(self):
        try:
            builder = importlib.import_module("build_demo_notebook")
        except ModuleNotFoundError:
            self.fail("Standalone demo notebook builder is missing")
        notebook = builder.build()
        code = []
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                self.assertEqual(cell["outputs"], [])
                compile(cell["source"], f"cell_{index}", "exec")
                code.append(cell["source"])
        combined = "\n".join(code)
        self.assertIn("RUN_LIVE = False", combined)
        self.assertIn('EXPERIMENT_ID = "E1_L4_001"', combined)
        self.assertIn('CASE_ID = "GU011"', combined)
        self.assertNotIn("nnUNetv2_train", combined)
        self.assertNotIn("train_stage(", combined)
        self.assertNotIn("plan_and_preprocess", combined)
        self.assertIn("--recorded-prediction", combined)
        self.assertIn("if RUN_LIVE:", combined)
        self.assertIn("surface_view.py", combined)


if __name__ == "__main__":
    unittest.main()
