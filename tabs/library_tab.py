"""
tabs/library_tab.py
══════════════════════════════════════════════════════════════
Library Generator tab.
Generates a focused, single-purpose library — narrower in scope
than a full project (Architect tab). Multi-file output via
MultiFileWorker.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QCursor, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QSplitter, QTabWidget, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from core.config import AppSettings
from core.i18n import t
from core.secrets import get_api_key
from core.workers.multifile_worker import MultiFileWorker
from tabs.base_tab import BaseTab
from ui.highlighters.code_highlighter import CodeHighlighter
from ui.theme import PALETTE as P


LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C#", "C++",
    "Ruby", "PHP", "Kotlin", "Swift", "Scala", "Dart",
]

# Scope → (max_files, label_key)
SCOPES = {
    "minimal":  {"max_files": 5,  "label_key": "library.scope_minimal"},
    "standard": {"max_files": 8,  "label_key": "library.scope_standard"},
    "complete": {"max_files": 12, "label_key": "library.scope_complete"},
}


class LibraryTab(BaseTab):
    """Generate a focused single-purpose library."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._worker: MultiFileWorker | None = None
        self._files: dict[str, str] = {}
        self._last_output_dir: str | None = None
        self._build_ui()

    # ── UI Construction ───────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([460, 900])
        layout.addWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(380)
        panel.setMaximumWidth(540)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 8, 4)
        layout.setSpacing(10)

        # Configuration
        self.cfg_group = QGroupBox(t("library.title"))
        cfg_layout = QVBoxLayout(self.cfg_group)
        cfg_layout.setSpacing(8)

        self.lbl_subtitle = QLabel(t("library.subtitle"))
        self.lbl_subtitle.setObjectName("hint")
        self.lbl_subtitle.setWordWrap(True)
        cfg_layout.addWidget(self.lbl_subtitle)

        # Name
        self.lbl_name = self.section_label(t("library.name_label"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("library.name_placeholder"))
        self.name_input.setMinimumHeight(32)
        cfg_layout.addWidget(self.lbl_name)
        cfg_layout.addWidget(self.name_input)

        # Description
        self.lbl_desc = self.section_label(t("library.desc_label"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(t("library.desc_placeholder"))
        self.desc_input.setFixedHeight(110)
        cfg_layout.addWidget(self.lbl_desc)
        cfg_layout.addWidget(self.desc_input)

        # Language
        self.lbl_lang = self.section_label(t("library.language_label"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(LANGUAGES)
        self.lang_combo.setMinimumHeight(32)
        cfg_layout.addWidget(self.lbl_lang)
        cfg_layout.addWidget(self.lang_combo)

        # Scope
        self.lbl_scope = self.section_label(t("library.scope_label"))
        self.scope_combo = QComboBox()
        self.scope_combo.setMinimumHeight(32)
        for scope_id, scope_def in SCOPES.items():
            self.scope_combo.addItem(t(scope_def["label_key"]), userData=scope_id)
        self.scope_combo.setCurrentIndex(1)  # default: standard
        cfg_layout.addWidget(self.lbl_scope)
        cfg_layout.addWidget(self.scope_combo)

        # Options
        self.chk_tests    = QCheckBox(t("library.include_tests"))
        self.chk_tests.setChecked(True)
        self.chk_examples = QCheckBox(t("library.include_examples"))
        self.chk_readme   = QCheckBox(t("library.include_readme"))
        self.chk_readme.setChecked(True)
        for chk in (self.chk_tests, self.chk_examples, self.chk_readme):
            cfg_layout.addWidget(chk)

        layout.addWidget(self.cfg_group)
        layout.addStretch()

        # Action buttons
        self.run_btn = QPushButton(t("library.run_btn"))
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumHeight(46)
        self.run_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.run_btn.clicked.connect(self._start_run)

        self.stop_btn = QPushButton(t("common.stop"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_run)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(self.run_btn, 3)
        btn_row.addWidget(self.stop_btn, 1)
        layout.addLayout(btn_row)

        self.open_btn = QPushButton("📂 " + t("architect.open_output_btn"))
        self.open_btn.setObjectName("accent")
        self.open_btn.setMinimumHeight(34)
        self.open_btn.clicked.connect(self._open_output_folder)
        layout.addWidget(self.open_btn)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(8)

        self.lbl_progress = self.section_label(t("shared.progress_label"))
        layout.addWidget(self.lbl_progress)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%  —  %v / 100")
        self.progress_bar.setMinimumHeight(22)
        layout.addWidget(self.progress_bar)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.tabs.addTab(self._build_log_tab(),     t("shared.live_log_tab"))
        self.tabs.addTab(self._build_tree_tab(),    t("shared.file_tree_tab"))
        self.tabs.addTab(self._build_preview_tab(), t("shared.code_preview_tab"))

        return panel

    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(self.section_label(t("shared.live_log_tab")))
        header.addStretch()
        self.clear_logs_btn = QPushButton(t("shared.clear_logs_btn"))
        self.clear_logs_btn.setObjectName("ghost")
        self.clear_logs_btn.setFixedHeight(26)
        self.clear_logs_btn.clicked.connect(lambda: self.log_view.clear())
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

    def _build_tree_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.section_label(t("shared.file_tree_tab")))
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["Name", "Size"])
        self.file_tree.setColumnWidth(0, 320)
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.itemClicked.connect(self._on_tree_clicked)
        layout.addWidget(self.file_tree)
        return w

    def _build_preview_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.preview_filename = QLabel(t("shared.no_file_selected"))
        self.preview_filename.setStyleSheet(
            f"color: {P['warning']}; font-weight: bold;"
        )
        self.copy_btn = QPushButton(t("shared.copy_btn"))
        self.save_btn = QPushButton(t("shared.save_btn"))
        for b in (self.copy_btn, self.save_btn):
            b.setObjectName("ghost")
            b.setFixedHeight(26)
            b.setFixedWidth(110)
        self.copy_btn.clicked.connect(self._copy_preview)
        self.save_btn.clicked.connect(self._save_preview)
        header.addWidget(self.preview_filename)
        header.addStretch()
        header.addWidget(self.copy_btn)
        header.addWidget(self.save_btn)
        layout.addLayout(header)

        self.code_view = QPlainTextEdit()
        self.code_view.setFont(QFont("JetBrains Mono", 11))
        self.code_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.code_view.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {P['bg_void']};
                border: 1px solid {P['border']};
                border-radius: 8px;
                color: {P['text_prim']};
                padding: 10px;
                selection-background-color: {P['primary']};
            }}
        """)
        self.highlighter = CodeHighlighter(self.code_view.document())
        layout.addWidget(self.code_view)
        return w

    # ── Generation ────────────────────────────────────────
    def _start_run(self):
        name = self.name_input.text().strip()
        desc = self.desc_input.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "—", t("validation.name_required"))
            return
        if not desc:
            QMessageBox.warning(self, "—", t("validation.desc_required"))
            return

        provider_id = self.settings.active_provider
        if not get_api_key(provider_id):
            QMessageBox.warning(self, "—", t("validation.no_provider"))
            return

        scope_id = self.scope_combo.currentData() or "standard"
        max_files = SCOPES[scope_id]["max_files"]

        # Build extra instructions based on options
        extras: list[str] = []
        if self.chk_tests.isChecked():
            extras.append("- Include a tests/ folder with at least one test file")
        else:
            extras.append("- Do NOT include test files")
        if self.chk_examples.isChecked():
            extras.append("- Include an examples/ folder with usage examples")
        if not self.chk_readme.isChecked():
            extras.append("- Do NOT include a README.md")

        config = {
            "name":             name,
            "description":      desc,
            "language":         self.lang_combo.currentText(),
            "kind":             "library",
            "extra_instructions": "\n".join(extras),
            "max_files":        max_files,
            "temperature":      0.4,
            "output_dir":       self.settings.output_directory,
            "provider_id":      provider_id,
            "architect_model":  self.settings.get_model(provider_id, "architect"),
            "coder_model":      self.settings.get_model(provider_id, "coder"),
        }

        # Reset UI
        self._files.clear()
        self.file_tree.clear()
        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.code_view.setPlainText("")
        self.preview_filename.setText(t("shared.processing_placeholder"))
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_signal.emit(t("status.generating"), "info")

        # Spawn worker
        self._worker = MultiFileWorker(config)
        self._worker.log_signal.connect(self._on_log)
        self._worker.progress_signal.connect(self.progress_bar.setValue)
        self._worker.file_signal.connect(self._on_file_ready)
        self._worker.done_signal.connect(self._on_done)
        self._worker.start()

    def _stop_run(self):
        if self._worker:
            self._worker.stop()
        self.stop_btn.setEnabled(False)

    # ── Worker callbacks ──────────────────────────────────
    def _on_log(self, message: str, level: str):
        from core.logger import LEVEL_ICONS
        import datetime
        icon = LEVEL_ICONS.get(level, "·")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] {icon}  {message}")
        cur = self.log_view.textCursor()
        self.log_view.moveCursor(cur.MoveOperation.End)

    def _on_file_ready(self, path: str, content: str):
        self._files[path] = content
        # Show in preview as it arrives
        self.preview_filename.setText(f"◉  {Path(path).name}")
        self.code_view.setPlainText(content)
        # Add to tree
        rel = Path(path)
        item = QTreeWidgetItem([f"◉ {rel.name}", f"{len(content)} chars"])
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        item.setForeground(1, QColor(P["text_dim"]))
        self.file_tree.addTopLevelItem(item)

    def _on_tree_clicked(self, item: QTreeWidgetItem, _col: int):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and path in self._files:
            self.preview_filename.setText(f"◉  {Path(path).name}")
            self.code_view.setPlainText(self._files[path])
            self.tabs.setCurrentIndex(2)

    def _on_done(self, success: bool, message: str):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if success:
            self._last_output_dir = message
            self.status_signal.emit(t("status.complete"), "ok")
            QMessageBox.information(
                self, t("status.complete"),
                f"✓ Library generated successfully!\n\nLocation:\n{message}",
            )
        else:
            self.status_signal.emit(t("status.error"), "err")
            QMessageBox.critical(self, t("status.error"), message)

    # ── Preview tools ─────────────────────────────────────
    def _copy_preview(self):
        text = self.code_view.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status_signal.emit(t("common.copied"), "ok")

    def _save_preview(self):
        text = self.code_view.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, t("common.save"), "", "All Files (*.*)")
        if path:
            try:
                Path(path).write_text(text, encoding="utf-8")
                self.status_signal.emit(f"Saved: {Path(path).name}", "ok")
            except OSError as e:
                QMessageBox.warning(self, "—", f"Save failed: {e}")

    def _open_output_folder(self):
        target = self._last_output_dir or self.settings.output_directory
        Path(target).mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", target], check=False)
            else:
                subprocess.run(["xdg-open", target], check=False)
        except Exception as e:
            QMessageBox.warning(self, "—", f"Could not open folder: {e}")

    # ── i18n ──────────────────────────────────────────────
    def on_language_changed(self):
        self.cfg_group.setTitle(t("library.title"))
        self.lbl_subtitle.setText(t("library.subtitle"))
        self.lbl_name.setText(t("library.name_label"))
        self.name_input.setPlaceholderText(t("library.name_placeholder"))
        self.lbl_desc.setText(t("library.desc_label"))
        self.desc_input.setPlaceholderText(t("library.desc_placeholder"))
        self.lbl_lang.setText(t("library.language_label"))
        self.lbl_scope.setText(t("library.scope_label"))
        self.chk_tests.setText(t("library.include_tests"))
        self.chk_examples.setText(t("library.include_examples"))
        self.chk_readme.setText(t("library.include_readme"))
        self.run_btn.setText(t("library.run_btn"))
        self.stop_btn.setText(t("common.stop"))
        self.open_btn.setText("📂 " + t("architect.open_output_btn"))
        self.lbl_progress.setText(t("shared.progress_label"))
        self.tabs.setTabText(0, t("shared.live_log_tab"))
        self.tabs.setTabText(1, t("shared.file_tree_tab"))
        self.tabs.setTabText(2, t("shared.code_preview_tab"))
        self.clear_logs_btn.setText(t("shared.clear_logs_btn"))
        self.copy_btn.setText(t("shared.copy_btn"))
        self.save_btn.setText(t("shared.save_btn"))

        # Re-translate scope combo (preserve selection)
        cur_scope = self.scope_combo.currentData()
        self.scope_combo.clear()
        for scope_id, scope_def in SCOPES.items():
            self.scope_combo.addItem(t(scope_def["label_key"]), userData=scope_id)
        idx = self.scope_combo.findData(cur_scope)
        if idx >= 0:
            self.scope_combo.setCurrentIndex(idx)
