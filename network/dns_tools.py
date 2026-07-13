"""
DNS management tools.

Provides functions to read, change, and flush DNS configuration on
Windows.  All operations use PowerShell or ``ipconfig``/``netsh`` and
are designed to be called from a background thread.

Functions
---------
- :func:`get_current_dns_servers` — list DNS servers for all adapters
- :func:`get_active_adapter_dns` — DNS for the primary connected adapter
- :func:`set_dns_servers` — set primary + secondary DNS on an adapter
- :func:`reset_dns_automatic` — revert an adapter to DHCP-assigned DNS
- :func:`flush_dns_cache` — ``ipconfig /flushdns``
- :func:`register_dns` — ``ipconfig /registerdns``
- :func:`clear_resolver_cache` — ``netsh int ip reset``
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from utils.logger import get_logger

_log = get_logger(__name__)


# --------------------------------------------------------------------- #
# DNS presets
# --------------------------------------------------------------------- #

@dataclass(frozen=True)
class DnsPreset:
    """A named DNS configuration with primary and optional secondary server."""

    name: str
    primary: str
    secondary: str = ""
    description: str = ""


#: Available DNS presets.
DNS_PRESETS: list[DnsPreset] = [
    DnsPreset(
        name="Automatic",
        primary="",
        secondary="",
        description="Use ISP-assigned DNS (DHCP)",
    ),
    DnsPreset(
        name="Cloudflare",
        primary="1.1.1.1",
        secondary="1.0.0.1",
        description="Fast, privacy-focused",
    ),
    DnsPreset(
        name="Google",
        primary="8.8.8.8",
        secondary="8.8.4.4",
        description="Google Public DNS",
    ),
    DnsPreset(
        name="Quad9",
        primary="9.9.9.9",
        secondary="149.112.112.112",
        description="Security-focused (malware blocking)",
    ),
    DnsPreset(
        name="OpenDNS",
        primary="208.67.222.222",
        secondary="208.67.220.220",
        description="Cisco Umbrella (content filtering)",
    ),
    DnsPreset(
        name="Shecan",
        primary="178.22.122.100",
        secondary="185.51.200.2",
        description="Iranian DNS resolver",
    ),
    DnsPreset(
        name="Electro",
        primary="78.157.42.100",
        secondary="78.157.42.101",
        description="Iranian DNS resolver",
    ),
]


# --------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------- #

@dataclass(frozen=True)
class AdapterDns:
    """DNS configuration for a single adapter."""

    adapter_name: str
    dns_servers: list[str] = field(default_factory=list)
    is_dhcp: bool = True


@dataclass(frozen=True)
class DnsOperationResult:
    """Result of a DNS change operation."""

    success: bool
    message: str
    adapter_name: str = ""


# --------------------------------------------------------------------- #
# Read DNS
# --------------------------------------------------------------------- #

def get_current_dns_servers() -> list[AdapterDns]:
    """Return DNS servers for every adapter that has one configured.

    Uses ``Get-DnsClientServerAddress`` via PowerShell.
    """
    try:
        from network.powershell import run_ps

        script = (
            "Get-DnsClientServerAddress -AddressFamily IPv4 | "
            "Where-Object { $_.ServerAddresses } | "
            "Select-Object InterfaceAlias, ServerAddresses | "
            "ConvertTo-Json -Depth 3"
        )
        result = run_ps(script, timeout=10)
        if not result.stdout:
            return []

        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]

        adapters: list[AdapterDns] = []
        for entry in data:
            name = entry.get("InterfaceAlias", "")
            servers = entry.get("ServerAddresses", [])
            if isinstance(servers, str):
                servers = [servers]
            if name and servers:
                adapters.append(AdapterDns(
                    adapter_name=name,
                    dns_servers=list(servers),
                    is_dhcp=False,
                ))
        return adapters

    except Exception as exc:
        _log.warning("Failed to read DNS servers: %s", exc)
        return []


def get_active_adapter_dns() -> AdapterDns:
    """Return the DNS configuration for the primary connected adapter.

    Identifies the adapter by matching the default gateway interface.
    """
    try:
        from network.powershell import run_ps

        # Get the interface alias of the adapter with the default route
        gw_script = (
            "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | "
            "Select-Object -First 1 -ExpandProperty InterfaceAlias"
        )
        gw_result = run_ps(gw_script, timeout=10)
        interface = (gw_result.stdout or "").strip()

        if not interface:
            # Fallback: first adapter with DNS
            all_dns = get_current_dns_servers()
            return all_dns[0] if all_dns else AdapterDns(adapter_name="—")

        # Get DNS for that interface
        dns_script = (
            f"Get-DnsClientServerAddress -InterfaceAlias '{interface}' "
            "-AddressFamily IPv4 | "
            "Select-Object -First 1 -ExpandProperty ServerAddresses | "
            "ConvertTo-Json"
        )
        dns_result = run_ps(dns_script, timeout=10)
        servers: list[str] = []
        if dns_result.stdout:
            raw = json.loads(dns_result.stdout)
            if isinstance(raw, str):
                servers = [raw]
            elif isinstance(raw, list):
                servers = raw

        return AdapterDns(
            adapter_name=interface,
            dns_servers=servers,
            is_dhcp=len(servers) == 0,
        )

    except Exception as exc:
        _log.warning("Failed to get active adapter DNS: %s", exc)
        return AdapterDns(adapter_name="—")


# --------------------------------------------------------------------- #
# Change DNS
# --------------------------------------------------------------------- #

def set_dns_servers(
    adapter_name: str,
    primary: str,
    secondary: str = "",
) -> DnsOperationResult:
    """Set DNS servers on the specified adapter.

    Parameters
    ----------
    adapter_name:
        Network adapter interface alias (e.g. "Wi-Fi", "Ethernet").
    primary:
        Primary DNS server IP.
    secondary:
        Optional secondary DNS server IP.
    """
    if not adapter_name or adapter_name == "—":
        return DnsOperationResult(
            success=False, message="No adapter selected.",
        )

    if not primary:
        return DnsOperationResult(
            success=False, message="Primary DNS server is required.",
        )

    # Validate IP format (basic check)
    import re
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    if not ip_pattern.match(primary.strip()):
        return DnsOperationResult(
            success=False, message=f"Invalid primary DNS IP: {primary}",
        )
    if secondary and not ip_pattern.match(secondary.strip()):
        return DnsOperationResult(
            success=False, message=f"Invalid secondary DNS IP: {secondary}",
        )

    try:
        from network.powershell import run_ps

        safe_name = adapter_name.replace("'", "''")
        safe_primary = primary.strip().replace("'", "''")
        safe_secondary = secondary.strip().replace("'", "''") if secondary else ""

        servers = f"'{safe_primary}'"
        if safe_secondary:
            servers = f"'{safe_primary}', '{safe_secondary}'"

        script = (
            f"Set-DnsClientServerAddress -InterfaceAlias '{safe_name}' "
            f"-ServerAddresses @({servers})"
        )
        run_ps(script, timeout=15)

        _log.info("DNS set on %s: %s %s", adapter_name, primary, secondary)
        return DnsOperationResult(
            success=True,
            message=f"DNS set to {primary}" + (f" / {secondary}" if secondary else ""),
            adapter_name=adapter_name,
        )

    except Exception as exc:
        _log.error("Failed to set DNS on %s: %s", adapter_name, exc)
        return DnsOperationResult(
            success=False,
            message=f"Failed to set DNS: {exc}",
            adapter_name=adapter_name,
        )


def reset_dns_automatic(adapter_name: str) -> DnsOperationResult:
    """Reset an adapter to automatically obtain DNS from DHCP.

    Parameters
    ----------
    adapter_name:
        Network adapter interface alias.
    """
    if not adapter_name or adapter_name == "—":
        return DnsOperationResult(
            success=False, message="No adapter selected.",
        )

    try:
        from network.powershell import run_ps

        safe_name = adapter_name.replace("'", "''")
        script = (
            f"Set-DnsClientServerAddress -InterfaceAlias '{safe_name}' "
            "-ResetServerAddresses"
        )
        run_ps(script, timeout=15)

        _log.info("DNS reset to automatic on %s", adapter_name)
        return DnsOperationResult(
            success=True,
            message="DNS reset to automatic (DHCP)",
            adapter_name=adapter_name,
        )

    except Exception as exc:
        _log.error("Failed to reset DNS on %s: %s", adapter_name, exc)
        return DnsOperationResult(
            success=False,
            message=f"Failed to reset DNS: {exc}",
            adapter_name=adapter_name,
        )


# --------------------------------------------------------------------- #
# Cache operations
# --------------------------------------------------------------------- #

def flush_dns_cache() -> DnsOperationResult:
    """Flush the DNS resolver cache (``ipconfig /flushdns``).

    This clears cached DNS entries so the next lookup goes to the server.
    """
    try:
        import subprocess
        import sys

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        proc = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=creationflags,
        )

        output = proc.stdout.strip()
        _log.info("Flush DNS: %s", output)
        return DnsOperationResult(
            success=proc.returncode == 0,
            message=output or "DNS cache flushed",
        )

    except Exception as exc:
        _log.error("Flush DNS failed: %s", exc)
        return DnsOperationResult(success=False, message=f"Flush failed: {exc}")


def register_dns() -> DnsOperationResult:
    """Register DNS records for all adapters (``ipconfig /registerdns``).

    This forces a re-registration of DNS names with the DNS server.
    """
    try:
        import subprocess
        import sys

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        proc = subprocess.run(
            ["ipconfig", "/registerdns"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            creationflags=creationflags,
        )

        output = proc.stdout.strip()
        _log.info("Register DNS: %s", output)
        return DnsOperationResult(
            success=proc.returncode == 0,
            message=output or "DNS registration initiated",
        )

    except Exception as exc:
        _log.error("Register DNS failed: %s", exc)
        return DnsOperationResult(success=False, message=f"Register failed: {exc}")


def reset_tcpip_stack() -> DnsOperationResult:
    """Reset the TCP/IP stack (``netsh int ip reset``).

    This is a destructive operation that rebuilds the TCP/IP configuration.
    **Requires administrator privileges.** A system restart may be needed.
    """
    try:
        from network.powershell import run_ps

        result = run_ps("netsh int ip reset", timeout=30)
        output = result.stdout.strip()
        _log.info("Clear resolver cache: %s", output)
        return DnsOperationResult(
            success=True,
            message="Network stack reset. A restart may be required.",
        )

    except Exception as exc:
        _log.error("Clear resolver cache failed: %s", exc)
        return DnsOperationResult(
            success=False, message=f"Reset failed: {exc}",
        )
