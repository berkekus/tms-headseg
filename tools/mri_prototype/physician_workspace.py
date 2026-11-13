"""Physician workflow over the existing MRI, inference, CHARM and 3D components."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QTimer, Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QPushButton, QToolButton, QVBoxLayout, QWidget,
)

from model import load_e1_model, load_model
from mesh_viewer import regions_module
from volume import load_volume
from visual_theme import centered_page, compact_action
from workspace_login import STORE_ERRORS
from workspace_store import STUDY_KINDS, fingerprint, result_identity


MRI_FILTER = "NIfTI images (*.nii *.nii.gz)"
MANAGED_FOLDER = ".workbench-users"


class PhysicianWorkspace(QObject):
    def __init__(self, window, store, account, setup, header, layout):
        super().__init__(window)
        self.window = window
        self.store = store
        self.account = account
        self.setup = setup or {}
        self.study_id = None
        self.source_path = None
        self.source_digest = None
        self.result_id = None
        self.view_name = None
        self.saved_views = {}
        self.baseline = None
        window.feedback.setTextFormat(Qt.TextFormat.PlainText)

        for index in (1, 3):
            window.tabs.setTabVisible(index, False)
        for widget in (window.open_e1_button, window.import_options_button, window.example_button,
                       window.selected_button, window.open_button, window.open_model_button,
                       window.labels_button, window.clear_button, window.more_file_actions):
            widget.hide()
        window.mesh_view.group_inspector()
        self.open_button = self.button("Open MRI…", self.open_mri)
        self.studies_button = self.button("Open study…", self.open_study)
        header.insertWidget(2, self.open_button)
        header.insertWidget(3, self.studies_button)

        self.step_label = QLabel()
        self.step_label.setObjectName("subtitle")
        steps = QHBoxLayout()
        steps.addWidget(self.step_label, 1)
        layout.insertLayout(1, steps)

        footer = QHBoxLayout()
        self.back_button = self.button("← Back to studies", self.back_to_studies)
        self.back_button.setAccessibleName("Back to studies")
        layout.removeWidget(window.feedback)
        feedback_policy = window.feedback.sizePolicy()
        feedback_policy.setRetainSizeWhenHidden(True)
        window.feedback.setSizePolicy(feedback_policy)
        footer.addWidget(window.feedback, 1)
        footer.addWidget(self.back_button)
        layout.addLayout(footer)

        self.study_bar = QWidget()
        bar = QHBoxLayout(self.study_bar)
        bar.setContentsMargins(0, 0, 0, 0)
        self.study_label = QLabel()
        self.study_label.setObjectName("cardTitle")
        self.study_label.setTextFormat(Qt.TextFormat.PlainText)
        self.study_label.setWordWrap(True)
        bar.addWidget(self.study_label, 1)
        self.reconstruct_button = self.button("Create detailed head model…", self.create_head_model)
        self.build_button = self.button("Build 3D view", self.build, primary=True)
        self.build_button.setToolTip("Build from the T1 MRI open in this study using the workstation model.")
        self.stop_button = self.button("Stop preparation", self.stop)
        self.review_button = self.button("View in 3D", lambda: window.tabs.setCurrentIndex(2), primary=True)
        self.save_button = self.button("Save view…", self.save_view, primary=True)
        self.views_button = QToolButton()
        self.views_button.setText("Saved views")
        self.views_button.setObjectName("importOptions")
        self.views_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.views_menu = QMenu(self.views_button)
        self.views_button.setMenu(self.views_menu)
        self.views_menu.aboutToShow.connect(self.fill_views_menu)
        self.results_button = QToolButton()
        self.results_button.setText("Results")
        self.results_button.setObjectName("importOptions")
        self.results_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.results_menu = QMenu(self.results_button)
        self.results_button.setMenu(self.results_menu)
        self.results_menu.aboutToShow.connect(self.fill_results_menu)
        self.result_tools = QToolButton()
        self.result_tools.setText("Result tools")
        self.result_tools.setObjectName("importOptions")
        self.result_tools.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        tools_menu = QMenu(self.result_tools)
        self.result_tools.setMenu(tools_menu)
        self.report_action = tools_menu.addAction("Open result report", self.open_report)
        self.mesh_action = tools_menu.addAction("Open mesh in Gmsh", self.open_mesh)
        self.export_action = tools_menu.addAction("Export head model", self.export_model)
        tools_menu.addAction("Open result folder", self.open_result_folder)
        for widget in (self.reconstruct_button, self.build_button, self.review_button, self.stop_button,
                       self.results_button, self.views_button, self.save_button, self.result_tools):
            bar.addWidget(widget)
        layout.insertWidget(2, self.study_bar)

        welcome = QWidget()
        welcome.setObjectName("workspaceChoices")
        column = QVBoxLayout(welcome)
        column.setContentsMargins(24, 24, 24, 24)
        column.setSpacing(18)
        column.addStretch(1)
        title = QLabel("Start or open a study")
        title.setObjectName("authTitle")
        column.addWidget(title)
        cards = QHBoxLayout()
        cards.setSpacing(20)
        new_card = QFrame()
        new_card.setObjectName("authCard")
        card_layout = QVBoxLayout(new_card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)
        new_title = QLabel("New study")
        new_title.setObjectName("cardTitle")
        card_layout.addWidget(new_title)
        source_hint = QLabel("Choose one T1-weighted MRI (.nii or .nii.gz) to start.")
        source_hint.setWordWrap(True)
        source_hint.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(source_hint, 1)
        self.home_open_button = self.button("Open T1 MRI…", self.open_mri, primary=True)
        card_layout.addWidget(self.home_open_button)
        cards.addWidget(new_card, 1)
        saved_card = QFrame()
        saved_card.setObjectName("authCard")
        saved_layout = QVBoxLayout(saved_card)
        saved_layout.setContentsMargins(24, 24, 24, 24)
        saved_layout.setSpacing(14)
        saved_title = QLabel("Saved study")
        saved_title.setObjectName("cardTitle")
        saved_layout.addWidget(saved_title)
        saved_hint = QLabel("Return to a study with its linked MRI and results.")
        saved_hint.setWordWrap(True)
        saved_hint.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        saved_layout.addWidget(saved_hint, 1)
        saved_layout.addWidget(self.button("Open saved study…", self.open_study))
        saved_layout.addWidget(self.button("Open existing head model…", self.open_head_model))
        cards.addWidget(saved_card, 1)
        column.addLayout(cards)
        column.addStretch(2)
        self.home = centered_page(welcome)
        welcome.setMaximumWidth(1160)
        window.preview_stack.addWidget(self.home)
        self.overlay_button = self.button("Source MRI / tissue overlay", self.toggle_overlay)
        self.overlay_button.setCheckable(True)
        self.overlay_button.setChecked(True)
        window.inspection_sidebar.widget().layout().insertWidget(0, self.overlay_button)
        window.inference.notice.disconnect(window.show_notice)
        window.inference.notice.connect(self.inference_notice)
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(400)
        self.progress_timer.timeout.connect(self.refresh)
        self.progress_timer.start()
        self.refresh()

    def button(self, text, action, primary=False):
        button = QPushButton(text)
        if primary:
            button.setObjectName("primary")
        compact_action(button)
        button.clicked.connect(action)
        return button

    def display_name(self):
        return f"Study {self.study_id[:6].upper()}" if self.study_id else ""

    def refresh(self):
        w = self.window
        result_open = w.head_model is not None and self.result_id is not None
        viewing_3d = result_open and w.tabs.currentIndex() == 2
        running = w.inference.busy or w.timer.isActive()
        opened = w.volume is not None
        w.notifications.setVisible(opened or w.notifications.currentWidget() is not w.ready_banner)
        w.feedback.setVisible(opened and w.notifications.currentWidget() is not w.error_banner)
        stage = 1 if running else 2 if result_open else 1 if opened else 0
        steps = ("1  Open MRI", "2  Prepare", "3  Review")
        self.step_label.setText(" &nbsp; › &nbsp; ".join(
            f'<b style="color: #0f766e">{label}</b>' if index == stage else label
            for index, label in enumerate(steps)
        ))
        self.study_bar.setVisible(opened)
        self.back_button.setVisible(opened)
        self.open_button.setVisible(opened)
        self.studies_button.setVisible(opened)
        w.tabs.tabBar().setVisible(opened)
        self.study_label.setText(f"{self.display_name()} · {self.source_path.name}" if self.source_path else "")
        if w.volume is None:
            w.preview_stack.setCurrentWidget(self.home)
        for button in (self.open_button, self.studies_button, self.back_button, self.reconstruct_button, self.build_button):
            button.setEnabled(not w.busy)
        self.build_button.setVisible(not running and not viewing_3d and (not result_open or w.head_model.kind != "e1"))
        self.reconstruct_button.setVisible(not running and not viewing_3d)
        self.stop_button.setVisible(running)
        self.review_button.setVisible(result_open and not viewing_3d and not running)
        self.results_button.setVisible(result_open and not running)
        self.results_button.setEnabled(not w.busy)
        self.views_button.setVisible(viewing_3d)
        self.views_button.setEnabled(bool(self.saved_views) and not w.busy)
        self.save_button.setVisible(viewing_3d)
        self.save_button.setText("Save view" if self.view_name else "Save view…")
        dirty = viewing_3d and self.dirty()
        self.save_button.setEnabled(not w.busy and (dirty or not self.view_name))
        if viewing_3d and not w.busy:
            suffix = f" · {self.view_name}" if self.view_name else ""
            self.save_button.setToolTip(("Unsaved view changes" if dirty else "Current 3D view") + suffix)
        self.overlay_button.setVisible(w.overlay is not None)
        self.result_tools.setVisible(viewing_3d)
        self.result_tools.setEnabled(not w.busy)
        self.report_action.setEnabled(result_open and self.report_path() is not None)
        self.mesh_action.setEnabled(result_open and w.head_model.kind == "simnibs" and w.head_model.mesh_path is not None)
        self.export_action.setEnabled(w.export_source is not None)
        w.tabs.setTabEnabled(2, result_open)
        if running:
            text = (w.inference.metrics.text() if w.inference.busy else w.elapsed.text())
            w.activity_label.setText(("Building 3D view" if w.inference.busy else "Creating head model") + " · " + text)
            w.notifications.setCurrentWidget(w.activity_banner)

    def allowed_path(self, path):
        path = Path(path).expanduser().resolve()
        parts = path.parts
        for index, part in enumerate(parts[:-1]):
            if part.casefold() == MANAGED_FOLDER and parts[index + 1] != self.account.id:
                raise PermissionError("This file belongs to another Workbench account.")
        return path

    def load_source(self, path, expected=None):
        path = self.allowed_path(path)
        digest = fingerprint(path)
        if expected is not None and digest != expected:
            raise ValueError("This MRI does not match the source linked to the study. Locate the original file.")
        volume = load_volume(path)
        if fingerprint(path) != digest:
            raise ValueError("The source MRI changed while it was being opened.")
        return volume, digest

    def open_mri(self):
        if self.window.busy:
            return
        path, _ = QFileDialog.getOpenFileName(self.window, "Open T1 MRI", "", MRI_FILTER)
        if path and self.confirm_leave():
            self.window.run_task(lambda: self.load_source(path), self.source_loaded,
                                 activity="Opening T1 MRI")

    def reset_view_record(self, result=None):
        self.result_id = result
        self.baseline = None
        self.view_name, self.saved_views = self.store.views(self.account, result) if result else (None, {})

    def source_loaded(self, loaded):
        volume, digest = loaded
        self.study_id = self.store.remember_source(self.account, volume.path, digest)
        self.source_path, self.source_digest = volume.path, digest
        self.reset_view_record()
        w = self.window
        w.clear_model()
        w.clear_overlay()
        w.t1.setText(str(volume.path))
        w.t2.clear()
        w.mri_loaded(volume)
        w.tabs.setCurrentIndex(0)
        self.refresh()

    def back_to_studies(self):
        if self.window.busy or not self.confirm_leave():
            return
        self.study_id = self.source_path = self.source_digest = None
        self.reset_view_record()
        w = self.window
        w.volume = None
        w.tabs.setCurrentIndex(0)
        w.clear_model()
        w.clear_overlay()
        for panel in w.panels:
            panel.set_volume(None)
        w.t1.clear()
        w.t2.clear()
        w.inference.mri.clear()
        w.metadata.clear()
        w.feedback.setText("Open a new MRI or return to a saved study.")
        w.clear_task_error()
        self.refresh()

    def output_directory(self, key):
        value = self.setup.get(key)
        root = Path(value).expanduser().resolve() if value else self.store.directory / "results"
        if any((parent / ".git").exists() for parent in (root, *root.parents)):
            raise ValueError("Technical Team must configure an output folder outside Git.")
        path = self.allowed_path(root / MANAGED_FOLDER / self.account.id)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path

    def verify_current_source(self):
        if not self.source_path or fingerprint(self.allowed_path(self.source_path)) != self.source_digest:
            raise ValueError("The source MRI changed. Open the study again and locate the original MRI.")

    def build(self):
        w = self.window
        if w.busy or not self.source_path or not self.confirm_leave():
            return
        try:
            if not w.inference.python.text() or not w.inference.model.text():
                raise ValueError("Technical Team can save a model in AI segmentation → Model setup. You can still inspect this MRI.")
            self.verify_current_source()
            w.inference.output.setText(str(self.output_directory("output")))
        except STORE_ERRORS as error:
            w.show_notice("error", "3D setup required", str(error))
            return
        w.inference.mri.setText(str(self.source_path))
        w.inference.start()
        self.refresh()

    def create_head_model(self):
        w = self.window
        if w.busy or not self.source_path:
            return
        if not w.charm.text() or not Path(w.charm.text()).is_file():
            w.show_notice("error", "Head model setup required",
                          "Technical Team needs to configure the CHARM launcher. You can still open an existing head model.")
            return
        dialog = QDialog(w)
        dialog.setWindowTitle("Create detailed head model")
        column = QVBoxLayout(dialog)
        label = QLabel(f"Source T1 MRI · {self.source_path.name}")
        label.setTextFormat(Qt.TextFormat.PlainText)
        column.addWidget(label)
        column.addWidget(QLabel("T2 is optional. If added, confirm it belongs to the same study."))
        t2 = []
        t2_label = QLabel("No T2 selected")
        t2_label.setTextFormat(Qt.TextFormat.PlainText)
        column.addWidget(t2_label)

        def choose_t2():
            path, _ = QFileDialog.getOpenFileName(dialog, "Choose matching T2 MRI", "", MRI_FILTER)
            if path and QMessageBox.question(dialog, "Confirm matching study",
                    "Does this T2 MRI belong to the same study as the open T1?") == QMessageBox.StandardButton.Yes:
                try:
                    selected = self.allowed_path(path)
                    if selected == self.source_path:
                        raise ValueError("Choose a separate T2 MRI for this study.")
                    t2[:] = [selected]
                    t2_label.setText(t2[0].name)
                except STORE_ERRORS as error:
                    QMessageBox.warning(dialog, "T2 unavailable", str(error))

        column.addWidget(self.button("Add or change T2…", choose_t2))
        actions = QHBoxLayout()
        actions.addWidget(self.button("Cancel", dialog.reject))
        actions.addStretch(1)
        actions.addWidget(self.button("Create head model", dialog.accept, primary=True))
        column.addLayout(actions)
        if dialog.exec() != QDialog.DialogCode.Accepted or not self.confirm_leave():
            return
        try:
            self.verify_current_source()
            w.output.setText(str(self.output_directory("charm_output")))
        except STORE_ERRORS as error:
            w.show_notice("error", "Head model could not start", str(error))
            return
        w.t1.setText(str(self.source_path))
        w.t2.setText(str(t2[0]) if t2 else "")
        w.subject.setText("study_" + self.study_id[:8] + "_" + uuid4().hex[:8])
        w.start_job()

    def stop(self):
        if self.window.inference.busy:
            self.window.inference.confirm_cancel()
        elif self.window.timer.isActive():
            self.window.confirm_reconstruction_cancel()

    def inference_notice(self, level, title, message):
        if self.window.inference.busy:
            self.refresh()
        else:
            self.window.show_notice(level, title, message)

    def inference_completed(self, job):
        def read():
            self.verify_current_source()
            model = load_e1_model(job.mri, self.allowed_path(job.prediction), assume_mm=job.assume_mm)
            self.verify_current_source()
            return model, result_identity(model)
        self.window.run_task(read, self.new_prediction_loaded, activity="Opening the generated 3D view")

    def new_prediction_loaded(self, loaded):
        model, digest = loaded
        result = self.store.add_result(self.account, self.study_id, "prediction", model.labels[0],
                                       digest, model.units_assumed)
        self.show_model(model, result)

    def reconstruction_completed(self, folder):
        def read():
            self.verify_current_source()
            model = load_model(self.allowed_path(folder))
            self.verify_current_source()
            return model, result_identity(model)
        self.window.run_task(read, self.new_head_loaded, activity="Opening the reconstructed head model")

    def new_head_loaded(self, loaded):
        model, digest = loaded
        result = self.store.add_result(self.account, self.study_id, "head", model.directory, digest)
        self.show_model(model, result)

    def open_head_model(self):
        if self.window.busy:
            return
        folder = QFileDialog.getExistingDirectory(self.window, "Open existing head model")
        if folder and self.confirm_leave():
            def read():
                model = load_model(self.allowed_path(folder))
                source = self.allowed_path(model.volume.path)
                return model, result_identity(model), source, fingerprint(source)

            def loaded(data):
                model, digest, self.source_path, self.source_digest = data
                self.study_id = self.store.remember_source(self.account, self.source_path, self.source_digest)
                self.new_head_loaded((model, digest))

            self.window.run_task(read, loaded, activity="Opening saved head model")

    def open_study(self):
        if self.window.busy:
            return
        try:
            studies = self.store.studies(self.account)
        except STORE_ERRORS as error:
            self.window.show_notice("error", "Studies unavailable", str(error))
            return
        if not studies:
            QMessageBox.information(self.window, "Saved studies", "Open a T1 MRI or import a head model to start a study.")
            return
        dialog = QDialog(self.window)
        dialog.setWindowTitle("Open saved study")
        dialog.resize(590, 345)
        column = QVBoxLayout(dialog)
        column.addWidget(QLabel("Choose one study to open its source MRI and saved result."))
        items = QListWidget()
        for study in studies:
            kind = STUDY_KINDS.get(study["kind"], "Source MRI")
            view = f" · {study['active_view']}" if study["active_view"] else ""
            date = datetime.fromtimestamp(study["updated"]).strftime("%Y-%m-%d %H:%M")
            items.addItem(QListWidgetItem(f"{Path(study['source']).name} · {kind}{view} · {date}"))
        items.setCurrentRow(0)
        column.addWidget(items)
        actions = QHBoxLayout()
        relink = self.button("Locate original MRI…", lambda: dialog.done(2))
        actions.addWidget(relink)
        actions.addStretch(1)
        actions.addWidget(self.button("Cancel", dialog.reject))
        actions.addWidget(self.button("Open study", dialog.accept, primary=True))
        column.addLayout(actions)
        items.itemDoubleClicked.connect(dialog.accept)
        choice = dialog.exec()
        if not choice or items.currentRow() < 0:
            return
        study = studies[items.currentRow()]
        path = study["source"]
        if choice == 2 or not Path(path).is_file():
            path, _ = QFileDialog.getOpenFileName(self.window, "Locate the original source MRI", "", MRI_FILTER)
        if path and self.confirm_leave():
            self.open_record(study["id"], path)

    def open_record(self, study_id, source, result_id=None, view_name=None):
        try:
            study, results = self.store.study(self.account, study_id)
            selected = result_id or study["active_result"]
            result = next((entry for entry in results if entry["id"] == selected), None)
            if selected and result is None:
                raise ValueError("The result is unavailable.")
            preferred, views = self.store.views(self.account, selected) if selected else (None, {})
            if view_name and view_name not in views:
                raise ValueError("The saved view is unavailable.")
            view_name = view_name or preferred
            state = views.get(view_name)
        except STORE_ERRORS as error:
            self.window.show_notice("error", "Study could not be opened", str(error))
            return

        def read():
            original = self.allowed_path(source)
            if fingerprint(original) != study["digest"]:
                raise ValueError("This MRI does not match the study. Use Locate original MRI to choose the linked file.")
            if result is None:
                return self.load_source(original, study["digest"])
            path = self.allowed_path(result["path"])
            model = (load_e1_model(original, path, assume_mm=bool(result["assume_mm"]),
                                   surface_step=state["surface_step"] if state else None,
                                   surface_smoothing=state["surface_smoothing"] if state else 0)
                     if result["kind"] == "prediction" else load_model(path))
            if result_identity(model) != result["digest"] or fingerprint(original) != study["digest"]:
                raise ValueError("The source MRI or result differs from the saved study.")
            regions = None
            if state and state["atlas"]:
                regions = regions_module().subject_regions(model.directory, state["atlas"])
            return model, regions, original

        def loaded(data):
            if result is None:
                self.source_loaded(data)
                return
            model, regions, original = data
            self.study_id = self.store.remember_source(self.account, original, study["digest"])
            self.source_path, self.source_digest = original, study["digest"]
            self.store.activate_result(self.account, self.study_id, selected)
            if view_name:
                self.store.activate_view(self.account, selected, view_name)
            self.show_model(model, selected, state, regions)

        self.window.run_task(read, loaded, activity="Opening the study and its saved result")

    def show_model(self, model, result, state=None, regions=None):
        w = self.window
        self.reset_view_record(result)
        w.mesh_view.show_planes.setChecked(False)
        w.mesh_view.region_targets.setChecked(False)
        self.overlay_button.setChecked(True)
        w.model_loaded(model)
        self.refresh()
        w.tabs.setCurrentIndex(2)
        w.mesh_view.ensure_renderer()
        if state is not None:
            self.restore_view(state, regions)
        self.baseline = self.view_state()
        if self.view_name and state is not None:
            w.feedback.setText(f"Restored view · {self.view_name}")
        self.refresh()

    def toggle_overlay(self, checked):
        for panel in self.window.panels:
            panel.labels = self.window.overlay if checked else None
        self.window.refresh_slices()

    def view_state(self):
        w = self.window
        state = w.mesh_view.view_state()
        state.update({"slices": [panel.slider.value() for panel in w.panels], "level": w.level.value(),
                      "width": w.width.value(), "overlay_opacity": w.opacity.value(),
                      "overlay_visible": self.overlay_button.isChecked()})
        return state

    def restore_view(self, state, regions):
        w = self.window
        for panel, index in zip(w.panels, state["slices"], strict=True):
            panel.slider.setValue(index)
        w.level.setValue(state["level"])
        w.width.setValue(state["width"])
        w.opacity.setValue(state["overlay_opacity"])
        self.overlay_button.setChecked(state["overlay_visible"])
        self.toggle_overlay(state["overlay_visible"])
        w.mesh_view.restore_view(state, regions)

    def dirty(self):
        return self.baseline is not None and self.window.head_model is not None and self.view_state() != self.baseline

    def save_view(self, *, new=False):
        if not self.result_id or self.window.busy:
            return False
        name = self.view_name
        if new or not name:
            name, accepted = QInputDialog.getText(self.window, "Save 3D view", "View name")
            if not accepted:
                return False
        try:
            state = self.view_state()
            self.view_name = self.store.save_view(self.account, self.result_id, name, state,
                                                  replace=bool(self.view_name and not new))
            _, self.saved_views = self.store.views(self.account, self.result_id)
        except STORE_ERRORS as error:
            self.window.show_notice("error", "View could not be saved", str(error))
            return False
        self.baseline = state
        self.window.feedback.setText(f"View saved · {self.view_name}")
        self.refresh()
        return True

    def confirm_leave(self):
        if not self.dirty():
            return True
        dialog = QDialog(self.window)
        dialog.setObjectName("workspaceDialog")
        dialog.setWindowTitle("Unsaved 3D view")
        dialog.setStyleSheet(self.window.styleSheet())
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        heading = QLabel("Save view changes before leaving?")
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
        layout.addWidget(QLabel("The study result remains available."))

        discard_code = 2
        stay = self.button("Stay in study", dialog.reject)
        discard = self.button("Discard view changes", lambda: dialog.done(discard_code))
        save = self.button("Save and leave", dialog.accept, primary=True)
        stay.setDefault(True)
        stay.setFocus()
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)
        for button in (stay, discard, save):
            actions.addWidget(button)
        layout.addLayout(actions)
        dialog.ensurePolished()
        for button in (stay, discard, save):
            button.ensurePolished()
            # Leave room for the text plus the Workbench button border and padding.
            width = max(button.fontMetrics().horizontalAdvance(button.text()),
                        self.window.fontMetrics().horizontalAdvance(button.text()))
            button.setMinimumWidth(max(button.sizeHint().width(), width + 32))

        choice = dialog.exec()
        dialog.deleteLater()
        return choice == discard_code or (choice == QDialog.DialogCode.Accepted and self.save_view())

    def fill_views_menu(self):
        self.views_menu.clear()
        for name in self.saved_views:
            action = self.views_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(name == self.view_name)
            action.triggered.connect(lambda checked=False, view=name: self.reopen_view(view))
        self.views_menu.addSeparator()
        self.views_menu.addAction("Save as new view…", lambda: self.save_view(new=True))

    def reopen_view(self, view):
        if not self.window.busy and self.confirm_leave():
            self.open_record(self.study_id, self.source_path, self.result_id, view)

    def fill_results_menu(self):
        self.results_menu.clear()
        try:
            _, results = self.store.study(self.account, self.study_id)
        except STORE_ERRORS as error:
            self.window.show_notice("error", "Results unavailable", str(error))
            return
        for result in results:
            path = Path(result["path"])
            label = path.parent.name if result["kind"] == "prediction" else path.name
            action = self.results_menu.addAction(f"{STUDY_KINDS[result['kind']]} · {label}")
            action.setCheckable(True)
            action.setChecked(result["id"] == self.result_id)
            action.triggered.connect(lambda checked=False, key=result["id"]: self.open_other_result(key))

    def open_other_result(self, result):
        if result != self.result_id and not self.window.busy and self.confirm_leave():
            self.open_record(self.study_id, self.source_path, result)

    def open_result_folder(self):
        if self.result_id and not self.window.busy:
            self.window.open_path(self.window.head_model.directory)

    def report_path(self):
        model = self.window.head_model
        if model.report is not None:
            return model.report
        report = model.directory / "report" / "report.html"
        return report if model.kind == "e1" and report.is_file() else None

    def open_report(self):
        if self.result_id and not self.window.busy and (report := self.report_path()) is not None:
            self.window.open_path(report)

    def open_mesh(self):
        w = self.window
        if self.result_id and not w.busy and w.head_model.mesh_path is not None:
            w.open_mesh(w.head_model.mesh_path, w.charm.text())

    def export_model(self):
        w = self.window
        if w.busy or w.export_source is None or not self.confirm_leave():
            return
        try:
            self.verify_current_source()
            destination = self.output_directory("output") / f"head_{self.study_id[:8]}_{uuid4().hex[:8]}"
        except STORE_ERRORS as error:
            w.show_notice("error", "Model could not be exported", str(error))
            return
        w.export_model(destination, callback=lambda model: self.new_head_loaded((model, result_identity(model))))
