from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from core.config import AppSettings
from core.i18n import t
from core.secrets import get_api_key
from core.workers.simple_worker import SimpleWorker
from tabs.base_tab import BaseTab
from ui.highlighters.code_highlighter import CodeHighlighter
from ui.theme import PALETTE as P
from ui.widgets.output_panel import OutputPanel


MODES = {
    "schema":    {"key": "db.mode_schema",    "log": "Designing schema",    "filename": "schema.sql"},
    "optimize":  {"key": "db.mode_optimize",  "log": "Optimizing query",    "filename": "optimized.md"},
    "migration": {"key": "db.mode_migration", "log": "Generating migration", "filename": "migration.sql"},
    "seed":      {"key": "db.mode_seed",      "log": "Generating seed data", "filename": "seed.sql"},
    "explain":   {"key": "db.mode_explain",   "log": "Explaining query",    "filename": "explanation.md"},
}

DIALECTS = {
    "postgres": "db.dialect_postgres",
    "mysql":    "db.dialect_mysql",
    "sqlite":   "db.dialect_sqlite",
    "mssql":    "db.dialect_mssql",
    "oracle":   "db.dialect_oracle",
}

ORMS = {
    "none":       "db.orm_none",
    "sqlalchemy": "db.orm_sqlalchemy",
    "prisma":     "db.orm_prisma",
    "typeorm":    "db.orm_typeorm",
    "django":     "db.orm_django",
    "drizzle":    "db.orm_drizzle",
}


def build_system_prompt(
    mode: str, dialect: str, orm: str,
    indexes: bool, constraints: bool, comments: bool,
    target_count: int,
) -> str:
    dialect_label = {
        "postgres": "PostgreSQL",
        "mysql":    "MySQL",
        "sqlite":   "SQLite",
        "mssql":    "Microsoft SQL Server (T-SQL)",
        "oracle":   "Oracle (PL/SQL)",
    }.get(dialect, "PostgreSQL")

    if mode == "schema":
        body_parts = [
            f"You are an expert database architect. Design a normalized "
            f"{dialect_label} schema based on the user's description.",
            "Output a single SQL script with:",
            "- CREATE TABLE statements in dependency order",
            f"- {'Primary keys, foreign keys, unique constraints, and check constraints' if constraints else 'Primary keys only — minimal constraints'}",
            f"- {'Recommended indexes on foreign keys and frequent query columns' if indexes else 'No indexes — keep it minimal'}",
            f"- {'COMMENT ON statements explaining each table and key column' if comments else 'No comments'}",
            "- Use idiomatic types and conventions for " + dialect_label,
        ]
        if orm and orm != "none":
            orm_label = {
                "sqlalchemy": "SQLAlchemy 2.0 declarative",
                "prisma":     "Prisma (schema.prisma)",
                "typeorm":    "TypeORM (TypeScript)",
                "django":     "Django models.py",
                "drizzle":    "Drizzle ORM (TypeScript)",
            }.get(orm, orm)
            body_parts.append(
                f"\nAFTER the SQL, append a section labeled `-- ORM Models ({orm_label})` "
                f"followed by matching {orm_label} model code in a comment block "
                f"(use multiline /* */ syntax)."
            )
        body_parts.append("\nOutput ONLY SQL. No markdown fences. No prose explanations.")
        return "\n".join(body_parts)

    if mode == "optimize":
        return (
            f"You are a {dialect_label} performance specialist. Analyze the user's slow "
            f"query and produce a Markdown report with:\n"
            f"## Diagnosis\n## Optimized Query\n## Recommended Indexes\n"
            f"## Estimated Improvement\n"
            f"\n"
            f"Be concrete about why each change helps (use of indexes, avoiding sequential "
            f"scans, reducing temporary tables, etc.). Include the optimized query in a "
            f"```sql code block."
        )

    if mode == "migration":
        return (
            f"You are a {dialect_label} expert. Generate a migration script with two clear "
            f"sections:\n\n-- ===== UP =====\n(forward migration SQL)\n"
            f"\n-- ===== DOWN =====\n(reverse/rollback SQL)\n\n"
            f"Use idempotent operations where the dialect supports it (IF EXISTS, IF NOT EXISTS).\n"
            f"{'Preserve referential integrity and indexes.' if constraints else ''}\n"
            f"Output ONLY SQL. No markdown fences. No prose."
        )

    if mode == "seed":
        return (
            f"You are a {dialect_label} expert. Generate INSERT statements producing "
            f"realistic seed data based on the user's description.\n"
            f"Target row count: approximately {target_count} rows total (distribute "
            f"sensibly across tables).\n"
            f"Use varied, realistic-looking values. For dates use ISO format. "
            f"Reference foreign keys correctly.\n"
            f"{'Wrap each table block with a comment header.' if comments else ''}\n"
            f"Output ONLY SQL. No markdown fences. No prose."
        )

    if mode == "explain":
        return (
            f"You are a {dialect_label} expert and patient teacher. Explain the user's SQL "
            f"query clearly to a developer who reads SQL but is unfamiliar with this query.\n"
            f"Use Markdown. Cover: what the query returns, the join graph, any subqueries "
            f"or CTEs, filtering logic, and any potential gotchas (NULL handling, "
            f"performance concerns, etc.). Use diagrams (ASCII or Mermaid) where helpful."
        )

    return "Generate SQL output for the user's request."


