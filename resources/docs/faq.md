# FAQ

Common questions, with honest answers.

---

## Privacy & Data

### Does Octar Lab send my code or prompts to Octarinox?

No. Octar Lab makes API calls directly from your machine to the AI
provider you chose. Your code and prompts go to that provider, not to
us. We do not run any servers that intermediate your traffic. We do not
have a database of your generations. We do not have a "telemetry"
feature, secret or otherwise.

If you want to verify this, the source is open — search the codebase
for any HTTP call. The only outbound traffic is to the provider SDKs.

### Where are my API keys stored?

In your operating system's secure credential store: macOS Keychain,
Windows Credential Manager, or Linux Secret Service. Never in a
plain-text file. Never on a server we control. Never logged.

If your system has no credential backend (rare; mostly headless Linux
without DBus), keys live in process memory only and are lost when you
quit. The Settings tab tells you which mode you're in.

### What about the AI providers themselves?

That's between you and them. Each provider has its own data-handling
policy:

- **Anthropic**: Does not train on API traffic by default
- **OpenAI**: Does not train on API traffic by default since 2023
- **Google**: Free-tier traffic may be used for improvement; paid is
  not. Check current AI Studio terms
- **Groq**: Does not train on customer data
- **Mistral**: Does not train on API traffic

These policies change. If data-handling is critical to your use case,
read the current policy from the provider directly before relying on
my summary.

---

## Cost

### How much does it cost to use?

Octar Lab itself is free, MIT-licensed, and always will be. You pay the
AI providers directly for their API usage. Typical costs are very low:

- A small library generation: usually under $0.05
- A medium project (10-12 files): typically $0.10 to $0.50
- A long chat conversation: a few cents
- Refactor / docs / single-file work: usually under $0.01

Groq's free tier and Gemini's free tier are generous enough that casual
use can stay at $0.

### What if I burn through credits accidentally?

You can't, in any reasonable sense. Octar Lab generates one project,
one component, or one chat reply at a time — there's no automated
loop running prompts in the background. If your provider account has
spending limits configured (and they all support this), Octar Lab
cannot exceed them.

Two pieces of advice for new users:

1. Set a monthly spending limit in your provider's billing settings
2. Watch the cost during your first few generations to calibrate
   intuition

### Can I use a free tier exclusively?

Yes. Groq has the most generous free tier for serious use. Gemini also
has a free tier on AI Studio that's plenty for personal use. OpenAI
sometimes gives free credits on signup.

If you want to be free-tier-only forever, configure Groq as your active
provider with `llama-3.3-70b-versatile` for both Architect and Coder.
That covers most workflows at zero cost.

---

## Capabilities

### Can I add a new AI provider?

Yes — that's an explicit design goal.

1. Drop a new file in `core/ai_providers/` (e.g. `cohere_provider.py`)
2. Subclass `BaseProvider` and implement `_do_chat`, `validate_key`,
   and `default_models`
3. Register it in `core/ai_providers/factory.py` by adding one line to
   `_REGISTRY`
4. Add the provider's id to `SUPPORTED_PROVIDERS` in `core/config.py`

Total: roughly 80 lines of code. We'd be happy to merge a clean
implementation as a PR.

### Can I add a new tab?

Yes. The pattern:

1. New file in `tabs/` (e.g. `audio_tab.py`)
2. Subclass `BaseTab`, build your UI in `_build_ui()`, define handlers
3. Register the tab in `main.py`'s `_TAB_DEFINITIONS` list
4. Add translation keys in `resources/translations/{en,ru,de}.json`
5. If your tab does generation, pick the right worker:
   `SimpleWorker` for one-prompt-one-response, `MultiFileWorker` for
   plan-then-files, `ChatWorker` for multi-turn

The existing tabs are good references — `tabs/devops_tab.py` is a
straightforward `SimpleWorker` example, `tabs/library_tab.py` is a
clean `MultiFileWorker` example.

### Can I use a local LLM (Ollama, LM Studio, etc.)?

Not in v1.0. There's no built-in support for local LLM endpoints.

That said: if you're running Ollama, you can probably get it working
right now by pointing the OpenAI provider at Ollama's OpenAI-compatible
endpoint by editing `core/ai_providers/openai_provider.py` to pass
`base_url="http://localhost:11434/v1"` to the `OpenAI(...)` constructor.
We don't bless this configuration, but it works.

Native local-LLM support is on the roadmap.

### Does Octar Lab work offline?

The app launches and the UI works offline. Actual generation requires
network access to your chosen provider's API. The app does not have a
local model bundled.

