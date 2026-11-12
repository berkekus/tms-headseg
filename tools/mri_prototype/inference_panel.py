"""Desktop controls for a fresh E1/E2 inference job and live local logs."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import uuid

from nibabel.filebasedimages import ImageFileError

from PySide6.QtCore import QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from inference_runner import InferenceJob, InferenceRunner
from time_estimates import duration, prediction_progress
from visual_theme import bind_disclosure, compact_action, compact_choice


class InferencePanel(QWidget):
    busy_changed = Signal()
    completed = Signal(object)
    notice = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.runner = None
        self.error = ""
        self.available = True
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.tick)
        layout = QVBoxLayout(self)
        title = QLabel("Create a segmentation")
        title.setStyleSheet("font-size: 23px; font-weight: 600;")
        layout.addWidget(title)
        note = self.intro = QLabel("1. Choose your MRI and model.  2. Create the result.  3. Review it in the MRI images and 3D view. Your original files stay unchanged.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.inputs = QWidget()
        form = QFormLayout(self.inputs)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.experiment = QComboBox()
        self.experiment.addItems(["E1", "E2"])
        compact_choice(self.experiment)
        self.experiment.setAccessibleName("Segmentation model version")
        form.addRow("Model version", self.experiment)
        self.setup_button = QPushButton("Model setup ▾")
        self.setup_button.setCheckable(True)
        form.addRow("", self.setup_button)
        self.setup_inputs = QWidget()
        setup_form = self.setup_form = QFormLayout(self.setup_inputs)
        setup_form.setContentsMargins(0, 0, 0, 0)
        form.addRow("", self.setup_inputs)
        self.setup_button.toggled.connect(self.setup_inputs.setVisible)
        bind_disclosure(self.setup_button, "Model setup")
        self.setup_inputs.setObjectName("disclosureBody")
        setup_form.setContentsMargins(12, 10, 12, 10)
        self.setup_button.setChecked(True)
        self.python = self.path_field(setup_form, "Inference Python", "file")
        self.python.setToolTip("Separate inference environment with nnU-Net 2.8.1 / torch 2.6.0. Keep its venv executable path; do not select SimNIBS Python.")
        self.model = self.path_field(setup_form, "Trained model folder", "folder")
        self.model.setToolTip("Your trusted model folder containing plans.json, dataset.json and fold_0/checkpoint_final.pth.")
        self.test_inputs_form = form
        self.workstation_output = None
        self.mri = self.path_field(form, "Source T1 MRI", "image")
        self.output = self.path_field(form, "Save results in", "folder")
        self.advanced_button = QPushButton("Advanced settings ▸")
        self.advanced_button.setCheckable(True)
        form.addRow("", self.advanced_button)
        advanced = QWidget()
        advanced_form = QFormLayout(advanced)
        advanced_form.setContentsMargins(0, 0, 0, 0)
        self.device = QComboBox()
        self.device.addItem("CPU (this computer)", "cpu")
        self.device.addItem("NVIDIA GPU (CUDA)", "cuda")
        self.device.setItemData(1, "Requires a compatible NVIDIA GPU and CUDA inference runtime.", Qt.ItemDataRole.ToolTipRole)
        compact_choice(self.device)
        advanced_form.addRow("Run on", self.device)
        self.tta = QCheckBox("Use mirrored inputs (extra passes; slower)")
        self.tta.setToolTip("Averages extra mirrored predictions. Use the same setting when comparing results.")
        advanced_form.addRow("", self.tta)
        self.assume_mm = QCheckBox("Assume millimetres when MRI units are missing (E1 only)")
        self.assume_mm.setToolTip("Explicitly use the provisional original handoff assumption; this does not repair headers or validate physical scale.")
        advanced_form.addRow("", self.assume_mm)
        form.addRow("", advanced)
        advanced.hide()
        self.advanced_button.toggled.connect(advanced.setVisible)
        bind_disclosure(self.advanced_button, "Advanced settings")
        advanced.setObjectName("disclosureBody")
        advanced_form.setContentsMargins(12, 10, 12, 10)
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
        self.run_button = QPushButton("Create E1 segmentation")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.start)
        buttons.addWidget(self.run_button)
        self.cancel_button = QPushButton("Cancel inference")
        self.cancel_button.setObjectName("stopAction")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.confirm_cancel)
        buttons.addWidget(self.cancel_button)
        self.folder_button = QPushButton("Open output folder")
        self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(self.open_output)
        buttons.addWidget(self.folder_button)
        for button in (self.run_button, self.cancel_button, self.folder_button):
            compact_action(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.metrics = QLabel("Elapsed: —  ·  Remaining estimate: —\nChoose files to get started.")
        self.metrics.setObjectName("runMetrics")
        self.metrics.setWordWrap(True)
        self.metrics.setFixedHeight(44)
        self.metrics.setTextFormat(Qt.TextFormat.PlainText)
        self.progress_text = ""
        self.progress_signature = None
        self.previous_elapsed = None
        self.progress_seen = 0.
        layout.addWidget(self.metrics)
        self.status = QLabel("Ready. This runs inference only; no training or CHARM job starts.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.log_toggle = QPushButton("Show technical log ▸")
        self.log_toggle.setCheckable(True)
        layout.addWidget(self.log_toggle)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(10000)
        self.logs.setMinimumHeight(120)
        layout.addWidget(self.logs, 1)
        self.logs.hide()
        self.log_toggle.toggled.connect(self.logs.setVisible)
        bind_disclosure(self.log_toggle, "Technical log")
        layout.addStretch()
        e2 = Path.home() / "Downloads/E2_L4_001/Dataset002_E2Charm/nnUNetTrainer_E2Preliminary__nnUNetPlans__3d_fullres"
        self.model_paths = {"E1": self.model.text(), "E2": str(e2) if (e2 / "fold_0/checkpoint_final.pth").is_file() else ""}
        self.selected_experiment = "E1"
        self.experiment.currentTextChanged.connect(self.change_experiment)

    def change_experiment(self, experiment):
        self.model_paths[self.selected_experiment] = self.model.text()
        self.selected_experiment = experiment
        self.model.setText(self.model_paths[experiment])
        label = "Run test" if self.workstation_output is not None else "Create"
        self.run_button.setText(f"{label} {experiment} segmentation")
        self.assume_mm.setEnabled(experiment == "E1")
        self.status.setText(f"{experiment} selected. Choose your MRI, then click Create {experiment} segmentation.")

    def restore_local_defaults(self, path=None):
        """Prefill reviewed local paths; never start work or enable unit assumptions."""
        self.apply_local_defaults(self.read_local_defaults(path))

    @staticmethod
    def read_local_defaults(path=None):
        path = Path(path) if path is not None else Path(__file__).resolve().parents[2] / "outputs/workbench/settings.json"
        try:
            if path.stat().st_size > 32_768:
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, ValueError):
            return None

    def apply_local_defaults(self, data):
        if not isinstance(data, dict):
            return
        for key, field, is_file in (("python", self.python, True), ("mri", self.mri, True), ("output", self.output, False)):
            value = data.get(key)
            if isinstance(value, str) and (Path(value).is_file() if is_file else Path(value).is_dir()):
                field.setText(value)
        models = data.get("models")
        experiment = data.get("experiment", self.experiment.currentText())
        if experiment in ("E1", "E2"):
            self.experiment.setCurrentText(experiment)
        if isinstance(models, dict):
            for key in ("E1", "E2"):
                value = models.get(key)
                if isinstance(value, str):
                    self.model_paths[key] = value if Path(value).is_dir() and value else ""
            self.model.setText(self.model_paths[self.experiment.currentText()])
        device = self.device.findData(data.get("device"))
        if device >= 0:
            self.device.setCurrentIndex(device)
        if type(data.get("tta")) is bool:
            self.tta.setChecked(data["tta"])
        if self.python.text() and Path(self.python.text()).is_file() and self.model.text() and all(
                (Path(self.model.text()) / name).is_file() for name in ("plans.json", "dataset.json", "fold_0/checkpoint_final.pth")):
            self.setup_button.setChecked(False)

    def workstation_defaults(self):
        experiment = self.experiment.currentText()
        output = self.output if self.workstation_output is None else self.workstation_output
        return {"experiment": experiment, "python": self.python.text().strip(),
                "models": {**self.model_paths, experiment: self.model.text().strip()},
                "output": output.text().strip(), "device": self.device.currentData(),
                "tta": self.tta.isChecked()}

    def add_physician_setup(self, output, save):
        self.intro.setText("Use Model setup to save the model for physicians. A test run is optional.")
        test_title = QLabel("Optional test run")
        test_title.setObjectName("cardTitle")
        row, _ = self.test_inputs_form.getWidgetPosition(self.mri.parentWidget())
        self.test_inputs_form.insertRow(row, test_title)
        for field, title in ((self.mri, "Test T1 MRI"), (self.output, "Test results folder")):
            self.test_inputs_form.labelForField(field.parentWidget()).setText(title)
            field.setAccessibleName(title)
        self.workstation_output = self.path_field(self.setup_form, "Physician results folder", "folder")
        self.workstation_output.setText(output)
        note = QLabel("Saving uses the selected model, inference Python and run settings. Each physician opens their own T1 MRI.")
        note.setWordWrap(True)
        self.setup_form.addRow(note)
        self.save_workstation_button = QPushButton("Save for Physician workspace")
        self.save_workstation_button.setObjectName("primary")
        compact_action(self.save_workstation_button)
        self.save_workstation_button.clicked.connect(save)
        self.setup_form.addRow("", self.save_workstation_button)
        self.run_button.setObjectName("")
        self.run_button.setText(f"Run test {self.experiment.currentText()} segmentation")
        self.run_button.setToolTip("Choose a Test T1 MRI to run an optional technical test.")
        self.mri.textChanged.connect(lambda: self.set_available(self.available))
        self.set_available(self.available)

    def path_field(self, form, label, kind):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        field = QLineEdit()
        field.setAccessibleName(label)
        field.setPlaceholderText("Choose a folder…" if kind == "folder" else "Choose a T1 MRI (.nii or .nii.gz)…" if kind == "image" else "Choose the inference environment's Python…")
        field.setClearButtonEnabled(True)
        button = QPushButton("Browse…")
        def choose():
            title = field.accessibleName()
            if kind == "folder":
                path = QFileDialog.getExistingDirectory(self, title, field.text() or str(Path.home()))
            else:
                path, _ = QFileDialog.getOpenFileName(self, title, field.text() or str(Path.home()),
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
        test_mri_ready = self.workstation_output is None or bool(self.mri.text().strip())
        self.run_button.setEnabled(available and not self.busy and test_mri_ready)

    def start(self):
        if self.busy or not self.available:
            return
        try:
            for field, guidance in ((self.python, "Choose inference Python in Model setup."),
                                    (self.model, "Choose the trained model folder in Model setup."),
                                    (self.mri, "Choose a T1 MRI (.nii or .nii.gz)."),
                                    (self.output, "Choose where to save the new result.")):
                if not field.text().strip():
                    if field in (self.python, self.model):
                        self.setup_button.setChecked(True)
                    field.setFocus()
                    raise ValueError(guidance)
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
            self.notice.emit("error", "Inference could not start", self.status.text())
            return
        if self.runner is not None:
            self.runner.close()
        self.runner, self.error = runner, ""
        self.progress_text = ""
        self.progress_signature = None
        self.previous_elapsed = runner.previous_elapsed()
        self.logs.setPlainText(f"New inference · {job.device.upper()} · mirror augmentation {'on' if job.tta else 'off'}\nOutput: {job.run_dir}\nLog: {runner.log_path}\n")
        self.progress.setRange(0, 0)
        self.status.setText(f"Creating an {job.experiment} segmentation. Follow the current step below; stop the run if needed.")
        self.cancel_button.setEnabled(True)
        self.folder_button.setEnabled(False)
        self.timer.start()
        self.update_metrics()
        self.set_available(self.available)
        self.busy_changed.emit()
        self.notice.emit("info", f"{job.experiment} segmentation started", "Follow progress in AI segmentation. Open the technical log for details. Review the result when it is ready.")

    def confirm_cancel(self):
        if not self.busy:
            return
        answer = QMessageBox.question(self, "Stop segmentation inference?",
            "Stop this prediction and its child workers? Partial output and logs will remain.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes and self.busy:
            self.cancel()

    def cancel(self):
        if self.busy:
            try:
                self.runner.cancel()
                self.cancel_button.setEnabled(False)
                self.status.setText("Stopping inference and child workers; partial files will be preserved.")
            except OSError as error:
                self.status.setText("Could not cancel: " + str(error))
                self.notice.emit("error", "Inference could not be stopped", self.status.text())

    def tick(self):
        runner = self.runner
        try:
            self.logs.moveCursor(QTextCursor.MoveOperation.End)
            text = runner.read_output()
            self.logs.insertPlainText(text)
            self.progress_text = (self.progress_text + text)[-65536:]
            code = runner.poll()
        except OSError as error:
            self.error = str(error)
            runner.cancel()
            code = runner.poll()
        elapsed = int(time.monotonic() - runner.started_at)
        if code is None:
            self.update_metrics()
            if not runner.cancelled:
                self.status.setText(f"Creating an {runner.job.experiment} segmentation. Keep this window open, or cancel the run to stop it.")
            return
        self.timer.stop()
        runner.close()
        complete = runner.complete and not self.error
        self.progress.setRange(0, 1)
        self.progress.setTextVisible(False)
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
        self.metrics.setText(f"Elapsed: {duration(elapsed)} · " + ("Cancelled" if runner.cancelled else "Prediction saved; preparing the 3D view" if complete else "Failed — see the error and technical log"))
        if not complete and not runner.cancelled:
            self.log_toggle.setChecked(True)
        self.set_available(self.available)
        self.busy_changed.emit()
        self.notice.emit("info" if runner.cancelled else "success" if complete else "error",
                         "Inference cancelled" if runner.cancelled else "Prediction generated" if complete else "Inference failed",
                         message)
        if complete:
            self.completed.emit(runner.job)

    def update_metrics(self):
        elapsed = max(0, time.monotonic() - self.runner.started_at)
        progress = prediction_progress(self.progress_text)
        self.progress.setTextVisible(False)
        earlier_estimate = None
        if self.previous_elapsed is not None and self.previous_elapsed > elapsed:
            earlier_estimate = f"~{duration(max(1, self.previous_elapsed - elapsed))} from a previous run"
        if progress is None:
            stage = "Preparing the model and MRI"
            estimate = earlier_estimate or "Available after the first tile"
            self.progress.setRange(0, 0)
        elif progress['stage'] == 'saving':
            stage, estimate = "Saving the result and building the report", "Not available for this step"
            self.progress.setRange(0, 0)
        else:
            signature = (progress['done'], progress['total'], progress.get('elapsed'))
            if signature != self.progress_signature:
                self.progress_signature, self.progress_seen = signature, time.monotonic()
            age = time.monotonic() - self.progress_seen
            remaining = progress['remaining']
            stage = f"Segmenting the MRI · {progress['done']} / {progress['total']} tiles"
            estimate = "Waiting for the next tile" if progress['done'] else (earlier_estimate or "Waiting for the first tile")
            if remaining and age < 30 and remaining > age:
                estimate = f"~{duration(max(1, remaining - age))} for prediction only"
            self.progress.setRange(0, progress['total'])
            self.progress.setValue(progress['done'])
            self.progress.setFormat("%v / %m prediction tiles")
            self.progress.setTextVisible(True)
        self.metrics.setText(f"Elapsed: {duration(elapsed)} · Remaining estimate: {estimate}\n{stage}")
        self.metrics.setToolTip("During preparation, a matching earlier run can provide an estimate. Live tile estimates cover prediction. Loading the 3D view is a separate step.")

    def open_output(self):
        if self.runner is not None:
            path = self.runner.job.run_dir
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path if path.is_dir() else path.parent)))
