"""Desktop controls for a fresh E1/E2 inference job and live local logs."""

from datetime import datetime, timezone
from pathlib import Path
import sys
import time
import uuid

from nibabel.filebasedimages import ImageFileError

from PySide6.QtCore import QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from inference_runner import InferenceJob, InferenceRunner


class InferencePanel(QWidget):
    busy_changed = Signal()
    completed = Signal(object)

    def __init__(self):
        super().__init__()
        self.runner = None
        self.error = ""
        self.available = True
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.tick)
        layout = QVBoxLayout(self)
        title = QLabel("Run our segmentation model")
        title.setStyleSheet("font-size: 23px; font-weight: 600;")
        layout.addWidget(title)
        note = QLabel("Choose a T1 MRI and our completed model. A new segmentation is generated locally and opens in 2D/3D when finished. Existing data and weights stay unchanged.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.inputs = QWidget()
        form = QFormLayout(self.inputs)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.experiment = QComboBox()
        self.experiment.addItems(["E1", "E2"])
        self.experiment.setAccessibleName("Segmentation model version")
        form.addRow("Model version", self.experiment)
        self.python = self.path_field(form, "Inference Python", "file")
        self.python.setToolTip("Separate Python 3.11 environment with nnU-Net 2.8.1 / torch 2.6.0. Keep its venv executable path; do not select SimNIBS Python.")
        self.model = self.path_field(form, "Our trained model folder", "folder")
        self.model.setToolTip("Your trusted model folder containing plans.json, dataset.json and fold_0/checkpoint_final.pth.")
        self.mri = self.path_field(form, "Source T1 MRI", "image")
        self.output = self.path_field(form, "Output parent folder", "folder")
        self.device = QComboBox()
        self.device.addItem("CPU (Mac compatible)", "cpu")
        self.device.addItem("CUDA (compatible NVIDIA runtime required)", "cuda")
        form.addRow("Device", self.device)
        self.tta = QCheckBox("Mirror augmentation (slower; off for the initial CPU demo)")
        form.addRow("", self.tta)
        self.assume_mm = QCheckBox("Use handoff mm assumption for unknown MRI units")
        self.assume_mm.setToolTip("Explicitly use the provisional original handoff assumption; this does not repair headers or validate physical scale.")
        form.addRow("", self.assume_mm)
        layout.addWidget(self.inputs)
        workspace = Path(__file__).resolve().parents[3]
        runtime = workspace / "training-runs/e1-demo-venv"
        python = runtime / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if python.is_file():
            self.python.setText(str(python))
        model = workspace / "training-runs/e1-demo/model"
        if (model / "fold_0/checkpoint_final.pth").is_file():
            self.model.setText(str(model))
        output = workspace / "training-runs"
        self.output.setText(str(output if output.is_dir() else Path.home() / "Documents"))
        buttons = QHBoxLayout()
        self.run_button = QPushButton("Generate E1 segmentation")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.start)
        buttons.addWidget(self.run_button)
        self.cancel_button = QPushButton("Cancel inference")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        buttons.addWidget(self.cancel_button)
        self.folder_button = QPushButton("Open output folder")
        self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(self.open_output)
        buttons.addWidget(self.folder_button)
        layout.addLayout(buttons)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel("Ready. This runs inference only; no training or CHARM job starts.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(10000)
        layout.addWidget(self.logs, 1)
        e2 = Path.home() / "Downloads/E2_L4_001/Dataset002_E2Charm/nnUNetTrainer_E2Preliminary__nnUNetPlans__3d_fullres"
        self.model_paths = {"E1": self.model.text(), "E2": str(e2) if (e2 / "fold_0/checkpoint_final.pth").is_file() else ""}
        self.selected_experiment = "E1"
        self.experiment.currentTextChanged.connect(self.change_experiment)

    def change_experiment(self, experiment):
        self.model_paths[self.selected_experiment] = self.model.text()
        self.selected_experiment = experiment
        self.model.setText(self.model_paths[experiment])
        self.run_button.setText(f"Generate {experiment} segmentation")
        self.assume_mm.setEnabled(experiment == "E1")
        self.status.setText(f"{experiment} selected. Choose the source MRI and generate a new segmentation.")

    def path_field(self, form, label, kind):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        field = QLineEdit()
        field.setAccessibleName(label)
        button = QPushButton("Browse…")
        def choose():
            if kind == "folder":
                path = QFileDialog.getExistingDirectory(self, label, field.text() or str(Path.home()))
            else:
                path, _ = QFileDialog.getOpenFileName(self, label, field.text() or str(Path.home()),
                    "NIfTI images (*.nii *.nii.gz)" if kind == "image" else "All files (*)")
            if path:
                field.setText(path)
        button.clicked.connect(choose)
        layout.addWidget(field, 1)
        layout.addWidget(button)
        form.addRow(label, row)
        return field

    @property
    def busy(self):
        return self.timer.isActive()

    def set_available(self, available):
        self.available = available
        self.inputs.setEnabled(available and not self.busy)
        self.run_button.setEnabled(available and not self.busy)

    def start(self):
        if self.busy or not self.available:
            return
        try:
            if not all(field.text().strip() for field in (self.python, self.model, self.mri, self.output)):
                raise ValueError("Choose inference Python, model, source MRI and output parent first.")
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            # Keep the lexical venv executable: resolving its symlink would select base Python.
            python = Path(self.python.text()).expanduser().absolute()
            job = InferenceJob(python, Path(self.model.text()).expanduser().resolve(),
                Path(self.mri.text()).expanduser().resolve(), Path(self.output.text()).expanduser().resolve(),
                f"{self.experiment.currentText().lower()}_{stamp}_{uuid.uuid4().hex[:8]}", self.device.currentData(),
                self.tta.isChecked(), self.assume_mm.isChecked() if self.experiment.currentText() == "E1" else False,
                self.experiment.currentText())
            runner = InferenceRunner(job)
            runner.start()
        except (ValueError, OSError, ImageFileError) as error:
            self.status.setText("Cannot start inference: " + str(error))
            return
        if self.runner is not None:
            self.runner.close()
        self.runner, self.error = runner, ""
        self.logs.setPlainText(f"New inference · {job.device.upper()} · mirror augmentation {'on' if job.tta else 'off'}\nOutput: {job.run_dir}\nLog: {runner.log_path}\n")
        self.progress.setRange(0, 0)
        self.status.setText(f"Running {job.experiment} inference. Live logs below; no reliable completion percentage is available.")
        self.cancel_button.setEnabled(True)
        self.folder_button.setEnabled(False)
        self.timer.start()
        self.set_available(self.available)
        self.busy_changed.emit()

    def cancel(self):
        if self.busy:
            try:
                self.runner.cancel()
                self.cancel_button.setEnabled(False)
                self.status.setText("Stopping inference and child workers; partial files will be preserved.")
            except OSError as error:
                self.status.setText("Could not cancel: " + str(error))

    def tick(self):
        runner = self.runner
        try:
            self.logs.moveCursor(QTextCursor.MoveOperation.End)
            self.logs.insertPlainText(runner.read_output())
            code = runner.poll()
        except OSError as error:
            self.error = str(error)
            runner.cancel()
            code = runner.poll()
        elapsed = int(time.monotonic() - runner.started_at)
        if code is None:
            if not runner.cancelled:
                self.status.setText(f"Running {runner.job.experiment} inference · {elapsed // 60:02d}:{elapsed % 60:02d} elapsed · logs below")
            return
        self.timer.stop()
        runner.close()
        complete = runner.complete and not self.error
        self.progress.setRange(0, 1)
        self.progress.setValue(1 if complete else 0)
        self.cancel_button.setEnabled(False)
        self.folder_button.setEnabled(True)
        if runner.cancelled:
            message = "Cancelled. Partial output/logs preserved; the next run uses a fresh folder."
        elif complete:
            message = f"Inference complete · {elapsed // 60:02d}:{elapsed % 60:02d}. Loading the new prediction in 3D…"
        else:
            message = f"Inference failed (exit {code}). {self.error} Inspect the log; partial files preserved."
        self.status.setText(message)
        self.set_available(self.available)
        self.busy_changed.emit()
        if complete:
            self.completed.emit(runner.job)

    def open_output(self):
        if self.runner is not None:
            path = self.runner.job.run_dir
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path if path.is_dir() else path.parent)))
