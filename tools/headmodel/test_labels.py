"""Label schemas: unexpected values must stop processing, never become background."""

import unittest

import numpy as np

from headmodel.labels import CHARM_TO_PROJECT, map_labels, validate_project_labels


class LabelTests(unittest.TestCase):
    def test_charm_labels_map_to_project_classes(self):
        charm = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], np.uint16)
        np.testing.assert_array_equal(map_labels(charm, CHARM_TO_PROJECT), [0, 5, 4, 3, 2, 1, 3, 2, 2, 3, 1, 1, 1])

    def test_charm_blood_is_csf_as_in_multiaxial(self):
        # MultiAxial labels intracranial blood (mostly dural sinuses) as CSF, not soft tissue.
        self.assertEqual(map_labels(np.array([9], np.uint16), CHARM_TO_PROJECT).tolist(), [3])

    def test_unmapped_source_label_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "500"):
            map_labels(np.array([0, 1, 500], np.uint16), CHARM_TO_PROJECT)

    def test_fractional_labels_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "integer"):
            map_labels(np.array([0., 1.5]), CHARM_TO_PROJECT)

    def test_project_labels_accept_the_schema_only(self):
        validate_project_labels(np.array([0, 1, 2, 3, 4, 5], np.uint8))
        with self.assertRaisesRegex(ValueError, "6"):
            validate_project_labels(np.array([0, 6], np.uint8))


if __name__ == "__main__":
    unittest.main()
