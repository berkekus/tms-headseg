import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import stage_open_datasets as stager

PAYLOAD = b"synthetic participants table"


def fake_record(files):
    return {
        "files": [
            {
                "key": name,
                "size": len(data),
                "checksum": "md5:" + hashlib.md5(data).hexdigest(),
                "links": {"self": f"https://example.invalid/{name}"},
            }
            for name, data in files.items()
        ]
    }


def fake_download(contents):
    def _download(url, target, expected_bytes):
        target.write_bytes(contents[target.name])
    return _download


class StageTests(unittest.TestCase):
    def setUp(self):
        spec = dict(stager.DATASETS["D14"], files=["participants.xlsx"], optional=[])
        self.patch_spec = mock.patch.dict(stager.DATASETS, {"T01": spec})
        self.patch_spec.start()
        self.addCleanup(self.patch_spec.stop)

    def test_stage_writes_manifest_and_guide(self):
        contents = {"participants.xlsx": PAYLOAD}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(stager, "fetch_record", return_value=fake_record(contents)), \
                mock.patch.object(stager, "download", side_effect=fake_download(contents)):
            folder = stager.stage("T01", Path(tmp), all_files=False)
            manifest = json.loads((folder / "kaynak_manifest.json").read_text(encoding="utf-8"))
            guide = (folder / "00_OKU_BENI.txt").read_text(encoding="utf-8")

        self.assertEqual(manifest["id"], "T01")
        self.assertEqual(manifest["files"][0]["sha256"], hashlib.sha256(PAYLOAD).hexdigest())
        self.assertEqual(manifest["files"][0]["bytes"], len(PAYLOAD))
        self.assertIn("LISANS NOTU: CC BY-NC 4.0", guide)

    def test_checksum_mismatch_stops(self):
        record = fake_record({"participants.xlsx": PAYLOAD})
        corrupted = {"participants.xlsx": b"x" * len(PAYLOAD)}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(stager, "fetch_record", return_value=record), \
                mock.patch.object(stager, "download", side_effect=fake_download(corrupted)):
            with self.assertRaises(SystemExit):
                stager.stage("T01", Path(tmp), all_files=False)

    def test_missing_file_in_record_stops(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(stager, "fetch_record", return_value=fake_record({})):
            with self.assertRaises(SystemExit):
                stager.stage("T01", Path(tmp), all_files=False)


if __name__ == "__main__":
    unittest.main()
