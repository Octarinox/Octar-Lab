from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChatMessage:
    """One message in a chat conversation."""
    role: str          # "system" | "user" | "assistant"
    content: str


@dataclass
class ProviderInfo:
    """Static metadata about a provider — for UI listing."""
    id:                str   # internal short name, e.g. "groq"
    display_name:      str   # user-visible name, e.g. "Groq"
    website:           str   # provider homepage
    api_key_url:       str   # where the user gets their key
    description:       str   # short blurb for UI
    requires_internet: bool = True


class BaseProvider(ABC):
    """
    Abstract AI provider.

    Subclasses must implement:
      - INFO          : ProviderInfo class attribute
      - _do_chat      : the actual API call
      - validate_key  : test that an API key works
      - default_models: a list of suggested model strings
    """

    INFO: ProviderInfo  # must be set by subclass

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key


    def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send a chat completion request and return the model's text response.
        Raises ProviderError on failure.
        """
        if not messages:
            raise ProviderError("messages list is empty")
        if not model:
            raise ProviderError("model name is required")

        try:
            return self._do_chat(messages, model, temperature, max_tokens)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"{self.INFO.display_name}: {e}") from e

    def chat_simple(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Convenience wrapper for single-prompt requests."""
        messages: list[ChatMessage] = []
        if system:
            messages.append(ChatMessage(role="system", content=system))
        messages.append(ChatMessage(role="user", content=prompt))
        return self.chat(messages, model, temperature, max_tokens)


    @abstractmethod
    def _do_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str: ...

    @abstractmethod
    def validate_key(self) -> tuple[bool, str]:
        """
        Verify the API key works.
        Returns (success, message). Message describes the result for UI.
        """
        ...

    @abstractmethod
    def default_models(self) -> list[str]:
        """Curated list of model identifiers users can pick from."""
        ...


class ProviderError(Exception):
    """Wraps any provider-side failure with a user-friendly message."""
    pass
