"""Shared batch CLI adapter and bounded, read-only desktop status snapshots."""

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import signal
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / "charm_batch"))
sys.path.insert(0, str(TOOLS / "charm_gui"))
import run_charm_batch as batch
from runner import Runner
from installation import command_prefix

BATCH = TOOLS / "charm_batch/run_charm_batch.py"
ASSIGNMENT = TOOLS / "charm_batch/ixi_assignment.csv"


def training_rows(owner):
    if owner not in ("K1", "K2"):
        raise ValueError("Choose K1 or K2.")
    rows = [r for r in batch.load_assignment(ASSIGNMENT, owner) if r["cohort"] == "train"]
    if not rows or any(not re.fullmatch(r"IXI\d{3}", r["subject"]) for r in rows):
        raise ValueError("Training assignment is empty or contains invalid subject IDs.")
    return rows


def read_record(path):
    try:
        if path.stat().st_size > 1_000_000:
            return {}
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def untracked_runs(output):
    candidates = {p.name.removeprefix("m2m_") for p in output.glob("m2m_IXI*")}
    candidates.update(p.stem for p in (output / "logs").glob("IXI*.log"))
    return sorted(s for s in candidates if re.fullmatch(r"IXI\d{3}", s)
                  and not read_record(output / "runs" / f"{s}.json"))


def read_cases(output, owner):
    output = Path(output)
    locked = batch.batch_is_running(output)
    cases = []
    for row in training_rows(owner):
        subject = row["subject"]
        record = read_record(output / "runs" / f"{subject}.json")
        model = output / f"m2m_{subject}"
        log = output / "logs" / f"{subject}.log"
        state = "pending"
        if record.get("outputs_ok"):
            state = "completed" if all((model / n).is_file() for n in batch.DELIVER[:3]) else "needs review"
        elif record.get("state") == "running":
            state = "running" if locked else "interrupted / unconfirmed"
        elif record:
            state = "failed"
        elif model.exists() or log.exists():
            state = "external / unconfirmed"
        cases.append({**row, "state": state, "record": record, "log": log, "model": model})
    return cases


def log_snapshot(path):
    """Read at most 64 KiB; the latest log line is a stage hint, never a percentage."""
    try:
        stat = path.stat()
        with path.open("rb") as f:
            head = f.read(2048).decode("utf-8", errors="replace")
            f.seek(max(0, stat.st_size - 65536))
            tail = f.read(65536).decode("utf-8", errors="replace")
        stages = re.findall(r"\[ simnibs \]\s+(?:INFO|WARNING):\s*(.+)", tail)
        match = re.search(r"charm run started:\s*(.+)", head)
        started = None
        if match:
            try:
                started = datetime.strptime(match.group(1).strip(), "%a %b %d %H:%M:%S %Y").astimezone()
            except ValueError:
                pass
        return tail, (stages[-1][:240] if stages else "See live log"), stat.st_mtime, started
    except OSError:
        return "", "Waiting for a log", None, None


@dataclass(frozen=True)
class BatchJob:
    python: Path
    charm: Path
    data: Path
    output: Path
    owner: str
    dry_run: bool = False

    @property
    def subject(self):
        return f"batch_{self.owner}"

    def command(self):
        return [str(self.python), "-E", "-u", str(BATCH), "--owner", self.owner,
                "--data", str(self.data), "--out", str(self.output), "--charm", str(self.charm),
                "--assignment", str(ASSIGNMENT)] + (["--dry-run"] if self.dry_run else [])

    def key(self):
        return tuple(s for s in self.command() if s != "--dry-run") + (batch.sha256(ASSIGNMENT),)

    def validate(self):
        rows = training_rows(self.owner)
        for label, path in (("SimNIBS Python", self.python), ("CHARM", self.charm)):
            if not path.is_file() or (sys.platform != "win32" and not os.access(path, os.X_OK)):
                raise ValueError(f"Select the installed {label} executable.")
        if self.python.suffix.lower() in (".cmd", ".bat"):
            raise ValueError("Select SimNIBS's python.exe, not its Python command wrapper.")
        command_prefix(self.charm)
        if not self.data.is_dir():
            raise ValueError("Select the unpacked D06 data folder.")
        if not self.output.is_dir() or not os.access(self.output, os.W_OK):
            raise ValueError("Select an existing writable output folder.")
        output = self.output.resolve()
        if any((p / ".git").exists() for p in (output, *output.parents)):
            raise ValueError("Keep batch outputs outside Git.")
        if not BATCH.is_file():
            raise ValueError("Keep tools/charm_batch beside the desktop prototype.")
        for row in rows:
            batch.find_inputs(self.data, row["subject"])
        if not self.dry_run and (batch.batch_is_running(output) or untracked_runs(output)):
            raise ValueError("Existing external or unconfirmed batch: monitor it; do not start another run.")


class BatchRunner(Runner):
    log_prefix = "charm-batch"

    def __init__(self, job):
        super().__init__(job)
        self.cleaned_group = False

    @property
    def complete(self):
        if self.returncode != 0 or self.cancelled:
            return False
        return self.job.dry_run or all(c["state"] == "completed" for c in read_cases(self.job.output, self.job.owner))

    def close(self):
        if self.process is not None and not self.cleaned_group:
            self._signal_group(signal.SIGTERM if sys.platform == "win32" else signal.SIGKILL)
            self.cleaned_group = True
        super().close()
