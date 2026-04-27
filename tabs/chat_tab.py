"""
tabs/chat_tab.py
══════════════════════════════════════════════════════════════
AI Chat Console tab.
Open-ended multi-turn conversation with the configured AI
provider. Supports a custom system prompt, message bubbles
with role-coloured styling, conversation export to Markdown,
keyboard shortcut (Ctrl+Enter) to send.

Uses ChatWorker — sends full conversation history each turn.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import datetime
import html as html_lib
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor, QFont, QKeySequence, QShortcut, QTextCursor
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTextBrowser,
    QVBoxLayout, QWidget,
)

from core.config import AppSettings
from core.i18n import t
from core.secrets import get_api_key
from core.workers.chat_worker import ChatWorker
from tabs.base_tab import BaseTab
from ui.theme import PALETTE as P


class ChatTab(BaseTab):
    """Open-ended AI chat console."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(settings, parent)
        self._worker: ChatWorker | None = None
        # Conversation state — list of {"role": ..., "content": ...}
        self._messages: list[dict[str, str]] = []
        # Active system prompt (separate from _messages so it can be edited
        # without polluting the visible transcript)
        self._system_prompt: str = ""
        self._build_ui()
        self._refresh_transcript()

    # ── UI Construction ───────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top: title + counters
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        self.title_label = QLabel(t("chat.title"))
        self.title_label.setStyleSheet(
            f"color: {P['accent']}; font-size: 18px; "
            f"font-weight: 700; letter-spacing: 1px;"
        )
        self.subtitle_label = QLabel(t("chat.subtitle"))
        self.subtitle_label.setObjectName("hint")

        header_row.addWidget(self.title_label)
        header_row.addSpacing(12)
        header_row.addWidget(self.subtitle_label)
        header_row.addStretch()

        # Counters
        self.msg_count_label = QLabel(self._counter_text())
        self.msg_count_label.setStyleSheet(
            f"color: {P['text_dim']}; font-size: 11px; "
            f"padding: 4px 10px; border: 1px solid {P['border']}; border-radius: 4px;"
        )
        header_row.addWidget(self.msg_count_label)

        layout.addLayout(header_row)

        # Splitter: system-prompt (top, small) + transcript (large) + input (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(2)
        splitter.addWidget(self._build_system_prompt_panel())
        splitter.addWidget(self._build_transcript_panel())
        splitter.addWidget(self._build_input_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([90, 600, 180])
        layout.addWidget(splitter, 1)

        # Bottom toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.clear_btn = QPushButton("🗑  " + t("chat.clear_btn"))
        self.clear_btn.setObjectName("ghost")
        self.clear_btn.setMinimumHeight(32)
        self.clear_btn.clicked.connect(self._on_clear)

        self.export_btn = QPushButton("⬇  " + t("chat.export_btn"))
        self.export_btn.setObjectName("ghost")
        self.export_btn.setMinimumHeight(32)
        self.export_btn.clicked.connect(self._on_export)

        toolbar.addStretch()
        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.export_btn)
        layout.addLayout(toolbar)

        # Keyboard shortcut: Ctrl+Enter to send
        self._send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self._send_shortcut.activated.connect(self._on_send)
        self._send_shortcut2 = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self._send_shortcut2.activated.connect(self._on_send)

    def _build_system_prompt_panel(self) -> QWidget:
        self.sys_group = QGroupBox(t("chat.system_label"))
        layout = QVBoxLayout(self.sys_group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        self.system_input = QPlainTextEdit()
        self.system_input.setPlaceholderText(t("chat.system_placeholder"))
        self.system_input.setMaximumHeight(60)
        self.system_input.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {P['bg_card']};
                border: 1px solid {P['border']};
                border-radius: 6px;
                color: {P['text_prim']};
                padding: 6px;
            }}
            QPlainTextEdit:focus {{ border-color: {P['primary']}; }}
        """)
        row.addWidget(self.system_input, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        self.sys_apply_btn = QPushButton(t("chat.system_apply_btn"))
        self.sys_apply_btn.setObjectName("accent")
        self.sys_apply_btn.setFixedWidth(100)
        self.sys_apply_btn.setFixedHeight(28)
        self.sys_apply_btn.clicked.connect(self._on_apply_system)
        self.sys_reset_btn = QPushButton(t("chat.system_reset_btn"))
        self.sys_reset_btn.setObjectName("ghost")
        self.sys_reset_btn.setFixedWidth(100)
        self.sys_reset_btn.setFixedHeight(28)
        self.sys_reset_btn.clicked.connect(self._on_reset_system)
        btn_col.addWidget(self.sys_apply_btn)
        btn_col.addWidget(self.sys_reset_btn)
        row.addLayout(btn_col)

        layout.addLayout(row)
        return self.sys_group

    def _build_transcript_panel(self) -> QWidget:
        # Use QTextBrowser for rich HTML rendering of message bubbles
        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(True)
        self.transcript.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {P['bg_void']};
                border: 1px solid {P['border']};
                border-radius: 8px;
                color: {P['text_prim']};
                padding: 10px;
            }}
        """)
        return self.transcript

    def _build_input_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.input_view = QPlainTextEdit()
        self.input_view.setPlaceholderText(t("chat.input_placeholder"))
        self.input_view.setFont(QFont("JetBrains Mono", 10))
        self.input_view.setMinimumHeight(80)
        self.input_view.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {P['bg_card']};
                border: 1px solid {P['border']};
                border-radius: 8px;
                color: {P['text_prim']};
                padding: 8px;
                selection-background-color: {P['primary']};
            }}
            QPlainTextEdit:focus {{ border-color: {P['primary']}; }}
        """)
        layout.addWidget(self.input_view, 1)

        # Send row
        send_row = QHBoxLayout()
        send_row.setSpacing(8)
        self.shortcut_label = QLabel(t("chat.send_shortcut"))
        self.shortcut_label.setStyleSheet(
            f"color: {P['text_dim']}; font-size: 11px; padding: 0 8px;"
        )
        send_row.addWidget(self.shortcut_label)
        send_row.addStretch()

        self.send_btn = QPushButton("⮕  " + t("chat.send_btn"))
        self.send_btn.setObjectName("primary")
        self.send_btn.setMinimumHeight(36)
        self.send_btn.setMinimumWidth(140)
        self.send_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.send_btn.clicked.connect(self._on_send)

        self.stop_btn = QPushButton(t("common.stop"))
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setMinimumWidth(80)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)

        send_row.addWidget(self.send_btn)
        send_row.addWidget(self.stop_btn)
        layout.addLayout(send_row)

        return panel

    # ── Counter helper ────────────────────────────────────
    def _counter_text(self) -> str:
        n = len(self._messages)
        approx_tokens = sum(len(m["content"]) for m in self._messages) // 4
        return f"{t('chat.message_count_label')}: {n}  ·  {t('chat.token_count_label')}≈ {approx_tokens}"

    def _update_counters(self):
        self.msg_count_label.setText(self._counter_text())

    # ── Transcript rendering ──────────────────────────────
    def _refresh_transcript(self):
        """Re-render the entire transcript from self._messages."""
        if not self._messages:
            empty_html = (
                f"<div style='color: {P['text_dim']}; padding: 40px; "
                f"text-align: center; font-style: italic;'>"
                f"{t('chat.empty_message')}</div>"
            )
            self.transcript.setHtml(empty_html)
            self._update_counters()
            return

        bubbles = []
        for msg in self._messages:
            bubbles.append(self._render_bubble(msg["role"], msg["content"]))
        full_html = "<div style='padding: 4px;'>" + "\n".join(bubbles) + "</div>"
        self.transcript.setHtml(full_html)

        # Scroll to the bottom
        self.transcript.verticalScrollBar().setValue(
            self.transcript.verticalScrollBar().maximum()
        )
        self._update_counters()

    def _render_bubble(self, role: str, content: str, pending: bool = False) -> str:
        """Render a single message bubble as HTML."""
        # Map role → label, color, alignment
        if role == "user":
            label     = t("chat.you_label")
            border_c  = P["primary"]
            bg_c      = P["bg_card"]
            label_c   = P["primary_hover"]
            align     = "right"
        elif role == "assistant":
            label     = t("chat.ai_label")
            border_c  = P["accent_pink"]
            bg_c      = P["bg_panel"]
            label_c   = P["accent"]
            align     = "left"
        else:
            label     = t("chat.system_label_short")
            border_c  = P["warning"]
            bg_c      = P["bg_panel"]
            label_c   = P["warning"]
            align     = "left"

        # Escape HTML in content, then convert newlines
        safe = html_lib.escape(content)
        safe = safe.replace("\n", "<br>")

        # Inline-style code blocks: ``` blocks → preformatted; `inline` → styled span
        safe = self._style_code_blocks(safe)

        thinking = (
            f"<span style='color: {P['warning']}; font-style: italic;'> "
            f"&middot; {t('chat.thinking')}</span>"
            if pending else ""
        )

        return f"""
        <div style='margin: 8px 0; text-align: {align};'>
          <div style='display: inline-block; max-width: 88%; text-align: left;
                      background-color: {bg_c}; border: 1px solid {border_c};
                      border-radius: 10px; padding: 8px 12px;'>
            <div style='color: {label_c}; font-weight: 700; font-size: 11px;
                        letter-spacing: 1px; margin-bottom: 4px;'>
              {label}{thinking}
            </div>
            <div style='color: {P["text_prim"]}; font-size: 13px; line-height: 1.5;'>
              {safe}
            </div>
          </div>
        </div>
        """

    @staticmethod
    def _style_code_blocks(html: str) -> str:
        """
        Quick-and-cheap code styling. The transcript uses HTML, so we transform
        the already-escaped `&#96;&#96;&#96; ... &#96;&#96;&#96;` markers and `&#96;...&#96;`
        markers back into styled blocks. Note: html_lib.escape doesn't actually
        escape backticks, but we work in the escaped space defensively.
        """
        # ```...``` (greedy across newlines, after they've become <br>)
        import re
        pre_style = (
            f"background: {P['bg_void']}; border: 1px solid {P['border']}; "
            f"border-radius: 6px; padding: 8px 10px; "
            f"color: {P['text_code']}; font-family: 'JetBrains Mono', monospace; "
            f"font-size: 12px; display: block; white-space: pre; overflow-x: auto;"
        )
        code_style = (
            f"background: {P['bg_void']}; border: 1px solid {P['border']}; "
            f"border-radius: 4px; padding: 1px 5px; "
            f"color: {P['text_code']}; font-family: 'JetBrains Mono', monospace; "
            f"font-size: 12px;"
        )
        # Restore the <br>s inside fenced blocks back to newlines for <pre>
        def fenced(m):
            inner = m.group(1)
            inner = inner.replace("<br>", "\n")
            return f"<pre style='{pre_style}'>{inner}</pre>"
        html = re.sub(r"```(.+?)```", fenced, html, flags=re.DOTALL)
        # `inline` (single line, no <br>)
        html = re.sub(
            r"`([^`<]+)`",
            lambda m: f"<code style='{code_style}'>{m.group(1)}</code>",
            html,
        )
        return html

    # ── System prompt actions ─────────────────────────────
    def _on_apply_system(self):
        text = self.system_input.toPlainText().strip()
        self._system_prompt = text
        if text:
            self.status_signal.emit("System prompt applied", "ok")
        else:
            self.status_signal.emit("System prompt cleared", "info")

    def _on_reset_system(self):
        self.system_input.clear()
        self._system_prompt = ""
        self.status_signal.emit("System prompt reset", "info")

    # ── Send / Stop / Clear / Export ──────────────────────
    def _on_send(self):
        if self._worker and self._worker.isRunning():
            return  # already busy

        user_text = self.input_view.toPlainText().strip()
        if not user_text:
            return

        provider_id = self.settings.active_provider
        if not get_api_key(provider_id):
            QMessageBox.warning(self, "—", t("validation.no_provider"))
            return

        # Append user message and re-render with a pending assistant bubble
        self._messages.append({"role": "user", "content": user_text})
        self.input_view.clear()
        self._refresh_transcript_with_pending()

        # Build the message list for the API:
        # (system prompt if set) + all conversation messages
        api_messages: list[dict] = []
        if self._system_prompt:
            api_messages.append({"role": "system", "content": self._system_prompt})
        api_messages.extend(self._messages)

        config = {
            "provider_id": provider_id,
            "model":       self.settings.get_model(provider_id, "coder"),
            "messages":    api_messages,
            "temperature": self.settings.temperature,
            "max_tokens":  4096,
        }

        # UI state
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_signal.emit(t("status.generating"), "info")

        self._worker = ChatWorker(config)
        self._worker.log_signal.connect(self._on_worker_log)
        self._worker.result_signal.connect(self._on_worker_result)
        self._worker.done_signal.connect(self._on_worker_done)
        self._worker.start()

    def _on_stop(self):
        if self._worker:
            self._worker.stop()
        self.stop_btn.setEnabled(False)

    def _on_clear(self):
        if not self._messages:
            return
        confirm = QMessageBox.question(
            self, t("common.confirm"), t("chat.confirm_clear"),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._messages.clear()
        self._refresh_transcript()
        self.status_signal.emit("Conversation cleared", "info")

    def _on_export(self):
        if not self._messages:
            QMessageBox.information(
                self, "—",
                "Nothing to export — start a conversation first.",
            )
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        suggested = f"chat_{timestamp}.md"
        path, _ = QFileDialog.getSaveFileName(
            self, t("chat.export_btn"), suggested,
            "Markdown (*.md);;All Files (*.*)",
        )
        if not path:
            return

        lines = [
            "# Octar Lab — AI Chat Export",
            "",
            f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Provider:** {self.settings.active_provider}",
            f"**Model:** {self.settings.get_model(self.settings.active_provider, 'coder')}",
            f"**Messages:** {len(self._messages)}",
            "",
        ]
        if self._system_prompt:
            lines.extend([
                "## System Prompt",
                "",
                "```",
                self._system_prompt,
                "```",
                "",
            ])
        lines.append("---")
        lines.append("")
        for m in self._messages:
            label = {
                "user":      "🙂 You",
                "assistant": "🤖 Assistant",
                "system":    "⚙️ System",
            }.get(m["role"], m["role"])
            lines.append(f"### {label}")
            lines.append("")
            lines.append(m["content"])
            lines.append("")

        try:
            Path(path).write_text("\n".join(lines), encoding="utf-8")
            self.status_signal.emit(t("chat.exported"), "ok")
        except OSError as e:
            QMessageBox.warning(self, "—", f"Export failed: {e}")

    # ── Worker callbacks ──────────────────────────────────
    def _on_worker_log(self, _message: str, _level: str):
        # We don't surface chat worker logs to the UI by default — too noisy
        # Could be wired to a hidden debug log if useful later.
        pass

    def _on_worker_result(self, text: str):
        # Append assistant message and re-render
        self._messages.append({"role": "assistant", "content": text})
        self._refresh_transcript()

    def _on_worker_done(self, success: bool, message: str):
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if success:
            self.status_signal.emit(t("status.complete"), "ok")
        else:
            self.status_signal.emit(t("status.error"), "err")
            # On failure, drop the optimistic pending bubble (re-render without it)
            self._refresh_transcript()
            if message and message != "OK":
                QMessageBox.warning(self, t("status.error"), message)

    def _refresh_transcript_with_pending(self):
        """Re-render transcript AND append a pending placeholder assistant bubble."""
        bubbles = [
            self._render_bubble(m["role"], m["content"]) for m in self._messages
        ]
        # Pending placeholder
        bubbles.append(self._render_bubble("assistant", "…", pending=True))
        full_html = "<div style='padding: 4px;'>" + "\n".join(bubbles) + "</div>"
        self.transcript.setHtml(full_html)
        # Scroll to bottom on next event-loop tick (after rendering)
        QTimer.singleShot(0, lambda: self.transcript.verticalScrollBar().setValue(
            self.transcript.verticalScrollBar().maximum()
        ))
        self._update_counters()

    # ── i18n ──────────────────────────────────────────────
    def on_language_changed(self):
        self.title_label.setText(t("chat.title"))
        self.subtitle_label.setText(t("chat.subtitle"))
        self.sys_group.setTitle(t("chat.system_label"))
        self.system_input.setPlaceholderText(t("chat.system_placeholder"))
        self.sys_apply_btn.setText(t("chat.system_apply_btn"))
        self.sys_reset_btn.setText(t("chat.system_reset_btn"))
        self.input_view.setPlaceholderText(t("chat.input_placeholder"))
        self.shortcut_label.setText(t("chat.send_shortcut"))
        self.send_btn.setText("⮕  " + t("chat.send_btn"))
        self.stop_btn.setText(t("common.stop"))
        self.clear_btn.setText("🗑  " + t("chat.clear_btn"))
        self.export_btn.setText("⬇  " + t("chat.export_btn"))
        self._update_counters()
        # Re-render transcript so role labels translate too
        self._refresh_transcript()
