import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import make_assignment
import run_charm_batch as batch

HERE = Path(__file__).resolve().parent


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        with open(HERE / "ixi_assignment.csv", newline="") as f:
            self.rows = list(csv.DictReader(f))

    def test_held_out_and_excluded_are_never_k2_or_train(self):
        for r in self.rows:
            if r["cohort"] in ("test_face", "calibration"):
                self.assertEqual(r["owner"], "K1")
            if r["cohort"] == "excluded_d05":
                self.assertEqual(r["owner"], "-")
        self.assertEqual(sum(r["cohort"] == "test_face" for r in self.rows), 10)
        self.assertEqual(sum(r["cohort"] == "calibration" for r in self.rows), 5)

    def test_d05_overlap_excluded(self):
        excluded = {r["subject"] for r in self.rows if r["cohort"] == "excluded_d05"}
        self.assertEqual(excluded, {"IXI002", "IXI020", "IXI139", "IXI230", "IXI276", "IXI401"})

    def test_workers_get_every_site_and_balanced_counts(self):
        train = [r for r in self.rows if r["cohort"] == "train"]
        k1, k2 = (sum(r["owner"] == o for r in train) for o in ("K1", "K2"))
        self.assertLessEqual(abs(k1 - k2), 1)
        for owner in ("K1", "K2"):
            self.assertEqual({r["site"] for r in train if r["owner"] == owner}, {"Guys", "HH", "IOP"})

    def test_deterministic(self):
        audit = [{"subject": f"IXI{i:03d}", "modality": "T1", "site": ("Guys", "HH", "IOP")[i % 3],
                  "edge_contact_axes": "ax1_lo"} for i in range(40)]
        self.assertEqual(make_assignment.assign(audit, set()), make_assignment.assign(audit, set()))


class FlagTests(unittest.TestCase):
    def test_qform_decisions(self):
        self.assertEqual(batch.charm_flags(0.0, True), [])
        self.assertEqual(batch.charm_flags(3.5e-6, False), ["--forceqform"])
        self.assertIsNone(batch.charm_flags(0.5, False))

    def test_version_parse(self):
        self.assertEqual(batch.simnibs_version("[ simnibs ] INFO: simnibs version 4.6.0"), "4.6.0")
        self.assertIsNone(batch.simnibs_version("no version here"))


class RunTests(unittest.TestCase):
    def make_inputs(self, root, subject, shift=0.0):
        import nibabel as nib
        folder = root / "data" / subject
        folder.mkdir(parents=True)
        for modality in ("T1", "T2"):
            image = nib.Nifti1Image(np.zeros((4, 4, 4), np.float32), np.eye(4))
            if shift:
                q = np.eye(4); q[0, 3] = shift
                image.set_qform(q, code=1); image.set_sform(np.eye(4), code=1)
            nib.save(image, str(folder / f"{subject}-HH-0001-{modality}.nii.gz"))

    def write_assignment(self, root, subjects):
        path = root / "assignment.csv"
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["subject", "site", "cohort", "owner", "note"])
            w.writeheader()
            for s in subjects:
                w.writerow({"subject": s, "site": "HH", "cohort": "train", "owner": "K2", "note": ""})
            w.writerow({"subject": "IXI999", "site": "HH", "cohort": "test_face", "owner": "K1", "note": ""})
        return path

    def fake_charm(self, root):
        """A stand-in charm that writes the expected outputs and the version line."""
        script = root / "fake_charm.py"
        script.write_text(
            "import sys, pathlib\n"
            "print('[ simnibs ] INFO: simnibs version 4.6.0')\n"
            "m = pathlib.Path('m2m_' + sys.argv[1]); m.mkdir()\n"
            "for n in ('final_tissues.nii.gz','final_tissues_LUT.txt','charm_report.html','charm_log.html'):\n"
            "    (m / n).write_text(' '.join(sys.argv[2:]))\n")
        launcher = root / ("fake_charm.cmd" if batch.sys.platform == "win32" else "fake_charm.sh")
        if batch.sys.platform == "win32":
            launcher.write_text(f'@"{batch.sys.executable}" "{script}" %*\n')
        else:
            launcher.write_text(f'#!/bin/sh\n"{batch.sys.executable}" "{script}" "$@"\n')
            launcher.chmod(0o755)
        return str(launcher)

    def test_runs_owner_train_only_delivers_and_skips_when_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_inputs(root, "IXI100")
            self.make_inputs(root, "IXI101", shift=3.5e-6)
            assignment = self.write_assignment(root, ["IXI100", "IXI101"])
            args = ["--owner", "K2", "--data", str(root / "data"), "--out", str(root / "out"),
                    "--assignment", str(assignment), "--charm", self.fake_charm(root)]
            self.assertEqual(batch.main(args), 0)
            out = root / "out"
            self.assertFalse((out / "m2m_IXI999").exists())
            rec = json.loads((out / "runs" / "IXI101.json").read_text())
            self.assertTrue(rec["forceqform"] and rec["outputs_ok"])
            self.assertIn("--forceqform", (out / "m2m_IXI101" / "charm_report.html").read_text())
            sums = (out / "deliver_K2" / "IXI100" / "SHA256SUMS.txt").read_text()
            self.assertIn("final_tissues.nii.gz", sums)
            self.assertTrue((out / "qc_K2.csv").exists())
            self.assertEqual(batch.main(args), 0)  # second pass skips both
            self.assertFalse(any(out.glob("m2m_IXI100_attempt_*")))

    def test_large_qform_mismatch_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_inputs(root, "IXI100", shift=2.0)
            assignment = self.write_assignment(root, ["IXI100"])
            code = batch.main(["--owner", "K2", "--data", str(root / "data"), "--out", str(root / "out"),
                               "--assignment", str(assignment), "--charm", self.fake_charm(root)])
            self.assertEqual(code, 1)
            self.assertFalse((root / "out" / "m2m_IXI100").exists())


if __name__ == "__main__":
    unittest.main()
