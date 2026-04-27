"""
main.py
══════════════════════════════════════════════════════════════
Octar Lab — application entry point.

Builds the main window, registers all 13 tabs, applies the
"Cosmic Violet" stylesheet, and wires the cross-cutting
signals (settings changes propagating to every tab, language
changes triggering UI re-translation).
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QStatusBar,
    QTabWidget, QVBoxLayout, QWidget,
)

from core.config import (
    APP_NAME, APP_VERSION, APP_REPO_URL, AppSettings,
)
from core.i18n import t, set_language
from ui.stylesheet import build_stylesheet
from ui.theme import PALETTE as P
from ui.widgets.glow_label import GlowLabel
from ui.widgets.pulsing_dot import PulsingDot

# Tabs
from tabs.architect_tab    import ArchitectTab
from tabs.library_tab      import LibraryTab
from tabs.refactor_tab     import RefactorTab
from tabs.docs_tab         import DocsGenTab
from tabs.test_tab         import TestGenTab
from tabs.ui_component_tab import UIComponentTab
from tabs.database_tab     import DatabaseTab
from tabs.api_builder_tab  import APIBuilderTab
from tabs.devops_tab       import DevOpsTab
from tabs.chat_tab         import ChatTab
from tabs.settings_tab     import SettingsTab
from tabs.help_tab         import HelpTab
from tabs.about_tab        import AboutTab


class MainWindow(QMainWindow):
    """Main application window — header, tab strip, status bar."""

    # Tab order (also order in which they appear in the strip)
    _TAB_DEFINITIONS = [
        ("tab.architect",      ArchitectTab),
        ("tab.library",        LibraryTab),
        ("tab.refactor",       RefactorTab),
        ("tab.docs_gen",       DocsGenTab),
        ("tab.tests",          TestGenTab),
        ("tab.ui_components",  UIComponentTab),
        ("tab.database",       DatabaseTab),
        ("tab.api",            APIBuilderTab),
        ("tab.devops",         DevOpsTab),
        ("tab.chat",           ChatTab),
        ("tab.settings",       SettingsTab),
        ("tab.help",           HelpTab),
        ("tab.about",          AboutTab),
    ]

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self._tabs: list[tuple[str, QWidget]] = []  # (i18n_key, tab_widget)
        self._build_window()
        self._build_menu()
        self._build_central_widget()
        self._build_status_bar()
        self._wire_signals()

    # ── Window setup ──────────────────────────────────────
    def _build_window(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1480, 900)
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(build_stylesheet())

    def _build_menu(self):
        menubar = self.menuBar()

        # File menu
        self.menu_file = menubar.addMenu(t("menu.file"))
        self.act_open_output = QAction(t("menu.open_output"), self)
        self.act_open_output.setShortcut("Ctrl+O")
        self.act_open_output.triggered.connect(self._open_output_folder)
        self.menu_file.addAction(self.act_open_output)
        self.menu_file.addSeparator()
        self.act_quit = QAction(t("menu.quit"), self)
        self.act_quit.setShortcut("Ctrl+Q")
        self.act_quit.triggered.connect(self.close)
        self.menu_file.addAction(self.act_quit)

        # Help menu
        self.menu_help = menubar.addMenu(t("menu.help"))
        self.act_docs = QAction(t("menu.documentation"), self)
        self.act_docs.triggered.connect(self._show_help_tab)
        self.menu_help.addAction(self.act_docs)

        self.act_github = QAction(t("menu.github"), self)
        self.act_github.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl(APP_REPO_URL))
        )
        self.menu_help.addAction(self.act_github)

        self.menu_help.addSeparator()
        self.act_about = QAction(t("menu.about"), self)
        self.act_about.triggered.connect(self._show_about_tab)
        self.menu_help.addAction(self.act_about)

    def _build_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 12, 14, 8)
        layout.setSpacing(8)

        # Header
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        self.header_title = GlowLabel(f"⬢  {APP_NAME.upper()}")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(20)
        self.header_title.setFont(title_font)

        self.header_subtitle = QLabel(t("app.subtitle"))
        self.header_subtitle.setObjectName("subtitle")

        spacer_label = QLabel()  # flexible spacer
        spacer_label.setSizePolicy(spacer_label.sizePolicy().horizontalPolicy().Expanding,
                                   spacer_label.sizePolicy().verticalPolicy().Preferred)

        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setStyleSheet(
            f"color: {P['text_dim']}; font-size: 11px; "
            f"padding: 4px 10px; border: 1px solid {P['border']}; "
            f"border-radius: 4px;"
        )

        header_row.addWidget(self.header_title)
        header_row.addSpacing(12)
        header_row.addWidget(self.header_subtitle)
        header_row.addStretch()
        header_row.addWidget(version_label)

        layout.addLayout(header_row)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMovable(False)
        self.tab_widget.setDocumentMode(True)

        for i18n_key, tab_cls in self._TAB_DEFINITIONS:
            tab = tab_cls(self.settings)
            self._tabs.append((i18n_key, tab))
            self.tab_widget.addTab(tab, t(i18n_key))
            # Forward status messages from any tab to the status bar
            if hasattr(tab, "status_signal"):
                tab.status_signal.connect(self._on_tab_status)

        layout.addWidget(self.tab_widget)

    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_dot = PulsingDot(P["primary_hover"])
        self.status_label = QLabel(t("status.ready"))
        self.status_label.setStyleSheet(f"color: {P['text_sec']};")

        self.status_bar.addWidget(self.status_dot)
        self.status_bar.addWidget(self.status_label)

        # Right-side info
        right_label = QLabel(f"⬢ Octarinox · {APP_VERSION}")
        right_label.setStyleSheet(f"color: {P['text_dim']}; font-size: 11px;")
        self.status_bar.addPermanentWidget(right_label)

    def _wire_signals(self):
        # Find the SettingsTab and hook into its signals
        for _, tab in self._tabs:
            if isinstance(tab, SettingsTab):
                tab.language_changed.connect(self._on_language_changed)
                tab.settings_changed.connect(self._on_settings_changed)
                break

    # ── Signal handlers ───────────────────────────────────
    def _on_tab_status(self, message: str, level: str):
        self.status_label.setText(message)
        color_map = {
            "info":  P["text_sec"],
            "ok":    P["success"],
            "warn":  P["warning"],
            "err":   P["danger"],
        }
        color = color_map.get(level, P["text_sec"])
        self.status_label.setStyleSheet(f"color: {color};")
        if level in ("info",):
            self.status_dot.set_color(P["primary_hover"])
            self.status_dot.start_pulse()
        elif level == "ok":
            self.status_dot.set_color(P["success"])
            self.status_dot.start_pulse()
        elif level == "err":
            self.status_dot.set_color(P["danger"])
            self.status_dot.start_pulse()
        else:
            self.status_dot.stop_pulse()

    def _on_language_changed(self, _new_lang: str):
        # Re-translate every tab's tab-strip label
        for i, (key, _) in enumerate(self._tabs):
            self.tab_widget.setTabText(i, t(key))
        # Re-translate menus
        self.menu_file.setTitle(t("menu.file"))
        self.menu_help.setTitle(t("menu.help"))
        self.act_open_output.setText(t("menu.open_output"))
        self.act_quit.setText(t("menu.quit"))
        self.act_docs.setText(t("menu.documentation"))
        self.act_github.setText(t("menu.github"))
        self.act_about.setText(t("menu.about"))
        # Re-translate header & status
        self.header_subtitle.setText(t("app.subtitle"))
        self.status_label.setText(t("status.ready"))
        # Tell every tab to re-translate its own UI
        for _, tab in self._tabs:
            try:
                tab.on_language_changed()
            except Exception as e:
                print(f"[main] Language refresh failed for {type(tab).__name__}: {e}",
                      file=sys.stderr)

    def _on_settings_changed(self):
        # Every tab gets a chance to refresh from new settings
        for _, tab in self._tabs:
            try:
                tab.on_settings_changed()
            except Exception as e:
                print(f"[main] Settings refresh failed for {type(tab).__name__}: {e}",
                      file=sys.stderr)

    # ── Menu actions ──────────────────────────────────────
    def _open_output_folder(self):
        target = self.settings.output_directory
        Path(target).mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", target], check=False)
            else:
                subprocess.run(["xdg-open", target], check=False)
        except Exception as e:
            self.status_label.setText(f"Could not open folder: {e}")

    def _show_help_tab(self):
        for i, (key, _) in enumerate(self._tabs):
            if key == "tab.help":
                self.tab_widget.setCurrentIndex(i)
                return

    def _show_about_tab(self):
        for i, (key, _) in enumerate(self._tabs):
            if key == "tab.about":
                self.tab_widget.setCurrentIndex(i)
                return


def main() -> int:
    # High-DPI scaling (no-ops in PyQt6 ≥ 6.x but harmless)
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Octarinox")

    # Load settings & set language *before* building UI
    settings = AppSettings.load()
    set_language(settings.language)

    window = MainWindow(settings)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
