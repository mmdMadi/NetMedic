"""
Per-adapter IP diagnostics.

Where :mod:`~netmedic.network.scanner` answers "which adapters exist?",
this module answers "what IP / DNS / gateway does this one have?". The
queries are independent and best-effort so a failure to read DNS, say,
does not block reading IPv4 addresses.

All public methods accept an :class:`Adapter` and mutate it in place --
this keeps the call site in the UI layer short.
"""

from __future__ import annotations

from typing import Optional

from .adapter import Adapter
from .powershell import PowerShellError, PowerShellRunner
from utils.logger import get_logger

_log = get_logger(__name__)


class Diagnostics:
    """Populate the IP-level fields of an :class:`Adapter`.

    A single :class:`Diagnostics` instance holds a runner and a timeout
    policy; methods are stateless beyond that.
    """

    def __init__(
        self,
        *,
        runner: Optional[PowerShellRunner] = None,
        timeout: int = 30,
    ) -> None:
        self._runner = runner or PowerShellRunner(default_timeout=timeout)
        self._timeout = timeout

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def enrich(self, adapter: Adapter) -> Adapter:
        """Populate IP/DNS/gateway fields on ``adapter`` and return it.

        The adapter is mutated in place *and* returned so callers may
        chain. Failures are logged and silently ignored so the UI can
        still display whatever data was already present.
        """
        if adapter.name in {"—", ""}:
            return adapter
        ip_info = self._fetch_ip_configuration(adapter.name)
        if ip_info:
            adapter.ipv4_addresses = ip_info.get("ipv4", [])
            adapter.ipv6_addresses = ip_info.get("ipv6", [])
            adapter.default_gateways = ip_info.get("gateways", [])
            adapter.dns_servers = ip_info.get("dns", [])
            adapter.subnet_prefixes = ip_info.get("prefixes", [])
        return adapter

    # ------------------------------------------------------------------ #
    # PowerShell fragments
    # ------------------------------------------------------------------ #
    def _fetch_ip_configuration(self, adapter_name: str) -> dict[str, list[str]]:
        """Return ``{ipv4, ipv6, gateways, dns, prefixes}`` for an adapter.

        Uses ``Get-NetIPAddress`` and ``Get-DnsClientServerAddress`` so
        the data is reliable even when DHCP is in use. Each call is
        wrapped independently so a partial failure does not lose all
        information.
        """
        result: dict[str, list[str]] = {
            "ipv4": [],
            "ipv6": [],
            "gateways": [],
            "dns": [],
            "prefixes": [],
        }
        safe_name = adapter_name.replace("'", "''")

        # ---- Addresses & prefixes -------------------------------------- #
        addr_script = (
            f"Get-NetIPAddress -InterfaceAlias '{safe_name}' "
            "-ErrorAction SilentlyContinue | "
            "Select-Object IPAddress,PrefixLength,AddressFamily | "
            "ConvertTo-Json -Depth 2 -Compress"
        )
        try:
            rows = self._runner.run_json(addr_script, timeout=self._timeout)
        except PowerShellError as exc:
            _log.debug("NetIPAddress lookup failed for %s: %s", adapter_name, exc)
            rows = []

        for row in rows:
            ip = (row.get("IPAddress") or "").strip()
            if not ip:
                continue
            family = row.get("AddressFamily")
            prefix = row.get("PrefixLength")
            if family in {"IPv4", 2}:
                result["ipv4"].append(ip)
                if prefix is not None:
                    result["prefixes"].append(f"{ip}/{prefix}")
            elif family in {"IPv6", 23}:
                result["ipv6"].append(ip)

        # ---- Gateway --------------------------------------------------- #
        gw_script = (
            f"Get-NetRoute -InterfaceAlias '{safe_name}' "
            "-DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty NextHop -Unique | "
            "ConvertTo-Json -Compress"
        )
        try:
            gw_rows = self._runner.run_json(gw_script, timeout=self._timeout)
            # -ExpandProperty collapses to bare strings.
            result["gateways"] = _normalize_string_rows(gw_rows)
        except PowerShellError as exc:
            _log.debug("Gateway lookup failed for %s: %s", adapter_name, exc)

        # ---- DNS ------------------------------------------------------- #
        dns_script = (
            "Get-DnsClientServerAddress -InterfaceAlias '"
            + safe_name
            + "' -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty ServerAddresses | "
            "ConvertTo-Json -Compress"
        )
        try:
            dns_rows = self._runner.run_json(dns_script, timeout=self._timeout)
            result["dns"] = _normalize_string_rows(dns_rows)
        except PowerShellError as exc:
            _log.debug("DNS lookup failed for %s: %s", adapter_name, exc)

        return result


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def _normalize_string_rows(rows: object) -> list[str]:
    """Flatten the various JSON shapes ``-ExpandProperty`` emits.

    A single value becomes a string, multiple become a list, empty
    output becomes ``""``. We normalize all three to ``list[str]``.
    """
    if not rows:
        return []
    if isinstance(rows, str):
        stripped = rows.strip()
        return [stripped] if stripped else []
    if isinstance(rows, list):
        return [str(r).strip() for r in rows if str(r).strip()]
    return [str(rows).strip()]
