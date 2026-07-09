"""
Public-facing network information.

Fetches the host's public IP address and optional ISP/geo metadata from
free, no-auth-required APIs. All calls are synchronous and designed to
be run on a background thread with a short timeout.

APIs used (no API key needed):

- ``https://api.ipify.org?format=json`` — public IPv4
- ``https://api64.ipify.org?format=json`` — public IPv4/IPv6
- ``https://ipapi.co/json/`` — ISP, city, country, ASN (free tier)

Each function degrades gracefully: on network failure it returns a
sentinel string rather than raising.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Optional

import requests

from utils.logger import get_logger

_log = get_logger(__name__)

#: Timeout for every external HTTP call (seconds).
_TIMEOUT: int = 5


@dataclass(frozen=True)
class PublicNetworkInfo:
    """Snapshot of the host's public-facing network identity."""

    public_ipv4: str = "—"
    public_ipv6: str = "—"
    isp: str = "—"
    city: str = "—"
    country: str = "—"
    region: str = "—"
    asn: str = "—"
    timezone: str = "—"
    error: Optional[str] = None


def _safe_get(url: str, timeout: int = _TIMEOUT) -> Optional[dict]:
    """GET ``url`` and return parsed JSON, or ``None`` on any failure."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError, OSError) as exc:
        _log.debug("HTTP request to %s failed: %s", url, exc)
        return None


def get_public_ipv4() -> str:
    """Return the public IPv4 address, or ``"—"`` on failure."""
    data = _safe_get("https://api.ipify.org?format=json")
    if data and "ip" in data:
        return str(data["ip"])
    return "—"


def get_public_ipv6() -> str:
    """Return the public IPv6 address, or ``"—"`` on failure."""
    data = _safe_get("https://api64.ipify.org?format=json")
    if data and "ip" in data:
        ip = str(data["ip"])
        if ":" in ip:
            return ip
    return "—"


def get_isp_info() -> dict[str, str]:
    """Return ISP / geo metadata from ``ipapi.co``.

    Returns a flat dict with keys: ``isp``, ``city``, ``country``,
    ``region``, ``asn``, ``timezone``. Missing fields default to
    ``"—"``.
    """
    data = _safe_get("https://ipapi.co/json/")
    if not data:
        return {
            "isp": "—",
            "city": "—",
            "country": "—",
            "region": "—",
            "asn": "—",
            "timezone": "—",
        }
    return {
        "isp": str(data.get("org") or "—"),
        "city": str(data.get("city") or "—"),
        "country": str(data.get("country_name") or "—"),
        "region": str(data.get("region") or "—"),
        "asn": str(data.get("asn") or "—"),
        "timezone": str(data.get("timezone") or "—"),
    }


def gather() -> PublicNetworkInfo:
    """Collect all public network information in one call.

    This is the main entry point. Each sub-call is independent and
    best-effort — partial results are still returned.
    """
    ipv4 = get_public_ipv4()
    ipv6 = get_public_ipv6()
    isp_data = get_isp_info()

    _log.info("Public info: ipv4=%s ipv6=%s isp=%s", ipv4, ipv6, isp_data.get("isp"))

    return PublicNetworkInfo(
        public_ipv4=ipv4,
        public_ipv6=ipv6,
        **isp_data,
    )
