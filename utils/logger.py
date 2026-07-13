"""
Centralized logging for NetMedic.

A single :class:`LogManager` configures the root ``netmedic`` logger
once per process. Subsequent calls to :func:`get_logger` return child
loggers that automatically inherit file + console handlers.

Daily log files are written to ``logs/netmedic-YYYY-MM-DD.log`` and a
config flag (``logging``) can disable the feature entirely.

Log files older than ``RETENTION_DAYS`` are automatically cleaned up
on each :meth:`LogManager.setup` call.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Sentinel attribute name used on the logger to remember that we have
# already installed our custom handlers. Keeps idempotent setup cheap
# without relying on a module-level mutable global.
_INSTALLED_ATTR = "_netmedic_handlers_installed"

#: Standard log line format for file output.
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
#: Slightly shorter format for stderr.
CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"

#: Number of days to keep log files before automatic cleanup.
RETENTION_DAYS: int = 30


class LogManager:
    """Configure and own the NetMedic logging infrastructure.

    The class is effectively a namespace; the public surface is the
    classmethod :meth:`setup`, which is idempotent across calls.
    """

    ROOT_LOGGER_NAME = "netmedic"

    @classmethod
    def setup(
        cls,
        logs_dir: Path,
        *,
        enable: bool = True,
        level: int = logging.INFO,
        retention_days: int = RETENTION_DAYS,
    ) -> logging.Logger:
        """Install handlers on the root NetMedic logger.

        Parameters
        ----------
        logs_dir:
            Directory that will hold the daily log files. Created if
            missing. Ignored when ``enable`` is ``False``.
        enable:
            When ``False`` no file handler is attached; the logger is
            still returned and a NullHandler guarantees no
            "No handlers could be found" warnings.
        level:
            Minimum severity that will be emitted.
        retention_days:
            Number of days to keep log files. Older files are deleted.

        Returns
        -------
        logging.Logger
            The configured root logger.
        """
        logger = logging.getLogger(cls.ROOT_LOGGER_NAME)
        logger.setLevel(level)

        already_installed = getattr(logger, _INSTALLED_ATTR, False)
        if already_installed:
            # Level is cheap to update; honor a re-call that changes it.
            logger.setLevel(level)
            return logger

        # Avoid accidental double-printing via parent root handlers.
        logger.propagate = False

        if enable:
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
                # Clean up old log files before creating the new handler.
                cls._cleanup_old_logs(logs_dir, retention_days)
                file_handler = logging.FileHandler(
                    cls._daily_path(logs_dir),
                    encoding="utf-8",
                    delay=True,
                )
                file_handler.setLevel(level)
                file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
                logger.addHandler(file_handler)
            except OSError as exc:
                # Logging must never crash the app; fall back to stderr only.
                print(f"[logger] file handler disabled: {exc}", file=sys.stderr)
        else:
            logger.addHandler(logging.NullHandler())

        # Always mirror to stderr so the terminal operator sees activity
        # when NetMedic is run outside the TUI (e.g. ``--version``).
        console_handler = logging.StreamHandler(stream=sys.stderr)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
        logger.addHandler(console_handler)

        setattr(logger, _INSTALLED_ATTR, True)
        return logger

    @staticmethod
    def _daily_path(logs_dir: Path) -> Path:
        """Return today's log file path: ``netmedic-YYYY-MM-DD.log``."""
        stamp = datetime.now().strftime("%Y-%m-%d")
        return logs_dir / f"netmedic-{stamp}.log"

    @staticmethod
    def _cleanup_old_logs(logs_dir: Path, retention_days: int) -> int:
        """Delete log files older than ``retention_days``.

        Returns the number of files deleted.
        """
        if retention_days <= 0:
            return 0

        cutoff = datetime.now() - timedelta(days=retention_days)
        deleted = 0

        for log_file in logs_dir.glob("netmedic-*.log"):
            try:
                # Parse date from filename: netmedic-YYYY-MM-DD.log
                stem = log_file.stem  # netmedic-YYYY-MM-DD
                date_str = stem.replace("netmedic-", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    log_file.unlink()
                    deleted += 1
            except (ValueError, OSError):
                # Skip files that don't match the expected pattern.
                continue

        return deleted


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger under the NetMedic root.

    Parameters
    ----------
        name: Optional explicit child name. When omitted, the caller's
            module ``__name__`` is the conventional choice and is what
            most call sites pass.

    Notes
    -----
    Callers should have invoked :meth:`LogManager.setup` at least once
    during application startup. If they have not, a ``NullHandler`` is
    attached automatically to keep the app quiet-but-safe.
    """
    root = logging.getLogger(LogManager.ROOT_LOGGER_NAME)
    if not root.handlers:
        root.addHandler(logging.NullHandler())
    if not name:
        return root
    return root.getChild(name)


def list_log_files(logs_dir: Path) -> list[dict]:
    """Return metadata for all log files in ``logs_dir``.

    Each entry contains ``name``, ``size_bytes``, ``modified``, and
    ``path``. Sorted by modification time (newest first).
    """
    files: list[dict] = []
    if not logs_dir.exists():
        return files

    for log_file in sorted(logs_dir.glob("netmedic-*.log"), reverse=True):
        try:
            stat = log_file.stat()
            files.append({
                "name": log_file.name,
                "path": str(log_file),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            })
        except OSError:
            continue

    return files


def read_log_file(path: str, max_lines: int = 500) -> str:
    """Read the last ``max_lines`` of a log file.

    Returns the content as a single string. If the file is larger than
    ``max_lines`` lines, only the most recent lines are returned.
    """
    try:
        p = Path(path)
        if not p.exists():
            return "Log file not found."

        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        if len(lines) > max_lines:
            lines = lines[-max_lines:]
            return f"--- Showing last {max_lines} of {len(lines)} lines ---\n" + "".join(lines)

        return "".join(lines)

    except Exception as exc:
        return f"Failed to read log file: {exc}"
