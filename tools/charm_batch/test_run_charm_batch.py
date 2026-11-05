import csv
import json
import tempfile
import subprocess
import sys
import time
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
    def test_only_one_real_batch_can_own_an_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(batch.batch_is_running(root))
            with batch.batch_lock(root):
                self.assertTrue(batch.batch_is_running(root))
                with self.assertRaises(RuntimeError):
                    with batch.batch_lock(root):
                        self.fail("Second batch acquired the same output folder")
            self.assertFalse(batch.batch_is_running(root))

    def test_running_record_is_visible_before_charm_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_inputs(root, "IXI100")
            assignment = self.write_assignment(root, ["IXI100"])
            charm = self.fake_charm(root)
            script = root / "fake_charm.py"
            script.write_text("import time\ntime.sleep(1.5)\n" + script.read_text())
            out = root / "out"
            process = subprocess.Popen([sys.executable, str(HERE / "run_charm_batch.py"), "--owner", "K2",
                "--data", str(root / "data"), "--out", str(out), "--assignment", str(assignment), "--charm", charm],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                record = out / "runs/IXI100.json"
                deadline = time.monotonic() + 5
                while not record.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(record.is_file(), "Active batch must publish a running record")
                self.assertEqual(json.loads(record.read_text())["state"], "running")
                self.assertIsNone(process.poll())
                self.assertEqual(process.wait(timeout=8), 0)
                self.assertEqual(json.loads(record.read_text())["state"], "completed")
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()

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
            launcher.write_text(f'@echo off\n"{batch.sys.executable}" -E -u "{script}" %*\n')
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

    def test_t1_only_multiaxial_layout(self):
        import nibabel as nib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            nib.save(nib.Nifti1Image(np.zeros((4, 4, 4), np.float32), np.eye(4)), str(root / "data" / "NC001_0000.nii.gz"))
            path = root / "assignment.csv"
            path.write_text("subject,site,cohort,owner,note\nNC001,NC,val,K1,\nNC002,NC,test,K1,\n")
            args = ["--owner", "K1", "--data", str(root / "data"), "--out", str(root / "out"), "--assignment", str(path),
                    "--charm", self.fake_charm(root), "--t1-only", "--cohort", "train,val"]
            self.assertEqual(batch.main(args), 0)
            rec = json.loads((root / "out" / "runs" / "NC001.json").read_text())
            self.assertTrue(rec["t1_only"] and rec["outputs_ok"])
            self.assertIsNone(rec["t2"])
            self.assertEqual(set(rec["input_sha256"]), {"t1"})
            self.assertFalse((root / "out" / "m2m_NC002").exists())
            self.assertEqual(batch.main(args), 0)  # resume verifies and skips

    def test_parts_cover_all_rows_without_overlap(self):
        rows = [{"subject": f"GU{i:03d}"} for i in range(11)]
        parts = [batch.select_part(rows, f"{k}/3") for k in (1, 2, 3)]
        names = [r["subject"] for p in parts for r in p]
        self.assertEqual(sorted(names), sorted(r["subject"] for r in rows))
        self.assertEqual(len(names), len(set(names)))

    def test_multiaxial_rows_exclude_test(self):
        manifest = [{"case_id": "GU001", "center": "GU", "split": "train"},
                    {"case_id": "GU002", "center": "GU", "split": "val"},
                    {"case_id": "GU003", "center": "GU", "split": "test"},
                    {"case_id": "subj1", "center": "healthy", "split": "test"}]
        rows = make_assignment.multiaxial_rows(manifest)
        self.assertEqual([r["subject"] for r in rows], ["GU001", "GU002"])
        with open(HERE / "multiaxial_assignment.csv", newline="") as f:
            committed = list(csv.DictReader(f))
        self.assertEqual(len(committed), 54)
        self.assertTrue(all(r["cohort"] in ("train", "val") for r in committed))

    def test_qc_sheet_keeps_rows_from_other_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "qc_K1.csv").write_text("subject,qc,notes\nIXI028,pass,ok\n")
            batch.ensure_qc_sheet(out, "K1", ["IXI111"])
            with open(out / "qc_K1.csv", newline="") as f:
                rows = {r["subject"]: r for r in csv.DictReader(f)}
            self.assertEqual(rows["IXI028"]["notes"], "ok")
            self.assertIn("IXI111", rows)

    def test_large_qform_mismatch_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_inputs(root, "IXI100", shift=2.0)
            assignment = self.write_assignment(root, ["IXI100"])
            code = batch.main(["--owner", "K2", "--data", str(root / "data"), "--out", str(root / "out"),
                               "--assignment", str(assignment), "--charm", self.fake_charm(root)])
            self.assertEqual(code, 1)
            self.assertFalse((root / "out" / "m2m_IXI100").exists())

    def test_accepted_qform_diff_runs_only_for_named_subject_and_below_cap(self):
        self.assertEqual(batch.charm_flags(1.2e-3, False, accepted=True), ["--forceqform"])
        self.assertIsNone(batch.charm_flags(1.2e-3, False))
        self.assertIsNone(batch.charm_flags(0.5, False, accepted=True))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_inputs(root, "IXI100", shift=1.2e-3)
            self.make_inputs(root, "IXI101", shift=1.2e-3)
            assignment = self.write_assignment(root, ["IXI100", "IXI101"])
            code = batch.main(["--owner", "K2", "--data", str(root / "data"), "--out", str(root / "out"),
                               "--assignment", str(assignment), "--charm", self.fake_charm(root),
                               "--accept-qform-diff", "IXI100"])
            self.assertEqual(code, 1)  # IXI101 not accepted, still skipped
            rec = json.loads((root / "out" / "runs" / "IXI100.json").read_text())
            self.assertTrue(rec["outputs_ok"] and rec["forceqform"])
            self.assertIn("qform_diff_accepted", rec)
            self.assertIn("skipped_reason", json.loads((root / "out" / "runs" / "IXI101.json").read_text()))

    def test_dry_run_rejects_large_qform_mismatch_without_writing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_inputs(root, "IXI100", shift=2.0)
            assignment = self.write_assignment(root, ["IXI100"])
            code = batch.main(["--owner", "K2", "--data", str(root / "data"), "--out", str(root / "out"),
                               "--assignment", str(assignment), "--charm", self.fake_charm(root), "--dry-run"])
            self.assertEqual(code, 1)
            self.assertFalse((root / "out" / "runs" / "IXI100.json").exists())
            self.assertFalse((root / "out" / "m2m_IXI100").exists())

    def test_resume_refuses_missing_or_changed_outputs_without_overwriting(self):
        for damage in ("missing", "changed"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.make_inputs(root, "IXI100")
                assignment = self.write_assignment(root, ["IXI100"])
                args = ["--owner", "K2", "--data", str(root / "data"), "--out", str(root / "out"),
                        "--assignment", str(assignment), "--charm", self.fake_charm(root)]
                self.assertEqual(batch.main(args), 0)
                record = root / "out" / "runs" / "IXI100.json"
                original_record = record.read_bytes()
                labels = root / "out" / "m2m_IXI100" / "final_tissues.nii.gz"
                if damage == "missing":
                    labels.unlink()
                else:
                    labels.write_text("damaged output")
                self.assertEqual(batch.main(args), 1)
                self.assertEqual(record.read_bytes(), original_record)
                self.assertFalse(any((root / "out").glob("m2m_IXI100_attempt_*")))

    def test_resume_refuses_changed_input(self):
        import nibabel as nib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_inputs(root, "IXI100")
            assignment = self.write_assignment(root, ["IXI100"])
            args = ["--owner", "K2", "--data", str(root / "data"), "--out", str(root / "out"),
                    "--assignment", str(assignment), "--charm", self.fake_charm(root)]
            self.assertEqual(batch.main(args), 0)
            t1 = next((root / "data" / "IXI100").glob("*-T1.nii.gz"))
            nib.save(nib.Nifti1Image(np.ones((4, 4, 4), np.float32), np.eye(4)), str(t1))
            self.assertEqual(batch.main(args), 1)
            self.assertFalse(any((root / "out").glob("m2m_IXI100_attempt_*")))

    def test_resume_restores_delivery_from_verified_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_inputs(root, "IXI100")
            assignment = self.write_assignment(root, ["IXI100"])
            args = ["--owner", "K2", "--data", str(root / "data"), "--out", str(root / "out"),
                    "--assignment", str(assignment), "--charm", self.fake_charm(root)]
            self.assertEqual(batch.main(args), 0)
            target = root / "out" / "deliver_K2" / "IXI100" / "final_tissues.nii.gz"
            target.unlink()
            self.assertEqual(batch.main(args), 0)
            self.assertTrue(target.is_file())
            self.assertEqual(target.read_bytes(), (root / "out" / "m2m_IXI100" / target.name).read_bytes())


if __name__ == "__main__":
    unittest.main()
