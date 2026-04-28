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


# Per-style framework lists. First entry is the default for that style.
FRAMEWORKS_BY_STYLE: dict[str, list[str]] = {
    "rest": [
        "FastAPI (Python)",
        "Flask (Python)",
        "Express (Node.js)",
        "NestJS (Node.js / TypeScript)",
        "Spring Boot (Java)",
        "ASP.NET Core (C#)",
        "Gin (Go)",
        "Echo (Go)",
        "Axum (Rust)",
        "Actix-web (Rust)",
        "Ruby on Rails (Ruby)",
        "Laravel (PHP)",
    ],
    "graphql": [
        "Strawberry (Python)",
        "Graphene (Python)",
        "Apollo Server (Node.js)",
        "Mercurius (Fastify)",
        "graphql-yoga (Node.js)",
        "GraphQL Ruby",
        "graphql-java (Spring Boot)",
        "async-graphql (Rust)",
        "gqlgen (Go)",
    ],
    "grpc": [
        "grpcio (Python)",
        "grpc-node (Node.js / TypeScript)",
        "grpc-go (Go)",
        "tonic (Rust)",
        "grpc-java",
    ],
}

STYLES = {
    "rest":    "api.style_rest",
    "graphql": "api.style_graphql",
    "grpc":    "api.style_grpc",
}

AUTH = {
    "none":    "api.auth_none",
    "jwt":     "api.auth_jwt",
    "apikey":  "api.auth_apikey",
    "oauth":   "api.auth_oauth",
    "session": "api.auth_session",
}

SCOPES = {
    "minimal":  {"max_files": 4,  "key": "api.scope_minimal"},
    "standard": {"max_files": 7,  "key": "api.scope_standard"},
    "complete": {"max_files": 12, "key": "api.scope_complete"},
}


