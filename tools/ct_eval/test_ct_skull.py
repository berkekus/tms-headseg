import json
import tempfile
import unittest
from pathlib import Path

import nibabel as nib
import numpy as np

import ct_skull as cs

SHAPE = (60, 60, 60)


def head(shift=0, calcification=False, pad_rows=0):
    """CT with a spherical bone shell; MR with signal everywhere except `pad_rows` bottom slices of zeros."""
    grid = np.indices(SHAPE).astype(float)
    radius = np.sqrt(((grid - 30) ** 2).sum(axis=0))
    ct = np.full(SHAPE, -1000.0)
    ct[radius < 25] = 40.0
    ct[(radius >= 20) & (radius < 25)] = 1200.0
    if calcification:
        ct[29:31, 29:31, 29:31] = 900.0  # 8 voxels, far below 1 mL
    mr = np.where(radius < 25, 500.0, 3.0)
    mr[:, :, :pad_rows] = 0.0
    pred_radius = np.sqrt(((grid - 30 - np.array([shift, 0, 0])[:, None, None, None]) ** 2).sum(axis=0))
    labels = np.zeros(SHAPE, np.uint8)
    labels[pred_radius < 25] = 1
    labels[(pred_radius >= 20) & (pred_radius < 25)] = cs.SKULL
    labels[pred_radius < 20] = 4
    return ct, mr, labels


class CtSkullTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, **arrays):
        paths = {}
        for name, data in arrays.items():
            paths[name] = self.dir / f"{name}.nii.gz"
            nib.save(nib.Nifti1Image(data, np.eye(4)), str(paths[name]))
        return paths

    def test_identical_skull_scores_perfectly(self):
        ct, mr, labels = head()
        p = self.save(ct=ct, mr=mr, pred=labels)
        result = cs.evaluate(p["ct"], p["mr"], p["pred"])
        for part in ("calvaria", "field"):
            self.assertAlmostEqual(result[part]["dice"], 1.0)
            self.assertAlmostEqual(result[part]["assd_mm"], 0.0)

    def test_a_shifted_skull_has_a_distance_near_the_shift(self):
        ct, mr, labels = head(shift=2)
        p = self.save(ct=ct, mr=mr, pred=labels)
        field = cs.evaluate(p["ct"], p["mr"], p["pred"])["field"]
        self.assertLess(field["dice"], 0.9)
        self.assertGreater(field["assd_mm"], 0.5)
        self.assertLessEqual(field["hd95_mm"], 2.5)

    def test_small_calcifications_are_not_skull(self):
        ct, _, _ = head(calcification=True)
        bone = cs.ct_bone(ct, np.ones(3))
        self.assertFalse(bone[29:31, 29:31, 29:31].any())
        self.assertTrue(bone[30, 30, 52])

    def test_bone_without_mr_signal_is_not_scored(self):
        ct, mr, labels = head(pad_rows=15)
        labels[:, :, :15] = 0  # a model sees nothing there
        p = self.save(ct=ct, mr=mr, pred=labels)
        result = cs.evaluate(p["ct"], p["mr"], p["pred"])
        self.assertAlmostEqual(result["field"]["dice"], 1.0)

    def test_calvaria_is_the_top_slab(self):
        ct, _, _ = head()
        region = cs.calvaria(cs.ct_bone(ct, np.ones(3)), np.ones(3), depth_mm=10)
        top = 54  # radius 25 around 30: last bone slice
        self.assertTrue(region[:, :, top - 9:top + 1].all())
        self.assertFalse(region[:, :, :top - 9].any() or region[:, :, top + 1:].any())

    def test_charm_labels_and_grid_check(self):
        ct, mr, labels = head()
        charm = np.zeros(SHAPE, np.uint8)
        charm[labels == cs.SKULL] = 7  # compact bone
        charm[labels == 1] = 5
        p = self.save(ct=ct, mr=mr, pred=charm)
        self.assertAlmostEqual(cs.evaluate(p["ct"], p["mr"], p["pred"], charm=True)["field"]["dice"], 1.0)
        moved = self.dir / "moved.nii.gz"
        affine = np.eye(4)
        affine[0, 3] = 5
        nib.save(nib.Nifti1Image(labels, affine), str(moved))
        with self.assertRaises(ValueError):
            cs.evaluate(p["ct"], p["mr"], moved)

    def test_cli_writes_json(self):
        ct, mr, labels = head()
        p = self.save(ct=ct, mr=mr, pred=labels)
        out = self.dir / "r.json"
        cs.main(["--ct", str(p["ct"]), "--mr", str(p["mr"]), "--pred", str(p["pred"]), "--json", str(out)])
        self.assertEqual(json.loads(out.read_text())["threshold_hu"], cs.BONE_HU)


if __name__ == "__main__":
    unittest.main()
