from __future__ import annotations

from core.ai_providers.base import (
    BaseProvider, ChatMessage, ProviderInfo, ProviderError
)

try:
    import anthropic
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    anthropic = None  # type: ignore


class AnthropicProvider(BaseProvider):

    INFO = ProviderInfo(
        id="anthropic",
        display_name="Anthropic Claude",
        website="https://www.anthropic.com",
        api_key_url="https://console.anthropic.com/settings/keys",
        description="Claude family — Opus, Sonnet, Haiku.",
    )

    def __init__(self, api_key: str):
        if not SDK_AVAILABLE:
            raise ProviderError("anthropic SDK not installed. Run: pip install anthropic")
        super().__init__(api_key)
        self._client = anthropic.Anthropic(api_key=api_key)

    def _do_chat(self, messages, model, temperature, max_tokens):
        # Anthropic separates `system` from the user/assistant message stream
        system_text = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_text = (system_text + "\n\n" + m.content).strip() if system_text else m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        kwargs: dict = {
            "model":       model,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "messages":    chat_msgs,
        }
        if system_text:
            kwargs["system"] = system_text

        resp = self._client.messages.create(**kwargs)

        # Concatenate all text-type content blocks into a single string
        parts = []
        for block in resp.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts)

    def validate_key(self) -> tuple[bool, str]:
        try:
            # Tiny probe message — costs ~1 token
            self._client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=8,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True, "✓ Anthropic API key is valid"
        except Exception as e:
            return False, f"✗ Validation failed: {e}"

    def default_models(self) -> list[str]:
        return [
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-haiku-4-5",
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-latest",
        ]
