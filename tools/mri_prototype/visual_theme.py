"""Presentation only: shared colors, selection states and disclosure affordances."""

from pathlib import Path
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QSizePolicy, QWidget

ASSETS = Path(__file__).with_name("assets")


def apply_light_theme(app):
    """Keep the Workbench's established palette independent of OS dark mode."""
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, "#f5f7fa"),
        (QPalette.ColorRole.WindowText, "#243449"),
        (QPalette.ColorRole.Base, "#ffffff"),
        (QPalette.ColorRole.AlternateBase, "#f0f4f7"),
        (QPalette.ColorRole.Text, "#243449"),
        (QPalette.ColorRole.Button, "#ffffff"),
        (QPalette.ColorRole.ButtonText, "#334b61"),
        (QPalette.ColorRole.ToolTipBase, "#ffffff"),
        (QPalette.ColorRole.ToolTipText, "#243449"),
        (QPalette.ColorRole.Highlight, "#0f766e"),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
        (QPalette.ColorRole.PlaceholderText, "#52677a"),
    ):
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#8b98a6"))
    app.setPalette(palette)


def compact_choice(combo):
    """Keep short choices at their content width, including in growing forms."""
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
    combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


def compact_action(button):
    """Size an action to its label while retaining normal click-target padding."""
    button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


def center_page_content(scroll, content):
    """Center one coherent page column, including headings, forms and actions."""
    content.setMaximumWidth(1120)
    scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)


def centered_page(content):
    """Balance a page containing its own scrolling without adding a scrollbar."""
    content.setMaximumWidth(1120)
    page = QWidget()
    row = QHBoxLayout(page)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    row.addStretch(0)
    row.addWidget(content, 1)
    row.addStretch(0)
    return page


def refresh_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def paint_disclosure(button, title, expanded):
    """Reflect an existing open/closed state without changing that state."""
    button.setObjectName("disclosure")
    button.setProperty("expanded", bool(expanded))
    button.setText(f"{title} · {'Hide' if expanded else 'Show'}")
    button.setIcon(QIcon(str(ASSETS / ("chevron-down.svg" if expanded else "chevron-right.svg"))))
    button.setIconSize(QSize(16, 16))
    button.setAccessibleDescription(f"{title} is {'expanded' if expanded else 'collapsed'}.")
    refresh_style(button)


def bind_disclosure(button, title):
    button.toggled.connect(lambda expanded: paint_disclosure(button, title, expanded))
    paint_disclosure(button, title, button.isChecked())


