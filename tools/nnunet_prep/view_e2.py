"""Open a predict_e2.py result directly in MRI Workbench's 3D view.

    tools/mri_prototype/.venv/Scripts/python.exe tools/nnunet_prep/view_e2.py <predict_e2 output folder>

The folder must hold T1_ras.nii.gz and prediction.nii.gz. Workbench's own E1 display is reused
(same label IDs); this launcher only skips the two file pickers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mri_prototype"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from prototype import Window  # noqa: E402


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    folder = Path(sys.argv[1])
    mri, prediction = folder / "T1_ras.nii.gz", folder / "prediction.nii.gz"
    for path in (mri, prediction):
        if not path.is_file():
            raise SystemExit(f"Missing {path}")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("MRI Workbench")
    window = Window()
    window.showMaximized()
    window.raise_()
    window.activateWindow()
    window.load_e1_prediction(str(mri), str(prediction), assume_mm=False, show_3d=True)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
