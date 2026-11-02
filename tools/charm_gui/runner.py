"""Fresh CHARM jobs on Windows and macOS with owned process trees and local logs."""

import codecs
from dataclasses import dataclass
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

from installation import command_prefix, external_environment


@dataclass(frozen=True)
class Job:
    charm: Path
    t1: Path
    t2: Path | None
    output: Path
    subject: str

    @property
    def model_dir(self):
        return self.output / f"m2m_{self.subject}"

    def command(self):
        return command_prefix(self.charm) + [self.subject, str(self.t1)] + (
            [str(self.t2)] if self.t2 else [])

    def validate(self):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", self.subject):
            raise ValueError("Subject ID: use 1–64 letters, numbers, underscores or hyphens; start with a letter or number.")
        if (not self.charm.is_file()
                or (sys.platform != "win32" and not os.access(self.charm, os.X_OK))):
            raise ValueError("Select charm (macOS) or charm.cmd (Windows) inside your SimNIBS bin folder.")
        self.command()
        for label, image in (("T1", self.t1), ("T2", self.t2)):
            if image is not None and (not image.is_file() or not os.access(image, os.R_OK)
                                      or not str(image).lower().endswith((".nii", ".nii.gz"))):
                raise ValueError(f"{label}: select a readable .nii or .nii.gz file.")
        if not self.output.is_dir() or not os.access(self.output, os.W_OK):
            raise ValueError("Choose an existing, writable output folder.")
        output = self.output.resolve()
        if any((parent / ".git").exists() for parent in (output, *output.parents)):
            raise ValueError("Choose an output folder outside any Git checkout to keep MRI data and generated files out of the repository.")
        if os.path.lexists(self.model_dir):
            raise ValueError(f"{self.model_dir.name} already exists. Choose a new subject ID; existing models are never overwritten.")


class Runner:
    def __init__(self, job):
        self.job = job
        self.process = None
        self.returncode = None
        self.cancelled = False
        self.cancel_deadline = None
        self.started_at = None
        self.log_path = None
        self.log = None
        self.reader = None
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    def start(self):
        if self.process is not None:
            raise ValueError("This job has already started.")
        self.job.validate()
        stamp = time.time_ns()
        self.log_path = self.job.output / f"charm.{self.job.subject}.{stamp}.launcher.log"
        self.log = self.log_path.open("xb", buffering=0)
        try:
            self.reader = self.log_path.open("rb", buffering=0)
            if sys.platform == "win32":
                try:
                    from windows_process import WindowsProcess
                except ImportError as error:
                    raise OSError("Windows process support is missing. Install requirements.txt in the launcher environment.") from error
                self.process = WindowsProcess(self.job.command(), self.job.output, self.log)
            else:
                self.process = subprocess.Popen(
                    self.job.command(), cwd=self.job.output,
                    stdout=self.log, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, start_new_session=True,
                    env=external_environment(),
                )
        except Exception:
            self.close()
            raise
        self.started_at = time.monotonic()

    def read_output(self):
        if self.process is None or self.reader is None or self.reader.closed:
            return ""
        # Tailing a regular file avoids platform-specific pipe modes and reader threads.
        return self.decoder.decode(self.reader.read(1024 * 1024))

    def _signal_group(self, sig):
        if self.process:
            if sys.platform == "win32":
                self.process.kill()
                return
            try:
                os.killpg(self.process.pid, sig)
            except ProcessLookupError:
                pass

    def cancel(self):
        if self.process is None or self.cancelled:
            return
        self.cancelled = True
        self._signal_group(signal.SIGTERM)
        if sys.platform != "win32":
            self.cancel_deadline = time.monotonic() + 2

    def poll(self):
        if self.process is None:
            return None
        code = self.process.poll()
        # Keep the group alive in our bookkeeping until resistant children are killed,
        # even when the immediate CHARM parent already exited after SIGTERM.
        if self.cancel_deadline is not None:
            if time.monotonic() < self.cancel_deadline:
                return None
            self._signal_group(signal.SIGKILL)
            self.cancel_deadline = None
            code = self.process.poll()
        if (code is not None and self.reader and not self.reader.closed
                and self.reader.tell() < self.log_path.stat().st_size):
            return None
        self.returncode = code
        return code

    @property
    def complete(self):
        return (self.returncode == 0 and not self.cancelled
                and (self.job.model_dir / f"{self.job.subject}.msh").is_file()
                and (self.job.model_dir / "final_tissues.nii.gz").is_file())

    def close(self):
        if self.process:
            if sys.platform == "win32":
                self.process.close()
            else:
                if self.process.poll() is None or self.cancel_deadline is not None:
                    self._signal_group(signal.SIGKILL)
                self.process.wait()
        if self.reader:
            self.reader.close()
        if self.log:
            self.log.close()
