"""Local role and study reopening regressions, with synthetic MRI data."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import nibabel as nib
import numpy as np
from PySide6.QtCore import QCoreApplication, QEvent, QTimer, Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

from prototype import Window, WorkspaceSession
from visual_theme import apply_light_theme
from workspace_login import AccountForm, SignIn
from workspace_store import WorkspaceStore


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = WorkspaceStore(self.root / "workbench")
        self.password = "test account password"
        self.technical = self.store.create_account("operator", self.password, "technical")
        self.physician = self.store.create_account("doctor", self.password, "physician", actor=self.technical)

    def wait_idle(self, window):
        deadline = time.monotonic() + 12
        while window.task is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIsNone(window.task, window.feedback.text())

    def close_login(self, login):
        login.close()
        login.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_selected_role_needs_matching_credentials_and_cannot_change_setup(self):
        login = SignIn(self.store, animate=False)
        self.addCleanup(self.close_login, login)
        login.choose_role("technical")
        login.username.setText(self.physician.username)
        login.password.setText(self.password)
        login.submit.click()
        self.assertIsNone(login.account)
        login.submit.setEnabled(True)
        login.choose_role("physician")
        login.password.setText(self.password)
        login.submit.click()
        self.assertEqual(login.account, self.physician)
        with self.assertRaises(PermissionError):
            self.store.save_setup(login.account, {})
        with self.assertRaises(PermissionError):
            self.store.create_account("intruder", self.password, "technical", actor=login.account)
        self.store.save_setup(self.technical, {"experiment": "E2"})
        self.assertEqual(self.store.setup(self.physician), {"experiment": "E2"})

    def test_welcome_precedes_sign_in_and_routes_to_the_original_workspaces(self):
        hints = self.app.styleHints()
        self.addCleanup(hints.setColorScheme, hints.colorScheme())
        self.addCleanup(self.app.setPalette, self.app.palette())
        self.addCleanup(self.app.setQuitOnLastWindowClosed, self.app.quitOnLastWindowClosed())
        hints.setColorScheme(Qt.ColorScheme.Dark)
        reports_color_scheme = hints.colorScheme() != Qt.ColorScheme.Unknown
        apply_light_theme(self.app)
        if reports_color_scheme:
            self.assertEqual(hints.colorScheme(), Qt.ColorScheme.Light)
        self.assertEqual(self.app.palette().color(QPalette.ColorRole.Base).name(), "#ffffff")
        session = WorkspaceSession(self.app, self.store)
        session.start()

        def close_session():
            if session.dialog is not None:
                session.dialog.reject()
            if session.window is not None:
                session.window.session_closed.disconnect(session.finish_workspace)
                session.window.close()
            session.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

        def sign_in(account):
            dialog = session.dialog
            self.assertEqual(dialog.role, account.role)
            dialog.username.setText(account.username)
            dialog.password.setText(self.password)
            dialog.submit.click()
            self.assertEqual(session.window.account, account)

        self.addCleanup(close_session)
        self.assertIsNone(session.window)
        self.assertIs(session.dialog.stack.currentWidget(), session.dialog.welcome)
        deadline = time.monotonic() + 5
        while session.dialog.stack.currentWidget() is session.dialog.welcome and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIs(session.dialog.stack.currentWidget(), session.dialog.selection)
        self.assertIsNone(session.window)
        session.dialog.role_buttons["technical"].click()
        image = session.dialog.grab().toImage()
        background = image.pixelColor(8, image.height() // 2)
        self.assertEqual((background.name(), background.alpha()), ("#f5f7fa", 255))
        sign_in(self.technical)
        self.assertTrue(session.window.welcome.isVisible())
        self.assertTrue(session.window.welcome_example_button.isVisible())
        session.window.welcome_generate_button.click()
        self.assertEqual(session.window.tabs.currentIndex(), 3)
        self.assertIs(session.window.tabs.widget(1), session.window.reference_shell)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            session.window.switch_account("physician")
        self.app.processEvents()
        sign_in(self.physician)
        self.assertTrue(session.window.physician.home.isVisible())
        self.assertFalse(session.window.welcome_example_button.isVisible())
        self.assertFalse(session.window.tabs.isTabVisible(3))

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            session.window.switch_account("signin")
        self.app.processEvents()
        self.assertIsNone(session.window)
        self.assertIs(session.dialog.stack.currentWidget(), session.dialog.selection)

    def test_signup_returns_to_sign_in_with_the_correct_role(self):
        store = WorkspaceStore(self.root / "empty")
        password = "demo1234"
        with self.assertRaises(ValueError):
            store.create_account("too-short", "short", "physician")
        for index, role in enumerate(("physician", "technical", "physician")):
            with self.subTest(role=role, index=index):
                login = SignIn(store, animate=False)
                self.addCleanup(self.close_login, login)
                login.show()
                name = f"new-{role}-{index}"
                signup = login.signup_buttons[role]
                if index:
                    login.role_buttons[role].click()
                    signup = login.form_signup
                self.assertIn("Physician account" if role == "physician" else "first Technical Team account", signup.text())

                previous = login.stack.currentWidget()
                signup.click()
                form = login.stack.currentWidget().findChild(AccountForm)
                self.assertIsNotNone(form)
                self.assertIs(form.window(), login)
                if index == 0:
                    form.password.setText(password)
                    form.cancel_button.click()
                    self.assertIs(login.stack.currentWidget(), previous)
                    self.assertFalse(form.password.text())
                    signup.click()
                    form = login.stack.currentWidget().findChild(AccountForm)
                form.username.setText(name)
                form.password.setText(password)
                form.repeated.setText(password)
                form.create_button.click()
                self.assertIsNone(login.account)
                self.assertIs(login.stack.currentWidget(), login.form)
                self.assertEqual(login.role, role)
                self.assertEqual(login.username.text(), name)
                self.assertFalse(login.password.text())
                login.password.setText(password)
                login.submit.click()
                self.assertEqual(login.account.role, role)
                self.assertEqual(store.has_technical_account(), index > 0)

        login = SignIn(store, role="technical", animate=False)
        self.addCleanup(self.close_login, login)
        self.assertEqual(login.form_signup.text(), "Need a Technical Team account?")
        login.form_signup.click()
        self.assertIn("Ask a Technical Team member", login.error.text())
        self.assertIs(login.stack.currentWidget(), login.form)
        with self.assertRaises(PermissionError):
            store.create_account("unapproved-tech", self.password, "technical")

    def test_technical_account_creation_stays_in_workbench_and_returns_to_same_tab(self):
        window = Window(self.store, self.technical)
        self.addCleanup(window.close)
        window.tabs.setCurrentIndex(3)
        previous = window.workspace_pages.currentWidget()
        window.create_local_account()
        page = window.workspace_pages.currentWidget()
        form = page.findChild(AccountForm)
        self.assertIsNotNone(form)
        self.assertIs(form.window(), window)
        form.roles.setCurrentIndex(form.roles.findData("technical"))
        form.username.setText("second-operator")
        form.password.setText(self.password)
        form.repeated.setText(self.password)
        form.create_button.click()
        self.assertIs(window.workspace_pages.currentWidget(), previous)
        self.assertEqual(window.tabs.currentIndex(), 3)
        self.assertIsNotNone(self.store.authenticate("second-operator", self.password, "technical"))

    def test_one_mri_prediction_save_and_resume(self):
        labels = np.zeros((16, 16, 16), dtype=np.uint8)
        labels[2:14, 2:14, 2:14] = 1
        labels[5:11, 5:11, 5:11] = 4
        paths = [self.root / name for name in ("T1.nii.gz", "prediction.nii.gz")]
        for path, voxels in zip(paths, (labels.astype(np.float32), labels), strict=True):
            image = nib.Nifti1Image(voxels, np.eye(4))
            image.header.set_xyzt_units("mm")
            nib.save(image, path)

        technical = Window(self.store, self.technical)
        self.addCleanup(technical.close)
        model = self.root / "model"
        (model / "fold_0").mkdir(parents=True)
        for name in ("plans.json", "dataset.json", "fold_0/checkpoint_final.pth"):
            (model / name).touch()
        results_dir = self.root / "physician-results"
        results_dir.mkdir()
        technical.open_physician_setup()
        panel = technical.inference
        self.assertTrue(panel.setup_button.isChecked())
        panel.python.setText(sys.executable)
        panel.model.setText(str(model))
        panel.workstation_output.setText(str(results_dir))
        panel.mri.clear()
        panel.output.setText(str(self.root / "unused-test-output"))
        self.assertFalse(panel.run_button.isEnabled())
        legacy = {"experiment": "E1", "models": {"E1": str(model)}, "python": sys.executable,
                  "output": str(results_dir), "mri": str(paths[1])}
        with patch.object(type(panel), "read_local_defaults", return_value=legacy):
            fallback = Window(self.store, self.physician)
            self.addCleanup(fallback.close)
        self.assertIsNone(self.store.setup(self.physician))
        self.assertEqual(fallback.inference.model.text(), str(model))
        self.assertFalse(fallback.inference.mri.text())
        self.assertNotIn("mri", fallback.physician.setup)
        panel.save_workstation_button.click()
        settings = self.store.setup(self.physician)
        self.assertIsNotNone(settings, technical.feedback.text())
        self.assertNotIn("mri", settings)
        self.assertEqual(settings["output"], str(results_dir))
        panel.mri.setText(str(paths[1]))
        panel.save_workstation_button.click()
        self.assertEqual(self.store.setup(self.physician), settings)

        with patch("mesh_viewer.MeshView.ensure_renderer"):
            window = Window(self.store, self.physician)
            self.addCleanup(window.close)
            flow = window.physician
            self.assertEqual([window.tabs.isTabVisible(i) for i in range(4)], [True, False, True, False])
            self.assertFalse(window.inference.mri.text())
            self.assertEqual(window.inference.model.text(), str(model))
            layout = window.centralWidget().layout()
            self.assertIs(layout.itemAt(layout.count() - 1).layout().itemAt(1).widget(), flow.back_button)
            with patch.object(QFileDialog, "getOpenFileName", return_value=(str(paths[0]), "")) as choose:
                flow.home_open_button.click()
            self.wait_idle(window)
            self.assertEqual(choose.call_count, 1)
            self.assertEqual(flow.source_path, paths[0])
            with patch.object(flow, "output_directory", return_value=self.root), patch.object(window.inference, "start") as start:
                flow.build_button.click()
            start.assert_called_once_with()
            self.assertEqual(window.inference.mri.text(), str(paths[0]))
            window.inference.completed.emit(SimpleNamespace(mri=paths[0], prediction=paths[1], assume_mm=False))
            self.wait_idle(window)
            self.assertEqual(window.tabs.currentIndex(), 2, window.feedback.text())

            window.mesh_view.checks[1].setChecked(False)
            window.mesh_view.sliders[4].setValue(62)
            window.mesh_view.show_planes.setChecked(True)
            window.panels[0].slider.setValue(4)
            self.assertTrue(flow.dirty())
            with patch.object(QInputDialog, "getText", return_value=("Review", True)):
                flow.save_button.click()
            self.assertFalse(flow.dirty())
            window.mesh_view.sliders[4].setValue(78)
            state = flow.view_state()
            study, result = flow.study_id, flow.result_id
            def save_and_leave():
                dialog = self.app.activeModalWidget()
                next(button for button in dialog.buttons() if button.text() == "Save and leave").click()

            QTimer.singleShot(0, save_and_leave)
            flow.back_button.click()
            self.assertIsNone(window.volume)
            self.assertEqual(self.store.studies(self.technical), [])
            with self.assertRaises(PermissionError):
                self.store.study(self.technical, study)
            with self.assertRaises(PermissionError):
                self.store.views(self.technical, result)

            reopened_store = WorkspaceStore(self.store.directory)
            reopened = Window(reopened_store, self.physician)
            self.addCleanup(reopened.close)
            reopened.physician.open_record(study, paths[1])
            self.wait_idle(reopened)
            self.assertIsNone(reopened.volume)
            self.assertIn("does not match", reopened.feedback.text())
            reopened.physician.open_record(study, paths[0])
            self.wait_idle(reopened)
            self.assertEqual(reopened.physician.view_name, "Review", reopened.feedback.text())
            self.assertEqual(reopened.physician.view_state(), state)
            self.assertFalse(reopened.physician.dirty())


if __name__ == "__main__":
    unittest.main()
