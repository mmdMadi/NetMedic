"""
Application configuration for NetMedic.

A single :class:`Config` dataclass is the source of truth for every
runtime knob. It loads from ``config.json`` (via :class:`Storage`),
falls back to typed defaults, validates values, and can be persisted
back to disk. The rest of the application reads configuration only
through this object -- never by re-parsing JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from utils.logger import get_logger
from utils.storage import Storage

_log = get_logger(__name__)

# --------------------------------------------------------------------- #
# Tunable defaults -- referenced by name throughout the app instead of
# sprinkling literals ("magic numbers") inside business logic.
# --------------------------------------------------------------------- #

#: Default PowerShell scan timeout in seconds.
DEFAULT_SCAN_TIMEOUT_SECONDS: int = 60
#: Lower clamp for the scan timeout -- anything below is unsafe.
MIN_SCAN_TIMEOUT_SECONDS: int = 5
#: Upper clamp for the scan timeout -- anything above would hang the TUI.
MAX_SCAN_TIMEOUT_SECONDS: int = 600
#: Default color theme name; must match a key in the TCSS theme file.
DEFAULT_THEME: str = "netmedic-dark"


@dataclass
class Config:
    """Strongly-typed runtime configuration.

    The dataclass is intentionally flat -- nested config sections are
    represented as plain lists/dicts so that JSON round-tripping stays
    trivial and the schema remains obvious from the type hints.
    """

    theme: str = DEFAULT_THEME
    scan_timeout: int = DEFAULT_SCAN_TIMEOUT_SECONDS
    logging: bool = True
    ignored_adapters: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Construction / IO
    # ------------------------------------------------------------------ #
    @classmethod
    def from_storage(cls, storage: Storage) -> "Config":
        """Load configuration, applying defaults and validation.

        Missing keys, malformed JSON, and out-of-range values never
        crash the application: the offending field is replaced with its
        default and a warning is logged.
        """
        raw = storage.read_json(storage.config_path, default={})
        if not isinstance(raw, Mapping):
            _log.warning("config.json is not an object; using defaults.")
            raw = {}

        return cls(
            theme=cls._coerce_str(
                raw.get("theme"), DEFAULT_THEME, label="theme"
            ),
            scan_timeout=cls._coerce_timeout(raw.get("scan_timeout")),
            logging=cls._coerce_bool(raw.get("logging"), default=True),
            ignored_adapters=cls._coerce_str_list(
                raw.get("ignored_adapters"), label="ignored_adapters"
            ),
        )

    def save(self, storage: Storage) -> bool:
        """Persist this configuration to ``config.json``."""
        payload = asdict(self)
        ok = storage.write_json(storage.config_path, payload)
        if ok:
            _log.info("Configuration saved to %s.", storage.config_path)
        else:
            _log.error("Failed to save configuration to %s.", storage.config_path)
        return ok

    # ------------------------------------------------------------------ #
    # Mutators (validated)
    # ------------------------------------------------------------------ #
    def set_timeout(self, seconds: Any) -> None:
        """Set ``scan_timeout`` after clamping to the legal range."""
        self.scan_timeout = self._coerce_timeout(seconds)

    def set_theme(self, name: str) -> None:
        """Set ``theme`` (empty/whitespace values keep the current theme)."""
        cleaned = (name or "").strip()
        if cleaned:
            self.theme = cleaned

    def ignore(self, adapter_name: str) -> None:
        """Add ``adapter_name`` to the ignore list if not already present."""
        cleaned = (adapter_name or "").strip()
        if cleaned and cleaned not in self.ignored_adapters:
            self.ignored_adapters.append(cleaned)

    def unignore(self, adapter_name: str) -> None:
        """Remove ``adapter_name`` from the ignore list if present."""
        cleaned = (adapter_name or "").strip()
        while cleaned in self.ignored_adapters:
            self.ignored_adapters.remove(cleaned)

    def is_ignored(self, adapter_name: str) -> bool:
        """Return ``True`` when ``adapter_name`` is on the ignore list."""
        return (adapter_name or "").strip() in self.ignored_adapters

    # ------------------------------------------------------------------ #
    # Coercion helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _coerce_str(value: Any, default: str, *, label: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None:
            _log.warning("config field '%s' invalid (%r); using default.", label, value)
        return default

    @staticmethod
    def _coerce_bool(value: Any, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str) and value.strip().lower() in {
            "true",
            "yes",
            "1",
            "on",
        }:
            return True
        if isinstance(value, str) and value.strip().lower() in {
            "false",
            "no",
            "0",
            "off",
        }:
            return False
        if value is not None:
            _log.warning("config boolean invalid (%r); using default %r.", value, default)
        return default

    @staticmethod
    def _coerce_timeout(value: Any) -> int:
        """Coerce ``value`` to a legal scan-timeout integer."""
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            if value is not None:
                _log.warning(
                    "scan_timeout invalid (%r); using default %ds.",
                    value,
                    DEFAULT_SCAN_TIMEOUT_SECONDS,
                )
            return DEFAULT_SCAN_TIMEOUT_SECONDS
        return max(MIN_SCAN_TIMEOUT_SECONDS, min(MAX_SCAN_TIMEOUT_SECONDS, seconds))

    @staticmethod
    def _coerce_str_list(value: Any, *, label: str) -> list[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if value is not None:
            _log.warning("config field '%s' is not a list; ignoring.", label)
        return []

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        """Return configuration formatted as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# --------------------------------------------------------------------- #
# Bootstrap helper
# --------------------------------------------------------------------- #
def load_config(storage: Optional[Storage] = None) -> tuple[Config, Storage]:
    """Convenience wrapper used by ``app.py``.

    Returns the loaded :class:`Config` together with the :class:`Storage`
    that produced it, so callers can immediately persist changes.
    """
    storage = storage or Storage()
    config = Config.from_storage(storage)
    return config, storage
