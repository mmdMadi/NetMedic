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

    Uses ``Get-NetAdapter`` combined with bulk ``Get-NetIPAddress``,
    ``Get-NetRoute``, ``Get-DnsClientServerAddress``, and MTU queries
    to minimize PowerShell round-trips.
    """
    try:
        from network.powershell import run_ps

        # 1. Get all adapters in one call
        adapter_script = (
            "Get-NetAdapter -IncludeHidden | "
            "Select-Object Name,InterfaceDescription,Status,MacAddress,"
            "LinkSpeed,DriverVersion,DriverProvider,ifIndex,"
            "AdminStatus,PhysicalAdapter,Virtual | "
            "ConvertTo-Json -Depth 3 -Compress"
        )
        result = run_ps(adapter_script, timeout=30)
        if not result.stdout:
            return []

        raw_adapters = json.loads(result.stdout)
        if isinstance(raw_adapters, dict):
            raw_adapters = [raw_adapters]

        # 2. Bulk fetch IP addresses for ALL adapters in one call
        ip_map = _bulk_fetch_ip_addresses()

        # 3. Bulk fetch default gateways for ALL adapters in one call
        gw_map = _bulk_fetch_gateways()

        # 4. Bulk fetch DNS servers for ALL adapters in one call
        dns_map = _bulk_fetch_dns()

        # 5. Bulk fetch MTU for ALL adapters in one call
        mtu_map = _bulk_fetch_mtu()

        adapters: list[AdapterDetail] = []
        for raw in raw_adapters:
            name = raw.get("Name", "")
            if not name:
                continue

            status = str(raw.get("Status") or "").strip()
            admin_status = str(raw.get("AdminStatus") or "").strip().lower()
            enabled = status.lower() == "up" or admin_status in {"up", "1"}

            category = "Unknown"
            if raw.get("PhysicalAdapter"):
                category = "Physical"
            elif raw.get("Virtual"):
                category = "Virtual"

            ipv4, ipv6 = ip_map.get(name, ([], []))
            gateways = gw_map.get(name, [])
            dns = dns_map.get(name, [])
            mtu = mtu_map.get(name, 0)

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


def _bulk_fetch_ip_addresses() -> dict[str, tuple[list[str], list[str]]]:
    """Fetch IPv4 and IPv6 addresses for all adapters in one PS call.

    Returns ``{adapter_name: (ipv4_list, ipv6_list)}``.
    """
    try:
        from network.powershell import run_ps

        script = (
            "Get-NetIPAddress -AddressFamily IPv4,IPv6 "
            "-ErrorAction SilentlyContinue | "
            "Select-Object InterfaceAlias,IPAddress,AddressFamily | "
            "ConvertTo-Json -Depth 2 -Compress"
        )
        result = run_ps(script, timeout=15)
        if not result.stdout:
            return {}

        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]

        ip_map: dict[str, tuple[list[str], list[str]]] = {}
        for entry in data:
            iface = entry.get("InterfaceAlias", "")
            addr = entry.get("IPAddress", "")
            fam = str(entry.get("AddressFamily", ""))
            if not iface or not addr:
                continue
            ipv4, ipv6 = ip_map.get(iface, ([], []))
            if "IPv4" in fam:
                ipv4.append(addr)
            elif "IPv6" in fam:
                ipv6.append(addr)
            ip_map[iface] = (ipv4, ipv6)
        return ip_map

    except Exception as exc:
        _log.debug("Bulk IP fetch failed: %s", exc)
        return {}


def _bulk_fetch_gateways() -> dict[str, list[str]]:
    """Fetch default gateways for all adapters in one PS call.

    Returns ``{adapter_name: [gateway_ip, ...]}``.
    """
    try:
        from network.powershell import run_ps

        script = (
            "Get-NetRoute -DestinationPrefix '0.0.0.0/0' "
            "-ErrorAction SilentlyContinue | "
            "Select-Object InterfaceAlias,NextHop | "
            "ConvertTo-Json -Depth 2 -Compress"
        )
        result = run_ps(script, timeout=15)
        if not result.stdout:
            return {}

        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]

        gw_map: dict[str, list[str]] = {}
        for entry in data:
            iface = entry.get("InterfaceAlias", "")
            hop = entry.get("NextHop", "")
            if iface and hop:
                gw_map.setdefault(iface, []).append(hop)
        return gw_map

    except Exception as exc:
        _log.debug("Bulk gateway fetch failed: %s", exc)
        return {}


def _bulk_fetch_dns() -> dict[str, list[str]]:
    """Fetch DNS servers for all adapters in one PS call.

    Returns ``{adapter_name: [dns_ip, ...]}``.
    """
    try:
        from network.powershell import run_ps

        script = (
            "Get-DnsClientServerAddress -AddressFamily IPv4 "
            "-ErrorAction SilentlyContinue | "
            "Where-Object { $_.ServerAddresses } | "
            "Select-Object InterfaceAlias,ServerAddresses | "
            "ConvertTo-Json -Depth 3"
        )
        result = run_ps(script, timeout=15)
        if not result.stdout:
            return {}

        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]

        dns_map: dict[str, list[str]] = {}
        for entry in data:
            iface = entry.get("InterfaceAlias", "")
            servers = entry.get("ServerAddresses", [])
            if isinstance(servers, str):
                servers = [servers]
            if iface and servers:
                dns_map[iface] = list(servers)
        return dns_map

    except Exception as exc:
        _log.debug("Bulk DNS fetch failed: %s", exc)
        return {}


def _bulk_fetch_mtu() -> dict[str, int]:
    """Fetch MTU for all adapters in one PS call.

    Returns ``{adapter_name: mtu}``.
    """
    try:
        from network.powershell import run_ps

        script = (
            "Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue | "
            "Select-Object Name,Mtu | "
            "ConvertTo-Json -Depth 2 -Compress"
        )
        result = run_ps(script, timeout=15)
        if not result.stdout:
            return {}

        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]

        mtu_map: dict[str, int] = {}
        for entry in data:
            name = entry.get("Name", "")
            mtu_val = entry.get("Mtu", 0)
            if name:
                try:
                    mtu_map[name] = int(mtu_val)
                except (TypeError, ValueError):
                    pass
        return mtu_map

    except Exception as exc:
        _log.debug("Bulk MTU fetch failed: %s", exc)
        return {}


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
