from __future__ import annotations

import datetime
import sys
import threading
from typing import Callable

LEVEL_ICONS = {
    "INFO":  "◈",
    "OK":    "✓",
    "WARN":  "⚠",
    "ERR":   "✗",
    "AI":    "◆",
    "FILE":  "◉",
    "DEBUG": "·",
}

_subscribers: list[Callable[[str], None]] = []
_lock = threading.Lock()


def subscribe(callback: Callable[[str], None]) -> None:
    """Register a callback to receive every formatted log line."""
    with _lock:
        if callback not in _subscribers:
            _subscribers.append(callback)


def unsubscribe(callback: Callable[[str], None]) -> None:
    with _lock:
        if callback in _subscribers:
            _subscribers.remove(callback)


def log(message: str, level: str = "INFO") -> str:
    """Format, dispatch, and return a log line."""
    icon = LEVEL_ICONS.get(level, "·")
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {icon}  {message}"

    with _lock:
        callbacks = list(_subscribers)

    for cb in callbacks:
        try:
            cb(line)
        except Exception as e:
            print(f"[logger] Subscriber error: {e}", file=sys.stderr)

    # Also echo to stdout for terminal users
    print(line)
    return line


# Convenience wrappers
def info(msg: str)  -> str: return log(msg, "INFO")
def ok(msg: str)    -> str: return log(msg, "OK")
def warn(msg: str)  -> str: return log(msg, "WARN")
def error(msg: str) -> str: return log(msg, "ERR")
def ai(msg: str)    -> str: return log(msg, "AI")
def file(msg: str)  -> str: return log(msg, "FILE")
def debug(msg: str) -> str: return log(msg, "DEBUG")
