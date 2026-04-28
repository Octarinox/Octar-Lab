from __future__ import annotations

from core.ai_providers.factory import ProviderFactory
from core.workers.base_worker import BaseWorker


class SimpleWorker(BaseWorker):
    """One prompt → one response, in a background thread."""

    def _run(self):
        cfg = self._config

        provider_id = cfg["provider_id"]
        model       = cfg["model"]
        temperature = cfg.get("temperature", 0.7)
        max_tokens  = cfg.get("max_tokens", 4096)
        sys_prompt  = cfg.get("system_prompt", "")
        usr_prompt  = cfg.get("user_prompt", "")
        strip       = cfg.get("strip_fences", True)
        label       = cfg.get("log_label", "Processing")

        # 1. Initialise provider
        self._log(f"Initialising {provider_id}…", "AI")
        provider = ProviderFactory.create(provider_id)
        self._log(f"Provider ready: {provider.INFO.display_name}", "OK")
        self._progress(15)

        if self.is_stopping:
            self.done_signal.emit(False, "Stopped by user")
            return

        # 2. Send the prompt
        self._log(f"{label} with model {model}…", "AI")
        self._progress(35)

        response = provider.chat_simple(
            prompt=usr_prompt,
            model=model,
            system=sys_prompt or None,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if self.is_stopping:
            self.done_signal.emit(False, "Stopped by user")
            return

        self._progress(85)

        if not response or not response.strip():
            self._log("Model returned empty response", "WARN")
            self.done_signal.emit(False, "Empty response from model")
            return

        # 3. Optional fence-stripping for code outputs
        if strip:
            response = self.strip_code_fences(response)

        char_count = len(response)
        self._log(f"Received {char_count} characters", "OK")

        # 4. Emit the result
        self.result_signal.emit(response)
        self._progress(100)
        self._log("✓ Done", "OK")
        self.done_signal.emit(True, f"{char_count} characters generated")
