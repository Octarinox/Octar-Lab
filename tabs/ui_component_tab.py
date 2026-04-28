from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor, QCursor, QDesktopServices, QFont
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
from core.workers.simple_worker import SimpleWorker
from tabs.base_tab import BaseTab
from ui.highlighters.code_highlighter import CodeHighlighter
from ui.theme import PALETTE as P


# Framework registry: id → (translation key, primary file extension, file pattern hint)
FRAMEWORKS = {
    "react_tsx": {
        "key":  "ui_comp.framework_react",
        "ext":  ".tsx",
        "kind": "React + TypeScript",
    },
    "react_jsx": {
        "key":  "ui_comp.framework_react_js",
        "ext":  ".jsx",
        "kind": "React + JavaScript",
    },
    "vue": {
        "key":  "ui_comp.framework_vue",
        "ext":  ".vue",
        "kind": "Vue 3 (Composition API, single-file component)",
    },
    "svelte": {
        "key":  "ui_comp.framework_svelte",
        "ext":  ".svelte",
        "kind": "Svelte 5 (single-file component)",
    },
    "html": {
        "key":  "ui_comp.framework_html",
        "ext":  ".html",
        "kind": "Standalone HTML + CSS + JavaScript (single self-contained file)",
    },
    "solid": {
        "key":  "ui_comp.framework_solid",
        "ext":  ".tsx",
        "kind": "SolidJS + TypeScript",
    },
}

STYLINGS = {
    "css":      "ui_comp.styling_css",
    "tailwind": "ui_comp.styling_tailwind",
    "styled":   "ui_comp.styling_styled",
    "module":   "ui_comp.styling_module",
    "inline":   "ui_comp.styling_inline",
}

SCOPES = {
    "single": "ui_comp.scope_single",
    "multi":  "ui_comp.scope_multi",
}


def build_single_file_prompt(
    name: str, description: str, framework_id: str, styling: str,
    a11y: bool, responsive: bool, props_doc: bool,
) -> str:
    fw = FRAMEWORKS[framework_id]
    style_text = {
        "css":      "Use plain CSS (in a <style> block or with className references).",
        "tailwind": "Use Tailwind CSS utility classes.",
        "styled":   "Use styled-components (CSS-in-JS).",
        "module":   "Use CSS Modules (assume `import styles from './X.module.css'`).",
        "inline":   "Use inline styles (style={{ ... }}).",
    }.get(styling, "Use idiomatic styling for the framework.")

    a11y_line = (
        "Apply accessibility best practices: semantic HTML, ARIA attributes where appropriate, "
        "keyboard navigation, focus management, sensible default `aria-label` values."
        if a11y else ""
    )
    responsive_line = (
        "Make the component responsive — work well on mobile (320px) through desktop (1920px)."
        if responsive else ""
    )
    props_line = (
        "Document all props/inputs at the top of the file in the language's idiomatic format "
        "(JSDoc, TSDoc, defineProps with types, etc.)."
        if props_doc else ""
    )

    return (
        f"You are an expert frontend engineer. Generate a production-ready "
        f"{fw['kind']} component named `{name}`.\n"
        f"\n"
        f"Component description:\n{description}\n"
        f"\n"
        f"Requirements:\n"
        f"- Output a single complete file ready to drop into a project\n"
        f"- {style_text}\n"
        f"- {a11y_line}\n"
        f"- {responsive_line}\n"
        f"- {props_line}\n"
        f"- Follow modern best practices for {fw['kind']} as of 2026\n"
        f"\n"
        f"Output ONLY the file contents. No markdown fences. No explanations."
    )


