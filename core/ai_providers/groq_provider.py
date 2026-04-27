"""
core/ai_providers/groq_provider.py
══════════════════════════════════════════════════════════════
Groq (LPU-accelerated open models) provider.
═══════════════════════════════════════════════════════════
"""
from __future__ import annotations

from core.ai_providers.base import (
    BaseProvider, ChatMessage, ProviderInfo, ProviderError
)

try:
    from groq import Groq
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    Groq = None  # type: ignore


class GroqProvider(BaseProvider):

    INFO = ProviderInfo(
        id="groq",
        display_name="Groq",
        website="https://groq.com",
        api_key_url="https://console.groq.com/keys",
        description="Ultra-fast inference of open-weight models on Groq LPUs.",
    )

    def __init__(self, api_key: str):
        if not SDK_AVAILABLE:
            raise ProviderError("groq SDK not installed. Run: pip install groq")
        super().__init__(api_key)
        self._client = Groq(api_key=api_key)

    def _do_chat(self, messages, model, temperature, max_tokens):
        resp = self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            stream=False,
        )
        return resp.choices[0].message.content or ""

    def validate_key(self) -> tuple[bool, str]:
        try:
            # Cheapest possible call — list models
            self._client.models.list()
            return True, "✓ Groq API key is valid"
        except Exception as e:
            return False, f"✗ Validation failed: {e}"

    def default_models(self) -> list[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]
