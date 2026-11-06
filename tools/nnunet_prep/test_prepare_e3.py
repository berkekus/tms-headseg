import csv
import json
import tempfile
import unittest
from pathlib import Path

import nibabel as nib
import numpy as np

import prepare_e3 as e3
from prepare_e2 import DATASET_NAME as E2_NAME

CASES = {"IXI001": ("IXI", "train"), "IXI002": ("IXI", "train"), "GU001": ("MultiAxial", "train"),
         "IXI003": ("IXI", "val"), "GU002": ("MultiAxial", "val")}


def volume():
    """A head of signal in the middle, an exactly-zero wedge in front (defacing) and noisy air elsewhere."""
    rng = np.random.default_rng(0)
    image = rng.uniform(1, 5, (20, 20, 20)).astype(np.float32)  # air: low but non-zero
    image[5:15, 5:15, 5:15] = 300                                  # head
    image[:, 15:, :8] = 0                                          # defacing wedge, touches the border
    labels = np.zeros(image.shape, np.uint8)
    labels[5:15, 5:15, 5:15] = 4
    labels[:, 15:, :8] = 1  # charm-like extrapolated skin inside the wedge
    return image, labels


def make_e2(root):
    raw = root / "nnUNet_raw" / E2_NAME
    (raw / "imagesTr").mkdir(parents=True)
    (raw / "labelsTr").mkdir()
    image, labels = volume()
    for case in CASES:
        nib.save(nib.Nifti1Image(image, np.eye(4)), str(raw / "imagesTr" / f"{case}_0000.nii.gz"))
        nib.save(nib.Nifti1Image(labels, np.eye(4)), str(raw / "labelsTr" / f"{case}.nii.gz"))
    with open(root / "e2_manifest.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "source", "split"])
        writer.writeheader()
        for case, (source, split) in CASES.items():
            writer.writerow({"case_id": case, "source": source, "split": split})
    pre = root / "nnUNet_preprocessed" / E2_NAME
    pre.mkdir(parents=True)
    pre.joinpath("splits_final.json").write_text(json.dumps([{
        "train": sorted(c for c, (_, s) in CASES.items() if s == "train"),
        "val": sorted(c for c, (_, s) in CASES.items() if s == "val")}]))
    return raw


class PrepareE3Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.e2_raw = make_e2(self.root / "e2")
        self.out = self.root / "e3"
        self.rows = e3.build(self.root / "e2", self.out, ixi_weight=2)
        self.raw = self.out / "nnUNet_raw" / e3.DATASET_NAME

    def tearDown(self):
        self.tmp.cleanup()

    def labels(self, case):
        return np.asarray(nib.load(str(self.raw / "labelsTr" / f"{case}.nii.gz")).dataobj)

    def test_training_voxels_without_signal_are_ignored_and_the_head_is_kept(self):
        labels = self.labels("GU001")
        self.assertTrue((labels[:, 15:, :8] == e3.IGNORE).all(), "the defacing wedge must be ignore")
        self.assertTrue((labels[5:15, 5:15, 5:15] == 4).all())
        self.assertEqual(int(labels[0, 0, 19]), 0, "noisy air stays background")

    def test_validation_is_byte_for_byte_e2(self):
        for case in ("IXI003", "GU002"):
            self.assertEqual((self.raw / "labelsTr" / f"{case}.nii.gz").read_bytes(),
                             (self.e2_raw / "labelsTr" / f"{case}.nii.gz").read_bytes())

    def test_only_ixi_training_cases_are_weighted(self):
        ids = {r["case_id"] for r in self.rows}
        self.assertEqual(ids, set(CASES) | {"IXI001w2", "IXI002w2"})
        self.assertTrue((self.raw / "imagesTr" / "IXI001w2_0000.nii.gz").is_file())
        np.testing.assert_array_equal(self.labels("IXI001w2"), self.labels("IXI001"))

    def test_split_and_dataset_json(self):
        split = json.loads((self.out / "nnUNet_preprocessed" / e3.DATASET_NAME / "splits_final.json").read_text())[0]
        self.assertEqual(split["val"], ["GU002", "IXI003"])
        self.assertEqual(set(split["train"]), {"GU001", "IXI001", "IXI001w2", "IXI002", "IXI002w2"})
        self.assertFalse(set(split["train"]) & set(split["val"]))
        dataset = json.loads((self.raw / "dataset.json").read_text())
        self.assertEqual(dataset["labels"]["ignore"], 6)
        self.assertEqual(max(dataset["labels"].values()), dataset["labels"]["ignore"], "nnU-Net needs ignore highest")
        self.assertEqual(dataset["numTraining"], 7)

    def test_refuses_unsafe_inputs(self):
        with self.assertRaises(SystemExit):
            e3.build(self.root / "e2", self.out)  # never write into an existing dataset
        with self.assertRaises(ValueError):
            e3.build(self.root / "e2", self.root / "other", ixi_weight=0)
        split_file = self.root / "e2" / "nnUNet_preprocessed" / E2_NAME / "splits_final.json"
        split_file.write_text(json.dumps([{"train": ["IXI001"], "val": ["GU002"]}]))
        with self.assertRaises(ValueError):
            e3.build(self.root / "e2", self.root / "third")


if __name__ == "__main__":
    unittest.main()