class APIBuilderTab(BaseTab):
    """Generate API scaffolding — REST/GraphQL/gRPC."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._worker: MultiFileWorker | None = None
        self._files: dict[str, str] = {}
        self._last_output_dir: str | None = None
        self._build_ui()

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

        # Sync framework list with the initial style
        self._populate_frameworks()

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(380)
        panel.setMaximumWidth(540)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 8, 4)
        layout.setSpacing(10)

        # Configuration
        self.cfg_group = QGroupBox(t("api.title"))
        cfg_layout = QVBoxLayout(self.cfg_group)
        cfg_layout.setSpacing(8)

        self.lbl_subtitle = QLabel(t("api.subtitle"))
        self.lbl_subtitle.setObjectName("hint")
        self.lbl_subtitle.setWordWrap(True)
        cfg_layout.addWidget(self.lbl_subtitle)

        # Name
        self.lbl_name = self.section_label(t("api.name_label"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("api.name_placeholder"))
        self.name_input.setMinimumHeight(32)
        cfg_layout.addWidget(self.lbl_name)
        cfg_layout.addWidget(self.name_input)

        # Description
        self.lbl_desc = self.section_label(t("api.desc_label"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(t("api.desc_placeholder"))
        self.desc_input.setFixedHeight(110)
        cfg_layout.addWidget(self.lbl_desc)
        cfg_layout.addWidget(self.desc_input)

        # Style + Framework
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.lbl_style = self.section_label(t("api.style_label"))
        self.style_combo = QComboBox()
        self.style_combo.setMinimumHeight(32)
        for style_id, key in STYLES.items():
            self.style_combo.addItem(t(key), userData=style_id)
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        row1.addWidget(self.lbl_style)
        row1.addWidget(self.style_combo, 1)
        cfg_layout.addLayout(row1)

        self.lbl_framework = self.section_label(t("api.framework_label"))
        self.framework_combo = QComboBox()
        self.framework_combo.setMinimumHeight(32)
        cfg_layout.addWidget(self.lbl_framework)
        cfg_layout.addWidget(self.framework_combo)

        # Auth + Scope
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.lbl_auth = self.section_label(t("api.auth_label"))
        self.auth_combo = QComboBox()
        self.auth_combo.setMinimumHeight(32)
        for auth_id, key in AUTH.items():
            self.auth_combo.addItem(t(key), userData=auth_id)
        self.auth_combo.setCurrentIndex(1)  # default: JWT
        self.lbl_scope = self.section_label(t("api.scope_label"))
        self.scope_combo = QComboBox()
        self.scope_combo.setMinimumHeight(32)
        for sc_id, sc_def in SCOPES.items():
            self.scope_combo.addItem(t(sc_def["key"]), userData=sc_id)
        self.scope_combo.setCurrentIndex(1)  # default: standard
        row2.addWidget(self.lbl_auth)
        row2.addWidget(self.auth_combo, 1)
        row2.addSpacing(8)
        row2.addWidget(self.lbl_scope)
        row2.addWidget(self.scope_combo, 1)
        cfg_layout.addLayout(row2)

        # Options
        self.chk_validation = QCheckBox(t("api.include_validation"))
        self.chk_validation.setChecked(True)
        self.chk_openapi    = QCheckBox(t("api.include_openapi"))
        self.chk_openapi.setChecked(True)
        self.chk_tests      = QCheckBox(t("api.include_tests"))
        self.chk_docker     = QCheckBox(t("api.include_docker"))
        for chk in (self.chk_validation, self.chk_openapi,
                    self.chk_tests, self.chk_docker):
            cfg_layout.addWidget(chk)

        layout.addWidget(self.cfg_group)
        layout.addStretch()

        # Action buttons
        self.run_btn = QPushButton(t("api.run_btn"))
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

    def _on_style_changed(self, _idx: int):
        self._populate_frameworks()

    def _populate_frameworks(self):
        style = self.style_combo.currentData() or "rest"
        frameworks = FRAMEWORKS_BY_STYLE.get(style, [])
        self.framework_combo.clear()
        self.framework_combo.addItems(frameworks)

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

        style     = self.style_combo.currentData()     or "rest"
        framework = self.framework_combo.currentText() or ""
        auth      = self.auth_combo.currentData()      or "none"
        scope_id  = self.scope_combo.currentData()     or "standard"
        max_files = SCOPES[scope_id]["max_files"]

        # Build extra instructions
        style_label = {"rest": "REST", "graphql": "GraphQL", "grpc": "gRPC"}[style]
        auth_label = {
            "none":    "no authentication",
            "jwt":     "JWT bearer token authentication",
            "apikey":  "API-key header authentication",
            "oauth":   "OAuth 2.0 authentication",
            "session": "session-based authentication",
        }[auth]

        extras = [
            f"- Build a {style_label} API using {framework}",
            f"- Authentication: {auth_label}",
        ]
        if self.chk_validation.isChecked():
            extras.append("- Include input validation (DTOs/schemas/Pydantic/Zod where appropriate)")
        if self.chk_openapi.isChecked() and style == "rest":
            extras.append("- Include an OpenAPI/Swagger specification file")
        if self.chk_openapi.isChecked() and style == "graphql":
            extras.append("- Include a complete schema.graphql file")
        if self.chk_tests.isChecked():
            extras.append("- Include integration tests for at least the main endpoints")
        if self.chk_docker.isChecked():
            extras.append("- Include a Dockerfile suitable for production deployment")
        extras.append("- Use a clear modular layout: routes/handlers, services, models, etc.")
        extras.append("- Follow the framework's idiomatic project structure")

        config = {
            "name":             name,
            "description":      desc,
            "language":         framework,  # passed as language to MultiFileWorker
            "kind":             "library",  # closest existing kind for endpoint scaffolding
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
        self.preview_filename.setText(f"◉  {Path(path).name}")
        self.code_view.setPlainText(content)
        item = QTreeWidgetItem([f"◉ {Path(path).name}", f"{len(content)} chars"])
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
                f"✓ API generated successfully!\n\nLocation:\n{message}",
            )
        else:
            self.status_signal.emit(t("status.error"), "err")
            QMessageBox.warning(self, t("status.error"), message)

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

    def on_language_changed(self):
        self.cfg_group.setTitle(t("api.title"))
        self.lbl_subtitle.setText(t("api.subtitle"))
        self.lbl_name.setText(t("api.name_label"))
        self.name_input.setPlaceholderText(t("api.name_placeholder"))
        self.lbl_desc.setText(t("api.desc_label"))
        self.desc_input.setPlaceholderText(t("api.desc_placeholder"))
        self.lbl_style.setText(t("api.style_label"))
        self.lbl_framework.setText(t("api.framework_label"))
        self.lbl_auth.setText(t("api.auth_label"))
        self.lbl_scope.setText(t("api.scope_label"))
        self.chk_validation.setText(t("api.include_validation"))
        self.chk_openapi.setText(t("api.include_openapi"))
        self.chk_tests.setText(t("api.include_tests"))
        self.chk_docker.setText(t("api.include_docker"))
        self.run_btn.setText(t("api.run_btn"))
        self.stop_btn.setText(t("common.stop"))
        self.open_btn.setText("📂 " + t("architect.open_output_btn"))
        self.lbl_progress.setText(t("shared.progress_label"))
        self.tabs.setTabText(0, t("shared.live_log_tab"))
        self.tabs.setTabText(1, t("shared.file_tree_tab"))
        self.tabs.setTabText(2, t("shared.code_preview_tab"))
        self.clear_logs_btn.setText(t("shared.clear_logs_btn"))
        self.copy_btn.setText(t("shared.copy_btn"))
        self.save_btn.setText(t("shared.save_btn"))

        # Re-translate combos (preserve selection)
        cur_style = self.style_combo.currentData()
        self.style_combo.clear()
        for style_id, key in STYLES.items():
            self.style_combo.addItem(t(key), userData=style_id)
        idx = self.style_combo.findData(cur_style)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)

        cur_auth = self.auth_combo.currentData()
        self.auth_combo.clear()
        for auth_id, key in AUTH.items():
            self.auth_combo.addItem(t(key), userData=auth_id)
        idx = self.auth_combo.findData(cur_auth)
        if idx >= 0:
            self.auth_combo.setCurrentIndex(idx)

        cur_scope = self.scope_combo.currentData()
        self.scope_combo.clear()
        for sc_id, sc_def in SCOPES.items():
            self.scope_combo.addItem(t(sc_def["key"]), userData=sc_id)
        idx = self.scope_combo.findData(cur_scope)
        if idx >= 0:
            self.scope_combo.setCurrentIndex(idx)
