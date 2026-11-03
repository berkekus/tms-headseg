"""Audit and package only the E1 train/validation handoff, outside Git."""

import argparse
import json
from pathlib import Path

from audit_handoff import audit, require
from colab_helpers import pack_handoff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(not any((parent / ".git").exists() for parent in (out, *out.parents)), "Keep data and audit artifacts outside Git.")
    out.mkdir(parents=True, exist_ok=True)
    report = audit(args.handoff)
    report_path = out / "audit_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    archive = out / "handoff_k2_e1.zip"
    digest = pack_handoff(args.handoff, report, archive)
    (out / "handoff_k2_e1.zip.sha256").write_text(digest + "  " + archive.name + "\n")
    print(f"Prepared {archive} ({archive.stat().st_size:,} bytes)\nSHA256: {digest}")


if __name__ == "__main__":
    main()
