# AI Providers Setup

Octar Lab supports five AI providers in v1.0. They all do roughly the same
thing — accept a prompt, return text — but they differ in pricing, speed,
context length, and rough quality on different kinds of tasks. This page
covers what each one is good at, how to get a key, and how to configure
it.

## How keys are stored

Before anything else: your API keys go into your operating system's secure
credential store, not into a plain-text file on disk.

| Platform | Backend |
|---|---|
| macOS | Keychain |
| Windows | Credential Manager |
| Linux | Secret Service (GNOME Keyring or KWallet) |

This is handled by the `keyring` Python library, which is a well-established
piece of infrastructure used by pip, AWS CLI, and many other tools. We do
not roll our own crypto.

If your system has no secure backend available — most commonly headless
Linux with no DBus session — Octar Lab will fall back to in-memory storage.
This is signalled by a yellow warning in the **General** section of
**Settings**. Memory-only keys are lost when you quit the application.

## Switching the active provider

The provider that's actually used by every tab is the one selected at the
top of the **Settings** tab as **Active Provider**. You can have keys
configured for all five providers and switch between them freely without
re-entering anything.

## Architect vs Coder models

Octar Lab uses two separate model slots per provider. The reasoning is
that tabs like **Architect** make two different kinds of API calls during
a single generation:

- **Planning calls** — "design the project structure as JSON" — these
  benefit from a more capable model. Slot: *Architect Model*.
- **Code-generation calls** — one per file — these can usually use a
  faster, cheaper model. Slot: *Coder Model*.

You can point both slots at the same model if you want simplicity, or at
different models if you want to optimise cost vs quality. Defaults are
sensible for each provider.

---

## Groq

**Get a key**: https://console.groq.com/keys

**What it's good at**: speed. Groq runs open-weight models on its own LPU
hardware with extraordinary throughput. A request that takes 30 seconds on
GPT-4o might complete in 3 seconds on Groq with Llama 3.3 70B. For
iteration-heavy work — refactor, refactor again, refactor differently —
this changes how you work.

**What to expect on quality**: Llama 3.3 70B is a very capable model. For
most code-generation tasks it's roughly comparable to GPT-4-class output.
For very complex architectural decisions, the larger frontier models
(Claude Opus, GPT-4o) sometimes have an edge.

**Free tier**: Yes, generous. Most users won't hit the rate limits during
casual use.

**Recommended Octar Lab configuration**:
- Architect: `llama-3.3-70b-versatile`
- Coder: `llama-3.1-8b-instant`

---

## OpenAI

**Get a key**: https://platform.openai.com/api-keys

**What it's good at**: well-rounded reliability. GPT-4o is the safest
default if you don't have a strong opinion. Long context (128k tokens),
strong instruction-following, and very mature tooling around it.

**What to expect on quality**: high. GPT-4o is the default benchmark
everyone else compares against. The smaller `gpt-4o-mini` is a
remarkable value-per-dollar pick.

**Free tier**: No, but new accounts often get a small free credit on signup.

**Recommended Octar Lab configuration**:
- Architect: `gpt-4o`
- Coder: `gpt-4o-mini`

---

## Anthropic Claude

**Get a key**: https://console.anthropic.com/settings/keys

**What it's good at**: code quality and architectural reasoning. Claude
Opus produces some of the highest-quality code on the market, particularly
for complex, multi-file projects where coherence across files matters.
Long context (200k tokens) and strong at following nuanced instructions.

**What to expect on quality**: top-tier for code. Claude Sonnet sits in the
sweet spot of price vs quality. Claude Haiku is fast and cheap but less
capable.

**Free tier**: Limited free tier on the API. Claude.ai has a more
generous free chat tier but that's separate.

**Recommended Octar Lab configuration**:
- Architect: `claude-opus-4-5`
- Coder: `claude-haiku-4-5`

---

## Google Gemini

**Get a key**: https://aistudio.google.com/app/apikey

**What it's good at**: generous free tier and large context window
(Gemini 1.5 Pro supports 2M tokens, 2.5 supports 1M). Strong at handling
large codebases or long context tasks where other providers would refuse
or charge extravagantly.

**What to expect on quality**: solid. Gemini 2.5 Pro is competitive with
GPT-4o on most benchmarks. The Flash variants are very fast and very
cheap, with a corresponding drop in nuance.

**Free tier**: Yes, generous on AI Studio. This is probably the best
free-tier option of the five for casual use.

**Recommended Octar Lab configuration**:
- Architect: `gemini-2.5-pro`
- Coder: `gemini-2.5-flash`

**Note on the SDK**: Octar Lab uses the new unified `google-genai` SDK
(`from google import genai`). If you have the older `google-generativeai`
package installed alongside, Octar Lab will still work — there's a
compatibility fallback path — but the new SDK is preferred.

---

## Mistral AI

**Get a key**: https://console.mistral.ai/api-keys/

**What it's good at**: European hosting (good for GDPR/data-residency
concerns) and excellent code-specific models. Codestral is purpose-built
for code generation and competes well above its price point on coding
benchmarks.

**What to expect on quality**: Mistral Large is a strong general model;
Codestral is exceptional for pure code work.

**Free tier**: Yes, with rate limits.

**Recommended Octar Lab configuration**:
- Architect: `mistral-large-latest`
- Coder: `codestral-latest` (for code-heavy tasks) or `mistral-small-latest`

---

## Choosing a provider for a specific task

Rough heuristics, not absolute rules:

- **Want speed above all** → Groq
- **Want maximum quality on a complex multi-file project** → Anthropic
  Claude Opus
- **Want a safe, well-rounded default** → OpenAI GPT-4o
- **Want generous free usage** → Google Gemini Flash or Groq
- **Working with very long context** (large existing codebase as input) →
  Google Gemini 2.5 Pro
- **Pure code refactoring/generation, no architecture** → Mistral
  Codestral

Multi-provider configuration is genuinely useful: many users keep keys for
two or three providers and switch between them depending on what they're
doing.

## Validation troubleshooting

If **Test Connection** fails:

- Double-check that you copied the entire key (some are very long; partial
  copies are a common cause)
- Confirm your account has billing enabled if the provider requires it
  (OpenAI requires payment method setup before API keys work)
- Check whether the provider has rate-limited you for the day
- Make sure your network can reach the provider's API host (corporate
  proxies sometimes block specific endpoints)

The error message returned by **Test Connection** comes directly from
the provider's API and usually pinpoints the issue.
