<div align="center">

# ⬢ OCTAR LAB

**Open-source AI-powered development workbench**
*by [Octarinox](https://github.com/octarinox)*

[![License: MIT](https://img.shields.io/badge/License-MIT-8b5cf6.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-c4b5fd.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-a78bfa.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Status: Active](https://img.shields.io/badge/status-active-10b981.svg)]()

A desktop platform for AI-assisted code generation. Plug in your favourite
provider — Groq, OpenAI, Anthropic, Gemini, or Mistral — and generate
production-ready projects, libraries, tests, docs, and more.

</div>

---

## ✨ Features

| Tab | Description | Status |
|---|---|---|
| 🏗️ **Project Architect** | Generate complete project scaffolds with src/, tests/, docs/, README, dependency manifests, and `.gitignore` | ✅ v1.0 |
| 📚 **Library Generator** | Build single-purpose libraries with optional tests/examples | ✅ v1.0 |
| 🧩 **Code Refactor & Review** | 5 modes: Refactor, Security review, Performance, Explain, Modernize | ✅ v1.0 |
| 📖 **Documentation Generator** | README, API docs, inline docstrings, tutorials, changelogs | ✅ v1.0 |
| 🧪 **Test Generator** | 14 languages × 28 frameworks (pytest, Jest, JUnit, RSpec, …) | ✅ v1.0 |
| 🎨 **UI Component Generator** | React, Vue, Svelte, SolidJS, HTML — single or multi-file with browser preview | ✅ v1.0 |
| 🗄️ **Database Tools** | Schema design, query optimization, migrations, seed data — 5 dialects, 6 ORMs | ✅ v1.0 |
| 🔌 **API Builder** | REST / GraphQL / gRPC scaffolding with auth, validation, OpenAPI | ✅ v1.0 |
| 🐳 **DevOps Templates** | Dockerfile, docker-compose, GitHub Actions, GitLab CI, K8s, Terraform, Nginx, systemd | ✅ v1.0 |
| 💬 **AI Chat Console** | Open-ended multi-turn conversation with system prompts and Markdown export | ✅ v1.0 |
| ⚙️ **Settings** | API keys, language, output dir, model selection per role | ✅ v1.0 |
| 📘 **Documentation** | In-app guide with markdown rendering | ✅ v1.0 |
| ℹ️ **About** | Mission, license, contributing | ✅ v1.0 |

## 🔌 Supported AI Providers

- **Groq** — ultra-fast inference of Llama, Mixtral, Gemma
- **OpenAI** — GPT-4o, GPT-4 Turbo, o1
- **Anthropic** — Claude Opus / Sonnet / Haiku
- **Google Gemini** — Gemini 1.5 Pro / Flash
- **Mistral AI** — Mistral Large / Small / Codestral

## 🌐 Supported Languages

- 🇬🇧 English
- 🇷🇺 Русский
- 🇩🇪 Deutsch

## 🔐 Security

API keys are stored in your operating system's secure keyring:

- **macOS** → Keychain
- **Windows** → Credential Manager
- **Linux** → Secret Service (GNOME Keyring / KWallet)

Never on disk in plain text. No telemetry. No tracking. Ever.

---

## 📦 Installation

### Requirements

- Python 3.10+
- Git (optional, for `auto git init` feature)
- A platform-supported keyring backend (built into macOS / Windows; Linux needs GNOME Keyring or KWallet)

### From source

```bash
git clone https://github.com/octarinox/octar-lab.git
cd octar-lab
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 🚀 Quick start

1. Launch the app — `python main.py`.
2. Open **⚙️ Settings**, pick a provider, paste your API key, click **Save** → **Test Connection**.
3. Switch to **🏗️ Architect**.
4. Fill in project name, description, language. Click **⚡ GENERATE PROJECT**.
5. When generation finishes, click **📂 Open Output**.

That's it.

---

## 🏗️ Architecture

```
octar_lab/
├── main.py                     # Entry point
├── core/
│   ├── config.py               # Settings & defaults
│   ├── secrets.py              # OS keyring wrapper
│   ├── i18n.py                 # Translation loader
│   ├── logger.py               # Pub/sub logging
│   ├── ai_providers/           # Pluggable provider system
│   │   ├── base.py             # Abstract interface
│   │   ├── factory.py          # Provider factory
│   │   └── *_provider.py       # Implementations (5)
│   └── workers/                # QThread workers
├── tabs/                       # 13 feature tabs
├── ui/
│   ├── theme.py                # Color palette
│   ├── stylesheet.py           # Generated QSS
│   ├── widgets/                # Custom widgets
│   └── highlighters/           # Syntax highlighting
└── resources/
    ├── translations/           # i18n JSON
    └── docs/                   # Markdown documentation
```

**Adding a new AI provider**: Drop a file in `core/ai_providers/`,
subclass `BaseProvider`, register one line in `factory.py`. Done.

---

## 🤝 Contributing

Pull requests, issues, and feature requests are very welcome.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Commit (`git commit -am 'feat: my new feature'`)
4. Push (`git push origin feat/my-feature`)
5. Open a Pull Request

Please follow the existing code style and add tests where appropriate.

---

## 📄 License

[MIT](LICENSE) © 2026 Octarinox

Free for personal and commercial use. The LICENSE file also contains a
small non-binding ceremonial clause; we encourage you to read it after
your build finally passes.

---

<div align="center">

**⬢ Made in Tbilisi · Released into the wild ⬢**

*Tools that point everywhere. Tools that don't rust.*

If this saved you time, consider a ⭐ on GitHub.<br>
If it didn't, file an issue and tell us why.

</div>
