"""
tabs/refactor_tab.py
══════════════════════════════════════════════════════════════
Code Refactor & Review tab.
Modes:
  • Refactor      — clean up, idiomatic rewrite
  • Security      — review for vulnerabilities
  • Performance   — review for perf bottlenecks
  • Explain       — line-by-line explanation
  • Modernize     — convert to latest syntax/idioms

The output is plain text (or code) — uses SimpleWorker.
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


# Common languages users will refactor
LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C#", "C++",
    "C", "Ruby", "PHP", "Kotlin", "Swift", "Scala", "Dart", "Shell / Bash",
    "SQL", "HTML / CSS",
]

# Mode definitions: (i18n_key, system_prompt_template, log_label, strip_fences)
MODES = {
    "refactor": {
        "label_key": "refactor.mode_refactor",
        "system": (
            "You are an expert {lang} developer with deep knowledge of idiomatic patterns.\n"
            "Your job: refactor the user's code to be cleaner, more idiomatic, and more "
            "maintainable while preserving exact original behavior unless asked otherwise.\n"
            "Output ONLY the refactored code. No explanations before or after, "
            "no markdown fences. {style_instr} {comment_instr}{preserve_instr}"
        ),
        "user": "Refactor this {lang} code:\n\n{code}",
        "log_label": "Refactoring code",
        "strip_fences": True,
        "result_filename": "refactored",
    },
    "security": {
        "label_key": "refactor.mode_security",
        "system": (
            "You are a senior security auditor. Review the {lang} code for vulnerabilities, "
            "unsafe patterns, injection risks, authentication flaws, and data leakage.\n"
            "Output a structured Markdown report with sections:\n"
            "  ## Summary\n  ## Findings (severity: critical/high/medium/low)\n"
            "  ## Recommended Fixes\n  ## Hardened Code (only if changes are clear)\n"
            "{style_instr}"
        ),
        "user": "Review this {lang} code for security issues:\n\n{code}",
        "log_label": "Running security review",
        "strip_fences": False,
        "result_filename": "security-review.md",
    },
    "performance": {
        "label_key": "refactor.mode_performance",
        "system": (
            "You are a performance engineer. Analyze the {lang} code for performance "
            "issues: complexity hotspots, unnecessary allocations, N+1 queries, "
            "blocking I/O, etc.\n"
            "Output a Markdown report with sections:\n"
            "  ## Summary\n  ## Bottlenecks\n  ## Optimizations\n  ## Optimized Code\n"
            "{style_instr}"
        ),
        "user": "Review this {lang} code for performance issues:\n\n{code}",
        "log_label": "Running performance review",
        "strip_fences": False,
        "result_filename": "performance-review.md",
    },
    "explain": {
        "label_key": "refactor.mode_explain",
        "system": (
            "You are a patient teacher. Explain the {lang} code clearly to a developer "
            "who is competent but unfamiliar with this specific code.\n"
            "Use Markdown. Cover: purpose, key data structures, control flow, "
            "any non-obvious patterns. {style_instr}"
        ),
        "user": "Explain this {lang} code:\n\n{code}",
        "log_label": "Explaining code",
        "strip_fences": False,
        "result_filename": "explanation.md",
    },
    "modernize": {
        "label_key": "refactor.mode_modernize",
        "system": (
            "You are an expert {lang} developer. Modernize the user's code using the "
            "latest stable syntax and idioms appropriate for {lang} as of 2026 — type "
            "hints, async where useful, modern stdlib features, etc.\n"
            "Output ONLY the modernized code. No explanations. No markdown fences. "
            "{style_instr} {comment_instr}{preserve_instr}"
        ),
        "user": "Modernize this {lang} code:\n\n{code}",
        "log_label": "Modernizing code",
        "strip_fences": True,
        "result_filename": "modernized",
    },
}


class RefactorTab(BaseTab):
    """Refactor / review / explain code."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._worker: SimpleWorker | None = None
        self._pending_filename: str = "result"
        self._build_ui()

    # ── UI Construction ───────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.addWidget(self._build_left_panel())
        right = self._build_right_panel()
        splitter.addWidget(right)
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
        self.cfg_group = QGroupBox(t("refactor.title"))
        cfg_layout = QVBoxLayout(self.cfg_group)
        cfg_layout.setSpacing(8)

        self.lbl_subtitle = QLabel(t("refactor.subtitle"))
        self.lbl_subtitle.setObjectName("hint")
        self.lbl_subtitle.setWordWrap(True)
        cfg_layout.addWidget(self.lbl_subtitle)

        # Mode + Language row
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.lbl_mode = self.section_label(t("refactor.mode_label"))
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumHeight(32)
        for mode_id, mode_def in MODES.items():
            self.mode_combo.addItem(t(mode_def["label_key"]), userData=mode_id)
        self.lbl_lang = self.section_label(t("refactor.language_label"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(LANGUAGES)
        self.lang_combo.setMinimumHeight(32)
        row1.addWidget(self.lbl_mode)
        row1.addWidget(self.mode_combo, 1)
        row1.addSpacing(8)
        row1.addWidget(self.lbl_lang)
        row1.addWidget(self.lang_combo, 1)
        cfg_layout.addLayout(row1)

        # Style + checkboxes
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.lbl_style = self.section_label(t("refactor.style_label"))
        self.style_combo = QComboBox()
        self.style_combo.setMinimumHeight(32)
        self.style_combo.addItem(t("refactor.style_concise"),  userData="concise")
        self.style_combo.addItem(t("refactor.style_balanced"), userData="balanced")
        self.style_combo.addItem(t("refactor.style_thorough"), userData="thorough")
        self.style_combo.setCurrentIndex(1)  # default: balanced
        row2.addWidget(self.lbl_style)
        row2.addWidget(self.style_combo, 1)
        cfg_layout.addLayout(row2)

        opts = QHBoxLayout()
        self.chk_preserve = QCheckBox(t("refactor.preserve_label"))
        self.chk_preserve.setChecked(True)
        self.chk_comments = QCheckBox(t("refactor.add_comments"))
        opts.addWidget(self.chk_preserve)
        opts.addWidget(self.chk_comments)
        opts.addStretch()
        cfg_layout.addLayout(opts)

        layout.addWidget(self.cfg_group)

        # Input area
        self.input_group = QGroupBox(t("refactor.input_label"))
        in_layout = QVBoxLayout(self.input_group)
        in_layout.setSpacing(6)

        in_header = QHBoxLayout()
        self.lbl_input = QLabel("")
        self.lbl_input.setObjectName("hint")
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
        self.input_view.setPlaceholderText(t("refactor.input_placeholder"))
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

        layout.addWidget(self.input_group, 1)  # stretch

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.run_btn = QPushButton(t("refactor.run_btn"))
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumHeight(44)
        self.run_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.run_btn.clicked.connect(self._start_run)

        self.stop_btn = QPushButton(t("common.stop"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_run)

        self.swap_btn = QPushButton(t("refactor.swap_btn"))
        self.swap_btn.setObjectName("ghost")
        self.swap_btn.setMinimumHeight(38)
        self.swap_btn.setToolTip(t("refactor.swap_btn"))
        self.swap_btn.clicked.connect(self._swap_input)

        btn_row.addWidget(self.run_btn, 3)
        btn_row.addWidget(self.swap_btn, 1)
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
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.input_view.setPlainText(text)

    def _swap_input(self):
        result = self.output.get_result_text()
        if result.strip():
            self.input_view.setPlainText(result)
            self.status_signal.emit("Result moved to input", "ok")

    def _copy_result(self):
        text = self.output.get_result_text()
        if text:
            QApplication.clipboard().setText(text)
            self.status_signal.emit(t("common.copied"), "ok")

    def _save_result(self):
        text = self.output.get_result_text()
        if not text:
            return
        mode_id = self.mode_combo.currentData() or "refactor"
        suggested = MODES[mode_id]["result_filename"]
        if not suggested.endswith(".md"):
            ext = self._extension_for_language(self.lang_combo.currentText())
            suggested = f"{suggested}{ext}"
        path, _ = QFileDialog.getSaveFileName(
            self, t("common.save"), suggested, "All Files (*.*)"
        )
        if path:
            try:
                Path(path).write_text(text, encoding="utf-8")
                self.status_signal.emit(f"Saved: {Path(path).name}", "ok")
            except OSError as e:
                QMessageBox.warning(self, "—", f"Save failed: {e}")

    # ── Generation ────────────────────────────────────────
    def _start_run(self):
        code = self.input_view.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "—", t("common.no_input"))
            return

        provider_id = self.settings.active_provider
        if not get_api_key(provider_id):
            QMessageBox.warning(self, "—", t("validation.no_provider"))
            return

        mode_id = self.mode_combo.currentData() or "refactor"
        mode_def = MODES[mode_id]
        lang = self.lang_combo.currentText()

        # Style instructions
        style = self.style_combo.currentData()
        style_instr = {
            "concise":  "Be concise — minimize prose.",
            "balanced": "Balance brevity and detail.",
            "thorough": "Be thorough — explain reasoning.",
        }.get(style, "")

        comment_instr = (
            "Add explanatory comments where the logic is non-obvious. "
            if self.chk_comments.isChecked() else "Avoid adding new comments. "
        )
        preserve_instr = (
            "Preserve the exact original behavior."
            if self.chk_preserve.isChecked() and mode_id in ("refactor", "modernize")
            else ""
        )

        system_prompt = mode_def["system"].format(
            lang=lang,
            style_instr=style_instr,
            comment_instr=comment_instr,
            preserve_instr=preserve_instr,
        )
        user_prompt = mode_def["user"].format(lang=lang, code=code)

        config = {
            "provider_id":   provider_id,
            "model":         self.settings.get_model(provider_id, "coder"),
            "system_prompt": system_prompt,
            "user_prompt":   user_prompt,
            "temperature":   0.3,
            "max_tokens":    4096,
            "strip_fences":  mode_def["strip_fences"],
            "log_label":     mode_def["log_label"],
        }

        # Reset UI
        self.output.clear()
        self.output.show_processing()
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_signal.emit(t("status.generating"), "info")

        # Determine result filename for the output tab header
        result_name = mode_def["result_filename"]
        if not result_name.endswith(".md"):
            ext = self._extension_for_language(lang)
            result_name = f"{result_name}{ext}"
        self._pending_filename = result_name

        # Spawn worker
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
        self.output.log("Stop requested — finishing current step…", "WARN")

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

    # ── Helpers ───────────────────────────────────────────
    @staticmethod
    def _extension_for_language(lang: str) -> str:
        lang_lower = lang.lower()
        mapping = {
            "python":     ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "go":         ".go",
            "rust":       ".rs",
            "java":       ".java",
            "c#":         ".cs",
            "c++":        ".cpp",
            "c":          ".c",
            "ruby":       ".rb",
            "php":        ".php",
            "kotlin":     ".kt",
            "swift":      ".swift",
            "scala":      ".scala",
            "dart":       ".dart",
            "shell":      ".sh",
            "sql":        ".sql",
            "html":       ".html",
        }
        for key, ext in mapping.items():
            if key in lang_lower:
                return ext
        return ".txt"

    # ── i18n ──────────────────────────────────────────────
    def on_language_changed(self):
        self.cfg_group.setTitle(t("refactor.title"))
        self.lbl_subtitle.setText(t("refactor.subtitle"))
        self.lbl_mode.setText(t("refactor.mode_label"))
        self.lbl_lang.setText(t("refactor.language_label"))
        self.lbl_style.setText(t("refactor.style_label"))
        self.input_group.setTitle(t("refactor.input_label"))
        self.input_view.setPlaceholderText(t("refactor.input_placeholder"))
        self.chk_preserve.setText(t("refactor.preserve_label"))
        self.chk_comments.setText(t("refactor.add_comments"))
        self.run_btn.setText(t("refactor.run_btn"))
        self.stop_btn.setText(t("common.stop"))
        self.swap_btn.setText(t("refactor.swap_btn"))
        self.paste_btn.setText("📋 " + t("common.paste"))
        self.clear_input_btn.setText(t("common.clear"))

        # Re-translate combo items (preserve selection)
        cur_mode = self.mode_combo.currentData()
        self.mode_combo.clear()
        for mode_id, mode_def in MODES.items():
            self.mode_combo.addItem(t(mode_def["label_key"]), userData=mode_id)
        idx = self.mode_combo.findData(cur_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)

        cur_style = self.style_combo.currentData()
        self.style_combo.clear()
        self.style_combo.addItem(t("refactor.style_concise"),  userData="concise")
        self.style_combo.addItem(t("refactor.style_balanced"), userData="balanced")
        self.style_combo.addItem(t("refactor.style_thorough"), userData="thorough")
        idx = self.style_combo.findData(cur_style)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)

        self.output.retranslate()