def stylesheet():
    icons = ASSETS.as_posix()
    return r'''
        QWidget { color: #243449; font-size: 13px; background: transparent; }
        QMainWindow, QDialog, QDialog#workspaceDialog { background: #f5f7fa; }
        QWidget#workbenchRoot { background: #f5f7fa; }
        QLabel#workbenchTitle { font-size: 26px; font-weight: 600; color: #152b3b; }
        QLabel#subtitle { color: #52677a; font-size: 12px; }
        QLabel#welcomeTitle { font-size: 24px; font-weight: 600; color: #152b3b; }
        QLabel#welcomeHero { font-size: 52px; font-weight: 700; color: #152b3b; }
        QLabel#welcomeSubtitle { font-size: 18px; color: #52677a; }
        QLabel#welcomeMark { font-size: 24px; color: #0f766e; background: #e4f2ef; border-radius: 12px; }
        QFrame#welcomeLine { background: #0f766e; }
        QFrame#authHeader { background: #ffffff; border-bottom: 1px solid #d9e3ea; }
        QLabel#authTitle { font-size: 38px; font-weight: 650; color: #152b3b; }
        QFrame#authCard { background: #ffffff; border: 1px solid #d9e3ea; border-radius: 14px; }
        QWidget#workspaceChoices QLabel, QFrame#authCard QLabel { font-size: 16px; }
        QWidget#workspaceChoices QLabel#authTitle, QFrame#authCard QLabel#authTitle { font-size: 38px; }
        QFrame#authCard QLabel#cardTitle { font-size: 20px; }
        QFrame#authCard QLineEdit { min-height: 27px; font-size: 16px; }
        QLabel#badge { color: #52677a; font-size: 10px; letter-spacing: 1px; }
        QFrame#startCard { background: #ffffff; border: 1px solid #d9e3ea; border-radius: 14px; padding: 12px; }
        QFrame#startCard QLabel { border: 0; background: transparent; padding: 0; }
        QLabel#cardTitle { font-size: 16px; font-weight: 600; color: #152b3b; }
        QLabel#runMetrics { color: #115e59; font-size: 13px; }
        QWidget#errorBanner { background: #fff1f2; border: 1px solid #f1a7b0; border-radius: 10px; }
        QWidget#errorBanner QLabel { color: #9f1239; border: 0; background: transparent; }
        QLabel#errorTitle { font-size: 15px; font-weight: 600; }
        QWidget#resultBanner { background: #ecfdf5; border: 1px solid #9ad8bd; border-radius: 10px; }
        QWidget#resultBanner QLabel { background: transparent; border: 0; color: #166047; }
        QWidget#resultBanner[level="info"], QWidget#activityBanner { background: #eff6ff; border: 1px solid #b9d0ed; border-radius: 10px; }
        QWidget#resultBanner[level="info"] QLabel, QWidget#activityBanner QLabel { color: #254d7e; background: transparent; border: 0; }
        QTabWidget::pane { border: 0; background: transparent; }
        QTabBar { background: transparent; }
        QTabBar::tab { background: #ffffff; border: 1px solid #d6e0e8; border-radius: 9px;
                        color: #425a70; padding: 10px 18px; margin: 2px 7px 7px 0; }
        QTabBar::tab:hover { background: #e8f6f3; border-color: #83bdb4; color: #115e59; }
        QTabBar::tab:selected { background: #0f766e; color: #ffffff; border-color: #0f766e; font-weight: 600; }
        QTabBar#inspectorTabs::tab { padding: 7px 8px; margin-right: 4px; }
        QFrame#referencePanel { background: #ffffff; border: 1px solid #d6e0e8; border-radius: 12px; }
        QLabel#referenceTitle { color: #152b3b; font-size: 20px; font-weight: 600; }
        QTabWidget#referenceModes::pane { background: #ffffff; border: 0; }
        QTabBar#referenceModeBar::tab { background: #f0f4f7; border: 1px solid #e0e7ed; border-radius: 7px;
                                      color: #52677a; padding: 7px 14px; margin: 2px 6px 9px 0; }
        QTabBar#referenceModeBar::tab:hover { background: #e8f6f3; border-color: #a8cfc6; }
        QTabBar#referenceModeBar::tab:selected { background: #def2ec; border-color: #96c5b8; color: #115e59; font-weight: 600; }
        QFrame#referencePanel QGroupBox { margin-top: 28px; padding-top: 14px; }
        QFrame#referencePanel QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left;
                                               left: 14px; top: 2px; padding: 0 6px 3px 6px; }
        QPushButton, QToolButton#importOptions { min-height: 22px; min-width: 76px; padding: 7px 12px; font-size: 13px;
                                                background: #ffffff; border: 2px solid #d6e0e8; border-radius: 9px; color: #334b61; }
        QPushButton:hover { background: #f0fdfa; border-color: #88bdb5; color: #115e59; }
        QPushButton:pressed { background: #d5eee8; border-color: #0f766e; }
        QPushButton:focus { border-color: #0f766e; }
        QPushButton:checked { background: #ddf3ee; border-color: #70b3a8; color: #115e59; }
        QPushButton#primary { background: #0f766e; border-color: #0f766e; color: #ffffff; font-weight: 600; }
        QPushButton#primary:hover { background: #115e59; border-color: #115e59; }
        QPushButton#primary:pressed { background: #134e4a; border-color: #134e4a; }
        QPushButton#primary:focus { border-color: #5eead4; }
        QPushButton#stopAction { color: #a4263f; border-color: #e6b5bf; background: #fff7f8; }
        QPushButton#stopAction:hover { background: #ffe4e9; border-color: #c24a62; }
        QPushButton#disclosure { text-align: left; font-weight: 500; background: #ffffff; }
        QPushButton#disclosure[expanded="true"] { background: #e2f2ee; border-color: #72afa3; color: #115e59; }
        QWidget#disclosureBody { background: #ffffff; border: 1px solid #bfd8d1; border-radius: 10px; }
        QPushButton:disabled, QPushButton#primary:disabled, QPushButton#stopAction:disabled {
            color: #8b98a6; background: #eef2f6; border-color: #e1e7ee; }
        QToolButton#importOptions { background: #ffffff; border: 2px solid #d6e0e8; border-radius: 9px;
                                    padding-right: 30px; color: #425a70; }
        QToolButton#importOptions:hover, QToolButton#importOptions[menuOpen="true"] { background: #e8f6f3; border-color: #0f766e; color: #115e59; }
        QToolButton#importOptions[attention="true"] { background: #fff7e6; border-color: #d7a54d; color: #85500c; }
        QToolButton#importOptions:focus { border-color: #0f766e; }
        QToolButton#importOptions:disabled { color: #8b98a6; background: #eef2f6; border-color: #e1e7ee; }
        QToolButton#importOptions::menu-indicator { image: url("__ICONS__/chevron-down.svg"); width: 13px; height: 13px;
                                                  subcontrol-origin: padding; subcontrol-position: right center; right: 10px; }
        QMenu { background: #ffffff; border: 1px solid #cbd8e3; border-radius: 10px; padding: 7px; }
        QMenu::item { padding: 11px 18px 11px 32px; border-radius: 6px; color: #334b61; }
        QMenu::item:selected { background: #e0f2ed; color: #115e59; }
        QMenu::item:checked { color: #115e59; font-weight: 600; }
        QMenu::indicator { width: 17px; height: 17px; border: 1px solid #aebfca; border-radius: 4px; }
        QMenu::indicator:checked { image: url("__ICONS__/check.svg"); background: #0f766e; border-color: #0f766e; }
        QMenu::separator { height: 1px; background: #e0e7ed; margin: 6px 4px; }
        QMenu#accountMenu { background: #ffffff; border: 1px solid #d6e0e8; border-radius: 9px; padding: 4px; }
        QMenu#accountMenu::item { min-width: 145px; padding: 8px 16px; color: #334b61; }
        QMenu#accountMenu::item:selected { background: #e8f6f3; color: #115e59; }
        QMenu#accountMenu::separator { margin: 4px 6px; }
        QLineEdit, QDoubleSpinBox, QComboBox { background: #ffffff; border: 1px solid #c5d3df; border-radius: 8px; padding: 8px; color: #243449; }
        QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #0f766e; background: #f6fffc; }
        QLineEdit:disabled, QDoubleSpinBox:disabled, QComboBox:disabled { background: #edf2f6; color: #7d8d9b; border-color: #dce4ec; }
        QComboBox { padding-right: 30px; }
        QComboBox::drop-down { width: 29px; border: 0; }
        QComboBox::down-arrow { image: url("__ICONS__/chevron-down.svg"); width: 13px; height: 13px; }
        QComboBox QAbstractItemView { background: #ffffff; color: #243449; selection-background-color: #ddf3ee; selection-color: #115e59; border: 1px solid #bfd1df; outline: 0; padding: 5px; }
        QCheckBox { spacing: 8px; padding: 3px 0; }
        QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #9badbd; background: #ffffff; border-radius: 4px; }
        QCheckBox::indicator:hover { border-color: #0f766e; background: #f0fdfa; }
        QCheckBox::indicator:checked { image: url("__ICONS__/check.svg"); background: #0f766e; border-color: #0f766e; }
        QCheckBox::indicator:disabled { background: #e8eef3; border-color: #c7d3de; }
        QCheckBox::indicator:checked:disabled { background: #91aaa5; }
        QCheckBox:disabled { color: #8b98a6; }
        QPlainTextEdit { background: #ffffff; border: 1px solid #cbd8e3; border-radius: 9px; padding: 10px; color: #334b61; selection-background-color: #ccfbf1; }
        QGroupBox { border: 1px solid #d3dee8; border-radius: 10px; margin-top: 15px; padding-top: 12px; background: #ffffff; }
        QGroupBox::title { subcontrol-origin: margin; padding: 0 7px; color: #334b61; font-weight: 600; }
        QFrame#slicePanel { background: #101c26; border: 1px solid #273c4a; border-radius: 10px; }
        QFrame#slicePanel QLabel { color: #b7cbd8; background: transparent; font-size: 11px; border: 0; }
        QLabel#planeTitle { font-size: 14px; font-weight: 600; color: #e4f0f5; }
        QSlider { background: transparent; }
        QSlider::groove:horizontal { height: 5px; background: #d4dfe6; border-radius: 2px; }
        QSlider::sub-page:horizontal { background: #0f766e; border-radius: 2px; }
        QSlider::handle:horizontal { width: 16px; margin: -6px 0; border: 2px solid #ffffff; background: #0f766e; border-radius: 9px; }
        QSlider::handle:horizontal:hover { background: #115e59; }
        QSlider::handle:horizontal:disabled { background: #9baebb; }
        QProgressBar { border: 1px solid #d3dfe8; border-radius: 5px; background: #e7edf2; max-height: 16px; color: #334b61; text-align: center; font-size: 11px; }
        QProgressBar::chunk { background: #0f766e; border-radius: 4px; }
        QWidget#activityBanner QProgressBar { max-height: 8px; }
        QScrollArea { border: 0; }
        QScrollBar:vertical { background: #e7edf2; width: 12px; border: 0; border-radius: 6px; }
        QScrollBar::handle:vertical { background: #a9bac8; min-height: 36px; border-radius: 5px; }
        QScrollBar::handle:vertical:hover { background: #7d98a7; }
        QScrollBar:horizontal { background: #e7edf2; height: 12px; border: 0; border-radius: 6px; }
        QScrollBar::handle:horizontal { background: #a9bac8; min-width: 36px; border-radius: 5px; }
    '''.replace("__ICONS__", icons)
