from __future__ import annotations

import datetime

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

from core.i18n import t
from core.logger import LEVEL_ICONS
from ui.highlighters.code_highlighter import CodeHighlighter
from ui.theme import PALETTE as P


class OutputPanel(QWidget):
    """Right-side output panel: progress + logs + result preview."""

    copy_requested = pyqtSignal()
    save_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(8)

        # Progress
        self.progress_label = QLabel(t("shared.progress_label"))
        self.progress_label.setObjectName("section")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%  —  %v / 100")
        self.progress_bar.setMinimumHeight(22)
        layout.addWidget(self.progress_bar)

        # Tab strip
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.tabs.addTab(self._build_log_tab(),    t("shared.live_log_tab"))
        self.tabs.addTab(self._build_result_tab(), t("shared.code_preview_tab"))

    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel(t("shared.live_log_tab"))
        title.setObjectName("section")
        self.clear_logs_btn = QPushButton(t("shared.clear_logs_btn"))
        self.clear_logs_btn.setObjectName("ghost")
        self.clear_logs_btn.setFixedHeight(26)
        self.clear_logs_btn.clicked.connect(lambda: self.log_view.clear())
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.clear_logs_btn)
        layout.addLayout(header)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("JetBrains Mono", 10))
        self.log_view.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {P['bg_void']};
                border: 1px solid {P['border']};
                border-radius: 8px;
                color: {P['text_code']};
                padding: 8px;
            }}
        """)
        layout.addWidget(self.log_view)
        return w

    def _build_result_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.result_filename = QLabel(t("shared.no_file_selected"))
        self.result_filename.setStyleSheet(
            f"color: {P['warning']}; font-weight: bold;"
        )
        self.copy_btn = QPushButton(t("shared.copy_btn"))
        self.save_btn = QPushButton(t("shared.save_btn"))
        for b in (self.copy_btn, self.save_btn):
            b.setObjectName("ghost")
            b.setFixedHeight(26)
            b.setFixedWidth(110)
        self.copy_btn.clicked.connect(self.copy_requested.emit)
        self.save_btn.clicked.connect(self.save_requested.emit)
        header.addWidget(self.result_filename)
        header.addStretch()
        header.addWidget(self.copy_btn)
        header.addWidget(self.save_btn)
        layout.addLayout(header)

        self.result_view = QPlainTextEdit()
        self.result_view.setFont(QFont("JetBrains Mono", 11))
        self.result_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.result_view.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {P['bg_void']};
                border: 1px solid {P['border']};
                border-radius: 8px;
                color: {P['text_prim']};
                padding: 10px;
                selection-background-color: {P['primary']};
            }}
        """)
        self.highlighter = CodeHighlighter(self.result_view.document())
        layout.addWidget(self.result_view)
        return w

    def log(self, message: str, level: str = "INFO"):
        icon = LEVEL_ICONS.get(level, "·")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] {icon}  {message}")
        cur = self.log_view.textCursor()
        self.log_view.moveCursor(cur.MoveOperation.End)

    def set_progress(self, percent: int):
        self.progress_bar.setValue(max(0, min(100, percent)))

    def set_result(self, text: str, filename: str = "result"):
        self.result_filename.setText(f"◉  {filename}")
        self.result_view.setPlainText(text)
        self.tabs.setCurrentIndex(1)  # switch to result tab

    def get_result_text(self) -> str:
        return self.result_view.toPlainText()

    def clear(self):
        self.log_view.clear()
        self.result_view.clear()
        self.progress_bar.setValue(0)
        self.result_filename.setText(t("shared.no_file_selected"))

    def show_processing(self):
        self.result_filename.setText(t("shared.processing_placeholder"))

    def retranslate(self):
        self.progress_label.setText(t("shared.progress_label"))
        self.tabs.setTabText(0, t("shared.live_log_tab"))
        self.tabs.setTabText(1, t("shared.code_preview_tab"))
        self.clear_logs_btn.setText(t("shared.clear_logs_btn"))
        self.copy_btn.setText(t("shared.copy_btn"))
        self.save_btn.setText(t("shared.save_btn"))
