"""
Adapter management service.

Provides functions to list, enable, disable, and restart network
adapters.  All operations use PowerShell and are designed to be called
from a background thread.

Functions
---------
- :func:`list_adapters` — enumerate all adapters with full details
- :func:`get_adapter_detail` — single adapter with IP/DNS/gateway info
- :func:`enable_adapter` — enable a disabled adapter
- :func:`disable_adapter` — disable an enabled adapter
- :func:`restart_adapter` — disable then enable (restart cycle)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from utils.logger import get_logger

_log = get_logger(__name__)


# --------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------- #

@dataclass(frozen=True)
class AdapterDetail:
    """Full detail view of a single network adapter."""

    name: str
    description: str
    status: str
    enabled: bool
    category: str
    mac_address: str
    link_speed: str
    driver_version: str
    driver_provider: str
    ipv4_addresses: list[str] = field(default_factory=list)
    ipv6_addresses: list[str] = field(default_factory=list)
    default_gateways: list[str] = field(default_factory=list)
    dns_servers: list[str] = field(default_factory=list)
    mtu: int = 0
    if_index: int = 0


@dataclass(frozen=True)
class AdapterOperationResult:
    """Result of an enable/disable/restart operation."""

    success: bool
    message: str
    adapter_name: str = ""


# --------------------------------------------------------------------- #
# List adapters
# --------------------------------------------------------------------- #

def list_adapters() -> list[AdapterDetail]:
    """Return all network adapters with their current configuration.

    Uses ``Get-NetAdapter`` combined with ``Get-NetIPAddress`` and
    ``Get-DnsClientServerAddress`` for full details.
    """
    try:
        from network.powershell import run_ps

        script = (
            "Get-NetAdapter -IncludeHidden | "
            "Select-Object Name,InterfaceDescription,Status,MacAddress,"
            "LinkSpeed,DriverVersion,DriverProvider,ifIndex,"
            "AdminStatus,PhysicalAdapter,Virtual | "
            "ConvertTo-Json -Depth 3 -Compress"
        )
        result = run_ps(script, timeout=30)
        if not result.stdout:
            return []

        raw_adapters = json.loads(result.stdout)
        if isinstance(raw_adapters, dict):
            raw_adapters = [raw_adapters]

        adapters: list[AdapterDetail] = []
        for raw in raw_adapters:
            name = raw.get("Name", "")
            if not name:
                continue

            status = str(raw.get("Status") or "").strip()
            admin_status = str(raw.get("AdminStatus") or "").strip().lower()
            # AdminStatus can be int (1=Up, 2=Down) or string
            enabled = status.lower() == "up" or admin_status in {"up", "1"}

            # Determine category
            category = "Unknown"
            if raw.get("PhysicalAdapter"):
                category = "Physical"
            elif raw.get("Virtual"):
                category = "Virtual"

            # Get IP info for this adapter
            ipv4, ipv6, gateways, dns, mtu = _get_adapter_ip_info(name)

            adapters.append(AdapterDetail(
                name=name,
                description=raw.get("InterfaceDescription", ""),
                status=status,
                enabled=enabled,
                category=category,
                mac_address=raw.get("MacAddress", ""),
                link_speed=raw.get("LinkSpeed", ""),
                driver_version=raw.get("DriverVersion", ""),
                driver_provider=raw.get("DriverProvider", ""),
                ipv4_addresses=ipv4,
                ipv6_addresses=ipv6,
                default_gateways=gateways,
                dns_servers=dns,
                mtu=mtu,
                if_index=int(raw.get("ifIndex") or 0),
            ))

        _log.info("Listed %d adapters", len(adapters))
        return adapters

    except Exception as exc:
        _log.warning("Failed to list adapters: %s", exc)
        return []


def _get_adapter_ip_info(
    adapter_name: str,
) -> tuple[list[str], list[str], list[str], list[str], int]:
    """Get IP, gateway, DNS, and MTU for a specific adapter.

    Returns ``(ipv4, ipv6, gateways, dns, mtu)``.
    """
    ipv4: list[str] = []
    ipv6: list[str] = []
    gateways: list[str] = []
    dns: list[str] = []
    mtu = 0

    try:
        from network.powershell import run_ps

        safe_name = adapter_name.replace("'", "''")

        # IP addresses
        ip_script = (
            f"Get-NetIPAddress -InterfaceAlias '{safe_name}' "
            "-AddressFamily IPv4,IPv6 -ErrorAction SilentlyContinue | "
            "Select-Object IPAddress,AddressFamily | "
            "ConvertTo-Json -Depth 2 -Compress"
        )
        ip_result = run_ps(ip_script, timeout=10)
        if ip_result.stdout:
            ip_data = json.loads(ip_result.stdout)
            if isinstance(ip_data, dict):
                ip_data = [ip_data]
            for entry in ip_data:
                addr = entry.get("IPAddress", "")
                fam = entry.get("AddressFamily", "")
                if "IPv4" in str(fam):
                    ipv4.append(addr)
                elif "IPv6" in str(fam):
                    ipv6.append(addr)

        # Default gateway
        gw_script = (
            f"Get-NetRoute -InterfaceAlias '{safe_name}' "
            "-DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty NextHop"
        )
        gw_result = run_ps(gw_script, timeout=10)
        if gw_result.stdout:
            gateways = [g.strip() for g in gw_result.stdout.splitlines() if g.strip()]

        # DNS servers
        dns_script = (
            f"Get-DnsClientServerAddress -InterfaceAlias '{safe_name}' "
            "-AddressFamily IPv4 -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty ServerAddresses"
        )
        dns_result = run_ps(dns_script, timeout=10)
        if dns_result.stdout:
            dns = [d.strip() for d in dns_result.stdout.splitlines() if d.strip()]

        # MTU
        mtu_script = (
            f"(Get-NetAdapter -Name '{safe_name}' -ErrorAction SilentlyContinue).Mtu"
        )
        mtu_result = run_ps(mtu_script, timeout=10)
        if mtu_result.stdout:
            try:
                mtu = int(mtu_result.stdout.strip())
            except ValueError:
                pass

    except Exception as exc:
        _log.debug("IP info fetch failed for %s: %s", adapter_name, exc)

    return ipv4, ipv6, gateways, dns, mtu


# --------------------------------------------------------------------- #
# Get single adapter detail
# --------------------------------------------------------------------- #

def get_adapter_detail(adapter_name: str) -> Optional[AdapterDetail]:
    """Return full details for a single adapter by name."""
    adapters = list_adapters()
    for a in adapters:
        if a.name == adapter_name:
            return a
    return None


# --------------------------------------------------------------------- #
# Enable / Disable / Restart
# --------------------------------------------------------------------- #

def enable_adapter(adapter_name: str) -> AdapterOperationResult:
    """Enable a network adapter.

    Parameters
    ----------
    adapter_name:
        The adapter's friendly name (e.g. "Wi-Fi", "Ethernet").
    """
    if not adapter_name or adapter_name == "—":
        return AdapterOperationResult(success=False, message="No adapter specified.")

    try:
        from network.powershell import run_ps

        safe_name = adapter_name.replace("'", "''")
        script = f"Enable-NetAdapter -Name '{safe_name}' -Confirm:$false"
        run_ps(script, timeout=30)

        _log.info("Enabled adapter: %s", adapter_name)
        return AdapterOperationResult(
            success=True,
            message=f"Enabled {adapter_name}",
            adapter_name=adapter_name,
        )

    except Exception as exc:
        _log.error("Enable failed for %s: %s", adapter_name, exc)
        return AdapterOperationResult(
            success=False,
            message=f"Enable failed: {exc}",
            adapter_name=adapter_name,
        )


def disable_adapter(adapter_name: str) -> AdapterOperationResult:
    """Disable a network adapter.

    Parameters
    ----------
    adapter_name:
        The adapter's friendly name.
    """
    if not adapter_name or adapter_name == "—":
        return AdapterOperationResult(success=False, message="No adapter specified.")

    try:
        from network.powershell import run_ps

        safe_name = adapter_name.replace("'", "''")
        script = f"Disable-NetAdapter -Name '{safe_name}' -Confirm:$false"
        run_ps(script, timeout=30)

        _log.info("Disabled adapter: %s", adapter_name)
        return AdapterOperationResult(
            success=True,
            message=f"Disabled {adapter_name}",
            adapter_name=adapter_name,
        )

    except Exception as exc:
        _log.error("Disable failed for %s: %s", adapter_name, exc)
        return AdapterOperationResult(
            success=False,
            message=f"Disable failed: {exc}",
            adapter_name=adapter_name,
        )


def restart_adapter(adapter_name: str) -> AdapterOperationResult:
    """Restart a network adapter (disable then enable).

    Parameters
    ----------
    adapter_name:
        The adapter's friendly name.
    """
    if not adapter_name or adapter_name == "—":
        return AdapterOperationResult(success=False, message="No adapter specified.")

    # Disable first
    disable_result = disable_adapter(adapter_name)
    if not disable_result.success:
        return disable_result

    # Wait briefly for the adapter to settle
    import time
    time.sleep(2)

    # Enable
    enable_result = enable_adapter(adapter_name)
    if not enable_result.success:
        return AdapterOperationResult(
            success=False,
            message=f"Restart partially failed — disabled but could not re-enable: {enable_result.message}",
            adapter_name=adapter_name,
        )

    _log.info("Restarted adapter: %s", adapter_name)
    return AdapterOperationResult(
        success=True,
        message=f"Restarted {adapter_name}",
        adapter_name=adapter_name,
    )
