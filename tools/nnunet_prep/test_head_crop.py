import unittest

import nibabel as nib
import numpy as np

import head_crop as hc


def body(shape=(200, 200, 400), spacing=(1.0, 1.0, 1.0), shoulders=True, marker=True, seed=0):
    """RAS volume in mm: a head, a neck below it, optional wide shoulders and a separate bright marker."""
    rng = np.random.default_rng(seed)
    x, y, z = np.meshgrid(*[np.arange(n) * s for n, s in zip(shape, spacing)], indexing="ij")
    head = ((x - 100) / 70) ** 2 + ((y - 100) / 85) ** 2 + ((z - 300) / 95) ** 2 <= 1  # top at z = 395 mm
    neck = ((x - 100) ** 2 + (y - 100) ** 2 <= 40 ** 2) & (z >= 100) & (z <= 230)
    tissue = head | neck
    if shoulders:
        tissue |= (z < 120) & (x >= 5) & (x <= 195) & (y >= 60) & (y <= 140)
    data = np.abs(rng.normal(0, 5, shape))
    data[tissue] = rng.normal(400, 40, int(tissue.sum()))
    if marker:  # separate and higher than the vertex, so it must not set the top
        data[(x < 10) & (y < 10) & (z >= 388)] = 900
    return data.astype(np.float32), head


class HeadBoxTest(unittest.TestCase):
    def test_keeps_the_head_and_drops_the_shoulders(self):
        data, head = body()
        box = hc.head_box(data, (1, 1, 1))
        z0, z1 = box[2].start, box[2].stop
        self.assertGreaterEqual(z0, 120, "shoulders must fall below the crop")
        self.assertLessEqual(abs(z0 - (395 - hc.HEAD_HEIGHT_MM)), 3)
        self.assertEqual(z1, 400)
        self.assertEqual(int(head[box].sum()), int(head.sum()), "the whole head must stay inside")
        self.assertLessEqual(abs(box[0].start - (30 - hc.SIDE_MARGIN_MM)), 3)
        self.assertLessEqual(abs(box[0].stop - (171 + hc.SIDE_MARGIN_MM)), 3)

    def test_head_only_field_of_view_loses_no_head(self):
        data, head = body(shape=(200, 200, 400), shoulders=False, marker=False)
        data = data[:, :, 200:]
        head = head[:, :, 200:]
        box = hc.head_box(data, (1, 1, 1))
        self.assertEqual(int(head[box].sum()), int(head.sum()))
        self.assertEqual((box[2].start, box[2].stop), (0, 200))

    def test_margins_are_in_millimetres_on_anisotropic_grids(self):
        data, head = body(shape=(200, 200, 200), spacing=(1.0, 1.0, 2.0))
        box = hc.head_box(data, (1, 1, 2))
        self.assertEqual(int(head[box].sum()), int(head.sum()))
        self.assertLessEqual(abs(box[2].start - (395 - hc.HEAD_HEIGHT_MM) / 2), 2)

    def test_empty_image_is_rejected(self):
        with self.assertRaises(ValueError):
            hc.head_box(np.zeros((50, 50, 50), np.float32), (1, 1, 1))


class NiftiCropTest(unittest.TestCase):
    def test_crop_keeps_world_positions_and_paste_restores_the_grid(self):
        data, _ = body()
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        affine[:3, 3] = (-100, -120, -300)
        img = nib.Nifti1Image(data, affine)
        cropped, box = hc.crop_head(img)
        i, j, k = 50, 60, 250
        world = img.affine @ (i, j, k, 1)
        local = np.linalg.inv(cropped.affine) @ world
        np.testing.assert_allclose(local[:3], (i - box[0].start, j - box[1].start, k - box[2].start))
        self.assertEqual(float(np.asarray(cropped.dataobj)[tuple(local[:3].astype(int))]), float(data[i, j, k]))

        labels = (np.asarray(cropped.dataobj) > 200).astype(np.uint8)
        full = hc.paste(labels, img.shape, box)
        self.assertEqual(full.shape, img.shape)
        np.testing.assert_array_equal(full[box], labels)
        self.assertEqual(int(full.sum()), int(labels.sum()))

    def test_file_round_trip_restores_the_full_grid(self):
        import tempfile
        from pathlib import Path
        data, _ = body()
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        affine[:3, 3] = (-100, -120, -300)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            nib.save(nib.Nifti1Image(data, affine), tmp / "full.nii.gz")
            record = hc.crop_file(tmp / "full.nii.gz", tmp / "head.nii.gz")
            head = nib.load(tmp / "head.nii.gz")
            self.assertEqual(list(head.shape), record["cropped_shape"])
            self.assertEqual(head.header.get_xyzt_units()[0], "mm")
            labels = (np.asarray(head.dataobj) > 200).astype(np.uint8)
            nib.save(nib.Nifti1Image(labels, head.affine), tmp / "pred_head.nii.gz")
            restored = hc.paste_file(tmp / "pred_head.nii.gz", tmp / "full.nii.gz", record, tmp / "pred.nii.gz")
            saved = nib.load(tmp / "pred.nii.gz")
            np.testing.assert_allclose(saved.affine, affine)
            self.assertEqual(saved.shape, data.shape)
            self.assertEqual(int(restored.sum()), int(labels.sum()))
            moved = head.affine.copy()
            moved[0, 3] += 5  # a prediction 5 mm off the cropped grid must not be pasted
            nib.save(nib.Nifti1Image(labels, moved), tmp / "moved.nii.gz")
            with self.assertRaises(ValueError):
                hc.paste_file(tmp / "moved.nii.gz", tmp / "full.nii.gz", record, tmp / "bad.nii.gz")

    def test_non_ras_input_is_rejected(self):
        data, _ = body(shape=(60, 60, 60), shoulders=False, marker=False)
        flipped = np.diag([-1.0, 1.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            hc.crop_head(nib.Nifti1Image(data, flipped))


if __name__ == "__main__":
    unittest.main()
