"""Isolated local MRI inspection prototype; reuses the CHARM launcher's workflow."""

from pathlib import Path
from html import escape
import sys
from tempfile import TemporaryDirectory

from PySide6.QtCore import QElapsedTimer, QObject, QStandardPaths, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider,
    QStackedWidget, QTabWidget, QToolButton, QVBoxLayout, QWidget,
)

# Reuse launcher behavior, including process ownership and packaged-runtime handling.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "charm_gui"))
from app import Window as LauncherWindow

from viewer import SlicePanel, label_color
from volume import load_labels, load_volume
from model import load_e1_model, load_model
from mesh_viewer import MeshView, configure_surface_format
from inference_panel import InferencePanel
from inference_runner import validate_model_files, validate_output_folder
from batch_panel import BatchPanel
from visual_theme import apply_light_theme, bind_disclosure, center_page_content, centered_page, compact_action, refresh_style, stylesheet

from headmodel.build_model import build_model
from physician_workspace import PhysicianWorkspace
from workspace_login import SignIn, show_account_form, STORE_ERRORS
from workspace_store import ROLES, WorkspaceStore


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
    session_closed = Signal(bool)

    def __init__(self, store=None, account=None):
        configure_surface_format()
        super().__init__()
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.confirm_reconstruction_cancel)
        processing = self.takeCentralWidget()
        for button in processing.findChildren(QPushButton):
            compact_action(button)
        processing.layout().setContentsMargins(16, 12, 16, 12)
        self.start_button.setStyleSheet("")
        self.start_button.setObjectName("primary")
        self.cancel_button.setObjectName("stopAction")
        self.volume = None
        self.task = None
        self.overlay = None
        self.head_model = None
        self.tissues = {}
        self.export_source = None
        self.inference = None
        self.batch = None
        self.physician = None
        self.store, self.account = store, account
        self.switching_account = False
        self.next_workspace = "choose"
        self.setWindowTitle("MRI Workbench · TMS HeadSeg prototype")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 740)
        root = QWidget()
        root.setObjectName("workbenchRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        header = QHBoxLayout()
        name = QLabel("MRI Workbench")
        name.setWordWrap(True)
        name.setObjectName("workbenchTitle")
        brand = QVBoxLayout()
        brand.setSpacing(2)
        brand.addWidget(name)
        subtitle = QLabel("View an MRI. Create or open a result. Review it in 3D.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")
        brand.addWidget(subtitle)
        header.addLayout(brand, 1)
        header.addStretch()
        self.open_e1_button = QPushButton("Open saved result…")
        self.open_e1_button.setToolTip("Choose an MRI and its saved segmentation. This does not run the model.")
        self.open_e1_button.clicked.connect(self.choose_e1_prediction)
        header.addWidget(self.open_e1_button)
        self.e1_assume_mm = QCheckBox("E1: assume mm")
        self.e1_assume_mm.setToolTip("Explicitly treat unknown MRI/prediction units as millimetres for this E1 display only. Original files stay unchanged; physical scale remains unverified.")
        self.e1_assume_mm.setParent(root)
        self.e1_assume_mm.hide()
        self.import_options_button = QToolButton()
        self.import_options_button.setObjectName("importOptions")
        menu = QMenu(self.import_options_button)
        self.import_menu = menu
        menu.setToolTipsVisible(True)
        choices = QActionGroup(menu)
        choices.setExclusive(True)
        self.standard_import_action = QAction("Standard — use MRI file units", choices)
        self.assume_import_action = QAction("Assume mm — older E1 files (scale unverified)", choices)
        for action in (self.standard_import_action, self.assume_import_action):
            action.setCheckable(True)
            menu.addAction(action)
        self.standard_import_action.triggered.connect(lambda: self.e1_assume_mm.setChecked(False))
        self.assume_import_action.triggered.connect(lambda: self.e1_assume_mm.setChecked(True))
        self.assume_import_action.setToolTip(self.e1_assume_mm.toolTip())
        self.e1_assume_mm.toggled.connect(self.refresh_import_options)
        menu.aboutToShow.connect(lambda: self.import_menu_state(True))
        menu.aboutToHide.connect(lambda: self.import_menu_state(False))
        self.import_options_button.setMenu(menu)
        self.import_options_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.refresh_import_options()
        header.addWidget(self.import_options_button)
        header.addSpacing(12)
        badge = QLabel("LOCAL PROTOTYPE")
        badge.setObjectName("badge")
        header.addWidget(badge)
        layout.addLayout(header)
        # Reserve one stable slot: messages must not move tabs or hide recovery controls.
        self.notifications = QStackedWidget()
        self.notifications.setFixedHeight(112)
        layout.addWidget(self.notifications)
        self.ready_banner = QWidget()
        ready_layout = QVBoxLayout(self.ready_banner)
        ready_layout.setContentsMargins(10, 8, 10, 8)
        ready_layout.setSpacing(4)
        ready_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        ready_layout.addWidget(QLabel("Ready for visual inspection"))
        ready_hint = QLabel("Choose a task below to get started. Review the images and result before using them.")
        ready_hint.setWordWrap(True)
        ready_layout.addWidget(ready_hint)
        self.notifications.addWidget(self.ready_banner)
        self.error_banner = QWidget()
        self.error_banner.setObjectName("errorBanner")
        error_layout = QHBoxLayout(self.error_banner)
        error_layout.setContentsMargins(10, 5, 10, 5)
        error_copy = QVBoxLayout()
        error_copy.setSpacing(2)
        self.error_title = QLabel()
        self.error_title.setObjectName("errorTitle")
        self.error_title.setTextFormat(Qt.TextFormat.PlainText)
        self.error_title.setWordWrap(True)
        error_copy.addWidget(self.error_title)
        self.error_detail = ""
        self.error_details_button = QPushButton("Details…")
        self.error_details_button.clicked.connect(self.show_error_details)
        self.error_details_button.hide()
        self.dismiss_error_button = QPushButton("Dismiss")
        self.dismiss_error_button.clicked.connect(self.clear_task_error)
        self.error_message = QLabel()
        self.error_message.setTextFormat(Qt.TextFormat.PlainText)
        self.error_message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.error_message.setWordWrap(True)
        self.error_message.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.error_recovery = QLabel()
        self.error_recovery.setTextFormat(Qt.TextFormat.PlainText)
        self.error_recovery.setWordWrap(True)
        error_copy.addWidget(self.error_message)
        error_copy.addWidget(self.error_recovery)
        error_layout.addLayout(error_copy, 1)
        error_layout.addWidget(self.error_details_button)
        error_layout.addWidget(self.dismiss_error_button)
        self.notifications.addWidget(self.error_banner)
        self.activity_banner = QWidget()
        self.activity_banner.setObjectName("activityBanner")
        activity_layout = QHBoxLayout(self.activity_banner)
        self.activity_label = QLabel()
        self.activity_label.setTextFormat(Qt.TextFormat.PlainText)
        self.activity_label.setWordWrap(True)
        activity_layout.addWidget(self.activity_label, 1)
        self.activity_progress = QProgressBar()
        self.activity_progress.setRange(0, 0)
        self.activity_progress.setTextVisible(False)
        self.activity_progress.setFixedWidth(120)
        self.activity_progress.setAccessibleName("Background operation in progress; completion percentage unknown")
        activity_layout.addWidget(self.activity_progress)
        self.notifications.addWidget(self.activity_banner)
        self.result_banner = QWidget()
        self.result_banner.setObjectName("resultBanner")
        result_layout = QVBoxLayout(self.result_banner)
        result_heading = QHBoxLayout()
        self.result_title = QLabel()
        self.result_title.setTextFormat(Qt.TextFormat.PlainText)
        result_heading.addWidget(self.result_title, 1)
        self.dismiss_result_button = QPushButton("Dismiss")
        self.dismiss_result_button.clicked.connect(lambda: self.notifications.setCurrentWidget(self.ready_banner))
        result_heading.addWidget(self.dismiss_result_button)
        result_layout.addLayout(result_heading)
        self.result_message = QLabel()
        self.result_message.setWordWrap(True)
        self.result_message.setTextFormat(Qt.TextFormat.PlainText)
        self.result_message.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        result_layout.addWidget(self.result_message)
        self.notifications.addWidget(self.result_banner)
        self.notifications.setCurrentWidget(self.ready_banner)
        self.activity_clock = QElapsedTimer()
        self.activity_timer = QTimer(self)
        self.activity_timer.setInterval(1000)
        self.activity_timer.timeout.connect(self.refresh_activity)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        if account is not None and account.role == "technical":
            self.workspace_pages = QStackedWidget()
            self.workspace_pages.addWidget(root)
            self.setCentralWidget(self.workspace_pages)
        else:
            self.setCentralWidget(root)

        inspection = QWidget()
        row = QHBoxLayout(inspection)
        row.setContentsMargins(0, 16, 0, 0)
        sidebar = QWidget()
        sidebar.setFixedWidth(265)
        controls = QVBoxLayout(sidebar)
        controls.setContentsMargins(0, 0, 18, 0)
        sidebar_column = QWidget()
        self.sidebar_column = sidebar_column
        sidebar_column.setFixedWidth(285)
        sidebar_layout = QVBoxLayout(sidebar_column)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.open_button = QPushButton("Open MRI…")
        self.open_button.setObjectName("primary")
        self.open_button.clicked.connect(self.choose_mri)
        sidebar_layout.addWidget(self.open_button)
        self.open_model_button = QPushButton("Open model folder…")
        self.open_model_button.clicked.connect(self.choose_model)
        sidebar_layout.addWidget(self.open_model_button)
        more_actions = self.more_file_actions = QPushButton("More file actions ▸")
        more_actions.setCheckable(True)
        controls.addWidget(more_actions)
        extra_actions = QWidget()
        extra_layout = QVBoxLayout(extra_actions)
        extra_layout.setContentsMargins(0, 0, 0, 0)
        controls.addWidget(extra_actions)
        extra_actions.hide()
        more_actions.toggled.connect(extra_actions.setVisible)
        bind_disclosure(more_actions, "More file actions")
        extra_actions.setObjectName("disclosureBody")
        extra_layout.setContentsMargins(10, 8, 10, 8)
        self.existing_report_button = QPushButton("Open model report")
        self.existing_report_button.clicked.connect(self.open_head_report)
        extra_layout.addWidget(self.existing_report_button)
        self.export_button = QPushButton("Export head model…")
        self.export_button.clicked.connect(self.choose_export)
        extra_layout.addWidget(self.export_button)
        self.example_button = QPushButton("Use Ernie example")
        self.example_button.clicked.connect(self.load_ernie)
        extra_layout.addWidget(self.example_button)
        self.selected_button = QPushButton("Load T1 selected in CHARM tab")
        self.selected_button.clicked.connect(lambda: self.load_mri(self.t1.text()))
        extra_layout.addWidget(self.selected_button)
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
        controls.addWidget(QLabel("Brightness"))
        controls.addWidget(self.level)
        self.level.setAccessibleName("Window level")
        self.level.setToolTip("MRI window level: changes display brightness without changing the file.")
        controls.addWidget(QLabel("Contrast range"))
        controls.addWidget(self.width)
        self.width.setAccessibleName("Window width")
        self.width.setToolTip("MRI window width: a narrower range increases display contrast. The file stays unchanged.")
        self.auto_button = QPushButton("Auto contrast")
        self.auto_button.clicked.connect(self.auto_contrast)
        controls.addWidget(self.auto_button)
        controls.addSpacing(14)
        self.labels_button = QPushButton("Add tissue overlay…")
        self.labels_button.setToolTip("Choose a segmentation of the same MRI to color its tissues.")
        self.labels_button.clicked.connect(self.choose_labels)
        controls.addWidget(self.labels_button)
        self.clear_button = QPushButton("Remove overlay")
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
        self.inspection_sidebar = QScrollArea()
        self.inspection_sidebar.setWidgetResizable(True)
        self.inspection_sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.inspection_sidebar.setFixedWidth(285)
        self.inspection_sidebar.setWidget(sidebar)
        sidebar_layout.addWidget(self.inspection_sidebar, 1)
        row.addWidget(sidebar_column)
        self.preview_stack = QStackedWidget()
        self.welcome = QWidget()
        welcome_layout = QVBoxLayout(self.welcome)
        welcome_layout.setContentsMargins(18, 18, 18, 18)
        welcome_title = QLabel("Start here")
        welcome_title.setObjectName("welcomeTitle")
        welcome_layout.addWidget(welcome_title)
        welcome_hint = QLabel("Choose a task below. Nothing runs until you choose your files and start it.")
        welcome_hint.setWordWrap(True)
        welcome_layout.addWidget(welcome_hint)
        cards = QHBoxLayout()
        self.welcome_open_button = QPushButton("Open an MRI…")
        self.welcome_open_button.setObjectName("primary")
        self.welcome_saved_button = QPushButton("Open a saved result…")
        self.welcome_generate_button = QPushButton("Create a segmentation")
        for title, description, button, action in (
            ("1  View MRI images", "Open a T1 MRI (.nii or .nii.gz). Move through three slice views and adjust the contrast.", self.welcome_open_button, self.choose_mri),
            ("2  Review a saved result", "Choose the matching MRI and segmentation files. View tissue overlays and a 3D preview.", self.welcome_saved_button, self.choose_e1_prediction),
            ("3  Create a new result", "Use our trained E1 or E2 model to segment an MRI. Review the result when it is ready.", self.welcome_generate_button, lambda: self.tabs.setCurrentIndex(3)),
        ):
            card = QFrame()
            card.setObjectName("startCard")
            card_layout = QVBoxLayout(card)
            heading = QLabel(title)
            heading.setWordWrap(True)
            heading.setObjectName("cardTitle")
            card_layout.addWidget(heading)
            detail = QLabel(description)
            detail.setWordWrap(True)
            card_layout.addWidget(detail, 1)
            button.clicked.connect(action)
            compact_action(button)
            card_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
            cards.addWidget(card, 1)
        welcome_layout.addLayout(cards)
        self.welcome_example_button = QPushButton("Try the public Ernie example")
        self.welcome_example_button.clicked.connect(self.load_ernie)
        self.welcome_model_button = QPushButton("Open a model folder…")
        self.welcome_model_button.setToolTip("Open a SimNIBS head model or an exported project model folder.")
        self.welcome_model_button.clicked.connect(self.choose_model)
        self.welcome_model_button.setFlat(True)
        self.welcome_auxiliary = QWidget()
        auxiliary_layout = QHBoxLayout(self.welcome_auxiliary)
        auxiliary_layout.setContentsMargins(0, 0, 0, 0)
        auxiliary_layout.setSpacing(12)
        for button in (self.welcome_example_button, self.welcome_model_button):
            compact_action(button)
            auxiliary_layout.addWidget(button)
        auxiliary_layout.addStretch(1)
        welcome_layout.addWidget(self.welcome_auxiliary)
        welcome_layout.addStretch()
        self.preview_stack.addWidget(self.welcome)
        self.slice_container = QWidget()
        views = QHBoxLayout(self.slice_container)
        views.setContentsMargins(0, 0, 0, 0)
        views.setSpacing(10)
        self.panels = [SlicePanel("Axial", 2, ("L", "R", "A", "P")),
                       SlicePanel("Coronal", 1, ("L", "R", "S", "I")),
                       SlicePanel("Sagittal", 0, ("P", "A", "S", "I"))]
        for panel in self.panels:
            views.addWidget(panel, 1)
        self.preview_stack.addWidget(self.slice_container)
        row.addWidget(self.preview_stack, 1)
        inspection_scroll = QScrollArea()
        inspection_scroll.setWidgetResizable(True)
        inspection_scroll.setWidget(inspection)
        self.tabs.addTab(inspection_scroll, "MRI images")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(processing)
        self.processing_tabs = QTabWidget()
        self.processing_tabs.setObjectName("referenceModes")
        self.processing_tabs.tabBar().setObjectName("referenceModeBar")
        self.processing_tabs.addTab(scroll, "Single MRI")
        self.batch = BatchPanel()
        batch_scroll = QScrollArea()
        batch_scroll.setWidgetResizable(True)
        batch_scroll.setWidget(self.batch)
        self.processing_tabs.addTab(batch_scroll, "CHARM batch")
        self.batch.busy_changed.connect(self.update_controls)
        self.batch.notice.connect(self.show_notice)
        self.reference_page = QFrame()
        self.reference_page.setObjectName("referencePanel")
        reference_layout = QVBoxLayout(self.reference_page)
        reference_layout.setContentsMargins(18, 16, 18, 18)
        reference_layout.setSpacing(10)
        reference_title = QLabel("Reference tools")
        reference_title.setObjectName("referenceTitle")
        reference_layout.addWidget(reference_title)
        reference_hint = QLabel("Choose a mode below: process one MRI or manage a CHARM batch.")
        reference_hint.setWordWrap(True)
        reference_hint.setObjectName("subtitle")
        reference_layout.addWidget(reference_hint)
        reference_layout.addWidget(self.processing_tabs, 1)
        self.reference_shell = centered_page(self.reference_page)
        self.tabs.addTab(self.reference_shell, "Reference tools")
        self.mesh_view = MeshView()
        self.mesh_view.detail_requested.connect(self.change_surface_detail)
        self.mesh_view.regions_requested.connect(self.change_regions)
        self.mesh_view.region_picked.connect(lambda name: self.feedback.setText(f"Brain region · {name}"))
        self.tabs.addTab(self.mesh_view, "3D view")
        self.inference = InferencePanel()
        self.inference_scroll = QScrollArea()
        self.inference_scroll.setWidgetResizable(True)
        self.inference_scroll.setWidget(self.inference)
        center_page_content(self.inference_scroll, self.inference)
        self.tabs.addTab(self.inference_scroll, "AI segmentation")
        self.tabs.tabBar().setDrawBase(False)
        self.processing_tabs.tabBar().setDrawBase(False)
        for index, help_text in enumerate((
            "Open an MRI, move through its slices, and add a saved tissue overlay.",
            "Optional SimNIBS CHARM reconstruction and batch monitoring. Not needed to view an MRI or use our AI model.",
            "Rotate the loaded result and show or hide its tissues and MRI planes.",
            "Generate a new segmentation with a trained E1 or E2 model; this is not model training.",
        )):
            self.tabs.setTabToolTip(index, help_text)
        self.inference.busy_changed.connect(self.update_controls)
        self.inference.notice.connect(self.show_notice)
        self.inference.completed.connect(self.inference_completed)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.model_button.setText("Open 3D mesh in Gmsh")
        self.feedback = QLabel("Choose a task above to get started.")
        self.feedback.setFixedHeight(20)
        self.feedback.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.feedback.setToolTip("Additional workflow details; select Details in the notification for the full error.")
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.feedback)
        for control in (self.level, self.width):
            control.valueChanged.connect(self.refresh_slices)
        self.opacity.valueChanged.connect(self.refresh_slices)
        for panel in self.panels:
            panel.slider.valueChanged.connect(self.refresh_slices)
        self.update_controls()
        self.setStyleSheet(stylesheet())
        if account is not None:
            self.configure_workspace(header, layout)

    def configure_workspace(self, header, layout):
        setup = self.store.setup(self.account)
        physician = self.account.role == "physician"
        if physician:
            self.inference.python.clear()
            self.inference.model.clear()
            self.inference.model_paths = {"E1": "", "E2": ""}
            if setup is None:
                setup = self.local_physician_setup()
        if not physician:
            self.inference.restore_local_defaults()
        if setup is not None:
            defaults = setup if physician else {key: value for key, value in setup.items() if key not in ("mri", "output")}
            self.inference.apply_local_defaults(defaults)
            for key, field in (("charm", self.charm), ("charm_output", self.output)):
                if key in setup:
                    field.setText(setup[key])
        account_button = self.account_button = QToolButton()
        account_button.setText(f"{ROLES[self.account.role]} · {self.account.username}")
        account_button.setObjectName("importOptions")
        account_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(account_button)
        menu.setObjectName("accountMenu")
        menu.setFont(account_button.font())
        account_button.setMenu(menu)
        header.addWidget(account_button)
        if physician:
            self.inference.mri.clear()
            self.notifications.setFixedHeight(80)
            self.physician = PhysicianWorkspace(self, self.store, self.account, setup, header, layout)
        else:
            output = setup.get("output", "") if setup is not None else self.inference.output.text()
            self.inference.add_physician_setup(output, self.save_workstation_setup)
            menu.addAction("Physician model setup…", self.open_physician_setup)
            menu.addAction("Create local account…", self.create_local_account)
            menu.addAction("Open Physician workspace…", lambda: self.switch_account("physician"))
            menu.addSeparator()
        menu.addAction("Switch account…", lambda: self.switch_account("choose"))
        menu.addAction("Sign out", lambda: self.switch_account("signin"))

    def open_physician_setup(self):
        self.tabs.setCurrentWidget(self.inference_scroll)
        self.inference.setup_button.setChecked(True)
        self.inference_scroll.verticalScrollBar().setValue(0)

    def validate_physician_setup(self, setup):
        experiment = setup.get("experiment")
        models = setup.get("models")
        if experiment not in ("E1", "E2") or not isinstance(models, dict):
            raise ValueError("Choose a segmentation model version.")
        runtime, weights = setup.get("python"), models.get(experiment)
        if not isinstance(runtime, str) or not runtime.strip() or not isinstance(weights, str) or not weights.strip():
            raise ValueError("Choose Inference Python and a Trained model folder in Model setup.")
        model = Path(weights).expanduser()
        validate_model_files(Path(runtime).expanduser(), model)
        output = Path(setup["output"]).expanduser() if setup.get("output") else self.store.directory
        validate_output_folder(output, model)

    def local_physician_setup(self):
        local = self.inference.read_local_defaults() or {}
        keys = ("experiment", "models", "python", "output", "device", "tta")
        setup = {key: local[key] for key in keys if key in local}
        try:
            self.validate_physician_setup(setup)
        except (OSError, TypeError, ValueError):
            return None
        return setup

    def save_workstation_setup(self):
        if self.account is None or self.account.role != "technical" or self.busy:
            return
        settings = self.inference.workstation_defaults()
        settings.update(charm=self.charm.text().strip(), charm_output=self.output.text().strip())
        try:
            self.validate_physician_setup(settings)
            self.store.save_setup(self.account, settings)
        except STORE_ERRORS as error:
            self.show_notice("error", "Setup could not be saved", str(error))
            return
        self.show_notice("success", "Physician model saved",
                         "New physician sessions use this setup with the T1 MRI opened in each study.")

    def create_local_account(self):
        if self.account is None or self.account.role != "technical" or self.busy:
            return
        if self.workspace_pages.currentIndex() != 0:
            return
        form = show_account_form(self.workspace_pages, self.store, actor=self.account)
        form.created.connect(lambda account: self.show_notice(
            "success", "Account created", f"The {ROLES[account.role]} account is ready to sign in."))

    def switch_account(self, destination="choose"):
        if self.busy:
            self.show_notice("info", "Study operation in progress", "Finish or stop the current operation before signing out.")
            return
        title, message = ("Sign out?", "End this session and return to sign-in?") if destination == "signin" else (
            "Switch account?", "End this session and sign in to another workspace?")
        answer = QMessageBox.question(self, title, message,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.switching_account = True
            self.next_workspace = destination
            if not self.close():
                self.switching_account = False

    def refresh_import_options(self):
        assumed = self.e1_assume_mm.isChecked()
        self.standard_import_action.setChecked(not assumed)
        self.assume_import_action.setChecked(assumed)
        self.import_options_button.setText("Import options · Assume mm" if assumed else "Import options · Standard")
        self.import_options_button.setProperty("attention", assumed)
        self.import_options_button.setToolTip(
            "Optional. Current choice: assume mm for older E1 files; physical scale is unverified."
            if assumed else "Optional. Standard reads units from the MRI file. Open this menu only to change that choice.")
        refresh_style(self.import_options_button)

    def import_menu_state(self, opened):
        self.import_options_button.setProperty("menuOpen", opened)
        refresh_style(self.import_options_button)

    def show_fitted(self):
        """Use Qt's logical desktop bounds, including display scaling and taskbars."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.setMinimumSize(min(900, available.width()), min(560, available.height()))
            self.resize(min(1440, available.width()), min(900, available.height()))
        self.showMaximized()

    @property
    def busy(self):
        return (self.task is not None or self.timer.isActive()
                or (self.inference is not None and self.inference.busy)
                or (self.batch is not None and self.batch.busy))

    def update_controls(self):
        busy = self.busy
        for control in (self.open_button, self.open_model_button, self.example_button, self.selected_button,
                        self.open_e1_button, self.e1_assume_mm, self.import_options_button,
                        self.welcome_open_button, self.welcome_saved_button, self.welcome_generate_button,
                        self.welcome_model_button, self.welcome_example_button):
            control.setEnabled(not busy)
        self.sidebar_column.setVisible(self.volume is not None)
        self.preview_stack.setCurrentWidget(self.slice_container if self.volume is not None else self.welcome)
        batch_external = self.batch is not None and self.batch.external_active
        self.mesh_view.set_detail_available(not busy and not batch_external)
        self.start_button.setEnabled(not busy and not batch_external)
        self.labels_button.setEnabled(self.volume is not None and not busy)
        for control in (self.level, self.width, self.auto_button):
            control.setEnabled(self.volume is not None)
        self.clear_button.setEnabled(self.overlay is not None and not busy)
        self.opacity.setEnabled(self.overlay is not None)
        self.existing_report_button.setEnabled(self.head_model is not None and self.head_model.report is not None and not busy)
        self.export_button.setEnabled(self.export_source is not None and not busy)
        if self.inference is not None:
            self.inference.set_available(self.task is None and not self.timer.isActive()
                                         and not self.batch.busy and not batch_external)
        if self.batch is not None:
            self.batch.set_available(self.task is None and not self.timer.isActive()
                                     and not (self.inference is not None and self.inference.busy))
        if self.physician is not None:
            self.physician.refresh()
        if self.closing and not busy:
            QTimer.singleShot(0, self.close)

    def choose_mri(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open T1 MRI", str(Path.home()), "NIfTI images (*.nii *.nii.gz)")
        if path:
            self.load_mri(path)

    def choose_model(self):
        path = QFileDialog.getExistingDirectory(self, "Open a SimNIBS or exported model folder", str(Path.home()))
        if path:
            self.load_head_model(path)

    def choose_e1_prediction(self):
        directory = str(self.volume.path.parent) if self.volume is not None else str(Path.home())
        mri, _ = QFileDialog.getOpenFileName(self, "Choose the MRI for this result", directory, "NIfTI images (*.nii *.nii.gz)")
        if not mri:
            return
        prediction, _ = QFileDialog.getOpenFileName(self, "Choose its saved segmentation", str(Path(mri).parent), "NIfTI labels (*.nii *.nii.gz)")
        if prediction:
            self.load_e1_prediction(mri, prediction, assume_mm=self.e1_assume_mm.isChecked())

    def load_e1_prediction(self, mri_path, prediction_path, assume_mm=False, show_3d=False):
        if self.busy:
            return
        self.clear_model()
        self.volume = None
        self.clear_overlay()
        for panel in self.panels:
            panel.set_volume(None)
        self.metadata.clear()
        self.source.setText(Path(prediction_path).name)
        self.feedback.setText("Opening MRI and prediction; extracting display surfaces…")
        self.tabs.setCurrentIndex(0)
        def loaded(model):
            self.model_loaded(model)
            if show_3d:
                self.tabs.setCurrentIndex(2)
                self.inference.status.setText("Inference complete. New prediction opened in 2D/3D.")
                self.feedback.setText("New result created on this computer · " + self.feedback.text())
        on_error = (lambda error: self.inference.status.setText("Inference complete; could not open the new result in 3D: " + error)) if show_3d else None
        self.run_task(lambda: load_e1_model(mri_path, prediction_path, assume_mm=assume_mm), loaded,
                      on_error=on_error, activity="Opening segmentation and building its 3D preview")

    def inference_completed(self, job):
        if self.closing:
            return
        if self.physician is not None:
            self.physician.inference_completed(job)
            return
        self.e1_assume_mm.setChecked(job.assume_mm)
        self.load_e1_prediction(job.mri, job.prediction, assume_mm=job.assume_mm, show_3d=True)

    def change_surface_detail(self, step, smoothing=None):
        if self.busy or self.head_model is None or self.head_model.kind != "e1":
            return
        current = self.head_model
        if smoothing is None:
            smoothing = current.surface_smoothing
        if step == current.surface_step and smoothing == current.surface_smoothing:
            return
        self.feedback.setText("Rebuilding display surfaces from the saved segmentation…")
        def loaded(model):
            self.head_model = model
            self.mesh_view.replace_model(model)
            detail = "Auto" if step is None else f"{step} voxel" + ("s" if step != 1 else "")
            self.feedback.setText(f"3D preview updated · {detail} · smoothing {smoothing:.2f}. Saved segmentation unchanged.")
        self.run_task(lambda: load_e1_model(current.volume.path, current.labels[0],
                                           assume_mm=current.units_assumed, surface_step=step,
                                           surface_smoothing=smoothing), loaded,
                      error_title="Surface detail could not be updated",
                      recovery="The previous preview is still open. Try a coarser voxel step or less smoothing, then apply again.",
                      activity="Updating 3D surface detail and smoothing")

    def change_regions(self, atlas):
        """Color charm's cortex with an atlas, computed in the background; an empty atlas removes it."""
        model = self.head_model
        if not atlas or model is None or model.kind != "simnibs":
            self.mesh_view.set_regions(None)
            return
        from mesh_viewer import regions_module
        subject_regions = regions_module().subject_regions
        def loaded(regions):
            self.mesh_view.set_regions(regions)
            self.feedback.setText(f"Brain regions · {atlas} · {len(regions.regions())} regions on charm's pial surface. "
                                  "Click the cortex to name a region.")
        self.feedback.setText(f"Mapping the {atlas} atlas onto the cortex…")
        self.run_task(lambda: subject_regions(model.directory, atlas), loaded,
                      error_title="Brain regions could not be colored",
                      recovery="Check that SimNIBS 4 is installed and the folder has charm surfaces, then choose the atlas again.",
                      activity="Coloring brain regions")

    def clear_model(self):
        self.head_model = None
        self.tissues = {}
        self.mesh_view.clear()
        self.update_controls()

    def load_head_model(self, directory):
        if self.busy:
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
        self.run_task(lambda: load_model(directory), self.model_loaded, activity="Opening head model")

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
            export = "" if model.export_source else "Export needs MRI and prediction units stated in their headers. "
            self.feedback.setText("Segmentation ready · review the MRI images or open 3D view. " + export + model.geometry_note)
        else:
            self.feedback.setText(" ".join(("Model ready · review the MRI images or open 3D view. Check that the model and MRI line up.", *model.notes)))

    def choose_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Name a new folder for the exported model", str(Path.home() / "head_model"))
        if path:
            self.export_model(path)

    def export_model(self, out, *, callback=None):
        if self.busy or self.export_source is None:
            return
        t1, labels, scheme = self.export_source
        self.feedback.setText("Cleaning labels, building head and brain surfaces, and verifying the export…")

        def build():
            build_model(t1, labels, out, label_scheme=scheme)
            return load_model(out)

        self.run_task(build, callback or self.export_finished, "Could not export: ",
                      error_title="Model could not be exported",
                      recovery="Check the error details and choose a new output folder outside Git before retrying.",
                      activity="Exporting and verifying head model")

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
        if self.physician is not None:
            self.physician.refresh()

    def load_ernie(self):
        self.use_ernie()
        if self.t1.text():
            self.load_mri(self.t1.text())

    def clear_task_error(self):
        self.notifications.setCurrentWidget(self.ready_banner)
        self.error_title.clear()
        self.error_message.clear()
        self.error_recovery.clear()
        self.error_detail = ""
        self.error_details_button.hide()
        if self.volume is None:
            for panel in self.panels:
                panel.canvas.set_empty_message("Open a T1 MRI to inspect slices")

    def show_error_details(self):
        if not self.error_detail:
            return
        dialog = QDialog(self)
        dialog.setObjectName("workspaceDialog")
        dialog.setWindowTitle(self.error_title.text())
        dialog.resize(640, 330)
        layout = QVBoxLayout(dialog)
        details = QPlainTextEdit(self.error_detail)
        details.setReadOnly(True)
        layout.addWidget(details, 1)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        controls.rejected.connect(dialog.reject)
        layout.addWidget(controls)
        dialog.exec()
        dialog.deleteLater()

    def show_notice(self, level, title, message, *, recovery=""):
        if level == "error":
            first_line = message.strip().partition("\n")[0].strip()
            summary = first_line if len(first_line) <= 150 else first_line[:147].rstrip() + "…"
            self.error_title.setText(title)
            self.error_message.setText(summary)
            self.error_recovery.setText(recovery)
            self.error_recovery.setVisible(bool(recovery))
            self.error_detail = message if summary != message.strip() else ""
            self.error_details_button.setVisible(bool(self.error_detail))
            self.notifications.setCurrentWidget(self.error_banner)
            message = summary
        else:
            self.result_banner.setProperty("level", level)
            self.result_banner.style().unpolish(self.result_banner)
            self.result_banner.style().polish(self.result_banner)
            self.result_title.setText(title)
            self.result_message.setText(message)
            self.result_message.setToolTip(message)
            self.notifications.setCurrentWidget(self.result_banner)
        self.notifications.show()
        if hasattr(self, "feedback") and self.task is None:
            self.feedback.setText(title + " · " + message)

    def refresh_activity(self):
        seconds = self.activity_clock.elapsed() // 1000
        self.activity_label.setText(f"{self.activity_name} · {seconds // 60:02d}:{seconds % 60:02d} elapsed\n"
                                    "Please wait. Completion time is not yet known.")

    def run_task(self, function, callback, failure="Could not load: ", on_error=None,
                 error_title="Unable to open the selected input",
                 recovery="Check the selected file or folder, then try again.",
                 activity="Preparing preview"):
        if self.busy:
            return
        self.clear_task_error()
        self.activity_name = activity
        self.activity_clock.start()
        self.refresh_activity()
        self.notifications.setCurrentWidget(self.activity_banner)
        self.activity_timer.start()
        if self.volume is None:
            for panel in self.panels:
                panel.canvas.set_empty_message("Preparing preview…\nSlices appear when loading completes.")
        self.task = LoadTask(function, self)
        def loaded(value):
            try:
                callback(value)
            except Exception as error:
                failed("Preview could not be displayed: " + (str(error) or type(error).__name__))
                return
            self.show_notice("success", "Operation completed", self.feedback.text())
        self.task.loaded.connect(loaded)
        def failed(error):
            self.feedback.setText(failure + error)
            self.show_notice("error", error_title, error, recovery=recovery)
            if self.volume is None:
                for panel in self.panels:
                    panel.canvas.set_empty_message("No MRI preview\nCheck the error above, then choose a valid T1 MRI.")
            if on_error is not None:
                on_error(error)
        self.task.failed.connect(failed)
        self.task.finished.connect(self.task_finished)
        self.update_controls()
        self.task.start()

    def task_finished(self):
        task, self.task = self.task, None
        self.activity_timer.stop()
        if self.notifications.currentWidget() is self.activity_banner:
            self.notifications.setCurrentWidget(self.ready_banner)
        self.activity_label.clear()
        task.deleteLater()
        self.update_controls()

    def load_mri(self, path):
        if not path or self.busy:
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
        self.run_task(lambda: load_volume(path), self.mri_loaded,
                      error_title="MRI could not be opened",
                      recovery="Choose a valid 3D MRI (.nii or .nii.gz) using Open MRI, then try again.",
                      activity="Opening T1 MRI and preparing slices")

    def mri_loaded(self, volume):
        self.volume = volume
        self.inference.mri.setText(str(volume.path))
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
        if self.volume is None or self.busy:
            return
        self.clear_model()
        self.clear_overlay()
        self.feedback.setText("Aligning discrete tissue labels to the MRI grid…")
        self.run_task(lambda: load_labels(path, self.volume), self.labels_loaded, activity="Aligning tissue labels to MRI")

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
        if self.busy or (self.batch is not None and self.batch.external_active):
            return
        selected = Path(self.t1.text()).expanduser().resolve()
        source = self.volume.path if self.volume is not None else None
        if self.physician is not None:
            source = self.physician.source_path
        if source != selected:
            self.feedback.setText("Load and inspect the selected T1 MRI before starting CHARM.")
            self.show_notice("error", "MRI inspection required", self.feedback.text())
            self.tabs.setCurrentIndex(0)
            return
        super().start_job()
        if self.timer.isActive() and self.physician is None:
            self.show_notice("info", "CHARM reconstruction started", "Follow live output in Reference tools. Review the result before use.")
        self.update_controls()

    def tick(self):
        was_running = self.timer.isActive()
        super().tick()
        if was_running and not self.timer.isActive():
            self.update_controls()
            if self.runner.cancelled:
                self.show_notice("info", "Reconstruction cancelled", self.status.text())
            elif not self.runner.complete or self.run_error:
                self.show_notice("error", "Reconstruction did not complete", self.status.text())
            if self.runner.complete and not self.run_error and not self.closing:
                if self.physician is not None:
                    self.physician.reconstruction_completed(self.runner.job.model_dir)
                else:
                    self.load_head_model(self.runner.job.model_dir)

    def confirm_reconstruction_cancel(self):
        if not self.timer.isActive():
            return
        answer = QMessageBox.question(self, "Stop active reconstruction?",
            "Stop CHARM and its child processes? Partial output and logs will remain.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes and self.timer.isActive():
            self.cancel_job()

    def closeEvent(self, event):
        if self.task is not None:
            self.feedback.setText("Image loading is finishing. Close again once it completes.")
            event.ignore()
            return
        if self.batch is not None and self.batch.busy:
            answer = QMessageBox.question(self, "Stop this CHARM batch?",
                "Closing will stop this window's batch and its child processes. Partial outputs and logs remain.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer == QMessageBox.StandardButton.Yes:
                self.closing = True
                if self.batch.busy:
                    self.batch.cancel()
                elif not self.busy:
                    QTimer.singleShot(0, self.close)
            event.ignore()
            return
        if self.inference.busy:
            answer = QMessageBox.question(self, "Stop segmentation inference?",
                "Closing will stop inference and its child workers. Partial files and logs will remain.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer == QMessageBox.StandardButton.Yes:
                self.closing = True
                if self.inference.busy:
                    self.inference.cancel()
                elif not self.busy:
                    QTimer.singleShot(0, self.close)
            event.ignore()
            return
        if not self.busy and self.physician is not None and not self.physician.confirm_leave():
            self.closing = False
            event.ignore()
            return
        super().closeEvent(event)
        if event.isAccepted():
            if self.batch is not None:
                self.batch.shutdown()
            if self.inference.runner is not None:
                self.inference.runner.close()
            self.mesh_view.shutdown()
            if self.physician is not None:
                self.physician.progress_timer.stop()
            if self.store is not None:
                self.session_closed.emit(self.switching_account)


def open_startup_selection(window, args):
    if "--model" in args:
        window.load_head_model(args[args.index("--model") + 1])
    elif "--ernie" in args:
        window.load_ernie()
    if "--batch" in args or "--batch-output" in args:
        if "--batch-output" in args:
            window.batch.output.setText(args[args.index("--batch-output") + 1])
        window.tabs.setCurrentIndex(1)
        window.processing_tabs.setCurrentIndex(1)
        window.batch.monitor()


class WorkspaceSession(QObject):
    def __init__(self, app, store, startup_args=()):
        super().__init__(app)
        self.app, self.store = app, store
        self.window = None
        self.dialog = None
        self.startup_args = list(startup_args)
        self.app.setQuitOnLastWindowClosed(False)

    def start(self):
        technical_cli = any(option in self.startup_args for option in ("--model", "--ernie", "--batch", "--batch-output"))
        self.open_sign_in("technical" if technical_cli else None, animate=True)

    def open_sign_in(self, role=None, *, animate=False):
        self.dialog = SignIn(self.store, role=role, animate=animate)
        self.dialog.finished.connect(self.finish_sign_in)
        self.dialog.showMaximized()

    def finish_sign_in(self, _):
        account = self.dialog.account
        self.dialog.deleteLater()
        self.dialog = None
        if account is None:
            self.app.quit()
            return
        try:
            authenticated = Window(self.store, account)
        except STORE_ERRORS as error:
            QMessageBox.critical(None, "Workspace unavailable", str(error))
            self.open_sign_in()
            return
        self.window = authenticated
        authenticated.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        authenticated.session_closed.connect(self.finish_workspace)
        authenticated.show_fitted()
        startup_args, self.startup_args = self.startup_args, []
        if account.role == "technical":
            open_startup_selection(authenticated, startup_args)

    def finish_workspace(self, switch):
        destination = self.window.next_workspace

        def return_from_session():
            self.window = None
            if not switch:
                self.app.quit()
                return
            self.open_sign_in(destination if destination in ROLES else None)

        QTimer.singleShot(0, return_from_session)


def main():
    for option in ("--model", "--batch-output"):
        if option in sys.argv and sys.argv.index(option) + 1 >= len(sys.argv):
            raise SystemExit(f"{option} needs a folder path")
    app = QApplication(sys.argv)
    app.setApplicationName("MRI Workbench")
    app.setOrganizationName("TMS HeadSeg")
    apply_light_theme(app)
    if "--smoke-test" in sys.argv:
        with TemporaryDirectory(prefix="workbench-smoke-") as directory:
            session = WorkspaceSession(app, WorkspaceStore(directory))
            session.start()
            QTimer.singleShot(2600, session.dialog.close)
            code = app.exec()
        sys.exit(code)
    store = WorkspaceStore(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    session = WorkspaceSession(app, store, sys.argv[1:])
    session.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
