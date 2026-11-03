"""Native Windows/macOS launcher for an independently installed SimNIBS CHARM."""

from datetime import datetime
from pathlib import Path
import shlex
import subprocess
import sys
import time

from PySide6.QtCore import QProcess, QProcessEnvironment, QStandardPaths, QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFontDatabase, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

from runner import Job, Runner
from installation import command_prefix, external_environment, external_runtime, find_charm


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.runner = None
        self.run_error = ""
        self.closing = False
        self.setWindowTitle("CHARM Launcher · TMS HeadSeg")
        self.resize(900, 850)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Create a head model")
        font = title.font()
        font.setPointSize(23)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        subtitle = QLabel("Choose MRI scans. CHARM creates tissue labels and a 3D head mesh locally.")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.inputs = QWidget()
        inputs_layout = QVBoxLayout(self.inputs)
        inputs_layout.setContentsMargins(0, 0, 0, 0)

        scans = QGroupBox("1   MRI scans")
        scan_form = QFormLayout(scans)
        self.t1 = self.path_field(scan_form, "T1 MRI", "Required · .nii or .nii.gz", "image")
        self.t2 = self.path_field(scan_form, "T2 MRI", "Optional · improves skull segmentation", "image")
        example = QPushButton("Use Ernie example…")
        example.clicked.connect(self.use_ernie)
        scan_form.addRow("", example)
        inputs_layout.addWidget(scans)

        settings = QGroupBox("2   Job and output")
        job_form = QFormLayout(settings)
        self.subject = QLineEdit("trial_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        self.subject.setAccessibleName("Subject ID")
        subject_label = QLabel("Subject ID")
        subject_label.setBuddy(self.subject)
        job_form.addRow(subject_label, self.subject)
        self.output = self.path_field(job_form, "Output folder", "Choose a folder outside this repository", "folder")
        self.output.setText(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation))
        self.charm = self.path_field(job_form, "CHARM launcher", "SimNIBS…/bin/charm or charm.cmd", "executable")
        self.charm.setText(find_charm())
        self.destination = QLabel()
        self.destination.setWordWrap(True)
        self.destination.setTextFormat(Qt.TextFormat.PlainText)
        job_form.addRow("Model folder", self.destination)
        inputs_layout.addWidget(settings)
        layout.addWidget(self.inputs)

        self.command = QLabel()
        self.command.setWordWrap(True)
        self.command.setTextFormat(Qt.TextFormat.PlainText)
        self.command.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.command.setToolTip("Exact command for review. Paths are passed as separate arguments, without a shell.")
        layout.addWidget(self.command)
        for field in (self.charm, self.t1, self.t2, self.output, self.subject):
            field.textChanged.connect(self.refresh_preview)
        self.refresh_preview()

        actions = QHBoxLayout()
        self.start_button = QPushButton("Create head model")
        self.start_button.setMinimumHeight(38)
        self.start_button.setStyleSheet("QPushButton { background: #236bd8; color: white; border-radius: 6px; padding: 8px 18px; } QPushButton:disabled { background: #75869e; }")
        self.start_button.clicked.connect(self.start_job)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_job)
        actions.addWidget(self.start_button)
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        self.elapsed = QLabel("Not started")
        actions.addWidget(self.elapsed)
        layout.addLayout(actions)

        self.status = QLabel("Ready. Existing model folders will not be overwritten.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setMaximumHeight(5)
        layout.addWidget(self.progress)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setAccessibleName("CHARM live output")
        self.logs.setPlaceholderText("Live CHARM output appears here after you start. Reconstruction can take several minutes or longer.")
        self.logs.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.logs.setMaximumBlockCount(10000)
        layout.addWidget(self.logs, 1)

        results = QHBoxLayout()
        self.folder_button = QPushButton("Open output folder")
        self.report_button = QPushButton("Open report")
        self.model_button = QPushButton("Open 3D mesh")
        for button in (self.folder_button, self.report_button, self.model_button):
            button.setEnabled(False)
            results.addWidget(button)
        results.addStretch()
        self.folder_button.clicked.connect(self.open_folder)
        self.report_button.clicked.connect(self.open_report)
        self.model_button.clicked.connect(self.open_model)
        layout.addLayout(results)
        note = QLabel("Uses your installed SimNIBS. This launcher does not change CHARM’s segmentation or assess model quality.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)

    def path_field(self, form, name, placeholder, kind):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setAccessibleName(name)
        browse = QPushButton("Choose…")
        browse.setAccessibleName(f"Choose {name}")
        browse.clicked.connect(lambda: self.choose_path(field, name, kind))
        row_layout.addWidget(field, 1)
        row_layout.addWidget(browse)
        label = QLabel(name)
        label.setBuddy(field)
        form.addRow(label, row)
        return field

    def choose_path(self, field, name, kind):
        start = str(Path(field.text()).expanduser()) if field.text() else str(Path.home())
        if kind == "folder":
            selected = QFileDialog.getExistingDirectory(self, name, start)
        else:
            filters = "NIfTI images (*.nii *.nii.gz)" if kind == "image" else "All files (*)"
            selected, _ = QFileDialog.getOpenFileName(self, name, start, filters)
        if selected:
            field.setText(selected)

    def use_ernie(self):
        root = Path.home() / "Downloads" / "simnibs4_examples"
        if not (root / "org" / "ernie_T1.nii.gz").is_file():
            selected = QFileDialog.getExistingDirectory(self, "Choose simnibs4_examples folder", str(Path.home()))
            if not selected:
                return
            root = Path(selected)
        if not (root / "org" / "ernie_T1.nii.gz").is_file():
            QMessageBox.warning(self, "Ernie not found", "Choose the folder containing org/ernie_T1.nii.gz.")
            return
        self.t1.setText(str(root / "org" / "ernie_T1.nii.gz"))
        t2 = root / "org" / "ernie_T2.nii.gz"
        self.t2.setText(str(t2) if t2.is_file() else "")
        self.subject.setText("ernie_" + datetime.now().strftime("%Y%m%d_%H%M%S"))

    def job(self):
        def path(field):
            return Path(field.text()).expanduser().resolve()
        return Job(path(self.charm), path(self.t1), path(self.t2) if self.t2.text() else None,
                   path(self.output), self.subject.text().strip())

    def refresh_preview(self):
        job = self.job()
        self.destination.setText(str(job.model_dir))
        try:
            args = job.command()
            command = subprocess.list2cmdline(args) if sys.platform == "win32" else shlex.join(args)
            self.command.setText("Command: " + command)
        except ValueError as error:
            self.command.setText(str(error))

    def start_job(self):
        if self.timer.isActive():
            return
        runner = Runner(self.job())
        try:
            runner.start()
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Cannot start CHARM", str(error))
            return
        self.runner = runner
        self.run_error = ""
        self.logs.clear()
        self.logs.insertPlainText(f"Log: {runner.log_path}\n\n")
        self.inputs.setEnabled(False)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        for button in (self.report_button, self.model_button, self.folder_button):
            button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status.setText("Running CHARM with math-library threads limited to 1. Live output below; no reliable completion percentage is available.")
        self.timer.start()

    def cancel_job(self):
        try:
            self.runner.cancel()
        except OSError as error:
            QMessageBox.warning(self, "Could not stop CHARM", str(error))
            return
        self.cancel_button.setEnabled(False)
        self.status.setText("Stopping CHARM and child processes. Partial files will be preserved.")

    def tick(self):
        runner = self.runner
        try:
            text = runner.read_output()
            self.logs.moveCursor(QTextCursor.MoveOperation.End)
            self.logs.insertPlainText(text)
            code = runner.poll()
        except OSError as error:
            self.run_error = str(error)
            runner.cancel()
            code = runner.poll()
        seconds = int(time.monotonic() - runner.started_at)
        self.elapsed.setText(f"{seconds // 60:02d}:{seconds % 60:02d} elapsed")
        if code is None:
            return
        self.timer.stop()
        self.logs.moveCursor(QTextCursor.MoveOperation.End)
        try:
            self.logs.insertPlainText(runner.read_output())
        except OSError as error:
            self.run_error = str(error)
        runner.close()
        self.progress.setRange(0, 1)
        self.progress.setValue(1 if runner.complete else 0)
        self.inputs.setEnabled(True)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if self.run_error:
            message = f"Launcher I/O error: {self.run_error}. Inspect retained files before starting a new job."
        elif runner.cancelled:
            message = "Cancelled. Partial files preserved. Choose a new subject ID for another run."
        elif runner.complete:
            message = "CHARM finished; mesh and tissue labels found. Open the report and review anatomy before use."
        elif code == 0:
            message = "Output incomplete: CHARM exited successfully, but mesh or tissue labels are missing. Inspect the log."
        else:
            message = f"CHARM failed (exit {code}). Inspect the log. Partial files preserved; retry with a new subject ID."
        self.status.setText(message)
        self.folder_button.setEnabled(True)
        self.report_button.setEnabled(self.report_path() is not None)
        self.model_button.setEnabled(runner.complete and not self.run_error)
        if self.closing:
            self.close()

    def report_path(self):
        for name in ("charm_report.html", "results.html"):
            path = self.runner.job.model_dir / name
            if path.is_file():
                return path
        return None

    def open_path(self, path):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, "Could not open", f"Open this path manually:\n{path}")

    def open_folder(self):
        job = self.runner.job
        self.open_path(job.model_dir if job.model_dir.is_dir() else job.output)

    def open_report(self):
        path = self.report_path()
        if path:
            self.open_path(path)

    def open_model(self):
        mesh = self.runner.job.model_dir / f"{self.runner.job.subject}.msh"
        directory = self.runner.job.charm.parent
        viewer = next((directory / name for name in ("gmsh.cmd", "gmsh.exe", "gmsh")
                       if (directory / name).is_file()), None)
        if viewer is None:
            self.open_path(mesh)
            return
        try:
            command = command_prefix(viewer) + [str(mesh)]
            process = QProcess(self)
            env = QProcessEnvironment()
            for key, value in external_environment().items():
                env.insert(key, value)
            process.setProcessEnvironment(env)
            process.setProgram(command[0])
            process.setArguments(command[1:])
            with external_runtime():
                started, _ = process.startDetached()
            process.deleteLater()
            if not started:
                raise OSError("Gmsh did not start.")
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Viewer did not start", f"{error}\nOpen the mesh manually in SimNIBS or Gmsh:\n{mesh}")

    def closeEvent(self, event):
        if self.timer.isActive():
            answer = QMessageBox.question(self, "Stop active reconstruction?",
                "Closing will stop CHARM and its child processes. Partial output will remain.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer == QMessageBox.StandardButton.Yes:
                self.closing = True
                self.cancel_job()
            event.ignore()
        else:
            event.accept()


def main():
    if sys.platform not in ("darwin", "win32"):
        raise SystemExit("This prototype supports Windows and macOS.")
    app = QApplication(sys.argv)
    app.setApplicationName("CHARM Launcher")
    window = Window()
    if "--ernie" in sys.argv:
        window.use_ernie()
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(500, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
