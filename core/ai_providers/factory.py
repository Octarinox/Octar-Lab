from __future__ import annotations

from typing import Optional, Type

from core.ai_providers.base import BaseProvider, ProviderInfo, ProviderError
from core.ai_providers.groq_provider      import GroqProvider
from core.ai_providers.openai_provider    import OpenAIProvider
from core.ai_providers.anthropic_provider import AnthropicProvider
from core.ai_providers.gemini_provider    import GeminiProvider
from core.ai_providers.mistral_provider   import MistralProvider
from core.secrets import get_api_key


# Internal registry — adding a new provider = adding one line here
_REGISTRY: dict[str, Type[BaseProvider]] = {
    "groq":      GroqProvider,
    "openai":    OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini":    GeminiProvider,
    "mistral":   MistralProvider,
}


class ProviderFactory:
    """Constructs provider instances by id."""

    @staticmethod
    def available_ids() -> list[str]:
        """List all registered provider ids (in display order)."""
        return list(_REGISTRY.keys())

    @staticmethod
    def info_list() -> list[ProviderInfo]:
        """Static metadata for every registered provider — for UI."""
        return [cls.INFO for cls in _REGISTRY.values()]

    @staticmethod
    def get_info(provider_id: str) -> Optional[ProviderInfo]:
        cls = _REGISTRY.get(provider_id.lower())
        return cls.INFO if cls else None

    @staticmethod
    def get_class(provider_id: str) -> Optional[Type[BaseProvider]]:
        return _REGISTRY.get(provider_id.lower())

    @staticmethod
    def create(provider_id: str, api_key: Optional[str] = None) -> BaseProvider:
        """
        Instantiate a provider. If no api_key is passed, read it from the keyring.
        Raises ProviderError on missing SDK, missing key, or invalid id.
        """
        cls = _REGISTRY.get(provider_id.lower())
        if cls is None:
            raise ProviderError(f"Unknown provider: {provider_id}")

        if api_key is None:
            api_key = get_api_key(provider_id.lower())

        if not api_key:
            display = cls.INFO.display_name
            raise ProviderError(
                f"No API key configured for {display}. "
                f"Add one in Settings tab."
            )
        return cls(api_key)

    @staticmethod
    def create_from_settings(settings) -> BaseProvider:
        """Instantiate the provider currently selected in app settings."""
        return ProviderFactory.create(settings.active_provider)
