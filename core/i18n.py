"""
core/i18n.py
══════════════════════════════════════════════════════════════
Translation loader. Translations live as JSON files under
resources/translations/{lang}.json and are flat key→string
maps. Missing keys fall back to English, then to the key
itself, so the UI never crashes on a missing translation.
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from core.config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

# Path to the translations directory (resolved relative to project root)
_TRANSLATIONS_DIR = Path(__file__).parent.parent / "resources" / "translations"

# Cached loaded translation maps
_loaded: dict[str, dict[str, str]] = {}
_current_language: str = DEFAULT_LANGUAGE


def _load_language(lang: str) -> dict[str, str]:
    """Load a language file, caching the result."""
    if lang in _loaded:
        return _loaded[lang]

    path = _TRANSLATIONS_DIR / f"{lang}.json"
    if not path.exists():
        _loaded[lang] = {}
        return _loaded[lang]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _loaded[lang] = {str(k): str(v) for k, v in data.items()}
        else:
            _loaded[lang] = {}
    except (json.JSONDecodeError, OSError):
        _loaded[lang] = {}
    return _loaded[lang]


def set_language(lang: str) -> None:
    """Change the active language. Falls back to default if unsupported."""
    global _current_language
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    _current_language = lang
    _load_language(lang)
    if lang != DEFAULT_LANGUAGE:
        _load_language(DEFAULT_LANGUAGE)  # ensure fallback is ready


def get_language() -> str:
    return _current_language


def t(key: str, **kwargs) -> str:
    """
    Translate a key to the current language.
    Supports str.format() interpolation:  t("greeting", name="Alice")
    """
    active = _load_language(_current_language)
    fallback = _load_language(DEFAULT_LANGUAGE) if _current_language != DEFAULT_LANGUAGE else {}

    text = active.get(key) or fallback.get(key) or key

    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def language_display_name(lang: str) -> str:
    """Native display name of a language code."""
    return {
        "en": "English",
        "ru": "Русский",
        "de": "Deutsch",
    }.get(lang, lang)


def reload_translations() -> None:
    """Drop the cache and force re-read on next access."""
    _loaded.clear()
    _load_language(_current_language)


# Initialize with default language at import time
set_language(DEFAULT_LANGUAGE)