class UIComponentTab(BaseTab):
    """Generate UI components for various frontend frameworks."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._simple_worker:    SimpleWorker | None    = None
        self._multifile_worker: MultiFileWorker | None = None
        self._files:            dict[str, str] = {}
        self._last_output_dir:  str | None = None
        self._pending_filename: str = "Component.tsx"
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

        # Initial sync — must run AFTER both panels are constructed, because
        # _update_preview_btn_state references widgets from the right panel.
        self._on_scope_changed(0)
        self._update_preview_btn_state()

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(380)
        panel.setMaximumWidth(540)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 8, 4)
        layout.setSpacing(10)

        # Configuration
        self.cfg_group = QGroupBox(t("ui_comp.title"))
        cfg_layout = QVBoxLayout(self.cfg_group)
        cfg_layout.setSpacing(8)

        self.lbl_subtitle = QLabel(t("ui_comp.subtitle"))
        self.lbl_subtitle.setObjectName("hint")
        self.lbl_subtitle.setWordWrap(True)
        cfg_layout.addWidget(self.lbl_subtitle)

        # Name
        self.lbl_name = self.section_label(t("ui_comp.name_label"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("ui_comp.name_placeholder"))
        self.name_input.setMinimumHeight(32)
        cfg_layout.addWidget(self.lbl_name)
        cfg_layout.addWidget(self.name_input)

        # Description
        self.lbl_desc = self.section_label(t("ui_comp.desc_label"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(t("ui_comp.desc_placeholder"))
        self.desc_input.setFixedHeight(110)
        cfg_layout.addWidget(self.lbl_desc)
        cfg_layout.addWidget(self.desc_input)

        # Framework + Styling
        self.lbl_framework = self.section_label(t("ui_comp.framework_label"))
        self.framework_combo = QComboBox()
        self.framework_combo.setMinimumHeight(32)
        for fw_id, fw_def in FRAMEWORKS.items():
            self.framework_combo.addItem(t(fw_def["key"]), userData=fw_id)
        self.framework_combo.currentIndexChanged.connect(self._on_framework_changed)
        cfg_layout.addWidget(self.lbl_framework)
        cfg_layout.addWidget(self.framework_combo)

        self.lbl_styling = self.section_label(t("ui_comp.styling_label"))
        self.styling_combo = QComboBox()
        self.styling_combo.setMinimumHeight(32)
        for sty_id, key in STYLINGS.items():
            self.styling_combo.addItem(t(key), userData=sty_id)
        cfg_layout.addWidget(self.lbl_styling)
        cfg_layout.addWidget(self.styling_combo)

        # Scope
        self.lbl_scope = self.section_label(t("ui_comp.scope_label"))
        self.scope_combo = QComboBox()
        self.scope_combo.setMinimumHeight(32)
        for sc_id, key in SCOPES.items():
            self.scope_combo.addItem(t(key), userData=sc_id)
        self.scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        cfg_layout.addWidget(self.lbl_scope)
        cfg_layout.addWidget(self.scope_combo)

        # Options
        self.chk_storybook  = QCheckBox(t("ui_comp.include_storybook"))
        self.chk_props_doc  = QCheckBox(t("ui_comp.include_props_doc"))
        self.chk_props_doc.setChecked(True)
        self.chk_a11y       = QCheckBox(t("ui_comp.include_a11y"))
        self.chk_a11y.setChecked(True)
        self.chk_responsive = QCheckBox(t("ui_comp.include_responsive"))
        self.chk_responsive.setChecked(True)
        for chk in (self.chk_storybook, self.chk_props_doc,
                    self.chk_a11y, self.chk_responsive):
            cfg_layout.addWidget(chk)

        layout.addWidget(self.cfg_group)
        layout.addStretch()

        # Action buttons
        self.run_btn = QPushButton(t("ui_comp.run_btn"))
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

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.preview_btn = QPushButton(t("ui_comp.preview_btn"))
        self.preview_btn.setObjectName("accent")
        self.preview_btn.setMinimumHeight(34)
        self.preview_btn.clicked.connect(self._preview_in_browser)
        self.preview_btn.setEnabled(False)
        self.open_btn = QPushButton("📂 " + t("architect.open_output_btn"))
        self.open_btn.setObjectName("ghost")
        self.open_btn.setMinimumHeight(34)
        self.open_btn.clicked.connect(self._open_output_folder)
        bottom.addWidget(self.preview_btn)
        bottom.addWidget(self.open_btn)
        layout.addLayout(bottom)

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

    def _on_framework_changed(self, _idx: int):
        # Update the styling combo's relevance hint
        # (we don't disable options — different stylings are valid per framework)
        self._update_preview_btn_state()

    def _on_scope_changed(self, _idx: int):
        # Multi-file mode unlocks the storybook checkbox
        is_multi = (self.scope_combo.currentData() == "multi")
        self.chk_storybook.setEnabled(is_multi)
        if not is_multi:
            self.chk_storybook.setChecked(False)
        self._update_preview_btn_state()

    def _update_preview_btn_state(self):
        # Preview only makes sense for plain HTML output we can render directly.
        # This method may be called during UI construction before code_view exists,
        # so we guard against that case explicitly.
        if not hasattr(self, "code_view") or not hasattr(self, "preview_btn"):
            return
        is_html = (self.framework_combo.currentData() == "html")
        has_output = bool(self.code_view.toPlainText().strip())
        self.preview_btn.setEnabled(is_html and has_output)
        if not is_html:
            self.preview_btn.setToolTip(t("ui_comp.preview_unavailable"))
        else:
            self.preview_btn.setToolTip("")

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

        framework_id = self.framework_combo.currentData() or "react_tsx"
        scope        = self.scope_combo.currentData()     or "single"

        # Reset UI common to both modes
        self._files.clear()
        self.file_tree.clear()
        self.log_view.clear()
        self.progress_bar.setValue(0)
        self.code_view.setPlainText("")
        self.preview_filename.setText(t("shared.processing_placeholder"))
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_signal.emit(t("status.generating"), "info")

        if scope == "single":
            self._run_single(name, desc, framework_id)
        else:
            self._run_multi(name, desc, framework_id)

    def _run_single(self, name: str, desc: str, framework_id: str):
        styling = self.styling_combo.currentData() or "css"
        system_prompt = build_single_file_prompt(
            name=name,
            description=desc,
            framework_id=framework_id,
            styling=styling,
            a11y=self.chk_a11y.isChecked(),
            responsive=self.chk_responsive.isChecked(),
            props_doc=self.chk_props_doc.isChecked(),
        )
        user_prompt = f"Generate the {name} component as described above."

        ext = FRAMEWORKS[framework_id]["ext"]
        self._pending_filename = f"{name}{ext}"

        config = {
            "provider_id":   self.settings.active_provider,
            "model":         self.settings.get_model(self.settings.active_provider, "coder"),
            "system_prompt": system_prompt,
            "user_prompt":   user_prompt,
            "temperature":   0.4,
            "max_tokens":    4096,
            "strip_fences":  True,
            "log_label":     f"Generating {framework_id} component",
        }

        self._simple_worker = SimpleWorker(config)
        self._simple_worker.log_signal.connect(self._on_log)
        self._simple_worker.progress_signal.connect(self.progress_bar.setValue)
        self._simple_worker.result_signal.connect(self._on_simple_result)
        self._simple_worker.done_signal.connect(self._on_done)
        self._simple_worker.start()

    def _run_multi(self, name: str, desc: str, framework_id: str):
        styling = self.styling_combo.currentData() or "css"
        fw_kind = FRAMEWORKS[framework_id]["kind"]

        # Build extra instructions from the option checkboxes
        extras = [
            f"- Use {fw_kind} as the target framework",
            f"- Use {self._styling_label(styling)} for styling",
        ]
        if self.chk_storybook.isChecked():
            extras.append("- Include a Storybook story file")
        if self.chk_props_doc.isChecked():
            extras.append("- Document all props in the language's idiomatic format")
        if self.chk_a11y.isChecked():
            extras.append("- Apply accessibility best practices (semantic HTML, ARIA, keyboard nav)")
        if self.chk_responsive.isChecked():
            extras.append("- Make the component responsive (mobile through desktop)")

        config = {
            "name":             name,
            "description":      desc,
            "language":         fw_kind,
            "kind":             "component",
            "extra_instructions": "\n".join(extras),
            "max_files":        6,  # component, styles, test, story, types, README
            "temperature":      0.4,
            "output_dir":       self.settings.output_directory,
            "provider_id":      self.settings.active_provider,
            "architect_model":  self.settings.get_model(self.settings.active_provider, "architect"),
            "coder_model":      self.settings.get_model(self.settings.active_provider, "coder"),
        }

        self._multifile_worker = MultiFileWorker(config)
        self._multifile_worker.log_signal.connect(self._on_log)
        self._multifile_worker.progress_signal.connect(self.progress_bar.setValue)
        self._multifile_worker.file_signal.connect(self._on_file_ready)
        self._multifile_worker.done_signal.connect(self._on_multi_done)
        self._multifile_worker.start()

    @staticmethod
    def _styling_label(styling_id: str) -> str:
        return {
            "css":      "plain CSS",
            "tailwind": "Tailwind CSS",
            "styled":   "styled-components",
            "module":   "CSS Modules",
            "inline":   "inline styles",
        }.get(styling_id, "plain CSS")

    def _stop_run(self):
        if self._simple_worker and self._simple_worker.isRunning():
            self._simple_worker.stop()
        if self._multifile_worker and self._multifile_worker.isRunning():
            self._multifile_worker.stop()
        self.stop_btn.setEnabled(False)

    def _on_log(self, message: str, level: str):
        from core.logger import LEVEL_ICONS
        import datetime
        icon = LEVEL_ICONS.get(level, "·")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] {icon}  {message}")
        cur = self.log_view.textCursor()
        self.log_view.moveCursor(cur.MoveOperation.End)

    def _on_simple_result(self, text: str):
        # Single-file mode: show in preview tab and add a single tree row
        self.preview_filename.setText(f"◉  {self._pending_filename}")
        self.code_view.setPlainText(text)
        self._files[self._pending_filename] = text

        item = QTreeWidgetItem([f"◉ {self._pending_filename}", f"{len(text)} chars"])
        item.setData(0, Qt.ItemDataRole.UserRole, self._pending_filename)
        item.setForeground(1, QColor(P["text_dim"]))
        self.file_tree.addTopLevelItem(item)

        self.tabs.setCurrentIndex(2)
        self._update_preview_btn_state()

    def _on_file_ready(self, path: str, content: str):
        # Multi-file mode: append to tree as files arrive
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
            self._update_preview_btn_state()

    def _on_done(self, success: bool, message: str):
        # Single-file completion handler
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._update_preview_btn_state()
        if success:
            self.status_signal.emit(t("status.complete"), "ok")
        else:
            self.status_signal.emit(t("status.error"), "err")
            QMessageBox.warning(self, t("status.error"), message)

    def _on_multi_done(self, success: bool, message: str):
        # Multi-file completion handler
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._update_preview_btn_state()
        if success:
            self._last_output_dir = message
            self.status_signal.emit(t("status.complete"), "ok")
            QMessageBox.information(
                self, t("status.complete"),
                f"✓ Component generated successfully!\n\nLocation:\n{message}",
            )
        else:
            self.status_signal.emit(t("status.error"), "err")
            QMessageBox.warning(self, t("status.error"), message)

    def _preview_in_browser(self):
        text = self.code_view.toPlainText()
        if not text.strip():
            return
        # Write to a temp HTML file and open it
        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, mode="w", encoding="utf-8",
            )
            tmp.write(text)
            tmp.close()
            QDesktopServices.openUrl(QUrl.fromLocalFile(tmp.name))
            self.status_signal.emit(f"Previewing: {Path(tmp.name).name}", "ok")
        except Exception as e:
            QMessageBox.warning(self, "—", f"Preview failed: {e}")

    def _copy_preview(self):
        text = self.code_view.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status_signal.emit(t("common.copied"), "ok")

    def _save_preview(self):
        text = self.code_view.toPlainText()
        if not text:
            return
        # Use the currently displayed filename as a hint
        filename = self.preview_filename.text().replace("◉  ", "").strip()
        if filename.startswith("—"):
            filename = self._pending_filename
        path, _ = QFileDialog.getSaveFileName(
            self, t("common.save"), filename, "All Files (*.*)"
        )
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
        self.cfg_group.setTitle(t("ui_comp.title"))
        self.lbl_subtitle.setText(t("ui_comp.subtitle"))
        self.lbl_name.setText(t("ui_comp.name_label"))
        self.name_input.setPlaceholderText(t("ui_comp.name_placeholder"))
        self.lbl_desc.setText(t("ui_comp.desc_label"))
        self.desc_input.setPlaceholderText(t("ui_comp.desc_placeholder"))
        self.lbl_framework.setText(t("ui_comp.framework_label"))
        self.lbl_styling.setText(t("ui_comp.styling_label"))
        self.lbl_scope.setText(t("ui_comp.scope_label"))
        self.chk_storybook.setText(t("ui_comp.include_storybook"))
        self.chk_props_doc.setText(t("ui_comp.include_props_doc"))
        self.chk_a11y.setText(t("ui_comp.include_a11y"))
        self.chk_responsive.setText(t("ui_comp.include_responsive"))
        self.run_btn.setText(t("ui_comp.run_btn"))
        self.stop_btn.setText(t("common.stop"))
        self.preview_btn.setText(t("ui_comp.preview_btn"))
        self.open_btn.setText("📂 " + t("architect.open_output_btn"))
        self.lbl_progress.setText(t("shared.progress_label"))
        self.tabs.setTabText(0, t("shared.live_log_tab"))
        self.tabs.setTabText(1, t("shared.file_tree_tab"))
        self.tabs.setTabText(2, t("shared.code_preview_tab"))
        self.clear_logs_btn.setText(t("shared.clear_logs_btn"))
        self.copy_btn.setText(t("shared.copy_btn"))
        self.save_btn.setText(t("shared.save_btn"))

        # Re-translate combos (preserve selection)
        cur_fw = self.framework_combo.currentData()
        self.framework_combo.clear()
        for fw_id, fw_def in FRAMEWORKS.items():
            self.framework_combo.addItem(t(fw_def["key"]), userData=fw_id)
        idx = self.framework_combo.findData(cur_fw)
        if idx >= 0:
            self.framework_combo.setCurrentIndex(idx)

        cur_sty = self.styling_combo.currentData()
        self.styling_combo.clear()
        for sty_id, key in STYLINGS.items():
            self.styling_combo.addItem(t(key), userData=sty_id)
        idx = self.styling_combo.findData(cur_sty)
        if idx >= 0:
            self.styling_combo.setCurrentIndex(idx)

        cur_scope = self.scope_combo.currentData()
        self.scope_combo.clear()
        for sc_id, key in SCOPES.items():
            self.scope_combo.addItem(t(key), userData=sc_id)
        idx = self.scope_combo.findData(cur_scope)
        if idx >= 0:
            self.scope_combo.setCurrentIndex(idx)
