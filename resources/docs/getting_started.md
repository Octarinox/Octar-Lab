# Getting Started

Welcome. This guide will get you from a fresh install to your first generated
project in about five minutes. No prior AI tooling experience is assumed —
just basic familiarity with whatever language you're already comfortable in.

## What is Octar Lab?

Octar Lab is an open-source desktop workbench for AI-assisted development.
Think of it as a thin, transparent layer between you and the major AI
providers — bring your own API key, pick your provider, and use one of
thirteen specialised tools to scaffold projects, refactor code, generate
tests, or have an open-ended conversation. Your code never leaves your
machine except to talk directly to the provider you chose.

There is no Octarinox cloud. There is no subscription. There is no telemetry.
We are not collecting your prompts or your generated code. The application
talks to the provider's API and writes the result to your disk. That's it.

## Step 1 — Install dependencies

If you haven't already, set up a Python virtual environment and install the
required packages. From a terminal in the project directory:

```bash
python -m venv .venv
source .venv/bin/activate         # macOS/Linux
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

Octar Lab requires Python 3.10 or newer. If `python --version` reports an
older version, install a newer Python first; everything else will follow.

## Step 2 — Launch the app

```bash
python main.py
```

The window that opens has a tab strip across the top with thirteen tabs.
The first time you run it, you'll see a status indicator near the bottom
saying something like *"No API key configured"* — that's expected.

## Step 3 — Configure an AI provider

Click the **⚙️ Settings** tab. You'll see one block per supported provider:

| Provider | Where to get a key | What it's good at |
|---|---|---|
| Groq | console.groq.com/keys | Speed. Llama 3.3 / Mixtral, very fast inference. |
| OpenAI | platform.openai.com/api-keys | General reliability. GPT-4o is a strong all-rounder. |
| Anthropic | console.anthropic.com/settings/keys | Code quality. Claude Opus is excellent for architecture. |
| Google Gemini | aistudio.google.com/app/apikey | Generous free tier. Gemini 2.5 is solid. |
| Mistral | console.mistral.ai/api-keys | European hosting. Codestral is strong for code. |

Pick whichever provider you have an account with — or sign up for one (most
have free tiers that are sufficient for trying things out). Paste the key
into the corresponding field and click **Save**. Then click **Test
Connection** to verify the key works.

You can have keys for multiple providers configured at once. The provider
that's actually used is whichever one is selected at the top of the
**Settings** tab as the *Active Provider*.

## Step 4 — Generate your first project

Click the **🏗️ Architect** tab. This is the flagship tool — it generates a
complete project scaffold from a one-paragraph description.

Try this:

- **Project Name**: `TodoLite`
- **Description**: `A simple command-line todo list manager that stores
  items in a local SQLite database. Supports add, remove, list, and mark
  done. Should be installable as a single command via pip.`
- **Language**: `Python`

Leave the other settings at defaults and click **⚡ GENERATE PROJECT**.

The right-hand pane will show three things as the generation proceeds:

1. **Live Logs** — a stream of what the worker is doing
2. **Project Tree** — the file structure as it's being designed
3. **Code Preview** — each file's contents as they're generated

When generation completes (typically 30 seconds to 2 minutes depending on
provider speed and project size), you'll get a confirmation dialog. Click
**📂 Open Output** to find the new project in your file manager.

## Step 5 — Explore the other tabs

Once you have a working setup, the other tabs become useful:

- **📚 Library Generator** — when you want a focused single-purpose
  library, not a whole project
- **🧩 Refactor & Review** — paste existing code, get back cleaner versions
  or security/performance reviews
- **📖 Documentation Generator** — point it at a chunk of code, get a
  README or API reference back
- **🧪 Test Generator** — paste a function, get a full test file
- **🎨 UI Component Generator** — describe a React/Vue/Svelte/HTML
  component, get production-ready code
- **🗄️ Database Tools** — natural-language to SQL schemas, query
  optimisation, migration scripts
- **🔌 API Builder** — REST or GraphQL endpoint scaffolding
- **🐳 DevOps Templates** — Dockerfile, docker-compose, CI workflows
- **💬 AI Chat Console** — open-ended conversation when you don't need a
  specialised tool

Each tab follows the same general layout: configuration on the left, output
on the right. Once you understand one, you understand all of them.

## A note on cost

You are billing your own API account. Octar Lab does not subsidise or mark
up usage. Most generation tasks cost a fraction of a cent (Groq's free tier
will handle thousands of generations per month at zero cost). Larger
projects or longer chats cost more, but rarely more than a few cents per
operation.

If you're cost-sensitive, configure two models per provider in **Settings**
— the *Architect Model* (used for planning and one-shot complex tasks)
and the *Coder Model* (used for individual file generation). Pointing the
Coder slot at a smaller, cheaper model often cuts costs by 80% with
minimal quality loss.

## Where to next

- For provider-specific setup details, see **AI Providers Setup**
- For a deep dive on each tab's options, see **Feature Reference**
- For when something goes wrong, see **Troubleshooting**
- For common questions, see **FAQ**

Happy generating.
