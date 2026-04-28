from __future__ import annotations

from core.ai_providers.base import (
    BaseProvider, ChatMessage, ProviderInfo, ProviderError
)

# Try the NEW unified SDK first
SDK_VARIANT: str = "none"
genai = None        # type: ignore
genai_types = None  # type: ignore

try:
    from google import genai as _genai_new           # type: ignore
    from google.genai import types as _genai_types   # type: ignore
    genai = _genai_new
    genai_types = _genai_types
    SDK_VARIANT = "new"
except ImportError:
    # Fall back to the legacy SDK (deprecated, but still works)
    try:
        import google.generativeai as _genai_legacy  # type: ignore
        genai = _genai_legacy
        SDK_VARIANT = "legacy"
    except ImportError:
        SDK_VARIANT = "none"


class GeminiProvider(BaseProvider):

    INFO = ProviderInfo(
        id="gemini",
        display_name="Google Gemini",
        website="https://ai.google.dev",
        api_key_url="https://aistudio.google.com/app/apikey",
        description="Google's Gemini family — Pro, Flash, etc.",
    )

    def __init__(self, api_key: str):
        if SDK_VARIANT == "none":
            raise ProviderError(
                "google-genai SDK not installed. "
                "Run: pip install google-genai"
            )
        super().__init__(api_key)
        self._client = None
        if SDK_VARIANT == "new":
            # New SDK — explicit client, no global state
            self._client = genai.Client(api_key=api_key)
        else:
            # Legacy SDK — global config
            genai.configure(api_key=api_key)

    @staticmethod
    def _split_messages(messages: list[ChatMessage]):
        """
        Gemini separates `system_instruction` from the user/model turns.
        Roles map: 'assistant' → 'model', 'user' → 'user', 'system' → folded out.
        """
        system_text = ""
        history: list[dict] = []
        for m in messages:
            if m.role == "system":
                system_text = (
                    f"{system_text}\n\n{m.content}".strip()
                    if system_text else m.content
                )
            elif m.role == "assistant":
                history.append({"role": "model", "parts": [{"text": m.content}]})
            else:
                history.append({"role": "user",  "parts": [{"text": m.content}]})
        return system_text, history

    def _do_chat(self, messages, model, temperature, max_tokens):
        system_text, history = self._split_messages(messages)
        if SDK_VARIANT == "new":
            return self._chat_new(model, system_text, history, temperature, max_tokens)
        return self._chat_legacy(model, system_text, history, temperature, max_tokens)

    def _chat_new(self, model, system_text, history, temperature, max_tokens):
        # New SDK: client.models.generate_content(model, contents, config)
        config_kwargs: dict = {
            "temperature":       temperature,
            "max_output_tokens": max_tokens,
        }
        if system_text:
            config_kwargs["system_instruction"] = system_text

        # Prefer the typed config object; fall back to plain dict (SDK accepts both)
        try:
            config = genai_types.GenerateContentConfig(**config_kwargs)
        except Exception:
            config = config_kwargs

        resp = self._client.models.generate_content(
            model=model,
            contents=history,
            config=config,
        )

        # Use the convenience accessor when present, walk parts otherwise.
        text = getattr(resp, "text", None)
        if text:
            return text
        parts: list[str] = []
        for cand in getattr(resp, "candidates", []) or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", []) or []:
                pt = getattr(part, "text", None)
                if pt:
                    parts.append(pt)
        return "\n".join(parts)

    def _chat_legacy(self, model, system_text, history, temperature, max_tokens):
        gen_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_text or None,
        )
        # Legacy SDK expects {"role": ..., "parts": [str]} not [{"text": str}]
        legacy_history = [
            {"role": h["role"], "parts": [p["text"] for p in h["parts"]]}
            for h in history
        ]
        resp = gen_model.generate_content(
            legacy_history,
            generation_config={
                "temperature":       temperature,
                "max_output_tokens": max_tokens,
            },
        )
        return resp.text or ""

    def validate_key(self) -> tuple[bool, str]:
        try:
            if SDK_VARIANT == "new":
                list(self._client.models.list())
            else:
                list(genai.list_models())
            return True, "✓ Gemini API key is valid"
        except Exception as e:
            return False, f"✗ Validation failed: {e}"

    def default_models(self) -> list[str]:
        return [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
