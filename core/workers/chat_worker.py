"""
core/workers/chat_worker.py
══════════════════════════════════════════════════════════════
Worker for multi-turn chat conversations.
Sends full conversation history (system + user/assistant turns)
and emits the assistant's reply via result_signal.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from core.ai_providers.base import ChatMessage
from core.ai_providers.factory import ProviderFactory
from core.workers.base_worker import BaseWorker


class ChatWorker(BaseWorker):
    """
    Multi-turn chat worker.

    Config schema:
      {
        "provider_id":  str,
        "model":        str,
        "messages":     list[dict],   # [{"role": "system"|"user"|"assistant", "content": str}, ...]
        "temperature":  float,
        "max_tokens":   int,
      }
    """

    def _run(self):
        cfg = self._config

        provider_id = cfg["provider_id"]
        model       = cfg["model"]
        messages    = cfg.get("messages", [])
        temperature = cfg.get("temperature", 0.7)
        max_tokens  = cfg.get("max_tokens", 4096)

        if not messages:
            self.done_signal.emit(False, "No messages to send")
            return

        # 1. Initialise provider
        self._log(f"Initialising {provider_id}…", "AI")
        provider = ProviderFactory.create(provider_id)
        self._log(f"Provider ready: {provider.INFO.display_name}", "OK")
        self._progress(20)

        if self.is_stopping:
            self.done_signal.emit(False, "Stopped by user")
            return

        # 2. Convert dicts → ChatMessage objects
        chat_messages = [
            ChatMessage(role=m["role"], content=m["content"]) for m in messages
        ]
        self._log(f"Sending {len(chat_messages)} messages to {model}…", "AI")
        self._progress(40)

        # 3. Send the request
        response = provider.chat(
            messages=chat_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if self.is_stopping:
            self.done_signal.emit(False, "Stopped by user")
            return

        if not response or not response.strip():
            self._log("Empty response from model", "WARN")
            self.done_signal.emit(False, "Empty response")
            return

        self._progress(95)
        self._log(f"Received {len(response)} characters", "OK")

        # 4. Emit and finish
        self.result_signal.emit(response)
        self._progress(100)
        self.done_signal.emit(True, "OK")
