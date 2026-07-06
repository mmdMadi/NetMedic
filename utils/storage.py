"""
On-disk storage and path resolution for NetMedic.

Everything that touches the filesystem in a "where do files live?" way is
centralized here so that the rest of the application never hard-codes
paths. Paths are resolved relative to the project root, which is the
directory containing the top-level ``app.py``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


class Storage:
    """Resolve NetMedic's on-disk locations and persist small JSON blobs.

    The class intentionally has **no mutable instance state** other than
    cached path objects; it is safe to instantiate many times or to share
    a single instance across threads.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        """Initialize storage rooted at ``base_dir``.

        Parameters
        ----------
        base_dir:
            Project root. When ``None`` (the default) the directory that
            contains the entry-point ``app.py`` is used. The path is
            resolved to an absolute path immediately.
        """
        if base_dir is None:
            # app.py lives at the project root.
            base_dir = Path(__file__).resolve().parent.parent
        self._base: Path = Path(base_dir).resolve()
        self._logs: Path = self._base / "logs"
        self._config: Path = self._base / "config.json"

    # ------------------------------------------------------------------ #
    # Path properties
    # ------------------------------------------------------------------ #
    @property
    def base_dir(self) -> Path:
        """Absolute path to the project root."""
        return self._base

    @property
    def logs_dir(self) -> Path:
        """Absolute path to the ``logs/`` directory (created on demand)."""
        self._logs.mkdir(parents=True, exist_ok=True)
        return self._logs

    @property
    def config_path(self) -> Path:
        """Absolute path to ``config.json``."""
        return self._config

    @property
    def theme_path(self) -> Path:
        """Absolute path to ``theme.tcss``."""
        return self._base / "theme.tcss"

    # ------------------------------------------------------------------ #
    # JSON persistence helpers
    # ------------------------------------------------------------------ #
    def read_json(self, path: Path, default: Any = None) -> Any:
        """Read a JSON file, returning ``default`` on any failure.

        Parameters
        ----------
        path:
            File to read.
        default:
            Value returned when the file is missing or invalid.
        """
        try:
            if not path.exists():
                return default
            text = path.read_text(encoding="utf-8")
            return json.loads(text)
        except (OSError, json.JSONDecodeError) as exc:
            # Use stderr rather than the logger to avoid a circular import.
            import sys

            print(f"[storage] failed to read {path}: {exc}", file=sys.stderr)
            return default

    def write_json(self, path: Path, data: Any, *, indent: int = 2) -> bool:
        """Atomically write ``data`` as JSON.

        Uses a sibling temporary file plus ``os.replace`` so that an
        interrupted write cannot corrupt the destination.

        Returns ``True`` on success, ``False`` on failure.
        """
        tmp: Path = path.with_suffix(path.suffix + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(
                json.dumps(data, indent=indent, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(tmp, path)
            return True
        except OSError as exc:
            import sys

            print(f"[storage] failed to write {path}: {exc}", file=sys.stderr)
            # Best-effort cleanup of the temp file.
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False
