"""
Internet connectivity check.

Determines whether the host has a working internet connection by
probing known endpoints. The check is designed to be fast (< 3s) and
non-blocking when called from a background thread.

Two-level check:

1. **Quick check** — attempt a TCP connection to ``1.1.1.1:53`` (Cloudflare DNS).
   This verifies basic IP connectivity without DNS.
2. **Full check** — HTTPS GET to ``https://api.ipify.org``. This verifies DNS
   resolution + HTTP(S) connectivity.

The result is a simple enum that the dashboard can render immediately.
"""

from __future__ import annotations

import socket
from enum import Enum
from typing import Optional

import requests

from utils.logger import get_logger

_log = get_logger(__name__)

#: Timeout for each probe (seconds).
_TIMEOUT: int = 3


class InternetStatus(str, Enum):
    """ coarse internet connectivity state. """

    CONNECTED = "Connected"
    NO_INTERNET = "No Internet"
    NO_DNS = "No DNS"
    CHECK_FAILED = "Check Failed"

    @classmethod
    def from_raw(cls, value: str) -> "InternetStatus":
        """Coerce arbitrary input into an InternetStatus."""
        if isinstance(value, cls):
            return value
        text = str(value).strip().lower()
        for member in cls:
            if member.value.lower() == text:
                return member
        return cls.CHECK_FAILED


def _tcp_probe(host: str = "1.1.1.1", port: int = 53, timeout: int = _TIMEOUT) -> bool:
    """Return ``True`` if a TCP connection to ``host:port`` succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False


def _http_probe(url: str = "https://api.ipify.org?format=json", timeout: int = _TIMEOUT) -> bool:
    """Return ``True`` if an HTTPS GET to ``url`` returns 200.

    Uses HTTPS by default to work behind corporate proxies that may
    intercept plain HTTP traffic.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code == 200
    except (requests.RequestException, OSError):
        return False


def check_internet() -> InternetStatus:
    """Determine the host's internet connectivity status.

    Returns
    -------
    InternetStatus
        - ``CONNECTED`` — both TCP and HTTP probes succeeded.
        - ``NO_DNS`` — TCP works but HTTP (DNS) fails.
        - ``NO_INTERNET`` — TCP probe failed.
        - ``CHECK_FAILED`` — unexpected error during check.
    """
    try:
        tcp_ok = _tcp_probe()
        if not tcp_ok:
            _log.info("Internet check: NO_INTERNET (TCP probe failed)")
            return InternetStatus.NO_INTERNET

        http_ok = _http_probe()
        if http_ok:
            _log.info("Internet check: CONNECTED")
            return InternetStatus.CONNECTED

        _log.info("Internet check: NO_DNS (HTTP probe failed)")
        return InternetStatus.NO_DNS

    except Exception as exc:
        _log.warning("Internet check failed unexpectedly: %s", exc)
        return InternetStatus.CHECK_FAILED


def is_connected() -> bool:
    """Convenience: return ``True`` when the internet is reachable."""
    return check_internet() == InternetStatus.CONNECTED
