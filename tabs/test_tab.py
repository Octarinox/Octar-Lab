"""
tabs/test_tab.py
══════════════════════════════════════════════════════════════
Test Generator tab.
Generates unit, integration, end-to-end, or property-based
tests for existing code. Framework selection is dynamic and
keyed off the chosen language.

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


# Per-language test framework options. First entry is the default.
FRAMEWORKS_BY_LANGUAGE: dict[str, list[str]] = {
    "Python":     ["pytest", "unittest", "hypothesis"],
    "JavaScript": ["Jest", "Vitest", "Mocha", "Jasmine"],
    "TypeScript": ["Jest", "Vitest", "Mocha", "Jasmine"],
    "Go":         ["testing (stdlib)", "testify", "ginkgo"],
    "Rust":       ["cargo test", "proptest"],
    "Java":       ["JUnit 5", "JUnit 4", "TestNG"],
    "C#":         ["xUnit", "NUnit", "MSTest"],
    "C++":        ["Google Test", "Catch2", "doctest"],
    "Ruby":       ["RSpec", "Minitest"],
    "PHP":        ["PHPUnit", "Pest"],
    "Kotlin":     ["JUnit 5 + MockK", "Kotest"],
    "Swift":      ["XCTest", "Quick + Nimble"],
    "Scala":      ["ScalaTest", "MUnit"],
    "Dart":       ["test package"],
}

KINDS = {
    "unit":        "tests.kind_unit",
    "integration": "tests.kind_integration",
    "e2e":         "tests.kind_e2e",
    "property":    "tests.kind_property",
}

COVERAGE_LEVELS = {
    "basic":      "tests.coverage_basic",
    "thorough":   "tests.coverage_thorough",
    "exhaustive": "tests.coverage_exhaustive",
}

STYLES = {
    "aaa":     "tests.style_aaa",
    "given":   "tests.style_given",
    "minimal": "tests.style_minimal",
}


def build_system_prompt(
    language: str, framework: str, kind: str, coverage: str, style: str,
    fixtures: bool, mocks: bool, comments: bool,
) -> str:
    coverage_text = {
        "basic":      "the main happy paths only",
        "thorough":   "all common paths plus edge cases (empty, null, boundary, error)",
        "exhaustive": "every branch and condition; aim for full code path coverage",
    }.get(coverage, "common paths plus edge cases")

    style_text = {
        "aaa":     "Use the Arrange-Act-Assert pattern with clear sections.",
        "given":   "Use the Given-When-Then pattern with descriptive names.",
        "minimal": "Keep tests minimal and focused — one clear concern per test.",
    }.get(style, "")

    kind_text = {
        "unit":        "isolated unit tests for individual functions/methods",
        "integration": "integration tests covering interactions between modules",
        "e2e":         "end-to-end tests covering full user flows",
        "property":    "property-based tests using generators/fuzzing",
    }.get(kind, "tests")

    fixtures_line = (
        "Include reusable fixtures/setup helpers where they reduce duplication."
        if fixtures else "Do not introduce fixtures unless absolutely necessary."
    )
    mocks_line = (
        "Use mocks/stubs for external dependencies (DB, network, filesystem) where helpful."
        if mocks else "Avoid mocks — test the real code path where reasonable."
    )
    comments_line = (
        "Add brief explanatory comments above non-obvious assertions."
        if comments else "Keep tests self-explanatory through naming; avoid comments."
    )

    return (
        f"You are an expert {language} test author writing {kind_text}.\n"
        f"Use the {framework} framework. Coverage goal: {coverage_text}.\n"
        f"{style_text}\n"
        f"{fixtures_line}\n"
        f"{mocks_line}\n"
        f"{comments_line}\n"
        f"\n"
        f"Output ONLY the test file contents — production-ready, runnable code. "
        f"No markdown fences, no explanations before or after."
    )


class TestGenTab(BaseTab):
    """Generate tests for source code."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._worker: SimpleWorker | None = None
        self._pending_filename: str = "test_result.py"
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
        self.cfg_group = QGroupBox(t("tests.title"))
        cfg_layout = QVBoxLayout(self.cfg_group)
        cfg_layout.setSpacing(8)

        self.lbl_subtitle = QLabel(t("tests.subtitle"))
        self.lbl_subtitle.setObjectName("hint")
        self.lbl_subtitle.setWordWrap(True)
        cfg_layout.addWidget(self.lbl_subtitle)

        # Language + framework
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.lbl_lang = self.section_label(t("tests.language_label"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(list(FRAMEWORKS_BY_LANGUAGE.keys()))
        self.lang_combo.setMinimumHeight(32)
        self.lang_combo.currentTextChanged.connect(self._on_language_changed_combo)
        self.lbl_framework = self.section_label(t("tests.framework_label"))
        self.framework_combo = QComboBox()
        self.framework_combo.setMinimumHeight(32)
        row1.addWidget(self.lbl_lang)
        row1.addWidget(self.lang_combo, 1)
        row1.addSpacing(8)
        row1.addWidget(self.lbl_framework)
        row1.addWidget(self.framework_combo, 1)
        cfg_layout.addLayout(row1)
        self._populate_frameworks()

        # Kind + Coverage
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.lbl_kind = self.section_label(t("tests.kind_label"))
        self.kind_combo = QComboBox()
        self.kind_combo.setMinimumHeight(32)
        for kind_id, key in KINDS.items():
            self.kind_combo.addItem(t(key), userData=kind_id)
        self.lbl_coverage = self.section_label(t("tests.coverage_label"))
        self.coverage_combo = QComboBox()
        self.coverage_combo.setMinimumHeight(32)
        for cov_id, key in COVERAGE_LEVELS.items():
            self.coverage_combo.addItem(t(key), userData=cov_id)
        self.coverage_combo.setCurrentIndex(1)  # default: thorough
        row2.addWidget(self.lbl_kind)
        row2.addWidget(self.kind_combo, 1)
        row2.addSpacing(8)
        row2.addWidget(self.lbl_coverage)
        row2.addWidget(self.coverage_combo, 1)
        cfg_layout.addLayout(row2)

        # Style
        row3 = QHBoxLayout()
        row3.setSpacing(8)
        self.lbl_style = self.section_label(t("tests.style_label"))
        self.style_combo = QComboBox()
        self.style_combo.setMinimumHeight(32)
        for style_id, key in STYLES.items():
            self.style_combo.addItem(t(key), userData=style_id)
        row3.addWidget(self.lbl_style)
        row3.addWidget(self.style_combo, 1)
        cfg_layout.addLayout(row3)

        # Options
        opts = QHBoxLayout()
        self.chk_fixtures = QCheckBox(t("tests.include_fixtures"))
        self.chk_fixtures.setChecked(True)
        self.chk_mocks    = QCheckBox(t("tests.include_mocks"))
        self.chk_mocks.setChecked(True)
        self.chk_comments = QCheckBox(t("tests.include_comments"))
        opts.addWidget(self.chk_fixtures)
        opts.addWidget(self.chk_mocks)
        opts.addWidget(self.chk_comments)
        opts.addStretch()
        cfg_layout.addLayout(opts)

        layout.addWidget(self.cfg_group)

        # Input
        self.input_group = QGroupBox(t("tests.input_label"))
        in_layout = QVBoxLayout(self.input_group)
        in_layout.setSpacing(6)

        in_header = QHBoxLayout()
        self.paste_btn = QPushButton("📋 " + t("common.paste"))
        self.clear_input_btn = QPushButton(t("common.clear"))
        for b in (self.paste_btn, self.clear_input_btn):
            b.setObjectName("ghost")
            b.setFixedHeight(26)
        self.paste_btn.clicked.connect(self._paste_input)
        self.clear_input_btn.clicked.connect(lambda: self.input_view.clear())
        in_header.addStretch()
        in_header.addWidget(self.paste_btn)
        in_header.addWidget(self.clear_input_btn)
        in_layout.addLayout(in_header)

        self.input_view = QPlainTextEdit()
        self.input_view.setPlaceholderText(t("tests.input_placeholder"))
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
        self.run_btn = QPushButton(t("tests.run_btn"))
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

    # ── Combo updates ─────────────────────────────────────
    def _populate_frameworks(self):
        lang = self.lang_combo.currentText()
        frameworks = FRAMEWORKS_BY_LANGUAGE.get(lang, ["generic"])
        self.framework_combo.clear()
        self.framework_combo.addItems(frameworks)

    def _on_language_changed_combo(self, _new_lang: str):
        self._populate_frameworks()

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

        language  = self.lang_combo.currentText()
        framework = self.framework_combo.currentText() or "generic"
        kind      = self.kind_combo.currentData()      or "unit"
        coverage  = self.coverage_combo.currentData()  or "thorough"
        style     = self.style_combo.currentData()     or "aaa"

        system_prompt = build_system_prompt(
            language=language,
            framework=framework,
            kind=kind,
            coverage=coverage,
            style=style,
            fixtures=self.chk_fixtures.isChecked(),
            mocks=self.chk_mocks.isChecked(),
            comments=self.chk_comments.isChecked(),
        )
        user_prompt = f"Write {kind} tests for this {language} code:\n\n{code}"

        config = {
            "provider_id":   provider_id,
            "model":         self.settings.get_model(provider_id, "coder"),
            "system_prompt": system_prompt,
            "user_prompt":   user_prompt,
            "temperature":   0.3,
            "max_tokens":    4096,
            "strip_fences":  True,
            "log_label":     f"Generating {kind} tests ({framework})",
        }

        # Determine output filename
        ext = self._extension_for_language(language)
        prefix = "test_" if "python" in language.lower() else ""
        suffix = ".test" if language.lower() in ("javascript", "typescript") else ""
        self._pending_filename = f"{prefix}generated{suffix}{ext}"

        # Reset UI
        self.output.clear()
        self.output.show_processing()
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_signal.emit(t("status.generating"), "info")

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
        self.cfg_group.setTitle(t("tests.title"))
        self.lbl_subtitle.setText(t("tests.subtitle"))
        self.lbl_lang.setText(t("tests.language_label"))
        self.lbl_framework.setText(t("tests.framework_label"))
        self.lbl_kind.setText(t("tests.kind_label"))
        self.lbl_coverage.setText(t("tests.coverage_label"))
        self.lbl_style.setText(t("tests.style_label"))
        self.input_group.setTitle(t("tests.input_label"))
        self.input_view.setPlaceholderText(t("tests.input_placeholder"))
        self.chk_fixtures.setText(t("tests.include_fixtures"))
        self.chk_mocks.setText(t("tests.include_mocks"))
        self.chk_comments.setText(t("tests.include_comments"))
        self.run_btn.setText(t("tests.run_btn"))
        self.stop_btn.setText(t("common.stop"))
        self.paste_btn.setText("📋 " + t("common.paste"))
        self.clear_input_btn.setText(t("common.clear"))

        # Re-translate combo items (preserve selection)
        cur_kind = self.kind_combo.currentData()
        self.kind_combo.clear()
        for kind_id, key in KINDS.items():
            self.kind_combo.addItem(t(key), userData=kind_id)
        idx = self.kind_combo.findData(cur_kind)
        if idx >= 0:
            self.kind_combo.setCurrentIndex(idx)

        cur_cov = self.coverage_combo.currentData()
        self.coverage_combo.clear()
        for cov_id, key in COVERAGE_LEVELS.items():
            self.coverage_combo.addItem(t(key), userData=cov_id)
        idx = self.coverage_combo.findData(cur_cov)
        if idx >= 0:
            self.coverage_combo.setCurrentIndex(idx)

        cur_style = self.style_combo.currentData()
        self.style_combo.clear()
        for style_id, key in STYLES.items():
            self.style_combo.addItem(t(key), userData=style_id)
        idx = self.style_combo.findData(cur_style)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)

        self.output.retranslate()
