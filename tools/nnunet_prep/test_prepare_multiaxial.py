import unittest

import numpy as np

import prepare_multiaxial as prep


def synthetic_subjects():
    clinical = {
        "GU": [f"GU{i:03d}" for i in range(28)],
        "NC": [f"NC{i:03d}" for i in range(22)],
        "NYU": [f"NYU{i:03d}" for i in range(10)],
    }
    return clinical, ["subj1", "subj2", "subj3", "subj4"]


class SplitTests(unittest.TestCase):
    def test_counts_and_stratification(self):
        clinical, healthy = synthetic_subjects()
        split = prep.make_split(clinical, healthy, seed=42)
        self.assertEqual(len(split), 64)
        counts = {s: list(split.values()).count(s) for s in ("train", "val", "test")}
        self.assertEqual(counts, {"train": 44, "val": 10, "test": 10})
        for center, ids in clinical.items():
            for name, expected in (("val", prep.VAL_PER_CENTER[center]),
                                   ("test", prep.TEST_PER_CENTER[center])):
                self.assertEqual(sum(split[i] == name for i in ids), expected)

    def test_healthy_subjects_only_in_test(self):
        clinical, healthy = synthetic_subjects()
        split = prep.make_split(clinical, healthy, seed=1)
        self.assertTrue(all(split[h] == "test" for h in healthy))

    def test_deterministic_per_seed(self):
        clinical, healthy = synthetic_subjects()
        self.assertEqual(prep.make_split(clinical, healthy, 42),
                         prep.make_split(clinical, healthy, 42))
        self.assertNotEqual(prep.make_split(clinical, healthy, 42),
                            prep.make_split(clinical, healthy, 7))


class LabelTests(unittest.TestCase):
    def test_mapping(self):
        source = np.array([0, 1, 2, 3, 4, 5, 6])  # release labels
        expected = np.array([0, 0, 4, 5, 3, 2, 1])
        np.testing.assert_array_equal(prep.remap_labels(source), expected)

    def test_unexpected_value_rejected(self):
        with self.assertRaises(ValueError):
            prep.remap_labels(np.array([0, 7]))


class AffineTests(unittest.TestCase):
    def test_orthonormal_affine_unchanged(self):
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        affine[:3, 3] = [-90, -126, -72]
        fixed, error = prep.orthonormalize(affine)
        np.testing.assert_array_equal(fixed, affine)
        self.assertLess(error, prep.SHEAR_TOLERANCE)

    def test_sheared_affine_becomes_orthonormal(self):
        affine = np.eye(4)
        affine[0, 1] = 0.3  # shear
        affine[:3, 3] = [5, 6, 7]
        fixed, error = prep.orthonormalize(affine)
        self.assertGreater(error, prep.SHEAR_TOLERANCE)
        linear = fixed[:3, :3]
        rotation = linear / np.linalg.norm(linear, axis=0)
        np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1e-9)
        np.testing.assert_allclose(np.linalg.norm(linear, axis=0),
                                   np.linalg.norm(affine[:3, :3], axis=0))
        np.testing.assert_array_equal(fixed[:3, 3], [5, 6, 7])


class WriteCaseTests(unittest.TestCase):
    def test_header_states_mm_and_coded_geometry(self):
        import tempfile
        from pathlib import Path
        import nibabel as nib

        sheared = np.eye(4)
        sheared[0, 1] = 0.2
        data = np.zeros((4, 5, 6), dtype=np.int16)
        labels = np.full((4, 5, 6), 6, dtype=np.uint8)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            nib.save(nib.Nifti1Image(data, sheared), str(tmp / "t1.nii"))
            nib.save(nib.Nifti1Image(labels, sheared), str(tmp / "lab.nii"))
            error, source_affine = prep.write_case(
                tmp / "t1.nii", tmp / "lab.nii", tmp / "out" / "img.nii.gz", tmp / "out" / "lab.nii.gz")
            for name in ("img.nii.gz", "lab.nii.gz"):
                header = nib.load(str(tmp / "out" / name)).header
                self.assertEqual(header.get_xyzt_units()[0], "mm")
                self.assertEqual(int(header["sform_code"]), 1)
                self.assertEqual(int(header["qform_code"]), 1)
            self.assertEqual(np.unique(np.asanyarray(nib.load(str(tmp / "out" / "lab.nii.gz")).dataobj)).tolist(), [1])
        self.assertGreater(error, prep.SHEAR_TOLERANCE)
        np.testing.assert_allclose(source_affine, sheared, atol=1e-6)  # header stores float32


if __name__ == "__main__":
    unittest.main()