class DatabaseTab(BaseTab):
    """Database tools — schema design, optimization, migrations."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._worker: SimpleWorker | None = None
        self._pending_filename: str = "result.sql"
        self._build_ui()

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

        # Initial sync — runs after both panels exist, so handlers can safely
        # reference widgets from either side.
        self._on_mode_changed(0)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 8, 4)
        layout.setSpacing(10)

        # Configuration
        self.cfg_group = QGroupBox(t("db.title"))
        cfg_layout = QVBoxLayout(self.cfg_group)
        cfg_layout.setSpacing(8)

        self.lbl_subtitle = QLabel(t("db.subtitle"))
        self.lbl_subtitle.setObjectName("hint")
        self.lbl_subtitle.setWordWrap(True)
        cfg_layout.addWidget(self.lbl_subtitle)

        # Mode + Dialect
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.lbl_mode = self.section_label(t("db.mode_label"))
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumHeight(32)
        for mode_id, mode_def in MODES.items():
            self.mode_combo.addItem(t(mode_def["key"]), userData=mode_id)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        self.lbl_dialect = self.section_label(t("db.dialect_label"))
        self.dialect_combo = QComboBox()
        self.dialect_combo.setMinimumHeight(32)
        for dia_id, key in DIALECTS.items():
            self.dialect_combo.addItem(t(key), userData=dia_id)

        row1.addWidget(self.lbl_mode)
        row1.addWidget(self.mode_combo, 1)
        row1.addSpacing(8)
        row1.addWidget(self.lbl_dialect)
        row1.addWidget(self.dialect_combo, 1)
        cfg_layout.addLayout(row1)

        # ORM (only relevant for schema mode)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.lbl_orm = self.section_label(t("db.orm_label"))
        self.orm_combo = QComboBox()
        self.orm_combo.setMinimumHeight(32)
        for orm_id, key in ORMS.items():
            self.orm_combo.addItem(t(key), userData=orm_id)
        row2.addWidget(self.lbl_orm)
        row2.addWidget(self.orm_combo, 1)
        cfg_layout.addLayout(row2)

        # Target row count (only for seed mode)
        self.row3 = QHBoxLayout()
        self.row3.setSpacing(8)
        self.lbl_target_count = self.section_label(t("db.target_count_label"))
        self.target_count_spin = QSpinBox()
        self.target_count_spin.setRange(10, 100000)
        self.target_count_spin.setValue(100)
        self.target_count_spin.setSingleStep(10)
        self.target_count_spin.setMinimumHeight(32)
        self.row3.addWidget(self.lbl_target_count)
        self.row3.addStretch()
        self.row3.addWidget(self.target_count_spin)
        cfg_layout.addLayout(self.row3)

        # Options
        opts = QHBoxLayout()
        self.chk_indexes     = QCheckBox(t("db.include_indexes"))
        self.chk_indexes.setChecked(True)
        self.chk_constraints = QCheckBox(t("db.include_constraints"))
        self.chk_constraints.setChecked(True)
        self.chk_comments    = QCheckBox(t("db.include_comments"))
        opts.addWidget(self.chk_indexes)
        opts.addWidget(self.chk_constraints)
        opts.addWidget(self.chk_comments)
        opts.addStretch()
        cfg_layout.addLayout(opts)

        layout.addWidget(self.cfg_group)

        # Input
        self.input_group = QGroupBox(t("db.input_label"))
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
        self.input_view.setPlaceholderText(t("db.input_schema_placeholder"))
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
        self.run_btn = QPushButton(t("db.run_btn"))
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

    def _on_mode_changed(self, _idx: int):
        mode = self.mode_combo.currentData() or "schema"

        # Update placeholder text per mode
        placeholders = {
            "schema":    "db.input_schema_placeholder",
            "optimize":  "db.input_query_placeholder",
            "migration": "db.input_migration_placeholder",
            "seed":      "db.input_seed_placeholder",
            "explain":   "db.input_query_placeholder",
        }
        self.input_view.setPlaceholderText(t(placeholders.get(mode, "db.input_schema_placeholder")))

        # ORM: only meaningful for schema mode
        is_schema = (mode == "schema")
        self.orm_combo.setEnabled(is_schema)
        self.lbl_orm.setEnabled(is_schema)

        # Target count: only for seed mode
        is_seed = (mode == "seed")
        self.target_count_spin.setEnabled(is_seed)
        self.lbl_target_count.setEnabled(is_seed)

        # Indexes/constraints checkboxes are most relevant for schema/migration
        relevant_checks = mode in ("schema", "migration")
        self.chk_indexes.setEnabled(relevant_checks)
        self.chk_constraints.setEnabled(relevant_checks)
        # Comments are relevant for schema/seed
        self.chk_comments.setEnabled(mode in ("schema", "seed"))

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
        input_text = self.input_view.toPlainText().strip()
        if not input_text:
            QMessageBox.warning(self, "—", t("common.no_input"))
            return

        provider_id = self.settings.active_provider
        if not get_api_key(provider_id):
            QMessageBox.warning(self, "—", t("validation.no_provider"))
            return

        mode    = self.mode_combo.currentData()    or "schema"
        dialect = self.dialect_combo.currentData() or "postgres"
        orm     = self.orm_combo.currentData()     or "none"

        system_prompt = build_system_prompt(
            mode=mode,
            dialect=dialect,
            orm=orm if mode == "schema" else "none",
            indexes=self.chk_indexes.isChecked(),
            constraints=self.chk_constraints.isChecked(),
            comments=self.chk_comments.isChecked(),
            target_count=self.target_count_spin.value(),
        )

        # Tailor the user prompt per mode
        user_prompt = {
            "schema":    f"Schema description:\n\n{input_text}",
            "optimize":  f"Slow query (and any schema context):\n\n{input_text}",
            "migration": f"Migration description:\n\n{input_text}",
            "seed":      f"Seed data description:\n\n{input_text}",
            "explain":   f"Query to explain:\n\n{input_text}",
        }.get(mode, input_text)

        # SQL outputs strip fences; markdown reports keep them
        strip_fences = mode in ("schema", "migration", "seed")

        config = {
            "provider_id":   provider_id,
            "model":         self.settings.get_model(provider_id, "coder"),
            "system_prompt": system_prompt,
            "user_prompt":   user_prompt,
            "temperature":   0.3,
            "max_tokens":    4096,
            "strip_fences":  strip_fences,
            "log_label":     MODES[mode]["log"],
        }

        self._pending_filename = MODES[mode]["filename"]

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

    def on_language_changed(self):
        self.cfg_group.setTitle(t("db.title"))
        self.lbl_subtitle.setText(t("db.subtitle"))
        self.lbl_mode.setText(t("db.mode_label"))
        self.lbl_dialect.setText(t("db.dialect_label"))
        self.lbl_orm.setText(t("db.orm_label"))
        self.lbl_target_count.setText(t("db.target_count_label"))
        self.input_group.setTitle(t("db.input_label"))
        self.chk_indexes.setText(t("db.include_indexes"))
        self.chk_constraints.setText(t("db.include_constraints"))
        self.chk_comments.setText(t("db.include_comments"))
        self.run_btn.setText(t("db.run_btn"))
        self.stop_btn.setText(t("common.stop"))
        self.paste_btn.setText("📋 " + t("common.paste"))
        self.clear_input_btn.setText(t("common.clear"))

        # Re-translate combos (preserve selection)
        cur_mode = self.mode_combo.currentData()
        self.mode_combo.clear()
        for mode_id, mode_def in MODES.items():
            self.mode_combo.addItem(t(mode_def["key"]), userData=mode_id)
        idx = self.mode_combo.findData(cur_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        # Trigger placeholder update for the (re-set) mode
        self._on_mode_changed(self.mode_combo.currentIndex())

        cur_dia = self.dialect_combo.currentData()
        self.dialect_combo.clear()
        for dia_id, key in DIALECTS.items():
            self.dialect_combo.addItem(t(key), userData=dia_id)
        idx = self.dialect_combo.findData(cur_dia)
        if idx >= 0:
            self.dialect_combo.setCurrentIndex(idx)

        cur_orm = self.orm_combo.currentData()
        self.orm_combo.clear()
        for orm_id, key in ORMS.items():
            self.orm_combo.addItem(t(key), userData=orm_id)
        idx = self.orm_combo.findData(cur_orm)
        if idx >= 0:
            self.orm_combo.setCurrentIndex(idx)

        self.output.retranslate()
