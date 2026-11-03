import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import nibabel as nib
import numpy as np

import prepare_e2 as e2


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["subject", "site", "cohort", "owner", "note"] if "cohort" in rows[0]
                           else ["subject", "qc", "notes"])
        w.writeheader()
        w.writerows(rows)


class E2Fixture:
    """Tiny IXI + MultiAxial layout with charm deliveries."""

    def __init__(self, root: Path):
        self.root = root
        self.ixi_images, self.ma_images = root / "D06", root / "imagesTr"
        self.deliver = root / "deliver"
        self.ixi = [{"subject": f"IXI{i:03d}", "site": ("Guys", "HH", "IOP")[i % 3], "cohort": "train",
                     "owner": "K1" if i % 2 else "K2", "note": ""} for i in range(1, 10)]
        self.ixi.append({"subject": "IXI900", "site": "Guys", "cohort": "test_face", "owner": "K1", "note": ""})
        self.ma = [{"subject": "GU001", "site": "GU", "cohort": "train", "owner": "K1", "note": ""},
                   {"subject": "NC001", "site": "NC", "cohort": "val", "owner": "K1", "note": ""}]
        write_csv(root / "ixi.csv", self.ixi)
        write_csv(root / "ma.csv", self.ma)
        self.labels = np.zeros((6, 6, 6), np.int16)
        self.labels[1:5, 1:5, 1:5] = 5   # scalp
        self.labels[2:4, 2:4, 2:4] = 9   # blood
        self.labels[2, 2, 2] = 1         # charm WM
        for r in self.ixi:
            folder = self.ixi_images / r["subject"]
            folder.mkdir(parents=True)
            self.image(folder / f"{r['subject']}-{r['site']}-0001-T1.nii.gz")
            self.delivery(r["subject"], t1_only=False)
        self.ma_images.mkdir()
        for r in self.ma:
            self.image(self.ma_images / f"{r['subject']}_0000.nii.gz")
            self.delivery(r["subject"], t1_only=True)
        self.qc = root / "qc.csv"
        self.write_qc({})

    def write_qc(self, overrides):
        write_csv(self.qc, [{"subject": r["subject"], "qc": overrides.get(r["subject"], "pass"), "notes": ""}
                            for r in self.ixi + self.ma])

    @staticmethod
    def image(path):
        nib.save(nib.Nifti1Image(np.ones((6, 6, 6), np.float32), np.eye(4)), str(path))

    def delivery(self, subject, t1_only):
        folder = self.deliver / subject
        folder.mkdir(parents=True)
        nib.save(nib.Nifti1Image(self.labels[..., None], np.eye(4)), str(folder / "final_tissues.nii.gz"))
        (folder / "run.json").write_text(json.dumps({"subject": subject, "outputs_ok": True, "owner": "K1",
                                                     "simnibs_version": "4.6.0", "t1_only": t1_only}))
        self.resum(folder)

    @staticmethod
    def resum(folder):
        lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
                 for p in sorted(folder.iterdir()) if p.name != "SHA256SUMS.txt"]
        (folder / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")

    def args(self, *extra):
        return e2.parse_args(["--deliver", str(self.deliver), "--qc", str(self.qc),
                              "--ixi-images", str(self.ixi_images), "--ma-images", str(self.ma_images),
                              "--ixi-assignment", str(self.root / "ixi.csv"), "--ma-assignment", str(self.root / "ma.csv"),
                              "--out", str(self.root / "out"), *extra])


class PrepareE2Tests(unittest.TestCase):
    def test_builds_dataset_without_held_out_and_maps_blood_to_csf(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = E2Fixture(Path(tmp))
            result = e2.build(fx.args("--require-all"))
            ids = {m["case_id"] for m in result["manifest"]}
            self.assertNotIn("IXI900", ids)
            self.assertEqual(len(ids), 11)
            raw = fx.root / "out" / "nnUNet_raw" / e2.DATASET_NAME
            labels = np.asanyarray(nib.load(str(raw / "labelsTr" / "IXI001.nii.gz")).dataobj)
            self.assertEqual(labels.ndim, 3)
            self.assertEqual(int(labels[3, 3, 3]), 3)   # blood -> CSF
            self.assertEqual(int(labels[2, 2, 2]), 5)   # charm WM -> project WM
            self.assertEqual(int(labels[1, 1, 1]), 1)   # scalp -> skin
            self.assertFalse((raw / "imagesTr" / "IXI900_0000.nii.gz").exists())
            split = json.loads((fx.root / "out" / "nnUNet_preprocessed" / e2.DATASET_NAME
                                / "splits_final.json").read_text())[0]
            self.assertIn("NC001", split["val"])
            self.assertIn("GU001", split["train"])
            self.assertEqual(sum(s.startswith("IXI") for s in split["val"]), 6)  # 2 per site
            self.assertFalse(set(split["train"]) & set(split["val"]))
            dataset = json.loads((raw / "dataset.json").read_text())
            self.assertEqual(dataset["numTraining"], 11)

    def test_ixi_split_is_deterministic_and_site_stratified(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = E2Fixture(Path(tmp))
            plan = e2.plan_cases(fx.ixi, fx.ma, 42)
            self.assertEqual(plan, e2.plan_cases(fx.ixi, fx.ma, 42))
            for site in ("Guys", "HH", "IOP"):
                self.assertEqual(sum(v["site"] == site and v["split"] == "val" for v in plan.values()), 2)

    def test_multiaxial_test_cohort_is_refused(self):
        with self.assertRaises(ValueError):
            e2.plan_cases([], [{"subject": "GU003", "site": "GU", "cohort": "test"}], 42)

    def test_checksum_mismatch_stops_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = E2Fixture(Path(tmp))
            nib.save(nib.Nifti1Image(np.zeros((6, 6, 6, 1), np.int16), np.eye(4)),
                     str(fx.deliver / "IXI002" / "final_tissues.nii.gz"))
            with self.assertRaisesRegex(ValueError, "IXI002: checksum mismatch"):
                e2.build(fx.args())

    def test_qc_fail_never_enters_and_unchecked_needs_the_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = E2Fixture(Path(tmp))
            fx.write_qc({"IXI001": "fail", "IXI002": "check", "IXI003": ""})
            ids = {m["case_id"] for m in e2.build(fx.args())["manifest"]}
            self.assertFalse({"IXI001", "IXI002", "IXI003"} & ids)
        with tempfile.TemporaryDirectory() as tmp:
            fx = E2Fixture(Path(tmp))
            fx.write_qc({"IXI001": "fail", "IXI003": ""})
            ids = {m["case_id"] for m in e2.build(fx.args("--allow-unchecked"))["manifest"]}
            self.assertIn("IXI003", ids)
            self.assertNotIn("IXI001", ids)

    def test_require_all_fails_when_a_case_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = E2Fixture(Path(tmp))
            for p in (fx.deliver / "NC001").iterdir():
                p.unlink()
            (fx.deliver / "NC001").rmdir()
            with self.assertRaises(SystemExit):
                e2.build(fx.args("--require-all"))

    def test_geometry_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = E2Fixture(Path(tmp))
            folder = fx.deliver / "GU001"
            shifted = np.eye(4)
            shifted[0, 3] = 1.0
            nib.save(nib.Nifti1Image(fx.labels[..., None], shifted), str(folder / "final_tissues.nii.gz"))
            fx.resum(folder)
            with self.assertRaisesRegex(ValueError, "affines differ"):
                e2.build(fx.args())

    def test_refuses_to_write_into_a_non_empty_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = E2Fixture(Path(tmp))
            e2.build(fx.args())
            with self.assertRaises(SystemExit):
                e2.build(fx.args())


if __name__ == "__main__":
    unittest.main()
