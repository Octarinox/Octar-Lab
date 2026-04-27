"""
tabs/docs_tab.py
══════════════════════════════════════════════════════════════
Documentation Generator tab.
Generates README, API references, inline docs/docstrings,
tutorials, or changelog drafts from source code.

Uses SimpleWorker — single-prompt, single-response.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QSplitter, QVBoxLayout, QWidget,
)

from core.config import AppSettings
from core.i18n import t
from core.secrets import get_api_key
from core.workers.simple_worker import SimpleWorker
from tabs.base_tab import BaseTab
from ui.highlighters.code_highlighter import CodeHighlighter
from ui.theme import PALETTE as P
from ui.widgets.output_panel import OutputPanel


LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C#", "C++",
    "Ruby", "PHP", "Kotlin", "Swift", "Scala", "Dart",
]

KINDS = {
    "readme":    {"label_key": "docs.kind_readme",    "filename": "README.md"},
    "api":       {"label_key": "docs.kind_api",       "filename": "API.md"},
    "inline":    {"label_key": "docs.kind_inline",    "filename": "inline-docs"},
    "tutorial":  {"label_key": "docs.kind_tutorial",  "filename": "TUTORIAL.md"},
    "changelog": {"label_key": "docs.kind_changelog", "filename": "CHANGELOG.md"},
}

FORMATS = {
    "markdown":    "docs.format_markdown",
    "rst":          "docs.format_rst",
    "jsdoc":       "docs.format_jsdoc",
    "sphinx":      "docs.format_sphinx",
}

AUDIENCES = {
    "users":   "docs.audience_users",
    "devs":    "docs.audience_devs",
    "contrib": "docs.audience_contrib",
}


def build_system_prompt(kind: str, language: str, fmt: str, audience: str,
                         include_examples: bool, include_install: bool,
                         include_badges: bool) -> str:
    """Compose the system prompt for the documentation request."""
    audience_text = {
        "users":   "end users who want to use the software",
        "devs":    "developers integrating with or building on this code",
        "contrib": "contributors who want to extend or improve the project",
    }.get(audience, "general developers")

    extras: list[str] = []
    if include_examples:
        extras.append("- Include concrete usage examples with code")
    if include_install:
        extras.append("- Include installation / setup instructions")
    if include_badges:
        extras.append("- Include shields.io style badges where appropriate")
    extras_block = ("\n" + "\n".join(extras)) if extras else ""

    if kind == "readme":
        body = (
            "Generate a high-quality README for the provided {lang} code/project.\n"
            "Audience: {aud}.\n"
            "Output FORMAT: {fmt}.\n"
            "Include sections appropriate for the project: Overview, Features, "
            "Installation, Usage, API summary, Contributing, License.\n"
            "{extras}"
        )
    elif kind == "api":
        body = (
            "Generate an API reference for the provided {lang} code.\n"
            "Audience: {aud}.\n"
            "Output FORMAT: {fmt}.\n"
            "Document each public class/function/method: signature, parameters, "
            "return value, exceptions, and a brief description. Group related items.\n"
            "{extras}"
        )
    elif kind == "inline":
        body = (
            "Add high-quality inline documentation (docstrings/JSDoc/equivalent) "
            "to the provided {lang} code. Output the FULL ANNOTATED CODE — same "
            "logic, with documentation added. Do NOT change behavior. "
            "Use the language's idiomatic format ({fmt} where applicable).\n"
            "{extras}"
        )
    elif kind == "tutorial":
        body = (
            "Generate a step-by-step tutorial that teaches a {aud} how to use "
            "the provided {lang} code. Output FORMAT: {fmt}. Walk through the main "
            "use cases with running examples and explanations.\n"
            "{extras}"
        )
    elif kind == "changelog":
        body = (
            "Analyze the provided {lang} code and produce a draft CHANGELOG entry "
            "describing what this code does as if it were a new release. Use "
            "Keep-a-Changelog format. Output FORMAT: {fmt}.\n"
            "{extras}"
        )
    else:
        body = "Generate documentation for the provided {lang} code in {fmt} format."

    fmt_label = {
        "markdown": "Markdown",
        "rst":      "reStructuredText",
        "jsdoc":    "JSDoc-style comments",
        "sphinx":   "Sphinx-style reST with directives",
    }.get(fmt, fmt)

    return body.format(lang=language, aud=audience_text, fmt=fmt_label, extras=extras_block)


class DocsGenTab(BaseTab):
    """Generate documentation for source code."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._worker: SimpleWorker | None = None
        self._pending_filename: str = "result.md"
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
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([700, 700])
        layout.addWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 8, 4)
        layout.setSpacing(10)

        # Configuration group
        self.cfg_group = QGroupBox(t("docs.title"))
        cfg_layout = QVBoxLayout(self.cfg_group)
        cfg_layout.setSpacing(8)

        self.lbl_subtitle = QLabel(t("docs.subtitle"))
        self.lbl_subtitle.setObjectName("hint")
        self.lbl_subtitle.setWordWrap(True)
        cfg_layout.addWidget(self.lbl_subtitle)

        # Kind + Language
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.lbl_kind = self.section_label(t("docs.kind_label"))
        self.kind_combo = QComboBox()
        self.kind_combo.setMinimumHeight(32)
        for kind_id, kind_def in KINDS.items():
            self.kind_combo.addItem(t(kind_def["label_key"]), userData=kind_id)
        self.lbl_lang = self.section_label(t("docs.language_label"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(LANGUAGES)
        self.lang_combo.setMinimumHeight(32)
        row1.addWidget(self.lbl_kind)
        row1.addWidget(self.kind_combo, 1)
        row1.addSpacing(8)
        row1.addWidget(self.lbl_lang)
        row1.addWidget(self.lang_combo, 1)
        cfg_layout.addLayout(row1)

        # Format + Audience
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.lbl_format = self.section_label(t("docs.format_label"))
        self.format_combo = QComboBox()
        self.format_combo.setMinimumHeight(32)
        for fmt_id, fmt_key in FORMATS.items():
            self.format_combo.addItem(t(fmt_key), userData=fmt_id)
        self.lbl_audience = self.section_label(t("docs.audience_label"))
        self.audience_combo = QComboBox()
        self.audience_combo.setMinimumHeight(32)
        for aud_id, aud_key in AUDIENCES.items():
            self.audience_combo.addItem(t(aud_key), userData=aud_id)
        row2.addWidget(self.lbl_format)
        row2.addWidget(self.format_combo, 1)
        row2.addSpacing(8)
        row2.addWidget(self.lbl_audience)
        row2.addWidget(self.audience_combo, 1)
        cfg_layout.addLayout(row2)

        # Options
        opts = QHBoxLayout()
        self.chk_examples = QCheckBox(t("docs.include_examples"))
        self.chk_examples.setChecked(True)
        self.chk_install  = QCheckBox(t("docs.include_install"))
        self.chk_install.setChecked(True)
        self.chk_badges   = QCheckBox(t("docs.include_badges"))
        opts.addWidget(self.chk_examples)
        opts.addWidget(self.chk_install)
        opts.addWidget(self.chk_badges)
        opts.addStretch()
        cfg_layout.addLayout(opts)

        layout.addWidget(self.cfg_group)

        # Input group
        self.input_group = QGroupBox(t("docs.input_label"))
        in_layout = QVBoxLayout(self.input_group)
        in_layout.setSpacing(6)

        in_header = QHBoxLayout()
        self.lbl_input = QLabel("")
        self.paste_btn = QPushButton("📋 " + t("common.paste"))
        self.clear_input_btn = QPushButton(t("common.clear"))
        for b in (self.paste_btn, self.clear_input_btn):
            b.setObjectName("ghost")
            b.setFixedHeight(26)
        self.paste_btn.clicked.connect(self._paste_input)
        self.clear_input_btn.clicked.connect(lambda: self.input_view.clear())
        in_header.addWidget(self.lbl_input)
        in_header.addStretch()
        in_header.addWidget(self.paste_btn)
        in_header.addWidget(self.clear_input_btn)
        in_layout.addLayout(in_header)

        self.input_view = QPlainTextEdit()
        self.input_view.setPlaceholderText(t("docs.input_placeholder"))
        self.input_view.setFont(QFont("JetBrains Mono", 10))
        self.input_view.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {P['bg_void']};
                border: 1px solid {P['border']};
                border-radius: 8px;
                color: {P['text_prim']};
                padding: 10px;
                selection-background-color: {P['primary']};
            }}
            QPlainTextEdit:focus {{ border-color: {P['primary']}; }}
        """)
        self.input_highlighter = CodeHighlighter(self.input_view.document())
        in_layout.addWidget(self.input_view)

        layout.addWidget(self.input_group, 1)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.run_btn = QPushButton(t("docs.run_btn"))
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.run_btn.clicked.connect(self._start_run)
        self.stop_btn = QPushButton(t("common.stop"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_run)
        btn_row.addWidget(self.run_btn, 4)
        btn_row.addWidget(self.stop_btn, 1)
        layout.addLayout(btn_row)

        return panel

    def _build_right_panel(self) -> QWidget:
        self.output = OutputPanel()
        self.output.copy_requested.connect(self._copy_result)
        self.output.save_requested.connect(self._save_result)
        return self.output

    # ── Actions ───────────────────────────────────────────
    def _paste_input(self):
        text = QApplication.clipboard().text()
        if text:
            self.input_view.setPlainText(text)

    def _copy_result(self):
        text = self.output.get_result_text()
        if text:
            QApplication.clipboard().setText(text)
            self.status_signal.emit(t("common.copied"), "ok")

    def _save_result(self):
        text = self.output.get_result_text()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, t("common.save"), self._pending_filename, "All Files (*.*)"
        )
        if path:
            try:
                Path(path).write_text(text, encoding="utf-8")
                self.status_signal.emit(f"Saved: {Path(path).name}", "ok")
            except OSError as e:
                QMessageBox.warning(self, "—", f"Save failed: {e}")

    def _start_run(self):
        code = self.input_view.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "—", t("common.no_input"))
            return

        provider_id = self.settings.active_provider
        if not get_api_key(provider_id):
            QMessageBox.warning(self, "—", t("validation.no_provider"))
            return

        kind     = self.kind_combo.currentData()    or "readme"
        lang     = self.lang_combo.currentText()
        fmt      = self.format_combo.currentData()  or "markdown"
        audience = self.audience_combo.currentData() or "devs"

        system_prompt = build_system_prompt(
            kind=kind,
            language=lang,
            fmt=fmt,
            audience=audience,
            include_examples=self.chk_examples.isChecked(),
            include_install=self.chk_install.isChecked(),
            include_badges=self.chk_badges.isChecked(),
        )
        user_prompt = f"Source code:\n\n{code}"

        # For "inline" mode we want code output without fences;
        # otherwise we want raw markdown/rst/etc.
        strip_fences = (kind == "inline")

        config = {
            "provider_id":   provider_id,
            "model":         self.settings.get_model(provider_id, "coder"),
            "system_prompt": system_prompt,
            "user_prompt":   user_prompt,
            "temperature":   0.4,
            "max_tokens":    4096,
            "strip_fences":  strip_fences,
            "log_label":     f"Generating {kind} docs",
        }

        # Reset UI
        self.output.clear()
        self.output.show_processing()
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_signal.emit(t("status.generating"), "info")

        # Determine result filename
        kind_def = KINDS[kind]
        result_name = kind_def["filename"]
        if kind == "inline":
            ext = self._extension_for_language(lang)
            result_name = f"annotated{ext}"
        elif fmt == "rst" and result_name.endswith(".md"):
            result_name = result_name[:-3] + ".rst"
        self._pending_filename = result_name

        self._worker = SimpleWorker(config)
        self._worker.log_signal.connect(self.output.log)
        self._worker.progress_signal.connect(self.output.set_progress)
        self._worker.result_signal.connect(self._on_result)
        self._worker.done_signal.connect(self._on_done)
        self._worker.start()

    def _stop_run(self):
        if self._worker:
            self._worker.stop()
        self.stop_btn.setEnabled(False)

    def _on_result(self, text: str):
        self.output.set_result(text, self._pending_filename)

    def _on_done(self, success: bool, message: str):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if success:
            self.status_signal.emit(t("status.complete"), "ok")
        else:
            self.status_signal.emit(t("status.error"), "err")
            QMessageBox.warning(self, t("status.error"), message)

    @staticmethod
    def _extension_for_language(lang: str) -> str:
        mapping = {
            "python": ".py", "javascript": ".js", "typescript": ".ts",
            "go": ".go", "rust": ".rs", "java": ".java", "c#": ".cs",
            "c++": ".cpp", "ruby": ".rb", "php": ".php",
            "kotlin": ".kt", "swift": ".swift", "scala": ".scala",
            "dart": ".dart",
        }
        for key, ext in mapping.items():
            if key in lang.lower():
                return ext
        return ".txt"

    # ── i18n ──────────────────────────────────────────────
    def on_language_changed(self):
        self.cfg_group.setTitle(t("docs.title"))
        self.lbl_subtitle.setText(t("docs.subtitle"))
        self.lbl_kind.setText(t("docs.kind_label"))
        self.lbl_lang.setText(t("docs.language_label"))
        self.lbl_format.setText(t("docs.format_label"))
        self.lbl_audience.setText(t("docs.audience_label"))
        self.input_group.setTitle(t("docs.input_label"))
        self.input_view.setPlaceholderText(t("docs.input_placeholder"))
        self.chk_examples.setText(t("docs.include_examples"))
        self.chk_install.setText(t("docs.include_install"))
        self.chk_badges.setText(t("docs.include_badges"))
        self.run_btn.setText(t("docs.run_btn"))
        self.stop_btn.setText(t("common.stop"))
        self.paste_btn.setText("📋 " + t("common.paste"))
        self.clear_input_btn.setText(t("common.clear"))

        # Re-translate combo items (preserve selection)
        cur_kind = self.kind_combo.currentData()
        self.kind_combo.clear()
        for kind_id, kind_def in KINDS.items():
            self.kind_combo.addItem(t(kind_def["label_key"]), userData=kind_id)
        idx = self.kind_combo.findData(cur_kind)
        if idx >= 0:
            self.kind_combo.setCurrentIndex(idx)

        cur_fmt = self.format_combo.currentData()
        self.format_combo.clear()
        for fmt_id, fmt_key in FORMATS.items():
            self.format_combo.addItem(t(fmt_key), userData=fmt_id)
        idx = self.format_combo.findData(cur_fmt)
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)

        cur_aud = self.audience_combo.currentData()
        self.audience_combo.clear()
        for aud_id, aud_key in AUDIENCES.items():
            self.audience_combo.addItem(t(aud_key), userData=aud_id)
        idx = self.audience_combo.findData(cur_aud)
        if idx >= 0:
            self.audience_combo.setCurrentIndex(idx)

        self.output.retranslate()