### Can I use it with a corporate proxy / VPN?

Yes, with caveats. The provider SDKs (httpx-based) respect
`HTTPS_PROXY` and `HTTP_PROXY` environment variables. If your proxy
does TLS interception, you may need to point the SDK at a custom
CA bundle via `SSL_CERT_FILE` or `REQUESTS_CA_BUNDLE`.

### Does it support streaming responses?

Not in v1.0. Every response arrives as a single chunk. Streaming is on
the roadmap — it will mostly affect the Chat Console, where the
typewriter effect is genuinely useful.

### Does it support tool/function calling, web search, vision, or file uploads?

Not in v1.0. Same answer as streaming — these are roadmap items.

### Can I customise the theme / colours?

Yes, manually. Edit `ui/theme.py` — every colour the app uses is in the
`PALETTE` dict at the top. Restart the app to see your changes.

A user-facing theme picker is on the roadmap.

---

## Project & Community

### Is Octar Lab actively maintained?

Yes. It's a primary project for Octarinox, not a side dump. We respond
to issues and we ship updates.

### Can I use it commercially?

Yes. The MIT license permits commercial use without restriction. The
ceremonial clause in the LICENSE file is non-binding (and a little
silly), but the actual MIT terms are fully permissive.

### Will you accept my pull request?

Probably yes, if it:

- Matches the existing code style (we're not strict about it; matching
  the surrounding code is enough)
- Includes a brief explanation of *why* the change is useful
- Doesn't break existing functionality
- Is, ideally, a focused change — small PRs get merged faster than
  large ones

PRs that are pure additions (new tab, new provider, new translation)
are easiest to review. Refactors of existing code go through more
discussion.

### How do I report a bug?

Open an issue on GitHub. Include:

- What you were trying to do
- What you expected
- What actually happened
- The full error message if there is one
- Your OS and Python version

If you can include steps to reproduce, we can usually fix it within a
day or two. If the bug is intermittent, mention that too.

### How do I request a feature?

Same place — open an issue, label it as a feature request. We don't
guarantee any specific feature will land, but we do read every request
and use them to inform priorities.

### Can I sponsor or financially support the project?

We don't currently have a sponsorship setup. The project is sustainable
without it. If you find Octar Lab useful in commercial work, the most
helpful thing you can do is:

1. Give it a star on GitHub (visibility helps)
2. Tell other developers about it
3. Send PRs for things you wish worked differently

If a sponsorship setup happens later, we'll mention it in the README.

### What's "Octarinox" supposed to mean?

A portmanteau:

- **Octar** — from the Latin/Greek root for "eight," referring to the
  eight directions of a compass
- **-inox** — from "stainless," like stainless steel

The intended meaning: tools that point everywhere and don't rust.

The brand has a Viking-Georgian aesthetic because both cultures share
a stubborn affection for craft and hospitality, which felt right for an
open-source studio in Tbilisi.

### What's that small Georgian text everywhere?

That's the legal-entity name in Georgian: შპს ოქტარინოქსი ("LLC
Octarinox"). The studio is registered in Georgia and the Georgian name
is the official one. The English name is just transliteration.

### Why Georgian, Russian, and German for the v1.0 languages?

Three pragmatic reasons:

- **Georgian** would be the native language but the developer time to
  do it justice in v1.0 went elsewhere; on the roadmap
- **Russian** is the largest non-English-speaking developer demographic
  in the wider region around Tbilisi
- **German** because there's a strong German-speaking user community
  for indie dev tooling

More languages are easy to add — just translate one of the JSON files
in `resources/translations/`. PRs welcome.

---

## Misc

### Where does the name "Octar Lab" come from?

"Octar" from the studio name, "Lab" because that's what this is — a
laboratory of small AI-powered tools rather than one monolithic feature.

### Is there a CLI version?

Not in v1.0. The Architect-style features could plausibly be exposed
via CLI; if there's demand we'll consider it.

### Will there be a web version?

No plans currently. Octar Lab is intentionally a desktop application:
your code stays on your machine, your keys stay in your local keyring,
no servers to maintain. A web version would have to introduce trust
boundaries we're not interested in introducing.

### Can I use this in a classroom / for teaching?

Yes, please do. The MIT license covers educational use. If you do, we'd
love to hear about it — drop a note in the GitHub Discussions.

### What if I just want to chat with an AI without all the tools?

Use the **💬 AI Chat Console** tab. It's a clean general-purpose chat
interface with the same five providers behind it. No specialised
features, just conversation.

---

If your question isn't here, ask it on GitHub. The FAQ grows over time
based on what people actually ask.
