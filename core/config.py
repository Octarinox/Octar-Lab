"""
core/config.py
══════════════════════════════════════════════════════════════
Application-wide configuration: paths, defaults, constants.
User preferences are persisted to a JSON file in the user's
config directory (XDG-compliant on Linux, AppData on Windows).
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

APP_NAME      = "Octar Lab"
APP_SLUG      = "octar-lab"
APP_VERSION   = "1.0.0"
APP_AUTHOR    = "Octarinox"
APP_REPO_URL  = "https://github.com/octarinox/octar-lab"
APP_LICENSE   = "MIT"

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "ru", "de")

# AI providers registered in v1.0
SUPPORTED_PROVIDERS = ("groq", "openai", "anthropic", "gemini", "mistral")

# Default models per provider (user can override in Settings)
DEFAULT_MODELS: dict[str, dict[str, str]] = {
    "groq": {
        "architect": "llama-3.3-70b-versatile",
        "coder":     "llama-3.1-8b-instant",
    },
    "openai": {
        "architect": "gpt-4o",
        "coder":     "gpt-4o-mini",
    },
    "anthropic": {
        "architect": "claude-opus-4-5",
        "coder":     "claude-haiku-4-5",
    },
    "gemini": {
        "architect": "gemini-1.5-pro",
        "coder":     "gemini-1.5-flash",
    },
    "mistral": {
        "architect": "mistral-large-latest",
        "coder":     "mistral-small-latest",
    },
}


def get_config_dir() -> Path:
    """Return the user's config directory, cross-platform."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    path = Path(base) / APP_SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_default_output_dir() -> Path:
    """Default location where generated projects are written."""
    return Path.home() / "OctarLabProjects"


CONFIG_FILE = get_config_dir() / "settings.json"


@dataclass
class AppSettings:
    """User-tweakable settings — persisted as JSON."""
    language:           str = DEFAULT_LANGUAGE
    active_provider:    str = "groq"
    output_directory:   str = field(default_factory=lambda: str(get_default_output_dir()))
    temperature:        float = 0.7
    max_files:          int = 12
    auto_git_init:      bool = True
    generate_readme:    bool = True
    generate_deps:      bool = True
    custom_models:      dict[str, dict[str, str]] = field(default_factory=dict)
    telemetry_opt_in:   bool = False  # always default OFF — privacy first

    @classmethod
    def load(cls) -> "AppSettings":
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                # Corrupt config — fall back to defaults rather than crash
                pass
        return cls()

    def save(self) -> None:
        try:
            CONFIG_FILE.write_text(
                json.dumps(asdict(self), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            print(f"[config] Failed to save settings: {e}", file=sys.stderr)

    def get_model(self, provider: str, role: str) -> str:
        """Resolve model name for (provider, role) — custom overrides default."""
        custom = self.custom_models.get(provider, {})
        if role in custom and custom[role]:
            return custom[role]
        return DEFAULT_MODELS.get(provider, {}).get(role, "")

    def set_model(self, provider: str, role: str, model: str) -> None:
        self.custom_models.setdefault(provider, {})[role] = model
