"""Centralized logging for the MyCobot Control extension.

All extension code uses this module instead of `print` or `carb.log_*`
directly. Each `info` / `warn` / `error` call fans out to:

- `carb.log_*`           (visible in Isaac Sim Console, if filter allows
                          it; the Console hides INFO by default).
- `print(..., flush=True)` (visible in the terminal that launched Isaac
                          Sim, useful for headless / CI runs).
- Registered subscribers (the in-window log panel uses this so the user
                          always sees output, regardless of Console
                          filter settings).

The module also keeps a small ring buffer of the most recent log lines
so a UI panel can show history when it is (re)built.
"""
from __future__ import annotations

from collections import deque
from typing import Callable, Deque, List, Tuple

import carb
import carb.settings

EXTENSION_TAG = "[MyCobot]"

LogLevel = str  # "info" | "warn" | "error"
LogEvent = Tuple[LogLevel, str]  # (level, formatted_line)
LogSubscriber = Callable[[LogLevel, str], None]

# carb derives the channel from the Python module that called log_*.
# Every call goes through this file, so bumping these two channels is
# enough for power users that look at the Console window directly.
_LOG_CHANNELS = ("mycobot_control", "mycobot_control.logger")
_VALID_CARB_LEVELS = ("verbose", "info", "warning", "error", "fatal")

_HISTORY_SIZE = 500
_history: Deque[LogEvent] = deque(maxlen=_HISTORY_SIZE)
_subscribers: List[LogSubscriber] = []


def configure_logging(level: str = "info") -> None:
    """Set the carb log channel level for this extension's channels.

    Only affects emission to carb sinks; the Isaac Sim Console window
    has its own display filter on top of this. The in-window log panel
    is the primary UX surface and is unaffected by either.
    """
    if level not in _VALID_CARB_LEVELS:
        raise ValueError(
            f"Invalid log level {level!r}; expected one of {_VALID_CARB_LEVELS}"
        )
    settings = carb.settings.get_settings()
    for channel in _LOG_CHANNELS:
        settings.set(f"/log/channels/{channel}/level", level)


def subscribe(callback: LogSubscriber) -> Callable[[], None]:
    """Register a callback that receives every future log event.

    Returns an unsubscribe function. The callback is invoked with
    `(level, formatted_line)`. Exceptions raised by the callback are
    swallowed and reported on stderr to avoid breaking the logger.
    """
    _subscribers.append(callback)

    def _unsubscribe() -> None:
        try:
            _subscribers.remove(callback)
        except ValueError:
            pass

    return _unsubscribe


def get_history() -> List[LogEvent]:
    """Return a snapshot of the most recent log events."""
    return list(_history)


def clear_history() -> None:
    _history.clear()


def _emit(level: LogLevel, line: str) -> None:
    _history.append((level, line))
    for sub in list(_subscribers):
        try:
            sub(level, line)
        except Exception as exc:  # pragma: no cover - defensive
            # Don't log via this module to avoid recursion.
            print(f"[MyCobot][logger] subscriber error: {exc!r}", flush=True)


class Logger:
    """Tiny wrapper around carb logging with an extension-wide prefix."""

    def __init__(self, component: str) -> None:
        self._component = component

    def _fmt(self, msg: str) -> str:
        return f"{EXTENSION_TAG}[{self._component}] {msg}"

    def info(self, msg: str) -> None:
        line = self._fmt(msg)
        carb.log_info(line)
        print(line, flush=True)
        _emit("info", line)

    def warn(self, msg: str) -> None:
        line = self._fmt(msg)
        carb.log_warn(line)
        print(line, flush=True)
        _emit("warn", line)

    def error(self, msg: str) -> None:
        line = self._fmt(msg)
        carb.log_error(line)
        print(line, flush=True)
        _emit("error", line)


def get_logger(component: str) -> Logger:
    """Return a logger tagged with the given component name."""
    return Logger(component)
