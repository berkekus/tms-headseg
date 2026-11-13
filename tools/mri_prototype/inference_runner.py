"""Use the reviewed segmentation CLI in an owned subprocess, without torch in Qt."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
from statistics import median
import sys
import time

import nibabel as nib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "charm_gui"))
from runner import Runner

DEMO = Path(__file__).resolve().parents[1] / "e1_training/demo.py"


def validate_model_files(python, model):
    if not python.is_file() or (sys.platform != "win32" and not os.access(python, os.X_OK)):
        raise ValueError("Choose the inference environment's Python executable (nnU-Net 2.8.1, torch 2.6.0).")
    if not DEMO.is_file():
        raise ValueError("Keep tools/e1_training beside the desktop prototype.")
    for name in ("plans.json", "dataset.json", "fold_0/checkpoint_final.pth"):
        if not (model / name).is_file():
            raise ValueError(f"Completed model is missing {name}.")


def validate_output_folder(output, model):
    if not output.is_dir() or not os.access(output, os.W_OK):
        raise ValueError("Choose an existing writable output folder.")
    output = output.resolve()
    if any((p / ".git").exists() for p in (output, *output.parents)):
        raise ValueError("Keep inference outputs outside Git.")
    if output.is_relative_to(model.resolve()):
        raise ValueError("Output must be outside the model folder.")


@dataclass(frozen=True)
class InferenceJob:
    python: Path
    model: Path
    mri: Path
    output: Path
    subject: str
    device: str = "cpu"
    tta: bool = False
    assume_mm: bool = False
    experiment: str = "E1"

    @property
    def run_dir(self):
        return self.output / self.subject

    @property
    def prediction(self):
        return self.run_dir / "prediction.nii.gz"

    @property
    def record_path(self):
        return self.output / f"{self.subject}.desktop.json"

    def command(self):
        return [str(self.python), "-u", str(DEMO), "predict", "--model", str(self.model),
                "--mri", str(self.mri), "--out", str(self.run_dir), "--device", self.device] + (
                    [] if self.tta else ["--disable-tta"]) + (
                    ["--experiment", "E2"] if self.experiment == "E2" else [])

    def validate(self):
        if self.experiment not in ("E1", "E2"):
            raise ValueError("Choose E1 or E2.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", self.subject):
            raise ValueError("Use a fresh run ID with letters, digits, underscores or hyphens.")
        if self.device not in ("cpu", "cuda"):
            raise ValueError("Choose CPU or CUDA.")
        validate_model_files(self.python, self.model)
        validate_output_folder(self.output, self.model)
        if os.path.lexists(self.run_dir) or os.path.lexists(self.record_path):
            raise ValueError("Run already exists; choose a fresh run ID.")
        if not self.mri.is_file() or not str(self.mri).lower().endswith((".nii", ".nii.gz")):
            raise ValueError("Select a source T1 MRI (.nii or .nii.gz).")
        image = nib.load(self.mri)
        if image.ndim != 3 or min(image.shape) < 2 or np.prod(image.shape) > 100_000_000:
            raise ValueError("Choose one bounded 3D T1 volume.")
        if (not np.isfinite(image.affine).all() or abs(np.linalg.det(image.affine[:3, :3])) < 1e-10
                or not any(int(image.header[k]) > 0 for k in ("qform_code", "sform_code"))):
            raise ValueError("MRI needs a finite coded spatial transform.")
        unit = image.header.get_xyzt_units()[0]
        if self.experiment == "E2" and unit != "mm":
            raise ValueError("E2 requires MRI headers with known millimetre units for reversible RAS preparation.")
        if unit == "unknown" and not self.assume_mm:
            raise ValueError("MRI units are unknown. Explicitly enable the handoff mm assumption to use this original E1 MRI.")
        if unit not in ("mm", "unknown"):
            raise ValueError("This initial inference workflow needs an independently prepared mm-space MRI copy.")


class InferenceRunner(Runner):
    log_prefix = "e1"
    math_threads = 4

    def __init__(self, job):
        super().__init__(job)
        self.recorded_finish = False
        self.cleaned_group = False

    def record(self, state):
        data = {"state": state, "mode": "inference", "experiment": self.job.experiment, "mri": str(self.job.mri), "model": str(self.job.model),
                "output": str(self.job.run_dir), "python": str(self.job.python), "device": self.job.device,
                "tta": self.job.tta, "unknown_units_assumed_mm": self.job.assume_mm,
                "math_threads": self.math_threads, "command": self.job.command(), "log": str(self.log_path),
                "updated_utc": datetime.now(timezone.utc).isoformat(), "exit_code": self.returncode,
                "elapsed_seconds": time.monotonic() - self.started_at if self.started_at else None}
        temporary = self.job.record_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2) + "\n")
        temporary.replace(self.job.record_path)

    def start(self):
        super().start()
        try:
            self.record("running")
        except OSError:
            self.close()
            raise

    def previous_elapsed(self):
        """Use prior completed desktop timings for the same source and run settings."""
        job = self.job
        roots = [job.output]
        if job.output.parent.name == ".workbench-users":
            roots.append(job.output.parent.parent)
        try:
            modified = max(path.stat().st_mtime_ns for path in
                           (job.mri, job.model / "fold_0/checkpoint_final.pth", job.model / "plans.json"))
            files = sorted((path for root in roots for path in root.glob(f"{job.experiment.lower()}_*.desktop.json")),
                           key=lambda path: path.name, reverse=True)[:32]
        except OSError:
            return None
        # Normalize aliases without resolving the executable symlink out of its venv.
        mri, model = job.mri.resolve(), job.model.resolve()
        python = job.python.parent.resolve() / job.python.name
        settings = {"state": "completed", "experiment": job.experiment, "device": job.device,
                    "tta": job.tta, "unknown_units_assumed_mm": job.assume_mm, "math_threads": self.math_threads}
        samples = []
        for file in files:
            try:
                stat = file.stat()
                if stat.st_mtime_ns < modified or stat.st_size > 32_768:
                    continue
                record = json.loads(file.read_text(encoding="utf-8"))
                if any(record.get(key) != value for key, value in settings.items()):
                    continue
                recorded_python = Path(record["python"])
                if (Path(record["mri"]).resolve() != mri
                        or Path(record["model"]).resolve() != model
                        or recorded_python.parent.resolve() / recorded_python.name != python):
                    continue
                seconds = record["elapsed_seconds"]
                if type(seconds) in (int, float) and 0 < seconds <= 7 * 86400:
                    samples.append(seconds)
                    if len(samples) == 3:
                        break
            except (OSError, AttributeError, KeyError, TypeError, ValueError):
                continue
        return median(samples) if samples else None

    @property
    def complete(self):
        if self.returncode != 0 or self.cancelled:
            return False
        try:
            status = self.job.run_dir / "status.json"
            return (status.stat().st_size < 1_000_000 and json.loads(status.read_text()).get("state") == "completed"
                    and self.job.prediction.is_file() and (self.job.run_dir / "report/report.html").is_file())
        except (OSError, ValueError, AttributeError):
            return False

    def poll(self):
        code = super().poll()
        if code is not None and not self.recorded_finish:
            self.recorded_finish = True
            self.record("cancelled" if self.cancelled else "completed" if self.complete else "failed")
        return code

    def close(self):
        active = self.process is not None and (self.process.poll() is None or self.cancel_deadline is not None)
        if active:
            self.cancelled = True
        if self.process is not None and not self.cleaned_group:
            self._signal_group(signal.SIGTERM if sys.platform == "win32" else signal.SIGKILL)
            self.cleaned_group = True
        super().close()
        if active and self.job.record_path.exists():
            self.record("cancelled")
