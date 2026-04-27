"""
core/secrets.py
══════════════════════════════════════════════════════════════
Secure storage for API keys via the OS keyring:
  • macOS  → Keychain
  • Windows → Credential Manager
  • Linux  → Secret Service (GNOME Keyring / KWallet)

If keyring fails (headless Linux without DBus, etc.), we fall
back to an in-memory dict so the app still runs. Keys held in
memory are lost when the process exits — by design.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import sys
from typing import Optional

try:
    import keyring
    from keyring.errors import KeyringError
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    KeyringError = Exception  # type: ignore

from core.config import APP_SLUG, SUPPORTED_PROVIDERS

# In-memory fallback (also used as a process-level cache)
_memory_store: dict[str, str] = {}


def _key_name(provider: str) -> str:
    """Generate a stable keyring entry name for a provider."""
    return f"{APP_SLUG}:{provider.lower()}"


def is_secure_backend() -> bool:
    """True if a real OS keyring is in use (not the fallback)."""
    if not KEYRING_AVAILABLE:
        return False
    try:
        kr = keyring.get_keyring()
        backend_name = type(kr).__name__.lower()
        # Known insecure fallback backends
        return "fail" not in backend_name and "null" not in backend_name
    except Exception:
        return False


def save_api_key(provider: str, api_key: str) -> bool:
    """
    Persist an API key. Returns True on success.
    Empty key clears the entry.
    """
    if provider not in SUPPORTED_PROVIDERS:
        return False

    key_name = _key_name(provider)

    if not api_key:
        return delete_api_key(provider)

    # Cache in memory
    _memory_store[key_name] = api_key

    if KEYRING_AVAILABLE:
        try:
            keyring.set_password(APP_SLUG, provider.lower(), api_key)
            return True
        except KeyringError as e:
            print(f"[secrets] Keyring write failed for {provider}: {e}", file=sys.stderr)
            return False
    return True  # memory-only is still "saved" for this session


def get_api_key(provider: str) -> Optional[str]:
    """Retrieve an API key, or None if not stored."""
    if provider not in SUPPORTED_PROVIDERS:
        return None

    key_name = _key_name(provider)

    # Check memory cache first
    if key_name in _memory_store:
        return _memory_store[key_name]

    if KEYRING_AVAILABLE:
        try:
            value = keyring.get_password(APP_SLUG, provider.lower())
            if value:
                _memory_store[key_name] = value
            return value
        except KeyringError as e:
            print(f"[secrets] Keyring read failed for {provider}: {e}", file=sys.stderr)
    return None


def delete_api_key(provider: str) -> bool:
    """Remove an API key from both keyring and memory cache."""
    if provider not in SUPPORTED_PROVIDERS:
        return False

    key_name = _key_name(provider)
    _memory_store.pop(key_name, None)

    if KEYRING_AVAILABLE:
        try:
            keyring.delete_password(APP_SLUG, provider.lower())
        except KeyringError:
            # Not found is fine — already deleted
            pass
        except Exception as e:
            print(f"[secrets] Keyring delete failed for {provider}: {e}", file=sys.stderr)
    return True


def list_configured_providers() -> list[str]:
    """Return providers that have a stored API key."""
    return [p for p in SUPPORTED_PROVIDERS if get_api_key(p)]


def mask_key(api_key: str | None) -> str:
    """Display-safe masked version of an API key."""
    if not api_key:
        return "—"
    if len(api_key) <= 12:
        return "•" * len(api_key)
    return f"{api_key[:4]}{'•' * 8}{api_key[-4:]}"
