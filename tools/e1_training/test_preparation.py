"""Small synthetic checks; never installs nnU-Net, accesses a GPU, or trains."""

import ast
import contextlib
import io
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

import nibabel as nib
import numpy as np

from audit_handoff import audit, DATASET, LABELS
from build_notebook import build, HELPERS, ROOT
from colab_helpers import extract_handoff, install_split, pack_handoff, record_run, run_logged, sha256, training_command, verify_manifest


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "handoff"
        self.dataset = self.root / "nnUNet_raw" / DATASET
        for name in ("imagesTr", "labelsTr"):
            (self.dataset / name).mkdir(parents=True)
        self.ids = [f"{center}{index:03d}" for center in ("GU", "NC", "NYU") for index in range(1, 19)]
        self.val = self.ids[-10:]
        self.train = self.ids[:-10]
        self.split = [{"train": self.train, "val": self.val}]
        (self.root / "splits_final.json").write_text(json.dumps(self.split))
        (self.dataset / "dataset.json").write_text(json.dumps({"channel_names": {"0": "T1"}, "labels": LABELS,
                                                                "numTraining": 54, "file_ending": ".nii.gz"}))
        self.affine = np.diag([1., 1., 1., 1.])
        grid = np.indices((4, 5, 6)).sum(axis=0)
        for index, case in enumerate(self.ids):
            self.save("imagesTr", case, grid.astype(np.float32) + index / 10)
            self.save("labelsTr", case, (grid % 6).astype(np.uint8))

    def save(self, folder, case, data, affine=None, units="mm"):
        name = f"{case}_0000.nii.gz" if folder == "imagesTr" else f"{case}.nii.gz"
        image = nib.Nifti1Image(data, self.affine if affine is None else affine)
        image.header.set_xyzt_units(units)
        nib.save(image, self.dataset / folder / name)

    def audit(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return audit(self.root)

    def test_fixed_split_and_file_fingerprints(self):
        report = self.audit()
        self.assertEqual((report["train_count"], report["validation_count"]), (44, 10))
        self.assertEqual(len(report["files"]), 110)
        self.assertTrue(report["technical_checks_passed"])
        self.assertFalse(report["anatomical_or_semantic_approval"])

    def test_unknown_units_are_visible_not_silently_normalized(self):
        case = self.ids[0]
        path = self.dataset / "imagesTr" / f"{case}_0000.nii.gz"
        image = nib.load(path)
        image.header.set_xyzt_units("unknown")
        nib.save(image, path)
        before = sha256(path)
        report = self.audit()
        self.assertTrue(any("unspecified" in message for message in report["warnings"]))
        self.assertEqual(sha256(path), before)

    def test_overlapping_split_is_rejected(self):
        self.split[0]["val"][0] = self.train[0]
        (self.root / "splits_final.json").write_text(json.dumps(self.split))
        with self.assertRaisesRegex(ValueError, "overlapping"):
            self.audit()

    def test_missing_label_is_rejected(self):
        (self.dataset / "labelsTr" / f"{self.ids[0]}.nii.gz").unlink()
        with self.assertRaisesRegex(ValueError, "labelsTr"):
            self.audit()

    def test_invalid_labels_nonfinite_images_and_affine_mismatch(self):
        case = self.ids[0]
        grid = np.indices((4, 5, 6)).sum(0).astype(np.float32)
        self.save("labelsTr", case, grid / 100)
        with self.assertRaisesRegex(ValueError, "label values"):
            self.audit()
        self.save("labelsTr", case, (grid % 6).astype(np.uint8))
        bad = grid.copy()
        bad[0, 0, 0] = np.nan
        self.save("imagesTr", case, bad)
        with self.assertRaisesRegex(ValueError, "non-finite"):
            self.audit()
        self.save("imagesTr", case, grid)
        shifted = self.affine.copy()
        shifted[0, 3] = 1
        self.save("labelsTr", case, (grid % 6).astype(np.uint8), shifted)
        with self.assertRaisesRegex(ValueError, "affines disagree"):
            self.audit()

    def test_cross_split_voxel_duplicate_is_rejected(self):
        shutil.copyfile(self.dataset / "imagesTr" / f"{self.train[0]}_0000.nii.gz",
                        self.dataset / "imagesTr" / f"{self.val[0]}_0000.nii.gz")
        with self.assertRaisesRegex(ValueError, "duplicate image"):
            self.audit()

    def test_test_holdout_directory_is_never_read(self):
        (self.root / "test_holdout").mkdir()
        with self.assertRaisesRegex(ValueError, "Hold-out"):
            self.audit()

    def test_bundle_roundtrip_manifest_and_reuse(self):
        report = self.audit()
        bundle = self.base / "handoff.zip"
        pack_handoff(self.root, report, bundle)
        destination = extract_handoff(bundle, self.base / "staged")
        with contextlib.redirect_stdout(io.StringIO()):
            repeated = audit(destination)
        verify_manifest(destination, repeated)
        self.assertEqual(repeated["dataset_sha256"], report["dataset_sha256"])
        self.assertEqual(extract_handoff(bundle, destination), destination)
        with self.assertRaisesRegex(ValueError, "already exists"):
            pack_handoff(self.root, report, bundle)

    def test_zip_traversal_is_rejected(self):
        bundle = self.base / "unsafe.zip"
        manifest = {"files": {"../escape": "0"}, "dataset_sha256": "0"}
        with zipfile.ZipFile(bundle, "w") as archive:
            archive.writestr("expected_files.json", json.dumps(manifest))
            archive.writestr("../escape", "bad")
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            extract_handoff(bundle, self.base / "unsafe")
        self.assertFalse((self.base / "escape").exists())

    def test_changed_manifest_and_existing_split_are_rejected(self):
        report = self.audit()
        (self.root / "expected_files.json").write_text(json.dumps({"files": {}, "dataset_sha256": "bad"}))
        with self.assertRaisesRegex(ValueError, "differs"):
            verify_manifest(self.root, report)
        preprocessed = self.base / "preprocessed"
        install_split(self.root, preprocessed)
        target = preprocessed / DATASET / "splits_final.json"
        target.write_text("[]")
        with self.assertRaisesRegex(ValueError, "refusing"):
            install_split(self.root, preprocessed)

    def test_no_overwrite_and_no_silent_checkpoint_restart(self):
        folder = self.base / "fold_0"
        command = training_command("nnUNetv2_train", "nnUNetTrainer_E1Smoke", folder)
        self.assertEqual(command[1:4], ["1", "3d_fullres", "0"])
        with self.assertRaisesRegex(ValueError, "no checkpoint"):
            training_command("nnUNetv2_train", "nnUNetTrainer_E1Smoke", folder, True)
        folder.mkdir()
        with self.assertRaisesRegex(ValueError, "Run directory exists"):
            training_command("nnUNetv2_train", "nnUNetTrainer_E1Smoke", folder)
        (folder / "checkpoint_latest.pth").write_bytes(b"broken")
        with self.assertRaisesRegex(ValueError, "Checkpoint"):
            training_command("nnUNetv2_train", "nnUNetTrainer_E1Smoke", folder, True)
        with zipfile.ZipFile(folder / "checkpoint_latest.pth", "w") as archive:
            archive.writestr("check", "synthetic checkpoint container")
        self.assertEqual(training_command("nnUNetv2_train", "nnUNetTrainer_E1Smoke", folder, True)[-1], "--c")

    def test_experiment_contract_changes_are_blocked(self):
        path = self.base / "contract.json"
        record_run(path, {"dataset": "a", "fold": 0})
        record_run(path, {"dataset": "a", "fold": 0})
        with self.assertRaisesRegex(ValueError, "contract changed"):
            record_run(path, {"dataset": "b", "fold": 0})

    def test_logged_commands_preserve_exit_code(self):
        result = run_logged([sys.executable, "-c", "print('fixture complete')"], self.base / "ok.log")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("fixture complete", (self.base / "ok.log").read_text())
        with self.assertRaises(subprocess.CalledProcessError):
            run_logged([sys.executable, "-c", "raise SystemExit(3)"], self.base / "bad.log")

    def test_notebook_cells_compile_and_training_is_disabled(self):
        notebook = build()
        values = {}
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                compile(cell["source"], cell["id"], "exec")
                for node in ast.walk(ast.parse(cell["source"])):
                    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                        if node.targets[0].id in ("RUN_5_EPOCH_PILOT", "RUN_100_EPOCH_PRELIMINARY", "ACKNOWLEDGE_PROVISIONAL_DATA"):
                            values[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(values, {"RUN_5_EPOCH_PILOT": False, "RUN_100_EPOCH_PRELIMINARY": False, "ACKNOWLEDGE_PROVISIONAL_DATA": False})
        self.assertEqual(set(notebook["metadata"]["e1_helper_sha256"]), set(HELPERS))
        committed = json.loads((ROOT / "E1_Colab.ipynb").read_text())
        self.assertEqual(committed, notebook, "Regenerate the notebook after changing a helper.")

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "Preview check requires matplotlib.")
    def test_colab_backend_does_not_break_external_preview(self):
        cell = next(cell for cell in build()["cells"] if cell["cell_type"] == "code"
                    and "ENV = os.environ.copy()" in cell["source"])
        nodes = [node for node in ast.parse(cell["source"]).body
                 if (isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "ENV" for target in node.targets))
                 or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                     and isinstance(node.value.func, ast.Attribute) and isinstance(node.value.func.value, ast.Name)
                     and node.value.func.value.id == "ENV")]
        namespace = {"os": os, "DATA": self.root, "PREPROCESSED": self.base / "preprocessed",
                     "RESULTS": self.base / "results", "AUGMENTATION_WORKERS": 2}
        # An invalid inherited backend reproduces Colab's unavailable inline module across matplotlib versions.
        with patch.dict(os.environ, {"MPLBACKEND": "e1_invalid_inherited_backend", "MPLCONFIGDIR": str(self.base / "mpl")}):
            exec(compile(ast.Module(body=nodes, type_ignores=[]), "notebook-env", "exec"), namespace)
            output = self.base / "preview.png"
            result = subprocess.run([sys.executable, str(ROOT / "preview_handoff.py"), str(self.root), "--out", str(output)],
                                    env=namespace["ENV"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(os.environ["MPLBACKEND"], "e1_invalid_inherited_backend")

    def test_checkpoint_variants_preserve_epoch_counts(self):
        class Base:
            def __init__(self, plans, configuration, fold, dataset_json, device="cuda"):
                # nnU-Net 2.8.1 reconstructs checkpoints from the subclass's named init parameters.
                self.my_init_kwargs = {}
                for key in inspect.signature(self.__init__).parameters:
                    self.my_init_kwargs[key] = locals()[key]
                self.save_every = 50
        class Fake5(Base):
            def __init__(self, plans, configuration, fold, dataset_json, device="cuda"):
                super().__init__(plans, configuration, fold, dataset_json, device)
                self.num_epochs = 5
        class Fake100(Base):
            def __init__(self, plans, configuration, fold, dataset_json, device="cuda"):
                super().__init__(plans, configuration, fold, dataset_json, device)
                self.num_epochs = 100
        parent = "nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs"
        module = types.ModuleType(parent)
        module.nnUNetTrainer_5epochs, module.nnUNetTrainer_100epochs = Fake5, Fake100
        torch = types.ModuleType("torch")
        torch.manual_seed = lambda value: None
        torch.device = lambda value: value
        namespace = {}
        with patch.dict(sys.modules, {parent: module, "torch": torch}):
            exec(compile((ROOT / "trainers.py").read_text(), "trainers.py", "exec"), namespace)
        inputs = {"plans": {"continue_training": False}, "configuration": "3d_fullres", "fold": 0,
                  "dataset_json": {"numTraining": 54}, "device": "cpu"}
        for name, epochs in (("nnUNetTrainer_E1Smoke", 5), ("nnUNetTrainer_E1Preliminary", 100)):
            trainer = namespace[name](**inputs)
            self.assertEqual((trainer.num_epochs, trainer.save_every), (epochs, 1))
            self.assertEqual(trainer.my_init_kwargs, inputs)
            self.assertEqual(list(inspect.signature(namespace[name]).parameters), list(inputs))

    def test_overnight_finish_requires_completed_outputs(self):
        source = ROOT / "overnight_finish_cell.py"
        self.assertTrue(source.is_file(), "Missing safe overnight completion cell.")
        calls = []
        colab = types.ModuleType("google.colab")
        colab.runtime = types.SimpleNamespace(unassign=lambda: calls.append("unassign"))
        namespace = {"RUN_100_EPOCH_PRELIMINARY": False, "RESULTS": self.base / "results",
                     "DATASET": DATASET, "json": json}
        folder = namespace["RESULTS"] / DATASET / "nnUNetTrainer_E1Preliminary__nnUNetPlans__3d_fullres/fold_0"
        script = compile(source.read_text(), str(source), "exec")
        with patch.dict(sys.modules, {"google": types.ModuleType("google"), "google.colab": colab}):
            exec(script, namespace)
            self.assertEqual(calls, [])
            namespace["RUN_100_EPOCH_PRELIMINARY"] = True
            with self.assertRaises(AssertionError):
                exec(script, namespace)
            folder.mkdir(parents=True)
            (folder / "checkpoint_final.pth").write_bytes(b"nonempty checkpoint placeholder")
            (folder / "validation").mkdir()
            summary = folder / "validation/summary.json"
            summary.write_text('{"foreground_mean":')
            with self.assertRaises(json.JSONDecodeError):
                exec(script, namespace)
            self.assertEqual(calls, [])
            summary.write_text(json.dumps({"foreground_mean": {"Dice": .8}, "metric_per_case": [{}]}))
            with self.assertRaises(AssertionError):
                exec(script, namespace)
            self.assertEqual(calls, [])
            summary.write_text(json.dumps({"foreground_mean": {"Dice": .8}, "metric_per_case": [{}] * 10}))
            with contextlib.redirect_stdout(io.StringIO()):
                exec(script, namespace)
            self.assertEqual(calls, ["unassign"])
            self.assertTrue((namespace["RESULTS"] / "overnight_success.json").is_file())

    def test_failed_init_repair_preserves_previous_experiment(self):
        tools = self.base / "tools"
        tools.mkdir()
        original = (ROOT / "trainers.py").read_text().replace(
            'def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):',
            "def __init__(self, *args, **kwargs):").replace(
            "super().__init__(plans, configuration, fold, dataset_json, device)", "super().__init__(*args, **kwargs)")
        (tools / "trainers.py").write_text(original)
        installed = self.base / "installed_trainer.py"
        installed.write_text(original)
        results = self.base / "runs" / "E1_test"
        results.mkdir(parents=True)
        previous = results / "experiment_contract.json"
        previous.write_text('{"preserve": true}')
        namespace = {"TOOLS": tools, "trainer_path": installed, "RESULTS": results,
                     "RESULTS_BASE": results.parent, "EXPERIMENT_ID": "E1_test", "require": lambda ok, msg: None if ok else self.fail(msg),
                     "EMBEDDED": {"trainers.py": original}, "TRAINER_SHA256": sha256(installed),
                     "sha256": sha256, "json": json, "ENV": {"MPLBACKEND": "module://matplotlib_inline.backend_inline"}}
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile((ROOT / "repair_failed_init_colab.py").read_text(), "repair-cell", "exec"), namespace)
        self.assertEqual(installed.read_text(), (ROOT / "trainers.py").read_text())
        self.assertEqual(namespace["EMBEDDED"]["trainers.py"], installed.read_text())
        self.assertEqual(namespace["TRAINER_SHA256"], sha256(installed))
        self.assertEqual(previous.read_text(), '{"preserve": true}')
        self.assertEqual(namespace["RESULTS"].name, "E1_test_initfix")
        self.assertEqual(namespace["ENV"]["nnUNet_results"], str(namespace["RESULTS"]))
        self.assertEqual(namespace["ENV"]["MPLBACKEND"], "Agg")
        self.assertFalse(namespace["RUN_5_EPOCH_PILOT"])
        self.assertFalse(namespace["RUN_100_EPOCH_PRELIMINARY"])
        origin = json.loads((namespace["RESULTS"] / "repair_origin.json").read_text())
        self.assertEqual(origin["previous_results"], str(results))


if __name__ == "__main__":
    unittest.main()
