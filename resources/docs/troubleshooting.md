# Troubleshooting

Most issues fall into one of three buckets: provider/credential problems,
generation quality issues, or environment/installation issues. This page
goes through them roughly in order of how often they occur.

---

## "No API key configured"

**Symptom**: Clicking Generate produces a dialog saying "No AI provider
configured. Add an API key in Settings."

**Cause**: Either no key is saved for the active provider, or the keyring
backend is unavailable and your in-memory key was lost.

**Fix**:
1. Open **⚙️ Settings**
2. Confirm the **Active Provider** is the one you actually want to use
3. Find the corresponding provider block, paste your key, click **Save**
4. Click **Test Connection** to confirm it works

If the General section shows *"Secure keyring unavailable — keys stored
in memory only"*, your keys are being lost on restart. On Linux this
typically means GNOME Keyring or KWallet isn't running. On macOS or
Windows this is unusual; check that your user account has access to the
system credential store.

---

## "Validation failed" when testing a key

**Symptom**: **Test Connection** returns a red error message.

**Common causes** in rough order of likelihood:

1. **Partial paste** — provider keys are long. Especially with
   `sk-...` style keys, it's easy to miss the leading or trailing
   characters. Re-copy from the provider's console and try again.

2. **Billing not enabled** — OpenAI in particular requires a payment
   method on file before any API key works, even for the free
   credits. Anthropic similarly requires billing setup. Groq, Gemini,
   and Mistral are friendlier here.

3. **Key revoked or expired** — providers periodically expire keys for
   security. Generate a fresh one.

