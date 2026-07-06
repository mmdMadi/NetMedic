"""
Windows administrator / elevation detection.

The destructive NetMedic operations (disable / reset / uninstall) are
gate-kept behind administrator privileges. This module exposes a tiny,
side-effect-free API that works whether or not the Python interpreter
is elevated, and degrades gracefully on non-Windows hosts.
"""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass
from typing import Optional

from .logger import get_logger

_log = get_logger(__name__)


def is_admin() -> bool:
    """Return ``True`` when the current process is elevated.

    On Windows this uses ``shell32.IsUserAnAdmin``. On other platforms
    it falls back to ``os.geteuid() == 0``. Any failure (for example a
    stripped-down Windows build lacking ``shell32``) resolves to
    ``False`` so the caller can warn the user rather than crash.
    """
    if sys.platform == "win32":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError) as exc:
            _log.warning("IsUserAnAdmin failed: %s", exc)
            return False
    try:
        return os_geteuid() == 0  # type: ignore[func-returns-value]
    except (AttributeError, OSError):
        return False


def os_geteuid() -> int:
    """Thin wrapper kept separate so it can be mocked in tests.

    Defined as a module-level function rather than a direct call so the
    codebase never needs an ``import os`` solely for ``geteuid`` on
    platforms where the symbol does not exist.
    """
    import os

    return os.geteuid()


@dataclass(frozen=True)
class ElevationInfo:
    """Structured summary of the current process's privilege context."""

    is_admin: bool
    platform: str
    detail: str

    def as_text(self) -> str:
        """Return a single human-readable line, e.g. ``Administrator (win32)``."""
        role = "Administrator" if self.is_admin else "Standard user"
        return f"{role} ({self.platform}) — {self.detail}"


def get_elevation_info() -> ElevationInfo:
    """Return an :class:`ElevationInfo` describing the current process.

    The ``detail`` field carries a short, user-facing hint, for example
    explaining that maintenance actions will be unavailable when not
    elevated.
    """
    platform = sys.platform
    admin = is_admin()
    if platform == "win32":
        if admin:
            detail = "Maintenance actions are available."
        else:
            detail = "Restart elevated to perform maintenance actions."
    else:
        detail = "Outside Windows: detection is best-effort."
    return ElevationInfo(is_admin=admin, platform=platform, detail=detail)
