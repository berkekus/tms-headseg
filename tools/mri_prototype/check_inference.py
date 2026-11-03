"""Explicit native desktop end-to-end check; starts one NEW CPU prediction."""

import argparse
import hashlib
import json
from pathlib import Path
import time

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication

from prototype import Window


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--mri", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Existing parent outside Git for fresh outputs/screenshots")
    parser.add_argument("--assume-mm", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_dir() and not any((p / ".git").exists() for p in (output, *output.parents))
    checkpoint = args.model / "fold_0/checkpoint_final.pth"
    sources = [args.mri, checkpoint, args.model / "plans.json", args.model / "dataset.json"]
    before = {str(p): sha256(p) for p in sources}
    app = QApplication([])
    window = Window()
    window.show()
    panel = window.inference
    panel.python.setText(str(args.python))
    panel.model.setText(str(args.model))
    panel.mri.setText(str(args.mri))
    panel.output.setText(str(output))
    panel.assume_mm.setChecked(args.assume_mm)
    window.tabs.setCurrentIndex(3)
    started = time.monotonic()
    try:
        panel.start()
        assert panel.busy, panel.status.text()
        assert not window.start_button.isEnabled(), "CHARM must be gated during inference"
        job = panel.runner.job
        print(f"NEW inference started: {job.run_dir}\nLive log: {panel.runner.log_path}", flush=True)
        next_update = started + 30
        captured = False
        while window.busy and time.monotonic() - started < 1800:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 40)
            time.sleep(.02)
            if not captured and time.monotonic() - started > 2:
                window.grab().save(str(output / f"{job.subject}-running.png"))
                captured = True
            if time.monotonic() >= next_update:
                print(panel.status.text(), flush=True)
                next_update += 30
        assert not window.busy, "Inference/UI timed out"
        assert panel.runner.complete, panel.status.text() + "\n" + panel.logs.toPlainText()[-2000:]
        assert window.head_model is not None, window.feedback.text()
        assert window.head_model.labels[0] == job.prediction
        assert window.tabs.currentIndex() == 2, "New result did not open automatically in 3D"
        for _ in range(5):
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 40)
        assert window.mesh_view.actors, "No native 3D actors"
        window.grab().save(str(output / f"{job.subject}-complete.png"))
        after = {str(p): sha256(p) for p in sources}
        assert before == after, "Source MRI/model changed"
        child_status = json.loads((job.run_dir / "status.json").read_text())
        desktop_status = json.loads(job.record_path.read_text())
        assert child_status["state"] == desktop_status["state"] == "completed"
        record = {"state": "passed", "new_inference": True, "run_dir": str(job.run_dir),
                  "prediction": str(job.prediction), "timing": child_status["timing"],
                  "elapsed_seconds": time.monotonic() - started, "source_hashes_unchanged": True,
                  "source_hashes": before, "surfaces": len(window.head_model.surfaces),
                  "triangles": sum(len(s.triangles) for s in window.head_model.surfaces),
                  "automatic_3d_open": True, "assumed_units": window.head_model.units_assumed}
        (output / f"{job.subject}-verification.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record, indent=2), flush=True)
    finally:
        if panel.busy:
            panel.cancel()
            panel.timer.stop()
            panel.runner.close()
        while window.task is not None:
            app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 40)
            time.sleep(.02)
        window.close()


if __name__ == "__main__":
    main()
