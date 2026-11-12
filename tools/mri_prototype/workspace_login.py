"""Welcome, role selection and local Workbench sign-in."""

import sqlite3

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from visual_theme import centered_page, compact_action, stylesheet
from workspace_store import MIN_PASSWORD_LENGTH, ROLES


STORE_ERRORS = (OSError, ValueError, sqlite3.Error)


class AccountForm(QFrame):
    created = Signal(object)
    cancelled = Signal()

    def __init__(self, store, *, actor=None, role=None):
        super().__init__()
        self.store, self.actor, self.role = store, actor, role
        self.setObjectName("authCard")
        title = "Create local account"
        if actor is None:
            title = "Create Physician account" if role == "physician" else "Set up the first Technical Team account"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("welcomeTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        self.username = QLineEdit()
        self.username.setMaxLength(64)
        self.roles = None
        self.password = QLineEdit()
        self.repeated = QLineEdit()
        for field in (self.password, self.repeated):
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setMaxLength(256)
        fields = [("Account", self.username)]
        if actor is not None:
            self.roles = QComboBox()
            for key, label in ROLES.items():
                self.roles.addItem(label, key)
            fields.append(("Role", self.roles))
        fields.extend((("Password", self.password), ("Confirm password", self.repeated)))
        for label, field in fields:
            caption = QLabel(label)
            caption.setBuddy(field)
            field.setAccessibleName(label)
            layout.addWidget(caption)
            layout.addWidget(field)
        layout.addWidget(QLabel(f"Use a password of at least {MIN_PASSWORD_LENGTH} characters."))
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        actions = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.cancelled)
        self.create_button = QPushButton("Create account")
        self.create_button.setAutoDefault(False)
        self.create_button.setObjectName("primary")
        self.create_button.clicked.connect(self.submit)
        self.repeated.returnPressed.connect(self.submit)
        actions.addWidget(self.cancel_button)
        actions.addStretch(1)
        actions.addWidget(self.create_button)
        layout.addLayout(actions)

    def submit(self):
        try:
            if self.password.text() != self.repeated.text():
                raise ValueError("The passwords do not match.")
            role = self.roles.currentData() if self.actor is not None else self.role
            account = self.store.create_account(self.username.text(), self.password.text(), role, actor=self.actor)
        except STORE_ERRORS as error:
            self.error.setText(str(error))
            self.error.show()
        else:
            self.created.emit(account)


def show_account_form(stack, store, *, actor=None, role=None):
    previous = stack.currentWidget()
    form = AccountForm(store, actor=actor, role=role)
    page = centered_auth_page(form, 680)

    def close_form():
        form.password.clear()
        form.repeated.clear()
        stack.setCurrentWidget(previous)
        stack.removeWidget(page)
        page.deleteLater()

    form.cancelled.connect(close_form)
    form.created.connect(close_form)
    stack.addWidget(page)
    stack.setCurrentWidget(page)
    form.username.setFocus()
    return form


def centered_auth_page(content, width):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(28, 24, 28, 24)
    layout.addStretch(1)
    layout.addWidget(centered_page(content))
    content.setMaximumWidth(width)
    layout.addStretch(1)
    scroll = QScrollArea()
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setWidget(page)
    return scroll


