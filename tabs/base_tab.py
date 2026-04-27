"""
tabs/base_tab.py
══════════════════════════════════════════════════════════════
Shared base class for all tabs. Provides common helpers like
section labels, separator lines, and a uniform constructor
contract (every tab receives the AppSettings instance).
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QWidget

from core.config import AppSettings


class BaseTab(QWidget):
    """
    Common parent for every tab.

    Tabs receive the shared AppSettings instance and emit
    `status_signal(message, level)` whenever they want to
    update the main window's status bar.
    """

    status_signal = pyqtSignal(str, str)  # (message, level: "info"|"ok"|"warn"|"err")

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings

    # ── Lifecycle hooks (override as needed) ──────────────
    def on_settings_changed(self) -> None:
        """Called when settings are saved elsewhere — refresh UI bindings here."""
        pass

    def on_language_changed(self) -> None:
        """Called when the user switches UI language — re-translate labels here."""
        pass

    # ── Shared widget helpers ─────────────────────────────
    @staticmethod
    def section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    @staticmethod
    def hint_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("hint")
        lbl.setWordWrap(True)
        return lbl

    @staticmethod
    def hline() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet("color: #2d2438; background-color: #2d2438; max-height: 1px;")
        return line
