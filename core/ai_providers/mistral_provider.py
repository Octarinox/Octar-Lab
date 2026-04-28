from __future__ import annotations

from core.ai_providers.base import (
    BaseProvider, ChatMessage, ProviderInfo, ProviderError
)

try:
    from mistralai import Mistral
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    Mistral = None  # type: ignore


class MistralProvider(BaseProvider):

    INFO = ProviderInfo(
        id="mistral",
        display_name="Mistral AI",
        website="https://mistral.ai",
        api_key_url="https://console.mistral.ai/api-keys/",
        description="Mistral Large, Medium, Small and Codestral.",
    )

    def __init__(self, api_key: str):
        if not SDK_AVAILABLE:
            raise ProviderError("mistralai SDK not installed. Run: pip install mistralai")
        super().__init__(api_key)
        self._client = Mistral(api_key=api_key)

    def _do_chat(self, messages, model, temperature, max_tokens):
        resp = self._client.chat.complete(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def validate_key(self) -> tuple[bool, str]:
        try:
            self._client.models.list()
            return True, "✓ Mistral API key is valid"
        except Exception as e:
            return False, f"✗ Validation failed: {e}"

    def default_models(self) -> list[str]:
        return [
            "mistral-large-latest",
            "mistral-small-latest",
            "open-mistral-nemo",
            "codestral-latest",
            "mistral-embed",
        ]
