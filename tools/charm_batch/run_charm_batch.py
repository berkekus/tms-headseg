"""Run charm on one worker's IXI subjects, one at a time, the same way on every machine.

Run with SimNIBS's own Python (it has nibabel):
    simnibs_python tools/charm_batch/run_charm_batch.py --owner K2 --data D06_DIR --out OUT_DIR
Add --dry-run first to see the plan. Re-running skips subjects that already finished.

Per subject: check inputs, check qform/sform (charm stops on a mismatch; a rounding-level one gets
--forceqform, a larger one is skipped), run charm with math-library threads limited to 1, verify outputs,
record the run, and copy the deliverable files with checksums. Labels stay raw charm labels; K1 maps them.
"""
import argparse
from contextlib import nullcontext
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from process_lock import batch_is_running, batch_lock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "charm_gui"))
from installation import command_prefix
SIMNIBS_VERSION = "4.6.0"
ROUNDING_MM = 1e-3          # qform/sform differences below this are float rounding
THREAD_LIMITS = {k: "1" for k in ("OPENBLAS_NUM_THREADS", "OPENBLAS_DEFAULT_NUM_THREADS", "OMP_NUM_THREADS")}
DELIVER = ("final_tissues.nii.gz", "final_tissues_LUT.txt", "charm_report.html", "charm_log.html", "settings.ini")


def load_assignment(path, owner):
    with open(path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["owner"] == owner]
    if not rows:
        raise SystemExit(f"No subjects assigned to {owner} in {path}.")
    return rows


def find_inputs(data_dir, subject):
    """Return (T1, T2) for a subject; files may sit in DATA/SUBJECT/ or directly in DATA/."""
    for folder in (Path(data_dir) / subject, Path(data_dir)):
        t1 = sorted(folder.glob(f"{subject}-*-T1.nii.gz"))
        t2 = sorted(folder.glob(f"{subject}-*-T2.nii.gz"))
        if len(t1) == 1 and len(t2) == 1:
            return t1[0], t2[0]
    raise FileNotFoundError(f"{subject}: expected one T1 and one T2 under {data_dir}")


def qform_sform_check(paths):
    """Worst qform/sform difference (mm) and whether charm's own check (charm_main.py) would pass."""
    import nibabel as nib
    import numpy as np
    worst, charm_ok = 0.0, True
    for path in paths:
        header = nib.load(str(path)).header
        q, s = header.get_qform(), header.get_sform()
        worst = max(worst, float(np.abs(q - s).max()))
        charm_ok &= bool(np.allclose(q, s, rtol=1e-5, atol=1e-6))
    return worst, charm_ok


def charm_flags(diff, charm_ok):
    """Flags for charm, or None to skip: --forceqform only where charm would stop on rounding noise."""
    if charm_ok:
        return []
    if diff < ROUNDING_MM:
        return ["--forceqform"]
    return None


def simnibs_version(log_text):
    match = re.search(r"simnibs version (\d+\.\d+\.\d+)", log_text)
    return match.group(1) if match else None


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_record(path, record):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2))
    temporary.replace(path)


def deliver(out, owner, subject, record):
    target = out / f"deliver_{owner}" / subject
    target.mkdir(parents=True, exist_ok=True)
    m2m = out / f"m2m_{subject}"
    for name in DELIVER:
        if (m2m / name).exists():
            shutil.copy2(m2m / name, target / name)
    (target / "run.json").write_text(json.dumps(record, indent=2))
    lines = [f"{sha256(p)}  {p.name}" for p in sorted(target.iterdir()) if p.name != "SHA256SUMS.txt"]
    (target / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")


def ensure_qc_sheet(out, owner, subjects):
    path = out / f"qc_{owner}.csv"
    existing = {}
    if path.exists():
        with open(path, newline="") as f:
            existing = {r["subject"]: r for r in csv.DictReader(f)}
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "qc", "notes"])
        writer.writeheader()
        for s in subjects:
            writer.writerow(existing.get(s, {"subject": s, "qc": "", "notes": ""}))


def completion_matches(record, expected, out):
    keys = ("subject", "owner", "cohort", "input_sha256", "forceqform", "thread_limits")
    if any(record.get(k) != expected[k] for k in keys):
        return False
    if record.get("exit_code") != 0 or record.get("simnibs_version") != SIMNIBS_VERSION:
        return False
    hashes = record.get("output_sha256")
    if not isinstance(hashes, dict) or not set(DELIVER[:3]) <= hashes.keys() or not hashes.keys() <= set(DELIVER):
        return False
    m2m = out / f"m2m_{expected['subject']}"
    return all((m2m / name).is_file() and sha256(m2m / name) == checksum for name, checksum in hashes.items())


