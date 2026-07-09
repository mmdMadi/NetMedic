"""
Local network information gathered via psutil.

This module provides a fast, non-blocking way to read the host's local
IP addresses, connected adapters, and basic interface statistics. It
does **not** make any external network calls — everything comes from
the operating system's network stack.

All public functions are synchronous and cheap to call from a
background thread.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import Optional

import psutil

from utils.logger import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class AdapterInfo:
    """Snapshot of a single network adapter's live state."""

    name: str
    is_up: bool
    speed: int  # Mbps, 0 = unknown
    mtu: int
    ipv4: list[str] = field(default_factory=list)
    ipv6: list[str] = field(default_factory=list)
    mac: str = ""


@dataclass(frozen=True)
class LocalNetworkInfo:
    """Aggregated local network snapshot."""

    hostname: str
    local_ip: str
    connected_adapter: str
    adapters: list[AdapterInfo] = field(default_factory=list)


def get_hostname() -> str:
    """Return the system hostname."""
    return socket.gethostname()


def get_local_ip() -> str:
    """Return the primary local IPv4 address.

    Uses a UDP socket connect to a public IP (no actual traffic is
    sent) to determine which local interface would be used for
    outbound connections. Falls back to ``127.0.0.1`` on failure.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def get_connected_adapter() -> str:
    """Return the name of the adapter that has the default route.

    Iterates psutil's interface stats and returns the first adapter
    that is up and has a non-zero speed. Returns ``"—"`` if none found.
    """
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    for name, stat in stats.items():
        if stat.isup and stat.speed > 0:
            if name in addrs:
                for addr in addrs[name]:
                    if addr.family == socket.AF_INET:
                        return name
    return "—"


def get_all_adapters() -> list[AdapterInfo]:
    """Return a list of every network adapter with its live state."""
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    result: list[AdapterInfo] = []

    for name, stat in stats.items():
        ipv4: list[str] = []
        ipv6: list[str] = []
        mac = ""

        if name in addrs:
            for addr in addrs[name]:
                if addr.family == socket.AF_INET:
                    ipv4.append(addr.address)
                elif addr.family == socket.AF_INET6:
                    ipv6.append(addr.address)
                elif addr.family == psutil.AF_LINK:
                    mac = addr.address

        result.append(
            AdapterInfo(
                name=name,
                is_up=stat.isup,
                speed=stat.speed,
                mtu=stat.mtu,
                ipv4=ipv4,
                ipv6=ipv6,
                mac=mac,
            )
        )

    return result


def get_primary_dns() -> str:
    """Return the primary DNS server for the active interface.

    Uses PowerShell as a fallback when psutil does not expose DNS
    information directly (which is the case on Windows).
    """
    try:
        from network.powershell import PowerShellError, run_ps

        script = (
            "Get-DnsClientServerAddress -AddressFamily IPv4 | "
            "Where-Object { $_.ServerAddresses } | "
            "Select-Object -First 1 -ExpandProperty ServerAddresses | "
            "Select-Object -First 1"
        )
        result = run_ps(script, timeout=10)
        dns = (result.stdout or "").strip()
        if dns:
            return dns
    except (PowerShellError, Exception) as exc:
        _log.debug("DNS lookup via PowerShell failed: %s", exc)

    return "—"


def get_default_gateway() -> str:
    """Return the default gateway IP address."""
    try:
        from network.powershell import PowerShellError, run_ps

        script = (
            "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | "
            "Select-Object -First 1 -ExpandProperty NextHop"
        )
        result = run_ps(script, timeout=10)
        gw = (result.stdout or "").strip()
        if gw:
            return gw
    except (PowerShellError, Exception) as exc:
        _log.debug("Gateway lookup via PowerShell failed: %s", exc)

    return "—"


def gather() -> LocalNetworkInfo:
    """Collect all local network information in one call.

    This is the main entry point for the dashboard. It aggregates
    hostname, local IP, connected adapter, and all adapter details.
    """
    hostname = get_hostname()
    local_ip = get_local_ip()
    connected = get_connected_adapter()
    adapters = get_all_adapters()

    _log.info(
        "Local info: hostname=%s ip=%s adapter=%s adapters=%d",
        hostname,
        local_ip,
        connected,
        len(adapters),
    )

    return LocalNetworkInfo(
        hostname=hostname,
        local_ip=local_ip,
        connected_adapter=connected,
        adapters=adapters,
    )
