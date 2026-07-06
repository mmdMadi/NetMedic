"""
Utility sub-package for NetMedic.

Provides cross-cutting concerns that are independent of both the network
domain logic and the UI layer:

- :mod:`netmedic.utils.logger`   -- centralized rotating daily logging.
- :mod:`netmedic.utils.admin`    -- Windows administrator detection.
- :mod:`netmedic.utils.storage`  -- paths and on-disk persistence helpers.
- :mod:`netmedic.utils.helpers`  -- small pure helper functions.
"""

from __future__ import annotations

from .logger import get_logger, LogManager
from .admin import is_admin, get_elevation_info
from .storage import Storage
from .helpers import (
    safe_str,
    truncate,
    format_speed,
    format_mac,
    coalesce,
    now_iso,
)

__all__ = [
    "get_logger",
    "LogManager",
    "is_admin",
    "ElevationInfo",
    "get_elevation_info",
    "Storage",
    "safe_str",
    "truncate",
    "format_speed",
    "format_mac",
    "coalesce",
    "now_iso",
]
