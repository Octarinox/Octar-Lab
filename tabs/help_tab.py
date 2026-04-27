"""
tabs/help_tab.py
══════════════════════════════════════════════════════════════
In-app documentation. A sidebar lists topics, the main pane
renders markdown content. Topics are loaded from
resources/docs/{topic}.md if available, otherwise falls back
to a built-in default for that topic.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QSplitter, QTextBrowser, QVBoxLayout, QWidget,
)

from core.config import APP_NAME, APP_VERSION, APP_REPO_URL
from core.i18n import t
from tabs.base_tab import BaseTab
from ui.theme import PALETTE as P


_DOCS_DIR = Path(__file__).parent.parent / "resources" / "docs"


# Built-in fallback content if markdown files aren't present yet
_FALLBACK_CONTENT = {
    "getting_started": """# Getting Started

Welcome to **{app}** v{version}.

## 1. Configure an AI Provider
Open the **Settings** tab. Pick a provider (Groq, OpenAI, Anthropic, Gemini, Mistral),
paste your API key, hit **Save**, then **Test Connection**.

## 2. Generate your first project
Switch to **🏗️ Architect**. Fill in:
- Project name (e.g. `MiniCache`)
- Description (what it does, target users)
- Language / framework

Click **⚡ GENERATE PROJECT**.

## 3. Watch it build
The right pane shows live logs, the project tree, and code previews
as files are produced.

## 4. Open your project
When generation completes, click **📂 Open Output** to find your new
project in your file manager.
""",

    "providers": """# AI Providers Setup

Octar Lab supports five providers in v1.0:

## Groq
Ultra-fast inference of open-weight models (Llama 3.x, Mixtral, Gemma).
Get a key at: https://console.groq.com/keys

## OpenAI
GPT-4o, GPT-4 Turbo, o1 series.
Get a key at: https://platform.openai.com/api-keys

## Anthropic
Claude Opus / Sonnet / Haiku.
Get a key at: https://console.anthropic.com/settings/keys

## Google Gemini
Gemini 1.5 Pro / Flash.
Get a key at: https://aistudio.google.com/app/apikey

## Mistral AI
Mistral Large / Small / Codestral.
Get a key at: https://console.mistral.ai/api-keys/

## How keys are stored
- macOS → Keychain
- Windows → Credential Manager
- Linux → Secret Service (GNOME Keyring / KWallet)

If your system has no keyring backend (headless Linux without DBus),
keys are kept in process memory only and are lost when you quit.
""",

    "tabs": """# Feature Reference

### 🏗️ Project Architect
Generates a complete project scaffold: source files, config, tests,
README, .gitignore, and dependency manifest. Optional `git init`.

### 📚 Library Generator *(coming soon)*
Single-file or single-folder library generation, similar to the legacy
Universal Architect, but with full multi-provider support.

### 🧩 Code Refactor & Review *(coming soon)*
Paste code, get back refactor suggestions, security review,
or performance review.

### 📖 Documentation Generator *(coming soon)*
Generate README, API docs, contributor guide.

### 🧪 Test Generator *(coming soon)*
Generate unit/integration tests for existing code.

### 🎨 UI Component Generator *(coming soon)*
Generate React / Vue / HTML components.

### 🗄️ Database Tools *(coming soon)*
SQL schema design, query optimization, migration scripts.

### 🔌 API Builder *(coming soon)*
REST / GraphQL endpoint scaffolding.

### 🐳 DevOps Templates *(coming soon)*
Dockerfile, docker-compose, GitHub Actions, CI templates.

### 💬 AI Chat Console *(coming soon)*
Open-ended conversation with any configured provider.
""",

    "troubleshooting": """# Troubleshooting

## "No API key configured"
Go to **⚙️ Settings**, pick a provider, paste your API key, click **Save**.

## "Validation failed"
- The key is wrong, expired, or has insufficient permissions.
- Try **Test Connection** in Settings to confirm.
- Some providers require billing / payment-method setup before keys work.

## "Architect did not return parseable JSON"
Some smaller models occasionally produce invalid JSON. Try:
- Switch to a more capable model in Settings (e.g. `gpt-4o`, `claude-sonnet-4-5`)
- Lower the AI Temperature in the Architect tab
- Try a more specific project description

## Files have markdown fences (` ``` `) inside
This is a model bug — the worker tries to strip them, but small
models occasionally embed fences mid-content. You can re-run, or
edit the affected file manually.

## Linux: keys aren't being saved
Linux needs a Secret Service backend (GNOME Keyring or KWallet) running.
If neither is available, keys live in process memory only.
""",

    "faq": """# FAQ

