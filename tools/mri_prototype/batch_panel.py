"""Assigned CHARM batch controls and read-only monitoring of existing runs."""

from datetime import datetime
from pathlib import Path
import sys
import time

from PySide6.QtCore import QTimer, Qt, QUrl, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)
from PySide6.QtGui import QDesktopServices

from batch_runner import MULTIAXIAL_ASSIGNMENT, BatchJob, BatchRunner, batch, command_prefix, log_snapshot, read_cases, untracked_runs
from installation import find_charm
from time_estimates import duration, queued_batch_estimate
from visual_theme import compact_choice, paint_disclosure


class BatchPanel(QWidget):
    busy_changed = Signal()
    notice = Signal(str, str, str)

    def __init__(self):
        super().__init__()
        self.runner = None
        self.owned_running = False
        self.external_active = False
        self.available = True
        self.preflight_key = None
        self.console = ""
        self.showing_check = False
        self.cases = []
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)
        layout = QVBoxLayout(self)
        title = QLabel("CHARM batch")
        title.setStyleSheet("font-size: 23px; font-weight: 600;")
        heading = QHBoxLayout()
        heading.addWidget(title)
        heading.addStretch()
        self.setup_button = QPushButton("Hide setup")
        paint_disclosure(self.setup_button, "Batch setup", True)
        self.setup_button.clicked.connect(lambda: self.show_setup(self.inputs.isHidden()))
        heading.addWidget(self.setup_button)
        layout.addLayout(heading)
        note = QLabel("Run assigned IXI training cases or monitor an existing IXI or MultiAxial run. Completed records still need visual QC. Keep the computer awake and its lid open.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.inputs = QWidget()
        form = QFormLayout(self.inputs)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.owner = QComboBox()
        self.owner.setAccessibleName("Batch owner")
        self.owner.addItems(["K2", "K1"])
        compact_choice(self.owner)
        form.addRow("Assigned worker", self.owner)
        self.python = self.path_field(form, "SimNIBS Python", False)
        self.python.setToolTip("Use SimNIBS's bin/simnibs_python on macOS, or simnibs_env/python.exe on Windows.")
        self.charm = self.path_field(form, "Batch CHARM", False)
        self.data = self.path_field(form, "Unpacked D06 data", True)
        self.output = self.path_field(form, "Batch output folder", True)
        charm = find_charm()
        if charm:
            self.charm.setText(charm)
            prefix = command_prefix(charm)
            python = Path(prefix[0]) if len(prefix) > 1 else Path(charm).parent / "simnibs_python"
            if python.is_file():
                self.python.setText(str(python))
        workspace = Path(__file__).resolve().parents[3]
        data = workspace / "data/D06_K2"
        output = workspace / "charm-runs/ixi-k2"
        if data.is_dir():
            self.data.setText(str(data))
        if output.is_dir():
            self.output.setText(str(output))
        layout.addWidget(self.inputs)
        actions = QHBoxLayout()
        self.check_button = QPushButton("1  Check inputs (dry run)")
        self.check_button.clicked.connect(lambda: self.start(dry_run=True))
        self.run_button = QPushButton("2  Start / resume remaining cases")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(lambda: self.start())
        self.cancel_button = QPushButton("Cancel this batch")
        self.cancel_button.clicked.connect(self.confirm_cancel)
        self.monitor_button = QPushButton("Monitor folder only")
        self.monitor_button.clicked.connect(self.monitor)
        for button in [self.check_button, self.run_button, self.cancel_button, self.monitor_button]:
            actions.addWidget(button)
        layout.addLayout(actions)
        self.status = QLabel("Choose folders, check inputs, then explicitly start the remaining training cases. Monitor does not start or stop CHARM.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.summary = QLabel("No batch is being monitored.")
        self.progress = QProgressBar()
        self.progress.setFormat("%v / %m cases completed")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.summary)
        self.estimate = QLabel("Queued time estimate: available after two cases finish in this batch.")
        self.estimate.setWordWrap(True)
        self.estimate.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.estimate)
        layout.addWidget(self.progress)
        self.table = QListWidget()
        self.table.setAccessibleName("Assigned cases: subject, site, state and runtime")
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setMaximumHeight(220)
        self.table.itemClicked.connect(self.select_case)
        self.table.currentRowChanged.connect(self.select_case)
        layout.addWidget(self.table)
        tools = QHBoxLayout()
        self.follow = QCheckBox("Follow active case")
        self.follow.setChecked(True)
        self.report_button = QPushButton("Open selected report")
        self.report_button.setEnabled(False)
        self.report_button.clicked.connect(self.open_report)
        self.folder_button = QPushButton("Open output folder")
        self.folder_button.clicked.connect(self.open_output)
        tools.addWidget(self.follow)
        tools.addStretch()
        tools.addWidget(self.report_button)
        tools.addWidget(self.folder_button)
        layout.addLayout(tools)
        self.stage = QLabel("No reliable per-case percentage or remaining-time estimate is available.")
        self.stage.setWordWrap(True)
        self.stage.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.stage)
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setMaximumBlockCount(3000)
        layout.addWidget(self.logs, 1)
        for field in [self.python, self.charm, self.data, self.output]:
            field.textChanged.connect(self.configuration_changed)
        self.owner.currentTextChanged.connect(self.configuration_changed)
        self.set_available(True)

    def path_field(self, form, label, folder):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        field = QLineEdit()
        field.setAccessibleName(label)
        button = QPushButton("Browse…")
        def choose():
            if folder:
                path = QFileDialog.getExistingDirectory(self, label, field.text() or str(Path.home()))
            else:
                path, _ = QFileDialog.getOpenFileName(self, label, field.text() or str(Path.home()))
            if path:
                field.setText(path)
        button.clicked.connect(choose)
        layout.addWidget(field, 1)
        layout.addWidget(button)
        form.addRow(label, row)
        return field

    @property
    def busy(self):
        return self.owned_running

    def job(self, dry_run=False):
        if not all(f.text().strip() for f in [self.python, self.charm, self.data, self.output]):
            raise ValueError("Choose SimNIBS Python, CHARM, unpacked data and output folders first.")
        return BatchJob(Path(self.python.text()).expanduser().absolute(),
                        Path(self.charm.text()).expanduser().absolute(),
                        Path(self.data.text()).expanduser().resolve(),
                        Path(self.output.text()).expanduser().resolve(), self.owner.currentText(), dry_run)

    def set_available(self, available):
        self.available = available
        multiaxial = (Path(self.output.text()).expanduser() / MULTIAXIAL_ASSIGNMENT).exists()
        self.inputs.setEnabled(available and not self.busy)
        self.check_button.setEnabled(available and not self.busy and not multiaxial)
        self.monitor_button.setEnabled(not self.busy)
        self.cancel_button.setEnabled(self.busy and not self.runner.cancelled)
        try:
            checked = self.preflight_key is not None and self.preflight_key == self.job().key()
        except (ValueError, OSError):
            checked = False
        self.run_button.setEnabled(available and not self.busy and not self.external_active and checked and not multiaxial)

    def configuration_changed(self, *_):
        self.preflight_key = None
        if self.timer.isActive() and not self.busy:
            self.refresh()
        self.set_available(self.available)

    def monitor(self):
        if self.busy:
            return
        self.showing_check = False
        self.status.setText("Monitoring only. This window does not own or cancel external runs.")
        self.show_setup(False)
        self.timer.start()
        self.refresh()

    def show_setup(self, visible):
        self.inputs.setVisible(visible)
        paint_disclosure(self.setup_button, "Batch setup", visible)

    def select_case(self, *_):
        self.follow.setChecked(False)
        self.showing_check = False
        self.show_log()

    def refresh(self):
        try:
            output = Path(self.output.text()).expanduser().resolve()
            if not self.output.text().strip() or not output.is_dir():
                raise ValueError("Select an existing batch output folder to monitor.")
            cases = read_cases(output, self.owner.currentText())
            external = not self.busy and (batch.batch_is_running(output) or bool(untracked_runs(output)))
            changed = external != self.external_active
            self.external_active = external
            self.cases = cases
            previous = self.table.currentRow()
            self.table.blockSignals(True)
            while self.table.count() < len(cases):
                self.table.addItem(QListWidgetItem())
            while self.table.count() > len(cases):
                self.table.takeItem(self.table.count() - 1)
            for i, case in enumerate(cases):
                runtime = case['record'].get('minutes')
                values = [case['subject'], case['site'], case['state'], f"{runtime} min" if runtime is not None else "—"]
                # Stable list items avoid Qt's macOS table-accessibility crash.
                item = self.table.item(i)
                value = "  ·  ".join(values)
                if item.text() != value:
                    item.setText(value)
            active = next((i for i, c in enumerate(cases) if c['state'] in ('running', 'external / unconfirmed')), None)
            selected = active if self.follow.isChecked() and active is not None else max(0, previous)
            self.table.setCurrentRow(min(selected, len(cases) - 1))
            self.table.blockSignals(False)
            done = sum(c['state'] == 'completed' for c in cases)
            pending = sum(c['state'] == 'pending' for c in cases)
            failed = sum(c['state'] in ('failed', 'needs review', 'interrupted / unconfirmed') for c in cases)
            elapsed = ""
            if self.busy and not self.runner.job.dry_run:
                seconds = int(time.monotonic() - self.runner.started_at)
                elapsed = f" · batch elapsed {seconds // 60:02d}:{seconds % 60:02d}"
            self.summary.setText(f"{self.owner.currentText()} · {done} / {len(cases)} completed · {pending} pending · {failed} need review{elapsed} · visual QC remains separate")
            estimate = queued_batch_estimate(cases)
            self.estimate.setText(f"Queued cases: about {duration(estimate['seconds'])} · based on {estimate['samples']} completed cases. The active case is excluded; case sizes vary."
                                  if estimate else "Queued time estimate: need at least two completed cases in this batch. No reliable estimate for the active case yet.")
            self.progress.setRange(0, len(cases))
            self.progress.setValue(done)
            self.show_log()
            self.set_available(self.available)
            if changed:
                self.busy_changed.emit()
        except (OSError, ValueError) as error:
            self.status.setText("Cannot read batch status: " + str(error))

    def show_log(self):
        index = self.table.currentRow()
        if not 0 <= index < len(self.cases):
            self.report_button.setEnabled(False)
            return
        case = self.cases[index]
        text, stage, modified, started = log_snapshot(case['log'])
        if self.showing_check:
            text, stage, modified, started = self.console, "Input check log · no reconstruction started", None, None
        if not text:
            text = self.console or "No CHARM log for this case yet."
        if text != self.logs.toPlainText():
            self.logs.setPlainText(text)
            self.logs.verticalScrollBar().setValue(self.logs.verticalScrollBar().maximum())
        age = f" · last log update {max(0, int(time.time() - modified))}s ago" if modified else ""
        elapsed = f" · elapsed {max(0, int((datetime.now().astimezone() - started).total_seconds())) // 60} min" if started and case['state'] != 'completed' else ""
        self.stage.setText(f"{case['subject']} · {stage}{elapsed}{age}")
        self.report_button.setEnabled(case['state'] == 'completed' and (case['model'] / 'charm_report.html').is_file())

    def start(self, dry_run=False):
        if self.busy or not self.available:
            return
        try:
            job = self.job(dry_run)
            if not dry_run and self.preflight_key != job.key():
                raise ValueError("Run a successful input check for these exact settings first.")
            runner = BatchRunner(job)
            runner.start()
        except (OSError, ValueError) as error:
            self.status.setText("Cannot start batch: " + str(error))
            self.notice.emit("error", "Batch could not start", self.status.text())
            return
        if self.runner is not None:
            self.runner.close()
        self.runner = runner
        self.show_setup(False)
        self.showing_check = dry_run
        self.owned_running = True
        self.external_active = False
        self.console = ""
        self.status.setText("Checking inputs only; no CHARM reconstruction starts." if dry_run else "Batch running sequentially. Recorded completions are rechecked and skipped; inspect reports for QC.")
        self.timer.start()
        self.refresh()
        self.set_available(self.available)
        self.busy_changed.emit()

    def tick(self):
        if self.busy:
            try:
                self.console = (self.console + self.runner.read_output())[-65536:]
                code = self.runner.poll()
            except OSError as error:
                self.console += "\n" + str(error)
                self.runner.cancel()
                code = self.runner.poll()
            if code is not None:
                runner = self.runner
                runner.close()
                self.owned_running = False
                if runner.job.dry_run:
                    self.preflight_key = runner.job.key() if runner.complete else None
                    self.status.setText("Input check passed. Start remaining cases when the pilot and its QC are accepted." if runner.complete else "Input check failed. Inspect the log and fix the inputs before starting.")
                    self.logs.setPlainText(self.console)
                else:
                    message = "Batch cancelled; partial files remain." if runner.cancelled else "Batch complete; inspect reports and fill in the QC sheet." if runner.complete else "Batch failed or incomplete. Inspect logs and records before resuming."
                    self.status.setText(message)
                    QApplication.alert(self.window(), 0)
                self.refresh()
                if runner.job.dry_run:
                    self.logs.setPlainText(self.console)
                self.set_available(self.available)
                self.busy_changed.emit()
                self.notice.emit("info" if runner.cancelled else "success" if runner.complete else "error",
                                 "Batch input check finished" if runner.job.dry_run else "Batch stopped" if runner.cancelled else "Batch finished",
                                 self.status.text())
                return
        self.refresh()

    def confirm_cancel(self):
        if not self.busy:
            return
        answer = QMessageBox.question(self, "Stop this CHARM batch?",
            "Stop this window's batch and its child processes? Partial outputs and logs will remain.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes and self.busy:
            self.cancel()

    def cancel(self):
        if self.busy:
            self.runner.cancel()
            self.cancel_button.setEnabled(False)
            self.status.setText("Stopping this owned batch and its child processes. Partial outputs are preserved.")

    def open_report(self):
        index = self.table.currentRow()
        if 0 <= index < len(self.cases) and self.cases[index]['state'] == 'completed':
            path = self.cases[index]['model'] / 'charm_report.html'
            if path.is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_output(self):
        path = Path(self.output.text()).expanduser()
        if path.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    def shutdown(self):
        self.timer.stop()
        if self.runner is not None:
            self.runner.close()
