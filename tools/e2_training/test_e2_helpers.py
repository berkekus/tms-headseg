"""E2 handoff checks on small synthetic archives; no GPU, no nnU-Net."""

import hashlib
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
sys.path.insert(0, str(HERE.parent / "nnunet_prep"))

import e2_helpers as e2  # noqa: E402

CONTRACT = json.loads((HERE / "e2_contract.json").read_text(encoding="utf-8"))


def psr(shape):
    """IXI-like sagittal storage: i posterior, j superior, k right."""
    return np.array([[0, 0, 1., -(shape[2] - 1) / 2], [-1., 0, 0, (shape[0] - 1) / 2],
                     [0, 1., 0, -(shape[1] - 1) / 2], [0, 0, 0, 1]])


def save(path, data, affine):
    image = nib.Nifti1Image(data, affine)
    image.set_data_dtype(data.dtype)
    image.set_sform(affine, code=1)
    image.set_qform(affine, code=1)
    image.header.set_xyzt_units("mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(image, str(path))


class E2HelperTests(unittest.TestCase):
    shape = (6, 7, 8)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract = {"train": ["IXI001", "GU001"], "val": ["IXI002"]}
        rng = np.random.default_rng(0)
        self.source = self.root / "pkg" / "e2_full" / "nnUNet_raw" / e2.DATASET
        for case in self.contract["train"] + self.contract["val"]:
            affine = psr(self.shape) if case.startswith("IXI") else np.diag([1., 1, 1, 1])
            save(self.source / "imagesTr" / f"{case}_0000.nii.gz", rng.random(self.shape).astype(np.float32), affine)
            save(self.source / "labelsTr" / f"{case}.nii.gz", rng.integers(0, 6, self.shape).astype(np.uint8), affine)
        (self.source / "dataset.json").write_text(json.dumps({"channel_names": {"0": "T1"}, "labels": e2.LABELS,
                                                              "numTraining": 3, "file_ending": ".nii.gz"}))
        split = self.root / "pkg" / "e2_full" / "nnUNet_preprocessed" / e2.DATASET / "splits_final.json"
        split.parent.mkdir(parents=True)
        split.write_text(json.dumps([{"train": self.contract["train"], "val": self.contract["val"]}]))
        (self.root / "pkg" / "e2_full" / "K2_BASLA_E2.md").write_text("notes")

    def archive(self, extra=None):
        path = self.root / "handoff_k2_e2.zip"
        path.unlink(missing_ok=True)
        with zipfile.ZipFile(path, "w") as archive:
            for file in sorted((self.root / "pkg").rglob("*")):
                if file.is_file():
                    archive.write(file, file.relative_to(self.root / "pkg").as_posix())
            for name, data in (extra or {}).items():
                archive.writestr(name, data)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_extract_finds_the_dataset_under_a_top_folder(self):
        path, digest = self.archive()
        layout = e2.extract_handoff(path, self.root / "out", digest)
        self.assertTrue((layout["dataset"] / "dataset.json").is_file())
        self.assertEqual(layout["splits"].name, "splits_final.json")
        again = e2.extract_handoff(path, self.root / "out", digest)  # a rerun reuses the extraction
        self.assertEqual(again, layout)

    def test_windows_backslash_paths_are_read_as_folders(self):
        path = self.root / "handoff_k2_e2.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for file in sorted((self.root / "pkg").rglob("*")):
                if file.is_file():
                    info = zipfile.ZipInfo("placeholder")
                    info.filename = file.relative_to(self.root / "pkg").as_posix().replace("/", "\\")  # as PowerShell 5.1 writes
                    archive.writestr(info, file.read_bytes())
        # Python on Windows converts "\" when it reads; Colab (Linux) does not. Check the stored bytes.
        self.assertIn(b"imagesTr\\IXI001_0000.nii.gz", path.read_bytes())
        layout = e2.extract_handoff(path, self.root / "out", hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertTrue((layout["dataset"] / "imagesTr" / "IXI001_0000.nii.gz").is_file())
        report = e2.audit(layout["dataset"], layout["splits"], self.contract)
        self.assertEqual(report["train_count"], 2)

    def test_wrong_archive_checksum_is_refused_before_extraction(self):
        path, _ = self.archive()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            e2.extract_handoff(path, self.root / "out", "0" * 64)
        self.assertFalse((self.root / "out").exists())

    def test_unsafe_paths_are_refused(self):
        path, digest = self.archive({"../evil.txt": "x"})
        with self.assertRaisesRegex(ValueError, "Güvensiz"):
            e2.extract_handoff(path, self.root / "out", digest)

    def test_two_datasets_in_one_archive_are_refused(self):
        path, digest = self.archive({f"other/nnUNet_raw/{e2.DATASET}/dataset.json": "{}"})
        with self.assertRaisesRegex(ValueError, "dataset.json"):
            e2.extract_handoff(path, self.root / "out", digest)

    def test_audit_passes_and_reports_mixed_axis_order(self):
        path, digest = self.archive()
        layout = e2.extract_handoff(path, self.root / "out", digest)
        report = e2.audit(layout["dataset"], layout["splits"], self.contract)
        self.assertEqual((report["train_count"], report["validation_count"]), (2, 1))
        self.assertEqual(report["axis_codes"], {"PSR": 2, "RAS": 1})
        self.assertTrue(any("eksen" in warning for warning in report["warnings"]))
        self.assertEqual(len(report["dataset_sha256"]), 64)

    def test_audit_refuses_a_split_that_differs_from_the_contract(self):
        path, digest = self.archive()
        layout = e2.extract_handoff(path, self.root / "out", digest)
        with self.assertRaisesRegex(ValueError, "Bölme"):
            e2.audit(layout["dataset"], layout["splits"], {"train": ["IXI001", "IXI002"], "val": ["GU001"]})

    def test_audit_refuses_extra_cases_and_foreign_labels(self):
        save(self.source / "imagesTr" / "IXI111_0000.nii.gz", np.zeros(self.shape, np.float32), np.eye(4))
        path, digest = self.archive()
        layout = e2.extract_handoff(path, self.root / "out", digest)
        with self.assertRaisesRegex(ValueError, "imagesTr"):
            e2.audit(layout["dataset"], layout["splits"], self.contract)
        (layout["dataset"] / "imagesTr" / "IXI111_0000.nii.gz").unlink()
        save(layout["dataset"] / "labelsTr" / "GU001.nii.gz", np.full(self.shape, 9, np.uint8), np.eye(4))
        with self.assertRaisesRegex(ValueError, "0–5"):
            e2.audit(layout["dataset"], layout["splits"], self.contract)

    def test_audit_refuses_labels_off_the_image_grid(self):
        shifted = np.eye(4)
        shifted[:3, 3] = 2
        save(self.source / "labelsTr" / "GU001.nii.gz", np.zeros(self.shape, np.uint8), shifted)
        path, digest = self.archive()
        layout = e2.extract_handoff(path, self.root / "out", digest)
        with self.assertRaisesRegex(ValueError, "ızgara"):
            e2.audit(layout["dataset"], layout["splits"], self.contract)

    def test_ras_copy_is_an_exact_permutation_with_unchanged_world_positions(self):
        path, digest = self.archive()
        layout = e2.extract_handoff(path, self.root / "out", digest)
        changes = e2.write_ras_dataset(layout["dataset"], self.root / "ras")
        self.assertEqual({case: change["source_axis_codes"] for case, change in changes.items()},
                         {"GU001": "RAS", "IXI001": "PSR", "IXI002": "PSR"})
        moved = self.root / "ras" / e2.DATASET
        for case in changes:
            for folder, name in (("imagesTr", f"{case}_0000.nii.gz"), ("labelsTr", f"{case}.nii.gz")):
                before, after = nib.load(layout["dataset"] / folder / name), nib.load(moved / folder / name)
                self.assertEqual(nib.aff2axcodes(after.affine), ("R", "A", "S"))
                a, b = np.asanyarray(before.dataobj), np.asanyarray(after.dataobj)
                self.assertEqual(a.dtype, b.dtype)
                # Same value at the same world point for every voxel.
                index = np.indices(a.shape).reshape(3, -1).T
                world = nib.affines.apply_affine(before.affine, index)
                back = np.rint(nib.affines.apply_affine(np.linalg.inv(after.affine), world)).astype(int)
                np.testing.assert_array_equal(b[tuple(back.T)], a[tuple(index.T)])
                self.assertEqual(int(after.header["qform_code"]), 1)
        report = e2.audit(moved, layout["splits"], self.contract)
        self.assertEqual(report["axis_codes"], {"RAS": 3})
        self.assertEqual(report["warnings"], [])
        with self.assertRaisesRegex(ValueError, "zaten var"):
            e2.write_ras_dataset(layout["dataset"], self.root / "ras")

    def test_interrupted_ras_copy_is_discarded_not_used(self):
        path, digest = self.archive()
        layout = e2.extract_handoff(path, self.root / "out", digest)
        partial = self.root / "ras" / f".partial_{e2.DATASET}" / "imagesTr"
        partial.mkdir(parents=True)
        (partial / "stale_0000.nii.gz").write_bytes(b"half")
        e2.write_ras_dataset(layout["dataset"], self.root / "ras")
        self.assertFalse((self.root / "ras" / f".partial_{e2.DATASET}").exists())
        self.assertNotIn("stale_0000.nii.gz", {p.name for p in (self.root / "ras" / e2.DATASET / "imagesTr").iterdir()})

    def test_command_line_steps_used_by_the_notebook(self):
        import subprocess
        path, digest = self.archive()
        layout = e2.extract_handoff(path, self.root / "out", digest)
        contract = self.root / "contract.json"
        contract.write_text(json.dumps(self.contract))
        run = lambda *args: subprocess.run([sys.executable, str(HERE / "e2_helpers.py"), *map(str, args)],
                                           capture_output=True, text=True, check=True).stdout
        self.assertIn("2 eğitim / 1 doğrulama", run("audit", layout["dataset"], layout["splits"], contract, self.root / "a.json"))
        self.assertIn("RAS'a çevrilen vaka: 2 / 3", run("ras", layout["dataset"], self.root / "ras", self.root / "changes.json"))
        run("audit", self.root / "ras" / e2.DATASET, layout["splits"], contract, self.root / "b.json")
        self.assertEqual(json.loads((self.root / "b.json").read_text())["axis_codes"], {"RAS": 3})
        run("preview", self.root / "ras" / e2.DATASET, self.root / "preview.png", "IXI001", "GU001")
        self.assertGreater((self.root / "preview.png").stat().st_size, 1000)

    def test_training_command_never_overwrites_or_restarts_silently(self):
        fold = self.root / "results" / "fold_0"
        command = e2.training_command("nnUNetv2_train", "nnUNetTrainer_E2Preliminary", fold)
        self.assertEqual(command[:4], ["nnUNetv2_train", "2", "3d_fullres", "0"])
        with self.assertRaisesRegex(ValueError, "eğitici"):
            e2.training_command("nnUNetv2_train", "nnUNetTrainer_E1Preliminary", fold)
        with self.assertRaisesRegex(ValueError, "checkpoint yok"):
            e2.training_command("nnUNetv2_train", "nnUNetTrainer_E2Preliminary", fold, resume=True)
        fold.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "klasörü var"):
            e2.training_command("nnUNetv2_train", "nnUNetTrainer_E2Preliminary", fold)
        with zipfile.ZipFile(fold / "checkpoint_latest.pth", "w") as checkpoint:
            checkpoint.writestr("data.pkl", "x")
        self.assertIn("--c", e2.training_command("nnUNetv2_train", "nnUNetTrainer_E2Preliminary", fold, resume=True))

    def test_validation_counts_every_case(self):
        fold = self.root / "fold_0"
        self.assertFalse(e2.validation_complete(fold, 16))
        (fold / "validation").mkdir(parents=True)
        (fold / "validation" / "summary.json").write_text(json.dumps({"metric_per_case": [{}] * 15}))
        self.assertFalse(e2.validation_complete(fold, 16))
        (fold / "validation" / "summary.json").write_text(json.dumps({"metric_per_case": [{}] * 16}))
        self.assertTrue(e2.validation_complete(fold, 16))


class ContractTests(unittest.TestCase):
    def test_contract_split_is_the_one_k1_planned(self):
        import prepare_e2
        cases = prepare_e2.plan_cases(prepare_e2.read_csv(prepare_e2.CHARM_BATCH / "ixi_assignment.csv"),
                                      prepare_e2.read_csv(prepare_e2.CHARM_BATCH / "multiaxial_assignment.csv"), 42)
        self.assertEqual(CONTRACT["train"], sorted(c for c, i in cases.items() if i["split"] == "train"))
        self.assertEqual(CONTRACT["val"], sorted(c for c, i in cases.items() if i["split"] == "val"))
        self.assertEqual(CONTRACT["dataset"], e2.DATASET)
        self.assertEqual(CONTRACT["labels"], e2.LABELS)

    def test_contract_holds_no_held_out_subject(self):
        import csv
        with open(HERE.parent / "charm_batch" / "ixi_assignment.csv", newline="") as stream:
            held_out = {row["subject"] for row in csv.DictReader(stream) if row["cohort"] != "train"}
        self.assertEqual(len(held_out), 21)
        self.assertFalse(held_out & set(CONTRACT["train"] + CONTRACT["val"]))


if __name__ == "__main__":
    unittest.main()
