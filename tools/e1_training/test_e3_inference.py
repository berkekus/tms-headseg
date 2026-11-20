"""E3 inference contracts, using synthetic volumes and restricted checkpoint fixtures."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import nibabel as nib
import numpy as np

import demo


class E3ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def summary(self, cases):
        path = self.root / "summary.json"
        path.write_text(json.dumps({
            "metric_per_case": [{"reference_file": case + ".nii.gz",
                                 "metrics": {str(i): {"Dice": .8} for i in range(1, 6)}} for case in cases],
            "foreground_mean": {"Dice": .8}}))
        return path

    def test_e3_uses_the_sixteen_case_cohort(self):
        result = demo.cohort_metrics(self.summary(demo.E2_VALIDATION_CASES), "E3")
        self.assertEqual(result["validation_cases"], 16)

    def test_e3_rejects_the_e1_cohort(self):
        with self.assertRaisesRegex(ValueError, "fixed validation"):
            demo.cohort_metrics(self.summary(demo.VALIDATION_CASES), "E3")

    def test_e3_report_identifies_experiment_and_cohort(self):
        data = (np.indices((8, 9, 10)).sum(0) % 6).astype(np.uint8)
        mri, pred = self.root / "mri.nii.gz", self.root / "prediction.nii.gz"
        nib.save(nib.Nifti1Image(data.astype(np.float32), np.eye(4)), mri)
        nib.save(nib.Nifti1Image(data, np.eye(4)), pred)
        output = self.root / "report"
        demo.make_report(mri, pred, output, experiment="E3", summary=self.summary(demo.E2_VALIDATION_CASES))
        result = json.loads((output / "report.json").read_text())
        self.assertEqual(result["experiment"], "E3")
        self.assertEqual(result["cohort"]["validation_cases"], 16)
        page = (output / "report.html").read_text()
        self.assertIn("E3 ön model", page)
        self.assertNotIn("E1 ön model", page)
        self.assertNotIn("E2 ön model", page)

    def test_e3_cli_forwards_experiment_for_report_and_prediction(self):
        for command, extra, target in (("report", ["--recorded-prediction", "pred.nii.gz"], "make_report"),
                                       ("predict", ["--model", "model"], "predict")):
            with self.subTest(command=command):
                arguments = ["demo.py", command, "--mri", "mri.nii.gz", "--out", "out", "--experiment", "E3", *extra]
                with patch("sys.argv", arguments), patch.object(demo, target, return_value="report.html") as call:
                    demo.main()
                self.assertEqual(call.call_args.kwargs["experiment"], "E3")


try:
    import torch
except ImportError:
    torch = None


@unittest.skipIf(torch is None, "Checkpoint tests require the inference runtime with torch")
class E3CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "fold_0").mkdir()
        self.dataset = {"labels": demo.LABELS | {"ignore": 6}, "channel_names": {"0": "T1"}, "file_ending": ".nii.gz"}
        self.plans = {"dataset_name": "Dataset003_E3Face", "plans_name": "nnUNetPlans",
                      "configurations": {"3d_fullres": {}}}
        self.network = torch.nn.Conv3d(1, 6, 1)
        self.checkpoint = {"trainer_name": "nnUNetTrainer_E3Preliminary", "current_epoch": 100,
                           "init_args": {"plans": self.plans, "dataset_json": self.dataset, "configuration": "3d_fullres"},
                           "network_weights": self.network.state_dict(), "inference_allowed_mirroring_axes": (0, 1, 2)}
        self.write()

    def write(self):
        (self.root / "dataset.json").write_text(json.dumps(self.dataset))
        (self.root / "plans.json").write_text(json.dumps(self.plans))
        torch.save(self.checkpoint, self.root / "fold_0/checkpoint_final.pth")

    def initialize(self):
        self.assertTrue(hasattr(demo, "initialize_e3"), "Explicit E3 checkpoint initialization is missing")
        from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
        from nnunetv2.utilities.label_handling.label_handling import LabelManager
        plans = Mock()
        plans.get_label_manager.return_value = LabelManager(self.dataset["labels"], None)
        predictor = Mock()
        with patch("nnunetv2.utilities.plans_handling.plans_handler.PlansManager", return_value=plans), \
             patch("nnunetv2.utilities.label_handling.label_handling.determine_num_input_channels", return_value=1), \
             patch.object(nnUNetTrainer, "build_network_architecture", return_value=self.network) as builder, \
             patch.object(torch, "load", wraps=torch.load) as load:
            demo.initialize_e3(predictor, self.root)
        self.assertTrue(load.call_args.kwargs["weights_only"])
        self.assertEqual(builder.call_args.args[-1], 6)
        return predictor

    def test_exact_e3_metadata_is_accepted_and_ignore_is_not_a_seventh_head(self):
        self.assertIn("experiment", __import__("inspect").signature(demo.validate_model).parameters,
                      "Model validation does not distinguish E3 metadata")
        metadata = demo.validate_model(self.root, experiment="E3")
        self.assertEqual(metadata["fold"], 0)
        predictor = self.initialize()
        self.assertEqual(predictor.manual_initialization.call_args.args[5], "nnUNetTrainer_E3Preliminary")

    def test_e3_label_mapping_is_exact(self):
        for labels in (demo.LABELS, demo.LABELS | {"ignore": 7}, demo.LABELS | {"extra": 6}):
            with self.subTest(labels=labels):
                self.dataset["labels"] = labels
                self.write()
                with self.assertRaisesRegex(ValueError, "labels"):
                    demo.validate_model(self.root, experiment="E3")

    def test_e3_rejects_other_dataset_plans(self):
        self.plans["dataset_name"] = "Dataset002_E2Face"
        self.write()
        with self.assertRaisesRegex(ValueError, "Dataset003_E3Face"):
            demo.validate_model(self.root, experiment="E3")

    def test_e2_and_smoke_checkpoints_cannot_be_used_as_e3(self):
        for trainer, epoch in (("nnUNetTrainer_E2Preliminary", 100), ("nnUNetTrainer_E3Smoke", 5),
                               ("nnUNetTrainer_E3Preliminary", 5)):
            with self.subTest(trainer=trainer, epoch=epoch):
                self.checkpoint.update(trainer_name=trainer, current_epoch=epoch)
                self.write()
                with self.assertRaisesRegex(ValueError, "E3"):
                    self.initialize()

    def test_checkpoint_dataset_and_plans_must_match_files(self):
        for key in ("dataset_json", "plans"):
            with self.subTest(key=key):
                original = copy.deepcopy(self.checkpoint["init_args"][key])
                self.checkpoint["init_args"][key] = {"different": True}
                self.write()
                with self.assertRaisesRegex(ValueError, "disagree"):
                    self.initialize()
                self.checkpoint["init_args"][key] = original

    def test_nonfinite_weights_are_rejected_before_prediction(self):
        self.checkpoint["network_weights"]["weight"][0, 0, 0, 0, 0] = float("nan")
        self.write()
        with self.assertRaisesRegex(ValueError, "finite"):
            self.initialize()

    def test_mismatched_weight_shape_is_rejected_strictly(self):
        self.checkpoint["network_weights"]["weight"] = torch.zeros(7, 1, 1, 1, 1)
        self.write()
        with self.assertRaisesRegex(RuntimeError, "size mismatch"):
            self.initialize()

    def test_e2_initializer_remains_compatible(self):
        self.dataset["labels"] = demo.LABELS
        self.plans["dataset_name"] = "Dataset002_E2Face"
        self.checkpoint["trainer_name"] = "nnUNetTrainer_E2Preliminary"
        self.write()
        from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
        plans = Mock()
        plans.get_label_manager.return_value.num_segmentation_heads = 6
        predictor = Mock()
        with patch("nnunetv2.utilities.plans_handling.plans_handler.PlansManager", return_value=plans), \
             patch("nnunetv2.utilities.label_handling.label_handling.determine_num_input_channels", return_value=1), \
             patch.object(nnUNetTrainer, "build_network_architecture", return_value=self.network):
            demo.initialize_e2(predictor, self.root)
        self.assertEqual(predictor.manual_initialization.call_args.args[5], "nnUNetTrainer_E2Preliminary")


@unittest.skipIf(torch is None, "Inference-path checks require the inference runtime with torch")
class E3GeometryTests(unittest.TestCase):
    def test_e3_uses_reversible_ras_crop_restore_and_rejects_output_ignore(self):
        sys.path.insert(0, str(Path(demo.__file__).resolve().parents[1]))
        from headmodel import model_io
        from nnunet_prep import head_crop
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mri = root / "mri.nii.gz"
            data = np.zeros((28, 30, 32), dtype=np.float32)
            data[4:24, 4:26, 4:28] = 10
            affine = np.array([[0, 0, 2, 1], [-2, 0, 0, 2], [0, -2, 0, 3], [0, 0, 0, 1]], dtype=float)
            image = nib.Nifti1Image(data, affine)
            image.header.set_xyzt_units("mm")
            nib.save(image, mri)
            before = demo.sha256(mri)
            for emitted_label in (1, 6):
                with self.subTest(emitted_label=emitted_label):
                    output = root / f"result_{emitted_label}"
                    predictor = Mock()

                    def emit(inputs, outputs, **kwargs):
                        source = nib.load(inputs[0][0])
                        self.assertEqual(nib.aff2axcodes(source.affine), ("R", "A", "S"))
                        mask = np.where(np.asarray(source.dataobj) > 0, emitted_label, 0).astype(np.uint8)
                        nib.save(nib.Nifti1Image(mask, source.affine), outputs[0] + ".nii.gz")

                    predictor.predict_from_files.side_effect = emit
                    with patch.object(demo, "validate_model", return_value={}), \
                         patch.object(demo, "initialize_e3", create=True) as initialize, \
                         patch("nnunetv2.inference.predict_from_raw_data.nnUNetPredictor", return_value=predictor), \
                         patch.object(model_io, "prepare", wraps=model_io.prepare) as prepare, \
                         patch.object(head_crop, "crop_file", wraps=head_crop.crop_file) as crop, \
                         patch.object(head_crop, "paste_file", wraps=head_crop.paste_file) as paste, \
                         patch.object(model_io, "restore_labels", wraps=model_io.restore_labels) as restore, \
                         patch.object(demo, "make_report", return_value=output / "report/report.html") as report:
                        if emitted_label == 6:
                            with self.assertRaisesRegex(ValueError, "label|Label"):
                                demo.predict(root / "model", mri, output, experiment="E3", tta=False)
                            self.assertEqual(json.loads((output / "status.json").read_text())["state"], "failed")
                            report.assert_not_called()
                            continue
                        demo.predict(root / "model", mri, output, experiment="E3", tta=False)
                    initialize.assert_called_once_with(predictor, root / "model")
                    for operation in (prepare, crop, paste, restore):
                        self.assertEqual(operation.call_count, 1)
                    prediction = nib.load(output / "prediction.nii.gz")
                    self.assertEqual(prediction.shape, image.shape)
                    np.testing.assert_allclose(prediction.affine, image.affine)
                    self.assertEqual(set(np.unique(prediction.dataobj)), {0, 1})
                    self.assertEqual(report.call_args.kwargs["experiment"], "E3")
                    self.assertEqual(report.call_args.kwargs["model"]["experiment"], "E3")
                    self.assertEqual(json.loads((output / "status.json").read_text())["state"], "completed")
            self.assertEqual(demo.sha256(mri), before)


if __name__ == "__main__":
    unittest.main()
