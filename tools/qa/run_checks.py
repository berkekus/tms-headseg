"""Run existing synthetic checks and report their coverage; never run a real model."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import importlib.metadata
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Suite:
    name: str
    directory: Path
    dependencies: tuple[str, ...] = ()
    pattern: str = "test_*.py"
    top: Path | None = None


IMAGE = ("numpy", "nibabel")
GEOMETRY = IMAGE + ("scipy", "skimage", "SimpleITK", "meshio")
WINDOWS = ("win32api",) if sys.platform == "win32" else ()
SUITES = (
    Suite("launcher-inputs", ROOT / "tools/charm_gui", pattern="test_simnibs.py"),
    Suite("batch", ROOT / "tools/charm_batch", IMAGE),
    Suite("data-preparation", ROOT / "tools/nnunet_prep", GEOMETRY),
    Suite("geometry-export", ROOT / "tools/headmodel", GEOMETRY, top=ROOT / "tools"),
    Suite("e1-demo", ROOT / "tools/e1_training", IMAGE + ("scipy", "skimage", "matplotlib", "plotly")),
    Suite("launcher-desktop", ROOT / "tools/charm_gui", ("PySide6.QtWidgets",) + WINDOWS),
    Suite("workbench", ROOT / "tools/mri_prototype",
          GEOMETRY + ("PySide6.QtWidgets", "vtk", "pyvistaqt") + WINDOWS),
)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_methods = 0

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_methods += 1


def worker(args):
    """Dependency failures are blockers; failures inside discovered tests stay failures."""
    versions, unavailable = {}, []
    try:
        with tempfile.TemporaryDirectory(prefix="tms-qa-preflight-") as temporary:
            folder = Path(temporary).resolve()
            if any((p / ".git").exists() for p in (folder, *folder.parents)):
                raise OSError("Test temporary directory is inside a Git checkout. Use --temp-root outside Git.")
            probe = Path(temporary) / "probe.txt"
            probe.write_text("qa", encoding="utf-8")
            if probe.read_text(encoding="utf-8") != "qa":
                raise OSError("Temporary-file readback failed")
    except OSError as error:
        unavailable.append(f"Temporary-directory access: {type(error).__name__}: {error}")
    for module in args.dependencies:
        try:
            imported = importlib.import_module(module)
            versions[module] = str(getattr(imported, "__version__", "importable"))
        except Exception as error:
            unavailable.append(f"{module}: {type(error).__name__}: {error}")
    if unavailable:
        write_json(args.result, {"status": "BLOCKED", "tests_run": 0,
                   "passed_methods": 0, "skipped": [], "failures": [], "errors": [],
                   "blockers": unavailable, "versions": versions})
        return 2
    sys.path.insert(0, str(ROOT / "tools"))
    tests = unittest.defaultTestLoader.discover(str(args.start), pattern=args.pattern,
                top_level_dir=str(args.top) if args.top else None)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=Result).run(tests)
    status = ("FAIL" if not result.wasSuccessful() else "BLOCKED" if result.testsRun == 0
              else "PASS_WITH_SKIPS" if result.skipped or result.expectedFailures else "PASS")
    write_json(args.result, {
        "status": status, "tests_run": result.testsRun, "passed_methods": result.passed_methods,
        "skipped": [{"test": t.id(), "reason": reason} for t, reason in result.skipped],
        "failures": [{"test": t.id(), "traceback": detail} for t, detail in result.failures],
        "errors": [{"test": t.id(), "traceback": detail} for t, detail in result.errors],
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "blockers": ["No tests discovered"] if result.testsRun == 0 else [], "versions": versions,
    })
    return 1 if status == "FAIL" else 0 if status == "PASS" else 2


def stop_tree(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()


def run_suite(suite, output, timeout, temp_root=None):
    detail = output / f"{suite.name}.json"
    log = output / f"{suite.name}.log"
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--start",
               str(suite.directory), "--pattern", suite.pattern, "--result", str(detail),
               "--dependencies", *suite.dependencies]
    if suite.top:
        command += ["--top", str(suite.top)]
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8",
               PYTHONUTF8="1", PYTHONPATH=str(ROOT / "tools"))
    if temp_root:
        env.update(TMP=str(temp_root), TEMP=str(temp_root), TMPDIR=str(temp_root))
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream,
            stderr=subprocess.STDOUT, start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_tree(process)
            process.wait()
            return {"name": suite.name, "status": "FAIL", "reason": "Suite timed out",
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "tests_run": None, "passed_methods": None, "skipped": [],
                    "log": log.name, "command": command}
    if not detail.is_file():
        data = {"status": "FAIL", "reason": "Worker exited without a result; inspect log",
                "tests_run": None, "passed_methods": None, "skipped": []}
    else:
        data = json.loads(detail.read_text(encoding="utf-8"))
        expected = 0 if data["status"] == "PASS" else 1 if data["status"] == "FAIL" else 2
        if process.returncode != expected:
            data.update(status="FAIL", reason="Worker exit code disagrees with its result")
    return dict(data, name=suite.name, duration_seconds=round(time.monotonic() - started, 3),
                exit_code=process.returncode, log=log.name, command=command)


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def overall(results):
    for status in ("FAIL", "BLOCKED", "PASS_WITH_SKIPS"):
        if any(item["status"] == status for item in results):
            return status
    return "PASS" if results else "BLOCKED"


def markdown(report):
    lines = ["# Demo QA check report", "", f"Status: **{report['status']}**",
        f"Started (UTC): {report['started_utc']}", f"Code commit: `{report['commit']}`",
        f"Branch: `{report['branch']}`", f"Working tree changed: {report['working_tree_changed']}",
        f"Runner SHA-256: `{report['runner_sha256']}`",
        f"Python: {report['python']}", f"Platform: {report['platform']}", "",
        "| Suite | Status | Methods run | Passed methods | Skips | Seconds | Log |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |"]
    for item in report["suites"]:
        count = item['tests_run'] if item['tests_run'] is not None else 'unknown'
        passed = item['passed_methods'] if item['passed_methods'] is not None else 'unknown'
        lines.append(f"| {item['name']} | {item['status']} | {count} | "
            f"{passed} | {len(item['skipped'])} | {item['duration_seconds']} | "
            f"[{item['log']}]({item['log']}) |")
    lines += ["", "## Blockers, failures and skipped checks", ""]
    for item in report["suites"]:
        if item["status"] == "PASS":
            continue
        lines.append(f"### {item['name']}: {item['status']}")
        lines.append("")
        for reason in item.get("blockers", []) + ([item["reason"]] if item.get("reason") else []):
            lines.append(f"- {reason}")
        for entry in item.get("failures", []) + item.get("errors", []):
            lines.append(f"- Failure/error: `{entry['test']}`. See JSON and log.")
        for entry in item["skipped"]:
            lines.append(f"- Skipped `{entry['test']}`: {entry['reason']}")
        if item.get("expected_failures"):
            lines.append(f"- Expected failures: {item['expected_failures']} (not passing coverage).")
        lines.append("")
    lines += ["## Scope", "",
        "Existing synthetic/unit and offscreen integration checks only. No real CHARM job, "
        "model training, real inference, held-out evaluation or native GPU/window rehearsal is run.",
        "Passed methods are counted directly. Subtest failure/error entries are not subtracted "
        "from the method count to invent a passed count. Skips remain visible.",
        "Manual demo acceptance is separate: use the ten scenarios in tools/qa/README.md.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="New local report directory (default: ignored outputs/qa timestamp)")
    parser.add_argument("--suite", action="append", choices=[s.name for s in SUITES])
    parser.add_argument("--timeout", type=float, default=300, help="Seconds per suite")
    parser.add_argument("--temp-root", type=Path, help="Test scratch directory outside every Git checkout")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--start", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--top", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--pattern", default="test_*.py", help=argparse.SUPPRESS)
    parser.add_argument("--result", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--dependencies", nargs="*", default=[], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if not args.start or not args.result:
            parser.error("Worker requires start/result")
        return worker(args)
    if args.timeout <= 0:
        parser.error("Timeout must be positive")
    temp_root = args.temp_root.resolve() if args.temp_root else None
    if temp_root:
        if any((p / ".git").exists() for p in (temp_root, *temp_root.parents)):
            parser.error("Test temporary root must be outside every Git checkout")
        temp_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (args.out or ROOT / "outputs/qa" / stamp).resolve()
    # A new directory prevents old JSON/log files from appearing to be fresh evidence.
    output.mkdir(parents=True, exist_ok=False)
    selected = [s for s in SUITES if not args.suite or s.name in args.suite]
    report = {"schema_version": 1, "started_utc": datetime.now(timezone.utc).isoformat(),
        "commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
        "working_tree_changed": bool(git("status", "--porcelain")),
        "python": sys.version, "executable": sys.executable, "platform": platform.platform()}
    report["runner_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report["installed_packages"] = dict(sorted((d.metadata["Name"], d.version)
        for d in importlib.metadata.distributions() if d.metadata.get("Name")))
    report["temp_root"] = str(temp_root) if temp_root else "OS default (validated by each worker)"
    report["suites"] = []
    for suite in selected:
        result = run_suite(suite, output, args.timeout, temp_root)
        report["suites"].append(result)
        print(f"{suite.name}: {result['status']}", flush=True)
    report["status"] = overall(report["suites"])
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(output / "summary.json", report)
    (output / "report.md").write_text(markdown(report), encoding="utf-8")
    print(f"Report: {output / 'report.md'}")
    return 1 if report["status"] == "FAIL" else 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
