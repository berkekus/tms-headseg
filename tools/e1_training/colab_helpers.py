"""Small reusable Colab helpers; importing this module never starts training."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import stat
import subprocess
import tempfile
import time
import zipfile

DATASET = "Dataset001_MultiAxial"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gpu_probe():
    import importlib.metadata
    import torch
    require(importlib.metadata.version("nnunetv2") == "2.8.1", "Expected nnU-Net 2.8.1.")
    require(torch.__version__.split("+")[0] == "2.6.0" and torch.version.cuda == "12.4", "Expected torch 2.6.0 / CUDA 12.4.")
    require(torch.cuda.is_available(), "Choose a GPU runtime in Colab; CUDA is unavailable.")
    props = torch.cuda.get_device_properties(0)
    require(props.total_memory >= 12 * 1024**3, "This handoff requests a GPU with at least 12 GB VRAM.")
    layer = torch.nn.Conv3d(1, 2, 3).cuda()
    value = torch.randn(1, 1, 12, 12, 12, device="cuda")
    with torch.autocast("cuda"):
        result = layer(value).square().mean()
    result.backward()
    torch.cuda.synchronize()
    del layer, value, result
    torch.cuda.empty_cache()
    return {"gpu": props.name, "vram_gib": props.total_memory / 1024**3,
            "torch": torch.__version__, "cuda": torch.version.cuda,
            "nnunetv2": importlib.metadata.version("nnunetv2"), "conv3d_backward_passed": True}


def pack_handoff(root, report, destination):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    require(not destination.exists(), "Archive already exists; choose a new output filename.")
    require(not any((parent / ".git").exists() for parent in destination.parents), "Keep MRI archives outside Git.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"files": report["files"], "dataset_sha256": report["dataset_sha256"]}
    partial = destination.with_suffix(destination.suffix + ".partial")
    try:
        with zipfile.ZipFile(partial, "x", compression=zipfile.ZIP_STORED) as archive:
            for relative, digest in sorted(manifest["files"].items()):
                source = root / relative
                require(sha256(source) == digest, f"Input changed after audit: {relative}")
                archive.write(source, relative)
            archive.writestr("expected_files.json", json.dumps(manifest, indent=2) + "\n")
        partial.rename(destination)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return sha256(destination)


def extract_handoff(archive_path, destination):
    archive_path, destination = Path(archive_path), Path(destination).resolve()
    archive_digest = sha256(archive_path)
    marker = destination / ".archive_sha256"
    if destination.exists():
        require(marker.is_file() and marker.read_text().strip() == archive_digest,
                "Existing extraction belongs to another archive. Choose a fresh destination.")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "Archive has duplicate paths.")
        require("expected_files.json" in names and archive.getinfo("expected_files.json").file_size < 2_000_000,
                "Use the prepared handoff_k2_e1.zip with its checksum manifest.")
        manifest = json.loads(archive.read("expected_files.json"))
        expected = manifest["files"]
        require(set(names) == set(expected) | {"expected_files.json"}, "Archive contains unexpected or missing entries.")
        require(sum(info.file_size for info in archive.infolist()) <= 20_000_000_000, "Archive is too large.")
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in info.filename,
                    "Unsafe archive path.")
            require(not stat.S_ISLNK(info.external_attr >> 16) and not info.is_dir(), "Archive links/directories are not supported.")
            allowed = (info.filename in ("splits_final.json", "expected_files.json", f"nnUNet_raw/{DATASET}/dataset.json")
                       or (path.parent.as_posix() in (f"nnUNet_raw/{DATASET}/imagesTr", f"nnUNet_raw/{DATASET}/labelsTr")
                           and path.name.endswith(".nii.gz")))
            require(allowed, "Archive contains files outside the E1 dataset.")
        with tempfile.TemporaryDirectory(prefix="e1-extract-", dir=destination.parent) as folder:
            temporary = Path(folder)
            for info in archive.infolist():
                output = temporary / info.filename
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, output.open("xb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                if info.filename in expected:
                    require(sha256(output) == expected[info.filename], f"Archive checksum mismatch: {info.filename}")
            (temporary / ".archive_sha256").write_text(archive_digest + "\n")
            temporary.rename(destination)
    return destination


def verify_manifest(root, report):
    manifest = json.loads((Path(root) / "expected_files.json").read_text())
    require(report["files"] == manifest["files"] and report["dataset_sha256"] == manifest["dataset_sha256"],
            "Extracted data differs from the audited handoff manifest.")


def install_split(root, preprocessed):
    source = Path(root) / "splits_final.json"
    target = Path(preprocessed) / DATASET / "splits_final.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        require(json.loads(target.read_text()) == json.loads(source.read_text()), "Existing split differs; refusing to overwrite it.")
    else:
        shutil.copyfile(source, target)
    return sha256(target)


def training_command(executable, trainer, fold_directory, resume=False):
    require(trainer in ("nnUNetTrainer_E1Smoke", "nnUNetTrainer_E1Preliminary"), "Unexpected E1 trainer.")
    folder = Path(fold_directory)
    if resume:
        checkpoints = [folder / f"checkpoint_{name}.pth" for name in ("final", "latest", "best")]
        checkpoint = next((path for path in checkpoints if path.is_file()), None)
        require(checkpoint is not None, "Resume requested but no checkpoint exists; refusing to silently restart.")
        require(not (folder / "validation/summary.json").is_file(), "Run already has completed validation; inspect results or use a new experiment ID.")
        require(zipfile.is_zipfile(checkpoint), "Checkpoint is incomplete or uses an unexpected format.")
        with zipfile.ZipFile(checkpoint) as archive:
            require(archive.testzip() is None, "Checkpoint archive failed its integrity check.")
    else:
        require(not folder.exists(), "Run directory exists. Use resume or a new experiment ID; no overwrite allowed.")
    return [str(executable), "1", "3d_fullres", "0", "-tr", trainer, "-device", "cuda"] + (["--c"] if resume else [])


def record_run(path, contract):
    path = Path(path)
    if path.exists():
        require(json.loads(path.read_text()) == contract, "Experiment contract changed; use a new experiment ID.")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(contract, indent=2) + "\n")


def run_logged(command, log_path, env=None):
    """Tail a durable log; stop owned process group when the notebook is interrupted."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    child_env = dict(os.environ if env is None else env)
    child_env["PYTHONUNBUFFERED"] = "1"
    with log_path.open("x", buffering=1) as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, env=child_env, start_new_session=True)
        try:
            with log_path.open(errors="replace") as reader:
                while True:
                    text = reader.read()
                    if text:
                        print(text, end="", flush=True)
                    code = process.poll()
                    if code is not None:
                        print(reader.read(), end="", flush=True)
                        if code != 0:
                            raise subprocess.CalledProcessError(code, command)
                        return {"elapsed_seconds": time.monotonic() - started, "exit_code": code}
                    time.sleep(.3)
        finally:
            # Colab is Linux; group ownership prevents orphaned augmentation workers.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            if process.poll() is None:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
