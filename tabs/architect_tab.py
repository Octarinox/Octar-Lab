"""
tabs/architect_tab.py
══════════════════════════════════════════════════════════════
The Project Architect tab — flagship feature of Octar Lab.
Generates complete production-ready project scaffolds via
the configured AI provider.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QSizePolicy, QSlider, QSpinBox,
    QSplitter, QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from core.ai_providers.factory import ProviderFactory
from core.config import AppSettings
from core.i18n import t
from core.secrets import get_api_key
from core.workers.generation_worker import GenerationWorker
from tabs.base_tab import BaseTab
from ui.highlighters.code_highlighter import CodeHighlighter
from ui.theme import PALETTE as P


SUPPORTED_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "React (TSX)", "Vue.js", "Next.js",
    "Node.js / Express", "C", "C++", "C#", "Java", "Go", "Rust", "Ruby",
    "Ruby on Rails", "Kotlin", "Swift", "PHP", "Laravel", "Dart / Flutter",
    "Scala", "Elixir / Phoenix", "Haskell", "Zig", "Lua", "Shell / Bash",
    "PowerShell", "R", "MATLAB / Octave",
]


class ArchitectTab(BaseTab):
    """Project architect — left-side configuration, right-side output."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._worker: GenerationWorker | None = None
        self._files: dict[str, str] = {}  # full_path -> content
        self._last_output_dir: str | None = None
        self._build_ui()

    # ── UI construction ───────────────────────────────────
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

        # ── Configuration ─────────────────────────────────
        cfg = QGroupBox(t("architect.title"))
        self._cfg_group = cfg
        cfg_layout = QVBoxLayout(cfg)
        cfg_layout.setSpacing(8)

        self.lbl_name = self.section_label(t("architect.name_label"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("architect.name_placeholder"))
        self.name_input.setMinimumHeight(34)
        cfg_layout.addWidget(self.lbl_name)
        cfg_layout.addWidget(self.name_input)

        self.lbl_desc = self.section_label(t("architect.desc_label"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(t("architect.desc_placeholder"))
        self.desc_input.setFixedHeight(110)
        cfg_layout.addWidget(self.lbl_desc)
        cfg_layout.addWidget(self.desc_input)

        self.lbl_lang = self.section_label(t("architect.language_label"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(SUPPORTED_LANGUAGES)
        self.lang_combo.setMinimumHeight(34)
        cfg_layout.addWidget(self.lbl_lang)
        cfg_layout.addWidget(self.lang_combo)

        layout.addWidget(cfg)

        # ── Generation Options ────────────────────────────
        self._opt_group = QGroupBox(t("architect.options_group"))
        opt_layout = QVBoxLayout(self._opt_group)
        opt_layout.setSpacing(6)
        self.chk_git    = QCheckBox(t("architect.opt_git"))
        self.chk_readme = QCheckBox(t("architect.opt_readme"))
        self.chk_deps   = QCheckBox(t("architect.opt_deps"))
        self.chk_git.setChecked(self.settings.auto_git_init)
        self.chk_readme.setChecked(self.settings.generate_readme)
        self.chk_deps.setChecked(self.settings.generate_deps)
        for chk in (self.chk_git, self.chk_readme, self.chk_deps):
            opt_layout.addWidget(chk)
        layout.addWidget(self._opt_group)

        # ── Advanced ──────────────────────────────────────
        self._adv_group = QGroupBox(t("architect.advanced_group"))
        adv_layout = QVBoxLayout(self._adv_group)
        adv_layout.setSpacing(8)

        # Temperature slider
        temp_row = QHBoxLayout()
        self.lbl_temp = self.section_label(t("architect.temperature_label"))
        self.temp_val = QLabel(f"{self.settings.temperature:.2f}")
        self.temp_val.setStyleSheet(
            f"color: {P['warning']}; font-weight: bold; min-width: 36px;"
        )
        temp_row.addWidget(self.lbl_temp)
        temp_row.addStretch()
        temp_row.addWidget(self.temp_val)
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 100)
        self.temp_slider.setValue(int(self.settings.temperature * 100))
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_val.setText(f"{v/100:.2f}")
        )
        adv_layout.addLayout(temp_row)
        adv_layout.addWidget(self.temp_slider)

        # Max files
        files_row = QHBoxLayout()
        self.lbl_maxf = self.section_label(t("architect.max_files_label"))
        self.maxfiles_spin = QSpinBox()
        self.maxfiles_spin.setRange(3, 30)
        self.maxfiles_spin.setValue(self.settings.max_files)
        self.maxfiles_spin.setFixedWidth(80)
        files_row.addWidget(self.lbl_maxf)
        files_row.addStretch()
        files_row.addWidget(self.maxfiles_spin)
        adv_layout.addLayout(files_row)

        layout.addWidget(self._adv_group)
        layout.addStretch()

        # ── Action buttons ────────────────────────────────
        self.gen_btn = QPushButton(t("architect.generate_btn"))
        self.gen_btn.setObjectName("primary")
        self.gen_btn.setMinimumHeight(46)
        self.gen_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.gen_btn.clicked.connect(self._start_generation)

        self.stop_btn = QPushButton(t("architect.stop_btn"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_generation)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(self.gen_btn, 3)
        btn_row.addWidget(self.stop_btn, 1)
        layout.addLayout(btn_row)

        self.open_btn = QPushButton(t("architect.open_output_btn"))
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

        self.lbl_progress = self.section_label(t("architect.progress_label"))
        layout.addWidget(self.lbl_progress)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%  —  %v / 100")
        self.progress_bar.setMinimumHeight(24)
        layout.addWidget(self.progress_bar)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_log_tab(), t("architect.live_log_tab"))
        self.tabs.addTab(self._build_tree_tab(), t("architect.file_tree_tab"))
        self.tabs.addTab(self._build_preview_tab(), t("architect.code_preview_tab"))

        return panel

    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(self.section_label(t("architect.live_log_tab")))
        header.addStretch()
        self.clear_logs_btn = QPushButton(t("architect.clear_logs_btn"))
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
        layout.addWidget(self.section_label(t("architect.file_tree_tab")))
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["Name", "Type", "Size"])
        self.file_tree.setColumnWidth(0, 280)
        self.file_tree.setColumnWidth(1, 80)
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.itemClicked.connect(self._on_tree_item_clicked)
        layout.addWidget(self.file_tree)
        return w

    def _build_preview_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.preview_filename = QLabel(t("architect.no_file_selected"))
        self.preview_filename.setStyleSheet(
            f"color: {P['warning']}; font-weight: bold;"
        )
        self.lint_btn = QPushButton(t("architect.lint_btn"))
        self.copy_btn = QPushButton(t("architect.copy_code_btn"))
        self.save_btn = QPushButton(t("architect.save_code_btn"))
        for b in (self.lint_btn, self.copy_btn, self.save_btn):
            b.setObjectName("ghost")
            b.setFixedHeight(26)
        self.lint_btn.setFixedWidth(150)
        self.copy_btn.setFixedWidth(110)
        self.save_btn.setFixedWidth(110)
        self.lint_btn.clicked.connect(self._lint_code)
        self.copy_btn.clicked.connect(self._copy_code)
        self.save_btn.clicked.connect(self._save_code)
        header.addWidget(self.preview_filename)
        header.addStretch()
        header.addWidget(self.lint_btn)
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

    # ── Tab lifecycle ─────────────────────────────────────
    def on_settings_changed(self):
        """Refresh from settings — picked-up before next generation."""
        self.chk_git.setChecked(self.settings.auto_git_init)
        self.chk_readme.setChecked(self.settings.generate_readme)
        self.chk_deps.setChecked(self.settings.generate_deps)

    def on_language_changed(self):
        self._cfg_group.setTitle(t("architect.title"))
        self.lbl_name.setText(t("architect.name_label"))
        self.name_input.setPlaceholderText(t("architect.name_placeholder"))
        self.lbl_desc.setText(t("architect.desc_label"))
        self.desc_input.setPlaceholderText(t("architect.desc_placeholder"))
        self.lbl_lang.setText(t("architect.language_label"))
        self._opt_group.setTitle(t("architect.options_group"))
        self.chk_git.setText(t("architect.opt_git"))
        self.chk_readme.setText(t("architect.opt_readme"))
        self.chk_deps.setText(t("architect.opt_deps"))
        self._adv_group.setTitle(t("architect.advanced_group"))
        self.lbl_temp.setText(t("architect.temperature_label"))
        self.lbl_maxf.setText(t("architect.max_files_label"))
        self.gen_btn.setText(t("architect.generate_btn"))
        self.stop_btn.setText(t("architect.stop_btn"))
        self.open_btn.setText(t("architect.open_output_btn"))
        self.lbl_progress.setText(t("architect.progress_label"))
        self.tabs.setTabText(0, t("architect.live_log_tab"))
        self.tabs.setTabText(1, t("architect.file_tree_tab"))
        self.tabs.setTabText(2, t("architect.code_preview_tab"))
        self.clear_logs_btn.setText(t("architect.clear_logs_btn"))
        self.lint_btn.setText(t("architect.lint_btn"))
        self.copy_btn.setText(t("architect.copy_code_btn"))
        self.save_btn.setText(t("architect.save_code_btn"))

    # ── Generation ────────────────────────────────────────
    def _start_generation(self):
        # Validate user input
        name = self.name_input.text().strip()
        desc = self.desc_input.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "—", t("validation.name_required"))
            return
        if not desc:
            QMessageBox.warning(self, "—", t("validation.desc_required"))
            return

        # Validate provider config
        provider_id = self.settings.active_provider
        if not get_api_key(provider_id):
            QMessageBox.warning(self, "—", t("validation.no_provider"))
            return

        config = {
            "name":            name,
            "description":     desc,
            "language":        self.lang_combo.currentText(),
            "temperature":     self.temp_slider.value() / 100,
            "max_files":       self.maxfiles_spin.value(),
            "git_init":        self.chk_git.isChecked(),
            "gen_readme":      self.chk_readme.isChecked(),
            "gen_deps":        self.chk_deps.isChecked(),
            "output_dir":      self.settings.output_directory,
            "provider_id":     provider_id,
            "architect_model": self.settings.get_model(provider_id, "architect"),
            "coder_model":     self.settings.get_model(provider_id, "coder"),
        }

        # Reset UI for new run
        self._files.clear()
        self.file_tree.clear()
        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.code_view.setPlainText("")
        self.preview_filename.setText(t("architect.generating_placeholder"))
        self.gen_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_signal.emit(t("status.generating"), "info")

        # Spawn worker
        self._worker = GenerationWorker(config)
        self._worker.log_signal.connect(self._on_log)
        self._worker.progress_signal.connect(self.progress_bar.setValue)
        self._worker.file_signal.connect(self._on_file_ready)
        self._worker.tree_signal.connect(self._populate_tree)
        self._worker.done_signal.connect(self._on_done)
        self._worker.start()

    def _stop_generation(self):
        if self._worker:
            self._worker.stop()
        self.stop_btn.setEnabled(False)
        self._on_log("Stop requested — finishing current file…", "WARN")

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
        self.preview_filename.setText(f"◉  {Path(path).name}")
        self.code_view.setPlainText(content)

    def _populate_tree(self, plan: dict):
        self.file_tree.clear()
        files = plan.get("files", [])
        dirs: dict[str, QTreeWidgetItem] = {}
        for f in files:
            path = f.get("path", "")
            ftype = f.get("type", "source")
            parts = Path(path).parts
            parent = self.file_tree.invisibleRootItem()
            for j, part in enumerate(parts[:-1]):
                key = "/".join(parts[: j + 1])
                if key not in dirs:
                    dir_item = QTreeWidgetItem(parent, [f"📁 {part}", "dir", ""])
                    dir_item.setForeground(0, QColor(P["accent"]))
                    dir_item.setExpanded(True)
                    dirs[key] = dir_item
                parent = dirs[key]
            icon = {
                "source": "◉", "config": "◈", "docs": "◆",
                "test":   "◇", "asset":  "◎",
            }.get(ftype, "·")
            item = QTreeWidgetItem(parent, [f"{icon} {parts[-1]}", ftype, "…"])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setForeground(1, QColor(P["text_dim"]))
        self.file_tree.expandAll()

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, _col: int):
        rel_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not rel_path:
            return
        for full_path, content in self._files.items():
            if full_path.endswith(rel_path):
                self.preview_filename.setText(f"◉  {rel_path}")
                self.code_view.setPlainText(content)
                self.tabs.setCurrentIndex(2)  # switch to preview
                return

    def _on_done(self, success: bool, message: str):
        self.gen_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if success:
            self._last_output_dir = message
            self.status_signal.emit(t("status.complete"), "ok")
            self._on_log(f"Project complete: {message}", "OK")
            QMessageBox.information(
                self, t("status.complete"),
                f"✓ Project generated successfully!\n\nLocation:\n{message}",
            )
        else:
            self.status_signal.emit(t("status.error"), "err")
            QMessageBox.critical(
                self, t("status.error"),
                f"✗ Generation failed:\n\n{message}",
            )

    # ── Tool buttons ──────────────────────────────────────
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

    def _copy_code(self):
        text = self.code_view.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status_signal.emit("Code copied to clipboard", "ok")

    def _save_code(self):
        text = self.code_view.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Code File", "", "All Files (*.*)")
        if path:
            try:
                Path(path).write_text(text, encoding="utf-8")
                self.status_signal.emit(f"Saved: {Path(path).name}", "ok")
            except OSError as e:
                QMessageBox.warning(self, "—", f"Save failed: {e}")

    def _lint_code(self):
        text = self.code_view.toPlainText()
        if not text:
            self._on_log("No code in preview to lint.", "WARN")
            return

        fname = self.preview_filename.text().replace("◉  ", "").strip()
        if fname.startswith("—"):
            self._on_log("No file selected.", "WARN")
            return

        ext = Path(fname).suffix.lower()
        formatter = self._pick_formatter(ext)
        if not formatter:
            self._on_log(f"No formatter configured for '{ext}' files.", "WARN")
            return

        tool, args_template = formatter
        if not shutil.which(tool):
            self._on_log(f"'{tool}' not installed — skipping format.", "WARN")
            return

        with tempfile.NamedTemporaryFile(
            suffix=ext, delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write(text)
            tmp_path = tmp.name

        try:
            args = [a.replace("{file}", tmp_path) for a in args_template]
            subprocess.run([tool] + args, capture_output=True, check=True)
            new_text = Path(tmp_path).read_text(encoding="utf-8")
            self.code_view.setPlainText(new_text)
            self._on_log(f"Formatted with {tool}", "OK")
        except subprocess.CalledProcessError as e:
            self._on_log(f"{tool} failed: {e.stderr.decode(errors='ignore')[:200]}", "WARN")
        except Exception as e:
            self._on_log(f"{tool} error: {e}", "WARN")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @staticmethod
    def _pick_formatter(ext: str) -> tuple[str, list[str]] | None:
        # (tool, arg-template list — "{file}" gets the temp path)
        mapping = {
            ".py":   ("black",    ["{file}"]),
            ".js":   ("prettier", ["--write", "{file}"]),
            ".ts":   ("prettier", ["--write", "{file}"]),
            ".tsx":  ("prettier", ["--write", "{file}"]),
            ".jsx":  ("prettier", ["--write", "{file}"]),
            ".json": ("prettier", ["--write", "{file}"]),
            ".rs":   ("rustfmt",  ["{file}"]),
        }
        return mapping.get(ext)