**Is my code or my prompts sent anywhere besides the AI provider?**
No. Octar Lab talks directly to the provider you configure. There is
no telemetry, no usage tracking, no analytics in v1.0.

**Where are my API keys stored?**
In your operating system's secure keyring. Never on disk in plain text.

**Can I add a new AI provider?**
Yes — drop a new file in `core/ai_providers/`, subclass `BaseProvider`,
and register it in `factory.py`. One file, one line.

**Is Octar Lab free?**
Yes — MIT licensed, free for personal and commercial use.

**Does it work offline?**
The UI does, but generation requires an internet connection to reach
the AI providers.

**Can I use a local LLM?**
Not in v1.0. A local-LLM provider (Ollama / LM Studio) is on the
roadmap.
""",
}


class HelpTab(BaseTab):
    """In-app help / documentation tab."""

    # (i18n_key, file_basename, fallback_key)
    _SECTIONS = [
        ("help.section_getting_started",  "getting_started",   "getting_started"),
        ("help.section_providers",        "providers_setup",   "providers"),
        ("help.section_tabs",              "feature_reference", "tabs"),
        ("help.section_troubleshooting",  "troubleshooting",   "troubleshooting"),
        ("help.section_faq",               "faq",               "faq"),
    ]

    def __init__(self, settings, parent=None):
        super().__init__(settings, parent)
        self._build_ui()
        # Show the first topic by default
        if self.sidebar.count() > 0:
            self.sidebar.setCurrentRow(0)

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # Sidebar
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(6)

        self.title_label = QLabel(t("help.title"))
        self.title_label.setStyleSheet(
            f"color: {P['accent']}; font-size: 14px; "
            f"font-weight: 700; letter-spacing: 1.5px; padding: 4px;"
        )
        side_layout.addWidget(self.title_label)

        self.sidebar = QListWidget()
        self.sidebar.setStyleSheet(f"""
            QListWidget {{
                background-color: {P['bg_card']};
                border: 1px solid {P['border']};
                border-radius: 8px;
                padding: 6px;
                color: {P['text_sec']};
            }}
            QListWidget::item {{
                padding: 10px 14px;
                border-radius: 6px;
                margin-bottom: 2px;
            }}
            QListWidget::item:selected {{
                background-color: {P['primary']};
                color: white;
            }}
            QListWidget::item:hover:!selected {{
                background-color: {P['bg_hover']};
                color: {P['text_prim']};
            }}
        """)
        self.sidebar.currentRowChanged.connect(self._on_section_changed)
        side_layout.addWidget(self.sidebar)
        side_layout.addStretch()

        # Content
        self.content = QTextBrowser()
        self.content.setOpenExternalLinks(True)
        self.content.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {P['bg_void']};
                border: 1px solid {P['border']};
                border-radius: 10px;
                color: {P['text_prim']};
                padding: 24px 28px;
                font-size: 14px;
            }}
        """)

        splitter.addWidget(side_panel)
        splitter.addWidget(self.content)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 900])

        layout.addWidget(splitter)
        self._populate_sidebar()

    def _populate_sidebar(self):
        self.sidebar.clear()
        for label_key, _, _ in self._SECTIONS:
            QListWidgetItem(t(label_key), self.sidebar)

    # ── Loading ───────────────────────────────────────────
    def _on_section_changed(self, row: int):
        if row < 0 or row >= len(self._SECTIONS):
            return
        _, file_basename, fallback_key = self._SECTIONS[row]
        self._load_section(file_basename, fallback_key)

    def _load_section(self, file_basename: str, fallback_key: str):
        # Try language-specific markdown file first, then default English file,
        # then the built-in fallback string
        candidates = [
            _DOCS_DIR / f"{file_basename}_{self.settings.language}.md",
            _DOCS_DIR / f"{file_basename}.md",
        ]
        markdown = None
        for p in candidates:
            if p.exists():
                try:
                    markdown = p.read_text(encoding="utf-8")
                    break
                except OSError:
                    pass
        if markdown is None:
            markdown = _FALLBACK_CONTENT.get(fallback_key, "_(content missing)_")
            markdown = markdown.format(app=APP_NAME, version=APP_VERSION)

        # QTextBrowser supports basic markdown via setMarkdown
        self.content.setMarkdown(markdown)

    # ── i18n ──────────────────────────────────────────────
    def on_language_changed(self):
        self.title_label.setText(t("help.title"))
        # Re-label sidebar items in-place (preserves selection)
        for i, (label_key, _, _) in enumerate(self._SECTIONS):
            item = self.sidebar.item(i)
            if item:
                item.setText(t(label_key))
        # Reload current section to fetch language-specific markdown
        row = self.sidebar.currentRow()
        if row >= 0:
            self._on_section_changed(row)