4. **Wrong provider selected** — pasted an Anthropic key into the OpenAI
   block by mistake. The error message will usually tell you ("Incorrect
   API key" or similar).

5. **Network issue** — corporate proxies sometimes block specific
   provider endpoints. Try from a different network to confirm.

The exact error message from the provider is shown directly in the
status line below the buttons; that text is your best clue.

---

## "Architect did not return parseable JSON"

**Symptom**: The Architect tab fails early with this message.

**Cause**: The provider's planning model returned text that wasn't valid
JSON. Smaller, faster models occasionally do this — they wrap the JSON
in markdown fences, add commentary, or produce malformed structure.

**Fixes** in order:

1. **Switch to a more capable Architect Model**. In **Settings**, set the
   provider's *Architect Model* to a stronger model: `gpt-4o`,
   `claude-opus-4-5`, `gemini-2.5-pro`, `mistral-large-latest`. The
   smaller models you might use for Coder are not always good at
   strict-JSON output.

2. **Lower the temperature**. The Architect tab has a temperature slider
   that affects code generation, but planning calls use a fixed lower
   value internally. Still, if you're consistently getting bad JSON,
   try a fresh provider.

3. **Be more specific in the description**. Vague descriptions sometimes
   confuse smaller models into returning prose instead of JSON.

4. **Try again**. Honestly, providers are non-deterministic and the same
   prompt may succeed on the next try. If it fails twice in a row,
   switch the model.

---

## Files contain markdown fences (` ``` `) inside the code

**Symptom**: Generated `.py` or `.js` files have stray ` ```python ` or
` ``` ` lines mid-file.

**Cause**: The model occasionally emits fenced code blocks despite being
instructed not to. Octar Lab's worker strips obvious leading/trailing
fences but can't remove every embedded one without false positives.

**Fixes**:

- For a one-off occurrence, just edit the file manually
- If it happens consistently, switch to a more capable model — this is
  almost always a problem with smaller, less instruction-following models
- The bigger Coder Model is more expensive per generation but rarely
  produces this kind of artefact

---

## Generation is very slow

**Symptom**: A single project takes 5+ minutes to generate.

**Cause**: Slow provider, or large projects with many files.

**Fixes**:

- **Switch to Groq** — its inference speed is dramatically faster than
  any other provider. A 12-file project on Groq Llama 3.3 might take
  90 seconds; the same on GPT-4o might take 6 minutes
- **Reduce Max Files** in the Architect tab — the most expensive part of
  generation is the per-file calls; cutting from 12 to 6 nearly halves
  the time
- **Use a smaller Coder Model** — set the Coder slot to a flash/mini/
  haiku-class model and keep the Architect slot on the bigger model

---

## "Stop" button doesn't immediately stop generation

**Symptom**: You click Stop and the worker continues for several seconds
before actually stopping.

**Cause**: Cancellation is cooperative — the worker checks the stop flag
between files, not in the middle of a network request. If a file is
mid-generation when you click Stop, that file completes before the
worker exits.

This is by design: hard-killing a thread mid-API-call would leave the
provider's response in an inconsistent state and could leak credits.
Just wait a few seconds; it will stop cleanly.

---

## Application crashes on startup with PyQt errors

**Symptom**: `python main.py` exits immediately with a traceback
mentioning `PyQt6` or `Qt`.

**Common causes**:

- **PyQt6 not installed** — run `pip install -r requirements.txt`
- **Wrong Python version** — Octar Lab requires Python 3.10+. Check with
  `python --version`. If you have an older Python, install a newer one
- **Missing system Qt libraries on Linux** — minimal Linux installs
  sometimes lack the system libraries Qt needs at runtime. Install
  `libgl1-mesa-glx`, `libxcb-xinerama0`, and similar via your distro's
  package manager
- **Multiple Python installations getting confused** — make sure you've
  activated the virtual environment where you installed dependencies

---

## Linux: API keys aren't being saved between runs

**Symptom**: You configure a key, restart the app, and it's gone.

**Cause**: No Secret Service backend (GNOME Keyring or KWallet) is
running on your system. The keyring library needs one to persist keys.

**Fix**:

- On GNOME-based desktops: install and start `gnome-keyring`
- On KDE-based desktops: install and start `kwallet`
- On headless servers: there is currently no good fix; keys will live
  in process memory only

The General section of Settings shows *"Secure keyring unavailable"*
when this is happening, so it's diagnosable at a glance.

---

## Generated UI components don't preview in browser

**Symptom**: The **🔍 Preview in browser** button is greyed out.

**Cause**: Preview only works for the **HTML + CSS + JS** framework
option. React, Vue, Svelte, etc. need a build step (Vite, webpack, etc.)
that Octar Lab doesn't bundle.

**Workaround**: Save the file, open it in your existing dev environment.
Or generate the same component as plain HTML for a quick visual check
before re-generating in your real framework.

---

## Translation says one thing in the UI and the language switcher disagrees

**Symptom**: The interface is mostly translated but a few labels remain
in the previous language.

**Cause**: Language switching re-translates labels by re-running the
`on_language_changed()` hook on each tab. If you encounter a tab where
one label doesn't update, that's a bug — please file an issue with the
specific tab and label.

**Workaround**: Restarting the application always loads the new language
fully.

---

## Web search / vision / file uploads don't work

That's not a bug — Octar Lab v1.0 only supports text-in / text-out
chat completions. Provider features like vision, web search,
function calling, file uploads, and audio are on the roadmap but not in
this release.

---

## I'm getting strange answers from the chat

The Chat Console sends the entire conversation history with each
request. If a previous message gave the AI an unusual instruction, it
may continue to follow it many turns later. Click **🗑 Clear
Conversation** to start fresh.

If you set a system prompt that's no longer appropriate, click the
**Reset** button next to the system prompt, then **Apply** an empty
prompt to clear it.

---

## Something else

If your problem isn't listed here:

1. Check the **FAQ** for common questions
2. Open an issue on GitHub with: the tab you were using, the inputs,
   the full error message (if any), your OS, and your Python version
3. If it's a provider-specific issue (e.g. rate limits or weird model
   behaviour), include which provider and model you were using

We read every issue. We don't guarantee a fix in any specific timeframe,
but we do read them. Bugs with reproductions get fixed faster than bugs
without.