def run_subject(row, args, out):
    subject = row["subject"]
    record_path = out / "runs" / f"{subject}.json"
    t1, t2 = find_inputs(args.data, subject)
    diff, charm_ok = qform_sform_check([t1, t2])
    flags = charm_flags(diff, charm_ok)
    command = command_prefix(args.charm) + [subject, str(t1.resolve()), str(t2.resolve()), *(flags or [])]
    print(f"{subject}: {' '.join(command)}  (qform/sform max diff {diff:.1e})")
    record = {"subject": subject, "owner": args.owner, "cohort": row["cohort"], "t1": t1.name, "t2": t2.name,
              "qform_sform_max_diff": diff, "forceqform": bool(flags), "thread_limits": THREAD_LIMITS,
              "host_os": sys.platform, "input_sha256": {"t1": sha256(t1), "t2": sha256(t2)}}
    if flags is None:
        record.update(outputs_ok=False, skipped_reason="qform/sform differ by more than rounding; ask K1")
        if not args.dry_run and not record_path.exists():
            write_record(record_path, record)
        print(f"{subject}: SKIPPED, qform/sform differ by {diff:.3g} mm; ask K1")
        return "failed"
    if record_path.exists():
        try:
            previous = json.loads(record_path.read_text())
            if previous.get("outputs_ok"):
                if not completion_matches(previous, record, out):
                    raise ValueError("completed inputs, settings or output checksums do not match")
                if not args.dry_run:
                    deliver(out, args.owner, subject, previous)
                print(f"{subject}: verified completed run, skipping")
                return "skipped"
        except (OSError, ValueError) as error:
            print(f"{subject}: FAILED verifying previous run ({error}); preserve it and choose a new --out folder")
            return "failed"
    if args.dry_run:
        return "planned"
    m2m = out / f"m2m_{subject}"
    if m2m.exists():  # a stopped or failed earlier attempt: keep it for inspection, start fresh
        m2m.rename(out / f"m2m_{subject}_attempt_{dt.datetime.now():%Y%m%d_%H%M%S}")
    log_path = out / "logs" / f"{subject}.log"
    env = {**os.environ, **THREAD_LIMITS}
    started = dt.datetime.now().astimezone()
    record.update(state="running", started=started.isoformat(timespec="seconds"), pid=os.getpid(), outputs_ok=False)
    write_record(record_path, record)
    with open(log_path, "w", encoding="utf-8", errors="replace") as log:
        code = subprocess.call(command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
    finished = dt.datetime.now().astimezone()
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    missing = [n for n in DELIVER[:3] if not (m2m / n).exists()]
    version = simnibs_version(log_text)
    record.update(started=started.isoformat(timespec="seconds"), finished=finished.isoformat(timespec="seconds"),
                  minutes=round((finished - started).total_seconds() / 60, 1), exit_code=code,
                  simnibs_version=version, missing_outputs=missing,
                  outputs_ok=code == 0 and not missing and version == SIMNIBS_VERSION)
    if record["outputs_ok"]:
        record["output_sha256"] = {name: sha256(m2m / name) for name in DELIVER if (m2m / name).is_file()}
    record["state"] = "completed" if record["outputs_ok"] else "failed"
    write_record(record_path, record)
    if record["outputs_ok"]:
        deliver(out, args.owner, subject, record)
        print(f"{subject}: done in {record['minutes']} min")
        return "done"
    print(f"{subject}: FAILED (exit {code}, version {version}, missing {missing}); see {log_path}")
    return "failed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--owner", required=True, choices=("K1", "K2"))
    parser.add_argument("--data", required=True, type=Path, help="Folder with the unpacked D06 IXI files")
    parser.add_argument("--out", required=True, type=Path, help="Output folder outside any Git checkout")
    parser.add_argument("--assignment", type=Path, default=HERE / "ixi_assignment.csv")
    parser.add_argument("--cohort", default="train", help="Cohort to run (default: train)")
    parser.add_argument("--charm", default="charm", help="charm executable if not on PATH")
    parser.add_argument("--only", nargs="*", help="Run only these subject IDs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    rows = [r for r in load_assignment(args.assignment, args.owner) if r["cohort"] == args.cohort]
    if args.only:
        rows = [r for r in rows if r["subject"] in set(args.only)]
    out = args.out.resolve()
    if (out / ".git").exists() or any((p / ".git").exists() for p in out.parents):
        raise SystemExit("Choose an output folder outside any Git checkout.")
    for sub in ("runs", "logs"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    try:
        with nullcontext() if args.dry_run else batch_lock(out):
            if not args.dry_run:
                ensure_qc_sheet(out, args.owner, [r["subject"] for r in rows])
            results = {r["subject"]: run_subject(r, args, out) for r in rows}
    except RuntimeError as error:
        print(error)
        return 1
    print("summary:", {k: sum(v == k for v in results.values()) for k in ("done", "skipped", "failed", "planned")})
    return 1 if "failed" in results.values() else 0


if __name__ == "__main__":
    sys.exit(main())