class SignIn(QDialog):
    def __init__(self, store, *, role=None, animate=True):
        super().__init__()
        self.setObjectName("workspaceDialog")
        self.store = store
        self.account = None
        self.role = None
        self.initial_role = role
        self.setWindowTitle("MRI Workbench")
        self.resize(980, 640)
        self.setStyleSheet(stylesheet())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.header = QFrame()
        self.header.setObjectName("authHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(24, 12, 24, 12)
        name = QLabel("MRI Workbench")
        name.setObjectName("cardTitle")
        header_layout.addWidget(name)
        header_layout.addStretch(1)
        header_layout.addWidget(QLabel("TMS HeadSeg"))
        outer.addWidget(self.header)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        welcome = QWidget()
        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.setSpacing(10)
        mark = QLabel("⊕")
        mark.setObjectName("welcomeMark")
        mark.setFixedSize(52, 52)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(mark, alignment=Qt.AlignmentFlag.AlignHCenter)
        title = QLabel("Welcome")
        title.setObjectName("welcomeHero")
        welcome_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        subtitle = QLabel("MRI Workbench")
        subtitle.setObjectName("welcomeSubtitle")
        welcome_layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignHCenter)
        line = QFrame()
        line.setObjectName("welcomeLine")
        line.setFixedSize(42, 2)
        welcome_layout.addSpacing(8)
        welcome_layout.addWidget(line, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.welcome = centered_auth_page(welcome, 480)
        self.stack.addWidget(self.welcome)

        selection = QWidget()
        selection.setObjectName("workspaceChoices")
        selection_layout = QVBoxLayout(selection)
        selection_layout.setSpacing(18)
        title = QLabel("Choose your workspace")
        title.setObjectName("authTitle")
        selection_layout.addWidget(title)
        selection_layout.addWidget(QLabel("Choose a workspace to sign in."))
        cards = QHBoxLayout()
        cards.setSpacing(20)
        self.role_buttons = {}
        self.signup_buttons = {}
        for key, description in (
            ("physician", "Open an MRI, build a 3D view and review saved studies."),
            ("technical", "Configure models, run comparisons and manage reference processing."),
        ):
            card = QFrame()
            card.setObjectName("authCard")
            column = QVBoxLayout(card)
            column.setContentsMargins(24, 24, 24, 24)
            column.setSpacing(14)
            heading = QLabel(ROLES[key])
            heading.setObjectName("cardTitle")
            column.addWidget(heading)
            text = QLabel(description)
            text.setWordWrap(True)
            column.addWidget(text, 1)
            button = QPushButton(f"Continue as {ROLES[key]}")
            if key == "physician":
                button.setObjectName("primary")
            compact_action(button)
            self.role_buttons[key] = button
            button.clicked.connect(lambda checked=False, selected=key: self.choose_role(selected))
            column.addWidget(button)
            signup = QPushButton()
            compact_action(signup)
            signup.clicked.connect(lambda checked=False, selected=key: self.create_account(selected))
            self.signup_buttons[key] = signup
            column.addWidget(signup)
            cards.addWidget(card, 1)
        selection_layout.addLayout(cards, 1)
        self.selection = centered_auth_page(selection, 1160)
        self.stack.addWidget(self.selection)

        form = QFrame()
        form.setObjectName("authCard")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(28, 28, 28, 28)
        form_layout.setSpacing(14)
        self.role_label = QLabel()
        self.role_label.setObjectName("cardTitle")
        form_layout.addWidget(self.role_label)
        heading = QLabel("Sign in")
        heading.setObjectName("authTitle")
        form_layout.addWidget(heading)
        self.username = QLineEdit()
        self.username.setMaxLength(64)
        self.password = QLineEdit()
        self.password.setMaxLength(256)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        for label, field in (("Account", self.username), ("Password", self.password)):
            heading = QLabel(label)
            heading.setBuddy(field)
            field.setAccessibleName(label)
            form_layout.addWidget(heading)
            form_layout.addWidget(field)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.hide()
        form_layout.addWidget(self.error)
        buttons = QHBoxLayout()
        back = QPushButton("Back")
        back.clicked.connect(self.show_roles)
        self.submit = QPushButton("Sign in")
        self.submit.setObjectName("primary")
        self.submit.clicked.connect(self.sign_in)
        self.retry_timer = QTimer(self)
        self.retry_timer.setSingleShot(True)
        self.retry_timer.setInterval(1000)
        self.retry_timer.timeout.connect(lambda: self.submit.setEnabled(True))
        self.password.returnPressed.connect(self.sign_in)
        buttons.addWidget(back)
        buttons.addStretch(1)
        buttons.addWidget(self.submit)
        form_layout.addLayout(buttons)
        self.form_signup = QPushButton()
        compact_action(self.form_signup)
        self.form_signup.clicked.connect(lambda: self.create_account(self.role))
        form_layout.addWidget(self.form_signup)
        self.form = centered_auth_page(form, 680)
        self.stack.addWidget(self.form)
        self.intro = None
        if animate:
            self.header.hide()
            effect = QGraphicsOpacityEffect(welcome)
            effect.setOpacity(0.0)
            welcome.setGraphicsEffect(effect)
            self.intro = QSequentialAnimationGroup(self)
            for duration, start, end in ((850, 0.0, 1.0), (300, 1.0, 0.0)):
                fade = QPropertyAnimation(effect, b"opacity", self.intro)
                fade.setDuration(duration)
                fade.setStartValue(start)
                fade.setEndValue(end)
                fade.setEasingCurve(QEasingCurve.Type.InOutCubic)
                self.intro.addAnimation(fade)
                if end == 1.0:
                    self.intro.addPause(1050)
            self.intro.finished.connect(self.show_initial)
        else:
            self.show_initial()

    def showEvent(self, event):
        super().showEvent(event)
        if self.intro is not None and self.stack.currentWidget() is self.welcome:
            self.intro.start()

    def show_initial(self):
        if self.initial_role in ROLES:
            self.choose_role(self.initial_role)
        else:
            self.show_roles()

    def show_roles(self):
        self.header.show()
        self.password.clear()
        self.refresh_signup_buttons()
        self.stack.setCurrentWidget(self.selection)

    def refresh_signup_buttons(self):
        physician = "Create Physician account…"
        technical = ("Need a Technical Team account?" if self.store.has_technical_account()
                     else "Set up first Technical Team account…")
        self.signup_buttons["physician"].setText(physician)
        self.signup_buttons["technical"].setText(technical)
        self.form_signup.setText(technical if self.role == "technical" else physician)

    def create_account(self, role):
        try:
            if role == "technical" and self.store.has_technical_account():
                self.choose_role(role)
                self.error.setText("Ask a Technical Team member to create an account for you from their account menu.")
                self.error.show()
                return
            form = show_account_form(self.stack, self.store, role=role)
        except STORE_ERRORS as error:
            QMessageBox.warning(self, "Account setup unavailable", str(error))
            return
        form.created.connect(self.account_created)

    def account_created(self, account):
        self.choose_role(account.role)
        self.username.setText(account.username)
        self.password.setFocus()

    def choose_role(self, role):
        self.role = role
        self.header.show()
        self.role_label.setText(f"{ROLES[role]} workspace")
        self.error.clear()
        self.error.hide()
        self.refresh_signup_buttons()
        self.password.clear()
        self.stack.setCurrentWidget(self.form)
        self.username.setFocus()

    def sign_in(self):
        if not self.submit.isEnabled():
            return
        password = self.password.text()
        self.password.clear()
        try:
            self.account = self.store.authenticate(self.username.text(), password, self.role)
        except STORE_ERRORS as error:
            QMessageBox.warning(self, "Sign-in unavailable", str(error))
            return
        if self.account is not None:
            self.accept()
            return
        self.error.setText("The account, password or selected workspace could not be verified.")
        self.error.show()
        self.submit.setEnabled(False)
        self.retry_timer.start()
        self.password.setFocus()
