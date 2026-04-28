from __future__ import annotations

import json
import re
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from core.ai_providers.base import ProviderError


class BaseWorker(QThread):
    """
    Common signal contract every tab can rely on:

      log_signal      (message, level)        — append to live log
      progress_signal (percent_int)           — 0-100
      result_signal   (text)                  — single-shot text output
      file_signal     (full_path, content)    — one file finished (multi-file workers)
      done_signal     (success_bool, message) — finished (success or failure reason)

    Single-output workers (Refactor, Docs etc.) emit `result_signal`.
    Multi-output workers (Library, Architect) emit `file_signal` per file.
    Both emit `done_signal` exactly once at the end.
    """

    log_signal      = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int)
    result_signal   = pyqtSignal(str)
    file_signal     = pyqtSignal(str, str)
    done_signal     = pyqtSignal(bool, str)

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self._config = config
        self._stop = False

    def stop(self):
        """Cooperative cancellation — workers check this between steps."""
        self._stop = True

    @property
    def is_stopping(self) -> bool:
        return self._stop

    def run(self):
        try:
            self._run()
        except ProviderError as e:
            self._log(f"Provider error: {e}", "ERR")
            self.done_signal.emit(False, str(e))
        except Exception as e:
            self._log(f"Unexpected error: {e}", "ERR")
            self.done_signal.emit(False, str(e))

    def _run(self):
        raise NotImplementedError("Subclasses must implement _run()")

    def _log(self, message: str, level: str = "INFO"):
        self.log_signal.emit(message, level)

    def _progress(self, percent: int):
        self.progress_signal.emit(max(0, min(100, percent)))

    @staticmethod
    def strip_code_fences(text: str) -> str:
        """Remove ``` fences the model might wrap output in."""
        if not text:
            return ""
        cleaned = re.sub(r'^```[\w]*\s*\n?', '', text, flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*$',         '', cleaned, flags=re.MULTILINE)
        return cleaned.strip()

    @staticmethod
    def extract_json(text: str) -> dict | None:
        """Best-effort JSON extraction from a model response."""
        if not text:
            return None
        clean = re.sub(r'```(?:json)?\s*', '', text)
        clean = re.sub(r'```\s*$', '', clean, flags=re.MULTILINE).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None
