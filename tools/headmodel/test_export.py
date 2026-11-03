"""Written surfaces are read back by an independent parser and checked against the labels."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import warnings

import meshio
import numpy as np

from headmodel.build_model import build_model
from headmodel.cleanup import ENVELOPE_SEAL_MM
from headmodel.export import read_stl_header, write_ply, write_stl
from headmodel.frames import voxel_to_world
from headmodel.images import write_nifti
from headmodel.phantom import phantom_labels
from headmodel.surfaces import Mesh, extract_surface
from headmodel.verify_model import verify_model


def psr_affine(shape, spacing=3.):
    """Sagittal storage order, as in IXI and Ernie: i runs posterior, j inferior, k right."""
    return np.array([[0, 0, spacing, -spacing * (shape[2] - 1) / 2],
                     [-spacing, 0, 0, spacing * (shape[0] - 1) / 2],
                     [0, -spacing, 0, spacing * (shape[1] - 1) / 2],
                     [0, 0, 0, 1]])


def sphere_mesh():
    shape = (31, 31, 31)
    affine = np.diag([2., 2., 2., 1.])
    affine[:3, 3] = (-30, -30, -30)
    points = voxel_to_world(affine, np.indices(shape).reshape(3, -1).T)
    return extract_surface((np.linalg.norm(points, axis=1) <= 20).reshape(shape), affine)


class SurfaceFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mesh = sphere_mesh()

    def assert_same_triangles(self, loaded):
        np.testing.assert_allclose(loaded.points[loaded.cells_dict["triangle"]],
                                   self.mesh.vertices[self.mesh.faces], atol=1e-3)

    def test_stl_declares_its_frame_and_round_trips(self):
        path = self.root / "surface.stl"
        write_stl(path, self.mesh)
        self.assertIn("SPACE=RAS", read_stl_header(path))
        self.assertIn("UNITS=mm", read_stl_header(path))
        self.assert_same_triangles(meshio.read(path))

    def test_stl_stores_outward_facet_normals(self):
        path = self.root / "surface.stl"
        write_stl(path, self.mesh)
        record = np.dtype([("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
        facets = np.fromfile(path, record, offset=84)
        self.assertEqual(len(facets), len(self.mesh.faces))
        self.assertTrue(((facets["normal"] * facets["vertices"].mean(axis=1)).sum(axis=1) > 0).all())

    def test_ply_declares_its_frame_and_round_trips(self):
        path = self.root / "surface.ply"
        write_ply(path, self.mesh)
        header = path.read_bytes().split(b"end_header")[0]
        self.assertIn(b"comment SPACE=RAS", header)
        self.assertIn(b"format binary_little_endian", header)
        self.assert_same_triangles(meshio.read(path))


class BuildModelTests(unittest.TestCase):
    shape = (71, 65, 61)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.affine = psr_affine(self.shape)
        self.labels = phantom_labels(self.shape, self.affine)
        self.t1 = self.root / "T1.nii.gz"
        self.segmentation = self.root / "segmentation.nii.gz"
        write_nifti(self.t1, self.labels.astype(np.float32) * 100, self.affine)
        write_nifti(self.segmentation, self.labels, self.affine)
        self.out = self.root / "output" / "case"

    def build(self, **options):
        return build_model(self.t1, self.segmentation, self.out, **options)

    def metadata(self):
        return json.loads((self.out / "model.json").read_text(encoding="utf-8"))

    def test_output_folder_holds_labels_surfaces_and_metadata(self):
        self.build()
        self.assertEqual(sorted(path.name for path in self.out.iterdir()),
                         ["brain.stl", "head.stl", "labels.nii.gz", "model.json", "reference.nii.gz"])

    def test_reference_copy_is_byte_identical(self):
        self.build()
        self.assertEqual((self.out / "reference.nii.gz").read_bytes(), self.t1.read_bytes())
        self.assertEqual(self.metadata()["reference_image"]["copy"], "reference.nii.gz")

    def test_metadata_names_frame_units_and_reference_identity(self):
        self.build()
        model = self.metadata()
        self.assertEqual((model["frame"]["name"], model["frame"]["units"]), ("RAS", "mm"))
        reference = model["reference_image"]
        self.assertEqual(reference["sha256"], hashlib.sha256(self.t1.read_bytes()).hexdigest())
        self.assertEqual(reference["axes"], "PIR")
        self.assertEqual(reference["shape"], list(self.shape))
        np.testing.assert_allclose(reference["affine"], self.affine)
        self.assertEqual(model["labels"]["values"]["1"], "skin")

    def test_metadata_describes_each_surface(self):
        self.build()
        head = self.metadata()["surfaces"]["head"]
        path = self.out / head["file"]
        self.assertEqual(head["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertTrue(head["closed"])
        self.assertEqual(head["triangles"], len(meshio.read(path).cells_dict["triangle"]))
        self.assertLess(head["bounds_mm"]["min"][0], -74)
        self.assertLess(head["bounds_mm"]["max"][0], 74)

    def test_face_coverage_is_never_implied(self):
        self.build()
        self.assertEqual(self.metadata()["coverage"]["face"], "not_assessed")

    def test_head_at_the_image_edge_is_reported(self):
        cut = self.labels.copy()
        write_nifti(self.segmentation, cut[:, :, 9:], self.affine)
        write_nifti(self.t1, cut[:, :, 9:].astype(np.float32), self.affine)
        self.build()
        model = self.metadata()
        self.assertIn("L", model["coverage"]["head_touches_image_edge"])
        self.assertTrue(any("image edge" in warning for warning in model["warnings"]))

    def test_airway_sealing_is_recorded_and_verified(self):
        """A 12 mm channel into an air pocket: sealed at 8 mm, its plug sits 6 mm from the walls."""
        points = voxel_to_world(self.affine, np.indices(self.shape).reshape(3, -1).T)
        pocket = np.linalg.norm(points - (0, 70, -10), axis=1) < 12
        channel = ((points[:, 0] > -4.5) & (points[:, 0] < 7.5) & (points[:, 2] > -16.5)
                   & (points[:, 2] < -4.5) & (points[:, 1] > 70))
        airway = self.labels.copy()
        airway[(pocket | channel).reshape(self.shape)] = 0
        write_nifti(self.segmentation, airway, self.affine)
        write_nifti(self.t1, airway.astype(np.float32), self.affine)
        self.build()
        self.assertEqual(self.metadata()["cleanup"]["settings"]["envelope_seal_mm"], ENVELOPE_SEAL_MM)
        self.assertEqual(verify_model(self.out), [])

    def test_ply_format_is_available(self):
        self.build(surface_format="ply")
        self.assertTrue((self.out / "head.ply").is_file())
        self.assertEqual(verify_model(self.out), [])

    def test_charm_labels_use_the_named_mapping(self):
        charm = np.choose(self.labels, [0, 5, 7, 3, 2, 1]).astype(np.uint16)
        write_nifti(self.segmentation, charm, self.affine)
        self.build(label_scheme="charm")
        model = self.metadata()
        self.assertEqual(model["labels"]["source_scheme"], "charm")
        self.assertIn("not accepted", model["labels"]["mapping_state"])
        self.assertEqual(verify_model(self.out), [])

    def test_labels_on_another_grid_are_rejected(self):
        moved = self.affine.copy()
        moved[:3, 3] += 5
        write_nifti(self.segmentation, self.labels, moved)
        with self.assertRaisesRegex(ValueError, "grid"):
            self.build()
        self.assertFalse(self.out.exists())

    def test_existing_output_is_never_overwritten(self):
        self.build()
        with self.assertRaisesRegex(ValueError, "exists"):
            self.build()

    def test_output_inside_a_git_checkout_is_rejected(self):
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(ValueError, "Git"):
            self.build()

    def test_warnings_from_the_reference_reach_the_metadata(self):
        sheared = self.affine.copy()
        sheared[0, 1] = .3
        write_nifti(self.t1, self.labels.astype(np.float32), sheared)
        write_nifti(self.segmentation, self.labels, sheared)
        self.build()
        self.assertTrue(any("shear" in warning for warning in self.metadata()["warnings"]))
        self.assertEqual(verify_model(self.out), [])


class VerifyTests(unittest.TestCase):
    shape = (71, 65, 61)

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        root = Path(cls.temp.name)
        affine = psr_affine(cls.shape)
        labels = phantom_labels(cls.shape, affine)
        write_nifti(root / "T1.nii.gz", labels.astype(np.float32), affine)
        write_nifti(root / "segmentation.nii.gz", labels, affine)
        cls.source = root / "source"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            build_model(root / "T1.nii.gz", root / "segmentation.nii.gz", cls.source)

    def tampered(self, name, change):
        """A consistent forgery: the changed surface also gets a matching checksum."""
        folder = Path(self.temp.name) / name
        folder.mkdir()
        for path in self.source.iterdir():
            (folder / path.name).write_bytes(path.read_bytes())
        loaded = meshio.read(folder / "head.stl")
        write_stl(folder / "head.stl", Mesh(change(loaded.points), loaded.cells_dict["triangle"]))
        model = json.loads((folder / "model.json").read_text(encoding="utf-8"))
        model["surfaces"]["head"]["sha256"] = hashlib.sha256((folder / "head.stl").read_bytes()).hexdigest()
        (folder / "model.json").write_text(json.dumps(model), encoding="utf-8")
        return folder

    def test_good_export_passes(self):
        self.assertEqual(verify_model(self.source), [])

    def test_mirrored_surface_fails(self):
        folder = self.tampered("mirrored", lambda points: points * [-1, 1, 1])
        self.assertTrue(any("label boundary" in failure for failure in verify_model(folder)))

    def test_lps_surface_written_as_ras_fails(self):
        folder = self.tampered("lps", lambda points: points * [-1, -1, 1])
        self.assertTrue(any("label boundary" in failure for failure in verify_model(folder)))

    def test_surface_with_spacing_applied_twice_fails(self):
        folder = self.tampered("scaled", lambda points: points * 3)
        self.assertTrue(any("label boundary" in failure for failure in verify_model(folder)))

    def test_changed_file_fails_the_checksum(self):
        folder = Path(self.temp.name) / "changed"
        folder.mkdir()
        for path in self.source.iterdir():
            (folder / path.name).write_bytes(path.read_bytes())
        with (folder / "brain.stl").open("ab") as file:
            file.write(b"\0")
        self.assertTrue(any("checksum" in failure for failure in verify_model(folder)))

    def test_changed_reference_fails_the_checksum(self):
        folder = Path(self.temp.name) / "other_reference"
        folder.mkdir()
        for path in self.source.iterdir():
            (folder / path.name).write_bytes(path.read_bytes())
        with (folder / "reference.nii.gz").open("ab") as file:
            file.write(b"\0")
        self.assertTrue(any("reference.nii.gz" in failure for failure in verify_model(folder)))

    def test_surface_without_a_declared_frame_fails(self):
        folder = self.tampered("unlabeled", lambda points: points)
        path = folder / "head.stl"
        data = bytearray(path.read_bytes())
        data[:80] = b" " * 80
        path.write_bytes(bytes(data))
        model = json.loads((folder / "model.json").read_text(encoding="utf-8"))
        model["surfaces"]["head"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (folder / "model.json").write_text(json.dumps(model), encoding="utf-8")
        self.assertTrue(any("frame" in failure for failure in verify_model(folder)))


if __name__ == "__main__":
    unittest.main()
