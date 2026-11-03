"""Isolated local MRI inspection prototype; reuses the CHARM launcher's workflow."""

from pathlib import Path
from html import escape
import sys

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSlider, QTabWidget, QVBoxLayout, QWidget,
)

# Reuse launcher behavior, including process ownership and packaged-runtime handling.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "charm_gui"))
from app import Window as LauncherWindow

from viewer import SlicePanel, label_color
from volume import load_labels, load_volume
from model import load_e1_model, load_model
from mesh_viewer import MeshView, configure_surface_format

from headmodel.build_model import build_model


class LoadTask(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, function, parent):
        super().__init__(parent)
        self.function = function

    def run(self):
        try:
            self.loaded.emit(self.function())
        except Exception as error:
            self.failed.emit(str(error) or type(error).__name__)


class Window(LauncherWindow):
    def __init__(self):
        configure_surface_format()
        super().__init__()
        processing = self.takeCentralWidget()
        processing.layout().setContentsMargins(16, 12, 16, 12)
        self.start_button.setStyleSheet("")
        self.start_button.setObjectName("primary")
        self.volume = None
        self.task = None
        self.overlay = None
        self.head_model = None
        self.tissues = {}
        self.export_source = None
        self.setWindowTitle("MRI Workbench · TMS HeadSeg prototype")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 740)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        header = QHBoxLayout()
        name = QLabel("MRI Workbench")
        name.setObjectName("workbenchTitle")
        header.addWidget(name)
        header.addStretch()
        self.open_e1_button = QPushButton("Open E1 segmentation…")
        self.open_e1_button.clicked.connect(self.choose_e1_prediction)
        header.addWidget(self.open_e1_button)
        self.e1_assume_mm = QCheckBox("E1: assume mm")
        self.e1_assume_mm.setToolTip("Explicitly treat unknown MRI/prediction units as millimetres for this E1 display only. Original files stay unchanged; physical scale remains unverified.")
        header.addWidget(self.e1_assume_mm)
        header.addSpacing(12)
        badge = QLabel("LOCAL  /  PROTOTYPE")
        badge.setObjectName("badge")
        header.addWidget(badge)
        layout.addLayout(header)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.setCentralWidget(root)

        inspection = QWidget()
        row = QHBoxLayout(inspection)
        row.setContentsMargins(0, 16, 0, 0)
        sidebar = QWidget()
        sidebar.setFixedWidth(265)
        controls = QVBoxLayout(sidebar)
        controls.setContentsMargins(0, 0, 18, 0)
        self.open_button = QPushButton("Open T1 MRI…")
        self.open_button.setObjectName("primary")
        self.open_button.clicked.connect(self.choose_mri)
        controls.addWidget(self.open_button)
        self.open_model_button = QPushButton("Open head model folder…")
        self.open_model_button.clicked.connect(self.choose_model)
        controls.addWidget(self.open_model_button)
        self.existing_report_button = QPushButton("Open model report")
        self.existing_report_button.clicked.connect(self.open_head_report)
        controls.addWidget(self.existing_report_button)
        self.export_button = QPushButton("Export head model…")
        self.export_button.clicked.connect(self.choose_export)
        controls.addWidget(self.export_button)
        self.example_button = QPushButton("Use Ernie example")
        self.example_button.clicked.connect(self.load_ernie)
        controls.addWidget(self.example_button)
        self.selected_button = QPushButton("Load T1 selected in CHARM tab")
        self.selected_button.clicked.connect(lambda: self.load_mri(self.t1.text()))
        controls.addWidget(self.selected_button)
        self.source = QLabel("Open a 3D NIfTI scan to inspect its anatomy before processing.")
        self.source.setWordWrap(True)
        self.source.setTextFormat(Qt.TextFormat.PlainText)
        self.source.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        controls.addWidget(self.source)
        self.metadata = QLabel("")
        self.metadata.setWordWrap(True)
        controls.addWidget(self.metadata)
        controls.addSpacing(14)
        self.level = QDoubleSpinBox()
        self.level.setRange(-1e12, 1e12)
        self.width = QDoubleSpinBox()
        self.width.setRange(.001, 1e12)
        self.width.setDecimals(3)
        controls.addWidget(QLabel("Window level"))
        controls.addWidget(self.level)
        self.level.setAccessibleName("Window level")
        controls.addWidget(QLabel("Window width"))
        controls.addWidget(self.width)
        self.width.setAccessibleName("Window width")
        self.auto_button = QPushButton("Auto contrast")
        self.auto_button.clicked.connect(self.auto_contrast)
        controls.addWidget(self.auto_button)
        controls.addSpacing(14)
        self.labels_button = QPushButton("Load tissue labels…")
        self.labels_button.clicked.connect(self.choose_labels)
        controls.addWidget(self.labels_button)
        self.clear_button = QPushButton("Clear overlay")
        self.clear_button.clicked.connect(self.clear_overlay)
        controls.addWidget(self.clear_button)
        controls.addWidget(QLabel("Overlay opacity"))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(40)
        self.opacity.setAccessibleName("Tissue overlay opacity")
        controls.addWidget(self.opacity)
        self.legend = QLabel("No tissue overlay loaded.")
        self.legend.setWordWrap(True)
        legend_scroll = QScrollArea()
        legend_scroll.setWidgetResizable(True)
        legend_scroll.setWidget(self.legend)
        legend_scroll.setMinimumHeight(75)
        controls.addWidget(legend_scroll, 1)
        row.addWidget(sidebar)
        views = QHBoxLayout()
        views.setSpacing(10)
        self.panels = [SlicePanel("Axial", 2, ("L", "R", "A", "P")),
                       SlicePanel("Coronal", 1, ("L", "R", "S", "I")),
                       SlicePanel("Sagittal", 0, ("P", "A", "S", "I"))]
        for panel in self.panels:
            views.addWidget(panel, 1)
        row.addLayout(views, 1)
        self.tabs.addTab(inspection, "01   Inspect MRI")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(processing)
        self.tabs.addTab(scroll, "02   CHARM processing")
        self.mesh_view = MeshView()
        self.tabs.addTab(self.mesh_view, "03   3D model")
        self.tabs.currentChanged.connect(self.tab_changed)
        self.model_button.setText("Open 3D mesh in Gmsh")
        self.feedback = QLabel("Ready · neurological convention: L on screen left in axial/coronal views.")
        self.feedback.setWordWrap(True)
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.feedback)
        for control in (self.level, self.width):
            control.valueChanged.connect(self.refresh_slices)
        self.opacity.valueChanged.connect(self.refresh_slices)
        for panel in self.panels:
            panel.slider.valueChanged.connect(self.refresh_slices)
        self.update_controls()
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f1f4f2; color: #213634; font-size: 13px; }
            QLabel#workbenchTitle { font-size: 26px; font-weight: 600; }
            QLabel#badge { color: #466862; font-size: 11px; letter-spacing: 2px; }
            QTabWidget::pane { border: 0; }
            QTabBar::tab { padding: 12px 20px; margin-right: 8px; color: #52706a; }
            QTabBar::tab:selected { color: #184e45; border-bottom: 3px solid #287c68; }
            QPushButton { background: #e4ebe6; border: 1px solid #c8d6ce; border-radius: 5px; padding: 9px 12px; }
            QPushButton:hover { background: #d5e4da; }
            QPushButton:disabled { color: #91a09b; background: #e9eeeb; }
            QPushButton#primary { background: #286b56; color: #f5faf6; border: 0; }
            QPushButton:focus, QDoubleSpinBox:focus { border: 2px solid #328469; }
            QDoubleSpinBox, QLineEdit { padding: 6px; background: #fafcf9; border: 1px solid #b9cac0; border-radius: 4px; }
            QFrame#slicePanel { background: #101c21; border-radius: 5px; }
            QFrame#slicePanel QLabel { color: #a9bfc4; background: #101c21; font-size: 11px; }
            QLabel#planeTitle { font-size: 14px; font-weight: 600; color: #e1eeed; }
            QSlider { background: transparent; }
            QSlider::groove:horizontal { height: 4px; background: #a4b9ad; border-radius: 2px; }
            QSlider::handle:horizontal { width: 14px; margin: -5px 0; background: #439573; border-radius: 7px; }
            QScrollArea { border: 0; }
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #8fa99a; background: #fafcf9; border-radius: 3px; }
            QCheckBox::indicator:checked { background: #286b56; border: 1px solid #286b56; }
            QGroupBox { border: 1px solid #c8d6ce; border-radius: 5px; margin-top: 14px; padding-top: 14px; }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 6px; }
        """)

    def update_controls(self):
        busy = self.task is not None or self.timer.isActive()
        for control in (self.open_button, self.open_model_button, self.example_button, self.selected_button,
                        self.open_e1_button, self.e1_assume_mm):
            control.setEnabled(not busy)
        self.start_button.setEnabled(not busy)
        self.labels_button.setEnabled(self.volume is not None and not busy)
        for control in (self.level, self.width, self.auto_button):
            control.setEnabled(self.volume is not None)
        self.clear_button.setEnabled(self.overlay is not None and not busy)
        self.opacity.setEnabled(self.overlay is not None)
        self.existing_report_button.setEnabled(self.head_model is not None and self.head_model.report is not None and not busy)
        self.export_button.setEnabled(self.export_source is not None and not busy)

    def choose_mri(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open T1 MRI", str(Path.home()), "NIfTI images (*.nii *.nii.gz)")
        if path:
            self.load_mri(path)

    def choose_model(self):
        path = QFileDialog.getExistingDirectory(self, "Open SimNIBS m2m model folder", str(Path.home()))
        if path:
            self.load_head_model(path)

    def choose_e1_prediction(self):
        directory = str(self.volume.path.parent) if self.volume is not None else str(Path.home())
        mri, _ = QFileDialog.getOpenFileName(self, "Choose E1 source T1 MRI", directory, "NIfTI images (*.nii *.nii.gz)")
        if not mri:
            return
        prediction, _ = QFileDialog.getOpenFileName(self, "Choose E1 prediction (labels 0–5)", str(Path(mri).parent), "NIfTI labels (*.nii *.nii.gz)")
        if prediction:
            self.load_e1_prediction(mri, prediction, assume_mm=self.e1_assume_mm.isChecked())

    def load_e1_prediction(self, mri_path, prediction_path, assume_mm=False):
        if self.task is not None or self.timer.isActive():
            return
        self.clear_model()
        self.volume = None
        self.clear_overlay()
        for panel in self.panels:
            panel.set_volume(None)
        self.metadata.clear()
        self.source.setText(Path(prediction_path).name)
        self.feedback.setText("Opening E1 MRI and prediction; extracting display surfaces…")
        self.tabs.setCurrentIndex(0)
        self.run_task(lambda: load_e1_model(mri_path, prediction_path, assume_mm=assume_mm), self.model_loaded)

    def clear_model(self):
        self.head_model = None
        self.tissues = {}
        self.mesh_view.clear()
        self.update_controls()

    def load_head_model(self, directory):
        if self.task is not None or self.timer.isActive():
            return
        self.clear_model()
        self.volume = None
        self.clear_overlay()
        for panel in self.panels:
            panel.set_volume(None)
        self.metadata.clear()
        self.source.setText(Path(directory).name)
        self.feedback.setText("Opening model MRI, tissue labels and mesh surfaces…")
        self.tabs.setCurrentIndex(0)
        self.run_task(lambda: load_model(directory), self.model_loaded)

    def model_loaded(self, model):
        self.head_model = model
        self.tissues = model.tissues
        self.t1.setText(str(model.volume.path))
        self.t2.clear()
        self.mri_loaded(model.volume)
        self.labels_loaded(model.labels)
        self.mesh_view.set_model(model)
        self.export_source = model.export_source
        if model.kind == "e1":
            if model.units_assumed:
                self.metadata.setText(self.metadata.text() + "\nMRI/prediction units assumed mm · physical scale unverified")
            self.feedback.setText("E1 ready · inspect slices or select 03 3D model. " + model.geometry_note)
        else:
            self.feedback.setText(" ".join(("Model ready · inspect slices or select 03 3D model. Mesh and MRI use subject-world millimeters; review alignment.", *model.notes)))

    def choose_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Name a new folder for the exported model", str(Path.home() / "head_model"))
        if path:
            self.export_model(path)

    def export_model(self, out):
        if self.export_source is None:
            return
        t1, labels, scheme = self.export_source
        self.feedback.setText("Cleaning labels, building head and brain surfaces, and verifying the export…")

        def build():
            build_model(t1, labels, out, label_scheme=scheme)
            return load_model(out)

        self.run_task(build, self.export_finished, "Could not export: ")

    def export_finished(self, model):
        self.clear_model()
        self.clear_overlay()
        self.model_loaded(model)

    def open_head_report(self):
        if self.head_model is not None and self.head_model.report is not None:
            self.open_path(self.head_model.report)

    def tab_changed(self, index):
        if index == 2:
            self.mesh_view.ensure_renderer()

    def load_ernie(self):
        self.use_ernie()
        if self.t1.text():
            self.load_mri(self.t1.text())

    def run_task(self, function, callback, failure="Could not load: "):
        if self.task is not None or self.timer.isActive():
            return
        self.task = LoadTask(function, self)
        self.task.loaded.connect(callback)
        self.task.failed.connect(lambda error: self.feedback.setText(failure + error))
        self.task.finished.connect(self.task_finished)
        self.update_controls()
        self.task.start()

    def task_finished(self):
        task, self.task = self.task, None
        task.deleteLater()
        self.update_controls()

    def load_mri(self, path):
        if not path or self.task is not None or self.timer.isActive():
            return
        self.t1.setText(str(Path(path).expanduser().resolve()))
        self.clear_model()
        self.volume = None
        self.clear_overlay()
        for panel in self.panels:
            panel.set_volume(None)
        self.metadata.clear()
        self.source.setText(Path(path).name)
        self.feedback.setText("Loading MRI and preparing world-aligned slices…")
        self.tabs.setCurrentIndex(0)
        self.run_task(lambda: load_volume(path), self.mri_loaded)

    def mri_loaded(self, volume):
        self.volume = volume
        self.source.setText(volume.path.name)
        self.source.setToolTip(str(volume.path))
        spacing = " × ".join(f"{value:.2f}" for value in volume.source_spacing)
        self.metadata.setText(f"Source: {' × '.join(map(str, volume.source_shape))} voxels\n"
                              f"Spacing: {spacing} mm\nSource axes: {volume.source_orientation}\nDisplay: RAS, world-aligned")
        if volume.units_assumed:
            self.metadata.setText(self.metadata.text() + "\nMRI units assumed mm")
        for panel in self.panels:
            panel.set_volume(volume)
        self.auto_contrast()
        self.feedback.setText("MRI loaded · drag slice controls to inspect anatomy. Original files remain unchanged.")

    def auto_contrast(self):
        if self.volume is not None:
            self.level.setValue(self.volume.window[0])
            self.width.setValue(self.volume.window[1])
            self.refresh_slices()

    def refresh_slices(self):
        for panel in self.panels:
            panel.level, panel.width = self.level.value(), self.width.value()
            panel.opacity = self.opacity.value() / 100
            panel.refresh()
        self.mesh_view.indices = [next(panel.slider.value() for panel in self.panels if panel.axis == axis) for axis in range(3)]
        self.mesh_view.level, self.mesh_view.width = self.level.value(), self.width.value()
        self.mesh_view.update_planes()

    def choose_labels(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open tissue labels for this MRI", str(self.volume.path.parent), "NIfTI labels (*.nii *.nii.gz)")
        if path:
            self.load_overlay(path)

    def load_overlay(self, path):
        if self.volume is None or self.task is not None or self.timer.isActive():
            return
        self.clear_model()
        self.clear_overlay()
        self.feedback.setText("Aligning discrete tissue labels to the MRI grid…")
        self.run_task(lambda: load_labels(path, self.volume), self.labels_loaded)

    def labels_loaded(self, result):
        path, self.overlay, ids = result
        self.export_source = (self.volume.path, path, "project")
        entries = []
        for label in ids:
            name, color = self.tissues.get(int(label), (f"Label {label}", label_color(label)))
            entries.append(f'<span style="color:rgb{color}">■</span> {escape(name)} ({label})')
        self.legend.setText("<b>Tissues</b><br>" + "<br>".join(entries))
        for panel in self.panels:
            panel.labels = self.overlay
            panel.colors = {label: tissue[1] for label, tissue in self.tissues.items()}
        self.refresh_slices()
        self.tabs.setCurrentIndex(0)
        self.feedback.setText(f"{path.name} · header-aligned overlay. Confirm same subject and inspect anatomy; this is not automatic QC.")

    def clear_overlay(self):
        self.overlay = None
        self.export_source = None
        self.legend.setText("No tissue overlay loaded.")
        for panel in self.panels:
            panel.labels = None
            panel.refresh()
        self.update_controls()

    def start_job(self):
        if self.task is not None:
            return
        if self.volume is None or self.volume.path != Path(self.t1.text()).expanduser().resolve():
            self.feedback.setText("Load and inspect the selected T1 MRI before starting CHARM.")
            self.tabs.setCurrentIndex(0)
            return
        super().start_job()
        self.update_controls()

    def tick(self):
        was_running = self.timer.isActive()
        super().tick()
        if was_running and not self.timer.isActive():
            self.update_controls()
            if self.runner.complete and not self.run_error and not self.closing:
                self.load_head_model(self.runner.job.model_dir)

    def closeEvent(self, event):
        if self.task is not None:
            self.feedback.setText("Image loading is finishing. Close again once it completes.")
            event.ignore()
            return
        super().closeEvent(event)
        if event.isAccepted():
            self.mesh_view.shutdown()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MRI Workbench")
    window = Window()
    window.show()
    if "--model" in sys.argv:
        index = sys.argv.index("--model")
        if index + 1 >= len(sys.argv):
            raise SystemExit("--model needs an m2m folder path")
        window.load_head_model(sys.argv[index + 1])
    elif "--ernie" in sys.argv:
        window.load_ernie()
    if "--smoke-test" in sys.argv:
        timer = QTimer()
        timer.timeout.connect(lambda: app.quit() if window.task is None else None)
        timer.start(500)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
