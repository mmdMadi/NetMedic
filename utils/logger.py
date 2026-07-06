"""
Centralized logging for NetMedic.

A single :class:`LogManager` configures the root ``netmedic`` logger
once per process. Subsequent calls to :func:`get_logger` return child
loggers that automatically inherit file + console handlers.

Daily log files are written to ``logs/netmedic-YYYY-MM-DD.log`` and a
config flag (``logging``) can disable the feature entirely.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
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
