"""
core/ai_providers/openai_provider.py
══════════════════════════════════════════════════════════════
OpenAI (GPT-4o, GPT-4 Turbo, o1) provider.
═══════════════════════════════════════════════════════════
"""
from __future__ import annotations

from core.ai_providers.base import (
    BaseProvider, ChatMessage, ProviderInfo, ProviderError
)

try:
    from openai import OpenAI
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    OpenAI = None  # type: ignore


class OpenAIProvider(BaseProvider):

    INFO = ProviderInfo(
        id="openai",
        display_name="OpenAI",
        website="https://openai.com",
        api_key_url="https://platform.openai.com/api-keys",
        description="GPT-4o, GPT-4, o1 and other OpenAI models.",
    )

    def __init__(self, api_key: str):
        if not SDK_AVAILABLE:
            raise ProviderError("openai SDK not installed. Run: pip install openai")
        super().__init__(api_key)
        self._client = OpenAI(api_key=api_key)

    def _do_chat(self, messages, model, temperature, max_tokens):
        resp = self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return resp.choices[0].message.content or ""

    def validate_key(self) -> tuple[bool, str]:
        try:
            self._client.models.list()
            return True, "✓ OpenAI API key is valid"
        except Exception as e:
            return False, f"✗ Validation failed: {e}"

    def default_models(self) -> list[str]:
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini",
        ]
