"""Files for the model must share one axis order and come back to the patient's grid exactly."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import nibabel as nib
import numpy as np

from headmodel.images import read_source, world_disagreement, write_nifti
from headmodel.model_io import prepare, restore_labels
from headmodel.phantom import phantom_labels
from headmodel.reversible import reorient

SCRIPT = Path(__file__).with_name("model_io.py")


def psr_affine(shape, spacing=4.):
    """Sagittal storage order as IXI and Ernie report it (PSR): i runs posterior, j superior, k right."""
    return np.array([[0, 0, spacing, -spacing * (shape[2] - 1) / 2],
                     [-spacing, 0, 0, spacing * (shape[0] - 1) / 2],
                     [0, spacing, 0, -spacing * (shape[1] - 1) / 2],
                     [0, 0, 0, 1]])


class ModelIoTests(unittest.TestCase):
    shape = (52, 50, 40)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.affine = psr_affine(self.shape)
        self.labels = phantom_labels(self.shape, self.affine)
        self.t1 = self.root / "t1.nii.gz"
        write_nifti(self.t1, (self.labels * 40 + 7).astype(np.int16), self.affine)
        self.labels_path = self.root / "labels.nii.gz"
        write_nifti(self.labels_path, self.labels, self.affine)

    def prepare(self, **options):
        out = {"out_image": self.root / "case_0000.nii.gz", "record_path": self.root / "case.geometry.json"}
        return prepare(self.t1, **out, **options), out

    def test_model_input_is_ras_and_labels_share_its_grid(self):
        _, out = self.prepare(labels=self.labels_path, out_labels=self.root / "case.nii.gz")
        image, labels = nib.load(out["out_image"]), nib.load(self.root / "case.nii.gz")
        self.assertEqual(nib.aff2axcodes(image.affine), ("R", "A", "S"))
        self.assertEqual(image.shape, labels.shape)
        np.testing.assert_array_equal(image.affine, labels.affine)
        self.assertEqual(labels.get_data_dtype(), np.uint8)
        # Same voxels, so the label of every image voxel is unchanged by the move.
        np.testing.assert_array_equal((np.asanyarray(image.dataobj) - 7) // 40, np.asanyarray(labels.dataobj))

    def test_restore_returns_labels_to_the_source_grid_exactly(self):
        _, out = self.prepare()
        prediction = self.root / "prediction.nii.gz"
        carrier = read_source(out["out_image"])
        write_nifti(prediction, ((carrier.data - 7) // 40).astype(np.uint8), carrier.affine)
        restored_path = self.root / "restored.nii.gz"
        restore_labels(prediction, out["record_path"], restored_path)
        restored = read_source(restored_path)
        np.testing.assert_array_equal(restored.data, self.labels)
        self.assertLess(world_disagreement(restored.affine, self.affine, self.shape), 1e-6)

    def test_record_says_where_the_input_came_from(self):
        record, out = self.prepare()
        saved = json.loads(out["record_path"].read_text(encoding="utf-8"))
        self.assertEqual(saved, record)
        self.assertEqual(saved["source"]["axes"], "PSR")
        self.assertEqual(saved["geometry"]["source_shape"], list(self.shape))
        self.assertEqual(len(saved["source"]["sha256"]), 64)

    def test_charm_labels_are_mapped_before_they_move(self):
        charm = np.where(self.labels == 3, 9, self.labels).astype(np.uint8)  # blood where CSF was
        charm_path = self.root / "charm.nii.gz"
        write_nifti(charm_path, charm, self.affine)
        self.prepare(labels=charm_path, out_labels=self.root / "case.nii.gz", label_scheme="charm")
        moved = np.asanyarray(nib.load(self.root / "case.nii.gz").dataobj)
        self.assertEqual(set(np.unique(moved)), {0, 1, 2, 3, 4, 5})
        self.assertNotIn(9, np.unique(moved))

    def test_labels_with_a_trailing_singleton_axis_are_accepted(self):
        path = self.root / "final_tissues.nii.gz"
        image = nib.Nifti1Image(self.labels[..., None], self.affine)
        image.set_qform(self.affine, code=1)
        image.header.set_xyzt_units("mm")
        nib.save(image, path)
        self.prepare(labels=path, out_labels=self.root / "case.nii.gz")
        self.assertEqual(nib.load(self.root / "case.nii.gz").ndim, 3)

    def test_labels_on_another_grid_are_rejected(self):
        shifted = self.affine.copy()
        shifted[:3, 3] += 2
        path = self.root / "shifted.nii.gz"
        write_nifti(path, self.labels, shifted)
        with self.assertRaisesRegex(ValueError, "grid"):
            self.prepare(labels=path, out_labels=self.root / "case.nii.gz")
        self.assertFalse((self.root / "case_0000.nii.gz").exists())

    def test_labels_outside_the_scheme_are_rejected(self):
        path = self.root / "odd.nii.gz"
        write_nifti(path, np.where(self.labels == 5, 7, self.labels).astype(np.uint8), self.affine)
        with self.assertRaisesRegex(ValueError, "7"):
            self.prepare(labels=path, out_labels=self.root / "case.nii.gz")

    def test_outputs_are_never_overwritten(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "exists"):
            self.prepare()

    def test_outputs_inside_a_git_checkout_are_refused(self):
        repository = self.root / "repo"
        (repository / ".git").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "Git"):
            prepare(self.t1, repository / "case_0000.nii.gz", repository / "case.geometry.json")

    def test_prediction_off_the_model_grid_is_rejected(self):
        _, out = self.prepare()
        carrier = read_source(out["out_image"])
        prediction = self.root / "prediction.nii.gz"
        write_nifti(prediction, np.zeros(carrier.data.shape[::-1], np.uint8), np.diag([4., 4., 4., 1.]))
        with self.assertRaisesRegex(ValueError, "model input grid"):
            restore_labels(prediction, out["record_path"], self.root / "restored.nii.gz")
        self.assertFalse((self.root / "restored.nii.gz").exists())

    def test_sheared_source_gets_its_own_affine_back(self):
        sheared = self.affine.copy()
        sheared[0, 1] = .3
        write_nifti(self.t1, (self.labels * 40 + 7).astype(np.int16), sheared)
        _, out = self.prepare()
        carrier = read_source(out["out_image"])
        prediction = self.root / "prediction.nii.gz"
        write_nifti(prediction, ((carrier.data - 7) // 40).astype(np.uint8), carrier.affine)
        restore_labels(prediction, out["record_path"], self.root / "restored.nii.gz")
        restored = nib.load(self.root / "restored.nii.gz")
        np.testing.assert_allclose(restored.get_sform(), sheared)
        self.assertEqual(int(restored.header["qform_code"]), 0)

    def test_reorient_follows_the_record_and_checks_the_grid(self):
        _, out = self.prepare()
        from headmodel.reversible import GeometryRecord
        record = GeometryRecord.from_json(json.loads(out["record_path"].read_text(encoding="utf-8"))["geometry"])
        moved = reorient(self.labels, record)
        np.testing.assert_array_equal(moved, (read_source(out["out_image"]).data - 7) // 40)
        with self.assertRaisesRegex(ValueError, "source grid"):
            reorient(self.labels[:-1], record)

    def test_command_line_round_trip(self):
        image, record = self.root / "cli_0000.nii.gz", self.root / "cli.geometry.json"
        run = lambda *args: subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                                           capture_output=True, text=True, check=True)
        run("prepare", self.t1, image, "--record", record)
        carrier = read_source(image)
        prediction = self.root / "cli_prediction.nii.gz"
        write_nifti(prediction, ((carrier.data - 7) // 40).astype(np.uint8), carrier.affine)
        run("restore", prediction, record, self.root / "cli_restored.nii.gz")
        np.testing.assert_array_equal(read_source(self.root / "cli_restored.nii.gz").data, self.labels)


if __name__ == "__main__":
    unittest.main()
