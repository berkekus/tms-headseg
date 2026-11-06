"""Dataset003 E3 regression checks, synthetic inputs unless explicitly staged elsewhere."""

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

import nibabel as nib
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def save(path, values, affine):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = nib.Nifti1Image(values, affine)
    image.set_sform(affine, code=1)
    image.set_qform(affine, code=1)
    image.header.set_xyzt_units("mm")
    nib.save(image, path)


class DatasetTests(unittest.TestCase):
    def setUp(self):
        import e3_data
        self.data = e3_data
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / "handoff_e3"
        self.dataset = self.package / "nnUNet_raw" / self.data.DATASET
        self.contract = {"train": ["GU001", "IXI001", "IXI001w2"], "val": ["IXI002"],
                         "source_train": ["GU001", "IXI001"], "copy_sources": {"IXI001w2": "IXI001"}}
        a = np.ones((7, 8, 9), dtype=np.float32)
        a[:2] = 0
        a[4, 4, 4] = 0  # An enclosed zero is not outside acquisition.
        b = np.ones(a.shape, np.uint8)
        b[:2] = 6
        for case in self.contract["train"] + self.contract["val"]:
            save(self.dataset / "imagesTr" / f"{case}_0000.nii.gz", a, np.diag([1., 1., 1., 1.]))
            save(self.dataset / "labelsTr" / f"{case}.nii.gz", b if case in self.contract["train"] else np.ones_like(b), np.eye(4))
        (self.dataset / "dataset.json").write_text(json.dumps({"channel_names": {"0": "T1"},
            "labels": self.data.LABELS, "numTraining": 4, "file_ending": ".nii.gz"}))
        self.splits = self.package / "splits_final.json"
        self.splits.write_text(json.dumps([{k: self.contract[k] for k in ("train", "val")}]))
        import csv
        with (self.package / "e3_manifest.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["case_id", "source_case", "source", "split", "weight_copy", "ignore_ml"])
            w.writeheader()
            for case in self.contract["train"] + self.contract["val"]:
                w.writerow({"case_id": case, "source_case": case.removesuffix("w2"),
                            "source": "IXI" if case.startswith("IXI") else "MultiAxial",
                            "split": "train" if case in self.contract["train"] else "val",
                            "weight_copy": 2 if case.endswith("w2") else 1,
                            "ignore_ml": .144 if case in self.contract["train"] else 0})

    def test_dataset003_ignore_and_copy_audit(self):
        report = self.data.audit(self.dataset, self.splits, self.contract)
        self.assertEqual((report["train_count"], report["validation_count"]), (3, 1))
        self.assertEqual(report["unique_training_subjects"], 2)
        self.assertEqual(report["weighted_copies"], 1)
        self.assertEqual(report["sampling"], "uniform_over_entries")

    def test_ras_fingerprint_ignores_gzip_container_differences(self):
        import gzip
        before = self.data.audit(self.dataset, self.splits, self.contract)
        p = self.dataset / "imagesTr/GU001_0000.nii.gz"
        p.write_bytes(gzip.compress(gzip.decompress(p.read_bytes()), compresslevel=1, mtime=123456))
        after = self.data.audit(self.dataset, self.splits, self.contract)
        self.assertNotEqual(before["dataset_sha256"], after["dataset_sha256"])
        self.assertEqual(before["semantic_dataset_sha256"], after["semantic_dataset_sha256"])

    def test_wrong_ignore_region_or_validation_ignore_is_refused(self):
        path = self.dataset / "labelsTr/GU001.nii.gz"
        b = np.asanyarray(nib.load(path).dataobj).copy()
        b[4, 4, 4] = 6
        save(path, b, np.eye(4))
        with self.assertRaisesRegex(ValueError, "ignore mask"):
            self.data.audit(self.dataset, self.splits, self.contract)
        b[4, 4, 4] = 1
        save(path, b, np.eye(4))
        save(self.dataset / "labelsTr/IXI002.nii.gz", b, np.eye(4))
        with self.assertRaisesRegex(ValueError, "Validation.*ignore"):
            self.data.audit(self.dataset, self.splits, self.contract)

    def test_copy_mismatch_and_source_person_leak_are_refused(self):
        path = self.dataset / "imagesTr/IXI001w2_0000.nii.gz"
        a = np.asanyarray(nib.load(path).dataobj).copy()
        a[3, 3, 3] += 1
        save(path, a, np.eye(4))
        with self.assertRaisesRegex(ValueError, "copy differs"):
            self.data.audit(self.dataset, self.splits, self.contract)
        bad = copy.deepcopy(self.contract)
        bad["source_train"].append("IXI002")
        with self.assertRaises(ValueError):
            self.data.validate_split(bad["train"], bad["val"], bad)

    def test_archive_sidecar_and_wrong_package_are_checked(self):
        archive = self.root / "handoff_e3.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for p in self.package.rglob("*"):
                if p.is_file():z.write(p, p.relative_to(self.root).as_posix())
        digest = self.data.sha256(archive)
        layout = self.data.extract_handoff(archive, self.root / "extracted", digest)
        self.assertEqual(layout["dataset"].name, "Dataset003_E3Face")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.data.extract_handoff(archive, self.root / "wrong", "0" * 64)
        sidecar = self.root / "handoff_e3.zip.sha256"
        sidecar.write_text(digest + "  handoff_e3.zip\n")
        self.data.verify_sidecar(sidecar, digest)
        sidecar.write_text("0" * 64 + "  handoff_e3.zip\n")
        with self.assertRaises(ValueError):self.data.verify_sidecar(sidecar, digest)

    def test_ras_copy_preserves_ignore_values_and_world_positions(self):
        path = self.dataset / "imagesTr/IXI001_0000.nii.gz"
        a = np.asanyarray(nib.load(path).dataobj).copy()
        affine = np.array([[0, 0, 1., 0], [-1., 0, 0, 6], [0, 1., 0, 0], [0, 0, 0, 1.]])
        for case in ("IXI001", "IXI001w2"):
            save(self.dataset / "imagesTr" / f"{case}_0000.nii.gz", a, affine)
            b = np.asanyarray(nib.load(self.dataset / "labelsTr" / f"{case}.nii.gz").dataobj).copy()
            save(self.dataset / "labelsTr" / f"{case}.nii.gz", b, affine)
        changes = self.data.write_ras_dataset(self.dataset, self.root / "ras")
        report = self.data.audit(self.root / "ras" / self.data.DATASET, self.splits, self.contract)
        self.assertEqual(report["axis_codes"], {"RAS": 4})
        self.assertEqual(changes["IXI001"]["source_axis_codes"], "PSR")
        before = nib.load(self.dataset / "labelsTr/IXI001.nii.gz")
        after = nib.load(self.root / "ras" / self.data.DATASET / "labelsTr/IXI001.nii.gz")
        idx = np.indices(before.shape).reshape(3, -1).T
        world = nib.affines.apply_affine(before.affine, idx)
        mapped = np.rint(nib.affines.apply_affine(np.linalg.inv(after.affine), world)).astype(int)
        np.testing.assert_array_equal(np.asanyarray(before.dataobj)[tuple(idx.T)], np.asanyarray(after.dataobj)[tuple(mapped.T)])


class ContractAndNotebookTests(unittest.TestCase):
    def test_e2_helpers_are_not_mutated_by_dataset003_adapter(self):
        sys.path.insert(0, str(HERE.parent / "e2_training"))
        import e2_helpers
        import e3_data
        self.assertEqual(e2_helpers.DATASET, "Dataset002_E2Charm")
        self.assertNotIn("ignore", e2_helpers.LABELS)
        self.assertEqual(e3_data.DATASET, "Dataset003_E3Face")

    def test_contract_matches_supplied_dataset_and_e2_people(self):
        c = json.loads((HERE / "e3_contract.json").read_text())
        e2 = json.loads((HERE.parent / "e2_training/e2_contract.json").read_text())
        self.assertEqual(c["dataset"], "Dataset003_E3Face")
        self.assertEqual(c["archive"], "handoff_e3.zip")
        self.assertEqual(c["archive_sha256"], "c12f5fb233d829d20bdcc112e412a1eb9fe17158a4a56377cec3e1951eba7698")
        self.assertEqual((len(c["train"]), len(c["val"])), (90, 16))
        self.assertEqual(c["source_train"], e2["train"])
        self.assertEqual(c["val"], e2["val"])
        self.assertEqual(c["labels"]["ignore"], 6)
        self.assertEqual(c["sampling"], "uniform_over_entries")
        self.assertEqual(len(c["copy_sources"]), 23)
        original = json.loads((HERE / "e2_plans.json").read_text())
        target = json.loads((HERE / "e3_plans.json").read_text())
        original["dataset_name"] = "Dataset003_E3Face"
        self.assertEqual(target, original)

    def test_generated_notebook_is_current_compiles_and_is_off_by_default(self):
        from build_e3_notebook import build
        n = build()
        self.assertEqual(n, json.loads((HERE / "E3_Colab.ipynb").read_text()))
        code = "\n".join(c["source"] for c in n["cells"] if c["cell_type"] == "code")
        for c in n["cells"]:
            if c["cell_type"] == "code":compile(c["source"], c["id"], "exec")
        config = next(c["source"] for c in n["cells"] if "EXPERIMENT_ID = " in c["source"])
        self.assertIn('ARCHIVE = Path("/content/drive/MyDrive/TMS_E3/handoff_e3.zip")', config)
        self.assertIn('EXPERIMENT_ID = "E3_Dataset003_001"', config)
        for flag in ["ACKNOWLEDGE_E3_DATA", "RUN_5_EPOCH_PILOT", "RUN_100_EPOCH_PRELIMINARY", "RESUME_PRELIMINARY"]:
            self.assertIn(flag + " = False", config)
        self.assertIn("verify_sidecar", code)
        self.assertIn('"sampling": "uniform_over_entries"', code)
        self.assertIn("e3_plans.json", code)
        self.assertNotIn("sampling_probabilities", code)
        self.assertNotIn("handoff_k2_e2.zip", code)

    def test_training_command_uses_dataset_three_and_resume_guards(self):
        import e3_helpers as h
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "fold_0"
            cmd = h.training_command("train", "nnUNetTrainer_E3Preliminary", p)
            self.assertEqual(cmd[:4], ["train", "3", "3d_fullres", "0"])
            self.assertNotIn("-pretrained_weights", cmd)
            with self.assertRaises(ValueError):h.training_command("train", "nnUNetTrainer_E2Preliminary", p)
            with self.assertRaises(ValueError):h.training_command("train", "nnUNetTrainer_E3Preliminary", p, True)
            p.mkdir()
            with self.assertRaises(ValueError):h.training_command("train", "nnUNetTrainer_E3Preliminary", p)
            with zipfile.ZipFile(p / "checkpoint_latest.pth", "w") as z:z.writestr("data.pkl", b"synthetic")
            self.assertIn("--c", h.training_command("train", "nnUNetTrainer_E3Preliminary", p, True))

    def test_final_validation_checks_identity_and_subgroups(self):
        import e3_helpers as h
        c = json.loads((HERE / "e3_contract.json").read_text())
        rows = [{"prediction_file": f"/p/{s}.nii.gz", "reference_file": f"/r/{s}.nii.gz",
                 "metrics": {str(i): {"Dice": .9} for i in range(1, 6)}} for s in c["val"]]
        report = h.subgroup_metrics({"metric_per_case": rows}, c["val"])
        self.assertEqual((report["IXI"]["cases"], report["MultiAxial"]["cases"]), (6, 10))
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "validation/summary.json";p.parent.mkdir()
            p.write_text(json.dumps({"metric_per_case": rows, "foreground_mean": {"Dice": .9}}))
            self.assertTrue(h.validation_complete(Path(temp), c["val"]))
            rows[-1]["prediction_file"] = rows[-1]["reference_file"] = "/x/IXI111.nii.gz"
            p.write_text(json.dumps({"metric_per_case": rows, "foreground_mean": {"Dice": .9}}))
            self.assertFalse(h.validation_complete(Path(temp), c["val"]))

    def test_fresh_main_run_requires_completed_gpu_pilot(self):
        import os
        from unittest.mock import patch
        import e3_helpers as h
        from build_e3_notebook import build
        stage = next(c["source"] for c in build()["cells"] if c["source"].startswith("def train_stage"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);(root / "experiment_contract.json").write_text("{}")
            c = json.loads((HERE / "e3_contract.json").read_text())
            ns = {"RUN_5_EPOCH_PILOT": False, "RESUME_PILOT": False, "ACKNOWLEDGE_E3_DATA": True,
                  "RESULTS": root, "ENV": {"nnUNet_results": str(root), "nnUNet_n_proc_DA": "4"},
                  "AUGMENTATION_WORKERS": 4, "DATASET": c["dataset"], "CONTRACT": c, "os": os,
                  "require": h.require, "validation_complete": h.validation_complete}
            exec(stage, ns)
            with patch("os.path.ismount", return_value=True), self.assertRaisesRegex(ValueError, "five-epoch pilot"):
                ns["train_stage"]("nnUNetTrainer_E3Preliminary", True, False)


@unittest.skipUnless(importlib.util.find_spec("nnunetv2"), "nnU-Net environment required")
class RealTrainingTests(unittest.TestCase):
    def test_trainers_use_standard_loader_and_six_output_channels(self):
        import os
        from unittest.mock import patch
        import torch
        from trainers_e3 import nnUNetTrainer_E3Preliminary, nnUNetTrainer_E3Smoke
        from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
        c = json.loads((HERE / "e3_contract.json").read_text())
        plan = json.loads((HERE / "e3_plans.json").read_text());plan["continue_training"] = False
        metadata = {"channel_names": {"0": "T1"}, "labels": c["labels"], "file_ending": ".nii.gz", "numTraining": 106}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
                "nnUNet_results": temp + "/out", "nnUNet_preprocessed": temp + "/pre", "nnUNet_compile": "false"}):
            main = nnUNetTrainer_E3Preliminary(copy.deepcopy(plan), "3d_fullres", 0, metadata, torch.device("cpu"))
            pilot = nnUNetTrainer_E3Smoke(copy.deepcopy(plan), "3d_fullres", 0, metadata, torch.device("cpu"))
            self.assertEqual((main.num_epochs, pilot.num_epochs, main.save_every), (100, 5, 1))
            self.assertEqual(main.label_manager.num_segmentation_heads, 6)
            self.assertEqual(main.label_manager.ignore_label, 6)
            self.assertIs(nnUNetTrainer_E3Preliminary.get_dataloaders, nnUNetTrainer.get_dataloaders)
            self.assertEqual(main._build_loss().loss.ignore_label, 6)

    def test_ignore_logits_do_not_affect_loss_or_receive_gradient(self):
        import torch
        from nnunetv2.training.loss.compound_losses import DC_and_CE_loss
        from nnunetv2.training.loss.dice import MemoryEfficientSoftDiceLoss
        torch.set_num_threads(2)
        loss_fn = DC_and_CE_loss({"batch_dice": False, "smooth": 1e-5, "do_bg": False, "ddp": False}, {},
                                ignore_label=6, dice_class=MemoryEfficientSoftDiceLoss)
        logits = torch.randn(2, 6, 8, 8, 8, requires_grad=True)
        target = torch.randint(0, 6, (2, 1, 8, 8, 8));target[:, :, :2] = 6
        changed = logits.detach().clone();changed[:, :, :2] = torch.randn_like(changed[:, :, :2]) * 200
        loss = loss_fn(logits, target)
        self.assertTrue(torch.isfinite(loss))
        torch.testing.assert_close(loss, loss_fn(changed, target))
        loss.backward()
        self.assertTrue(torch.all(logits.grad[:, :, :2] == 0))
        self.assertGreater(float(logits.grad[:, :, 2:].abs().sum()), 0)

    def test_standard_loader_uniform_copy_sampling_and_cpu_update(self):
        import os
        from types import SimpleNamespace
        from unittest.mock import patch
        import torch
        from trainers_e3 import nnUNetTrainer_E3Preliminary
        from nnunetv2.utilities.label_handling.label_handling import LabelManager
        from nnunetv2.training.loss.compound_losses import DC_and_CE_loss
        from nnunetv2.training.loss.deep_supervision import DeepSupervisionWrapper
        from nnunetv2.training.loss.dice import MemoryEfficientSoftDiceLoss
        from dynamic_network_architectures.architectures.unet import PlainConvUNet
        torch.set_num_threads(2)
        c = json.loads((HERE / "e3_contract.json").read_text())
        rng = np.random.default_rng(42)
        data = rng.normal(size=(1, 24, 24, 24)).astype(np.float32)
        seg = rng.integers(0, 6, size=data.shape, dtype=np.int16);seg[:, :3] = 6
        locations = {i: np.argwhere(seg == i)[:128] for i in range(6)}
        locations[tuple([-1] + list(range(6)))] = np.argwhere(seg != 6)
        class SyntheticDataset:
            def __init__(self, identifiers):self.identifiers = identifiers
            def load_case(self, case):return data, seg, None, {"class_locations": locations}
        t = object.__new__(nnUNetTrainer_E3Preliminary)
        t.dataset_class = SyntheticDataset
        t.configuration_manager = SimpleNamespace(patch_size=[16]*3, use_mask_for_norm=[False])
        t.batch_size = 2;t.oversample_foreground_percent = .33;t.probabilistic_oversampling = False
        t.label_manager = LabelManager(c["labels"], None);t.is_cascaded = False;t.device = torch.device("cpu")
        t._get_deep_supervision_scales = lambda: [[1., 1., 1.], [.5, .5, .5]]
        t.configure_rotation_dummyDA_mirroring_and_inital_patch_size = lambda: ((-.1, .1), False, [20]*3, (0, 1, 2))
        t.get_tr_and_val_datasets = lambda: (SyntheticDataset(c["train"]), SyntheticDataset(c["val"]))
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"nnUNet_n_proc_DA": "0"}):
            t.output_folder = temp
            train, val = t.get_dataloaders()
            self.assertIsNone(train.data_loader.sampling_probabilities)
            self.assertIsNone(val.data_loader.sampling_probabilities)
            np.random.seed(42)
            draws = np.concatenate([train.data_loader.get_indices() for _ in range(20000)])
            self.assertAlmostEqual(np.mean([s.startswith("IXI") for s in draws]), 46/90, delta=.012)
            self.assertFalse(set(draws) & set(c["val"]))
            batch = next(train)
            network = PlainConvUNet(1, 3, [4, 8, 16], torch.nn.Conv3d, [3]*3, [1, 2, 2], [2]*3,
                                   6, [2]*2, norm_op=torch.nn.InstanceNorm3d, nonlin=torch.nn.LeakyReLU, deep_supervision=True)
            loss_fn = DeepSupervisionWrapper(DC_and_CE_loss(
                {"batch_dice": False, "smooth": 1e-5, "do_bg": False, "ddp": False}, {},
                ignore_label=6, dice_class=MemoryEfficientSoftDiceLoss), [.67, .33])
            opt = torch.optim.SGD(network.parameters(), lr=.01, momentum=.99, nesterov=True)
            before = next(network.parameters()).detach().clone()
            loss = loss_fn(network(batch["data"]), batch["target"])
            self.assertTrue(torch.isfinite(loss));loss.backward();opt.step()
            self.assertFalse(torch.equal(before, next(network.parameters()).detach()))


if __name__ == "__main__":unittest.main()
