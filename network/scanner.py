"""
High-level adapter scanning.

:class:`AdapterScanner` orchestrates the PowerShell queries needed to
populate :class:`Adapter` objects, runs them through the
:class:`Categorizer`, and returns a :class:`ScanResult` containing both
the adapters and aggregate statistics.

Every PowerShell call is funneled through :class:`PowerShellRunner` so
timeouts and encoding are handled centrally. Any error is wrapped in a
:class:`ScanError` so the UI can display a friendly message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .adapter import Adapter, AdapterCategory
from .categorizer import Categorizer
from .powershell import PowerShellError, PowerShellRunner
from config import Config
from utils.logger import get_logger

_log = get_logger(__name__)


class ScanError(RuntimeError):
    """Raised when scanning cannot complete.

    The UI catches this, logs the detail, and shows a non-blocking toast
    rather than crashing.
    """


@dataclass(frozen=True)
class ScanStats:
    """Aggregate counts produced by a successful scan.

    Fields are computed from the final adapter list, so they are always
    consistent with what the table shows.
    """

    total: int = 0
    physical: int = 0
    virtual: int = 0
    vpn: int = 0
    ghost: int = 0
    disabled: int = 0
    connected: int = 0
    disconnected: int = 0
    unknown: int = 0

    @classmethod
    def from_adapters(cls, adapters: list[Adapter]) -> "ScanStats":
        """Compute statistics from a categorized adapter list."""
        counts: dict[AdapterCategory, int] = {c: 0 for c in AdapterCategory}
        connected = disconnected = 0
        for adapter in adapters:
            counts[adapter.category] = counts.get(adapter.category, 0) + 1
            if adapter.is_connected:
                connected += 1
            elif adapter.is_disconnected:
                disconnected += 1
        return cls(
            total=len(adapters),
            physical=counts[AdapterCategory.PHYSICAL],
            virtual=counts[AdapterCategory.VIRTUAL],
            vpn=counts[AdapterCategory.VPN],
            ghost=counts[AdapterCategory.GHOST],
            disabled=counts[AdapterCategory.DISABLED],
            connected=connected,
            disconnected=disconnected,
            unknown=counts[AdapterCategory.UNKNOWN],
        )


@dataclass
class ScanResult:
    """Output of a scan: the adapters plus derived statistics."""

    adapters: list[Adapter] = field(default_factory=list)
    stats: ScanStats = field(default_factory=ScanStats)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """``True`` when the scan completed without an error."""
        return self.error is None


class AdapterScanner:
    """Scan Windows network adapters via PowerShell.

    The scanner is constructed once (typically by the app) and may be
    invoked many times. Each :meth:`scan` call returns an immutable
    :class:`ScanResult`.
    """

    def __init__(
        self,
        config: Config,
        *,
        runner: Optional[PowerShellRunner] = None,
        categorizer: Optional[Categorizer] = None,
    ) -> None:
        self._config = config
        self._runner = runner or PowerShellRunner(
            default_timeout=config.scan_timeout
        )
        self._categorizer = categorizer or Categorizer()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def scan(self) -> ScanResult:
        """Run a full scan and return a :class:`ScanResult`.

        Failures are caught and returned as ``ScanResult.error`` rather
        than raised, so the UI layer can render either data or a friendly
        message without try/except scaffolding of its own.
        """
        try:
            raw_adapters = self._fetch_adapters()
            raw_pnp = self._fetch_pnp_index()
        except PowerShellError as exc:
            _log.error("PowerShell failure during scan: %s", exc)
            return ScanResult(error=f"PowerShell error: {exc}")
        except OSError as exc:
            _log.error("OS error during scan: %s", exc)
            return ScanResult(error=f"OS error: {exc}")

        adapters: list[Adapter] = []
        for raw in raw_adapters:
            adapter = Adapter.from_ps(raw)
            # Enrich with PnP / class data keyed by InterfaceGuid.
            self._merge_pnp(adapter, raw_pnp)
            # Honor the user's ignore list.
            if self._config.is_ignored(adapter.name):
                _log.debug("Ignoring adapter %r (config).", adapter.name)
                continue
            adapter.category = self._categorizer.categorize(adapter)
            adapters.append(adapter)

        stats = ScanStats.from_adapters(adapters)
        _log.info(
            "Scan complete: %d adapters (physical=%d vpn=%d virtual=%d ghost=%d).",
            stats.total,
            stats.physical,
            stats.vpn,
            stats.virtual,
            stats.ghost,
        )
        return ScanResult(adapters=adapters, stats=stats)

    # ------------------------------------------------------------------ #
    # PowerShell fragments
    # ------------------------------------------------------------------ #
    def _fetch_adapters(self) -> list[dict]:
        """Return the raw adapter rows from ``Get-NetAdapter``."""
        script = (
            "Get-NetAdapter -IncludeHidden | "
            "Select-Object Name,InterfaceDescription,ifIndex,InterfaceGuid,"
            "Status,MacAddress,LinkSpeed,MediaConnectionState,"
            "DriverVersion,DriverDate,DriverProvider,PnPDeviceID,Hidden,Physical,"
            "AdminStatus,PhysicalAdapter | "
            "ConvertTo-Json -Depth 3 -Compress"
        )
        return self._runner.run_json(script, timeout=self._config.scan_timeout)

    def _fetch_pnp_index(self) -> dict[str, dict]:
        """Build a ``{key: pnp_data}`` lookup for enrichment.

        Uses ``Get-PnpDevice`` plus the standalone
        ``Get-PnpDeviceProperty`` cmdlet (rather than the
        ``.GetDeviceProperties()`` instance method, which is not
        available on the standard CIM instance returned by
        ``Get-PnpDevice``). The whole call is best-effort: any failure
        is logged and an empty index is returned.
        """
        script = (
            "$devs = Get-PnpDevice -Class Net -PresentOnly -ErrorAction SilentlyContinue;"
            " $output = @();"
            " foreach ($d in $devs) {"
            "  $cg = $d | Get-PnpDeviceProperty "
            "-KeyName 'DEVPKEY_DeviceClass_ClassGuid' -ErrorAction SilentlyContinue;"
            "  $output += [pscustomobject]@{"
            "    FriendlyName = $d.FriendlyName;"
            "    InstanceId   = $d.InstanceId;"
            "    ClassGuid    = if ($cg) { $cg.Data } else { $null };"
            "    Status       = $d.Status;"
            "    Present      = $d.Present;"
            "  };"
            " }"
            " $output | Select-Object FriendlyName,InstanceId,ClassGuid,Status,Present "
            "| ConvertTo-Json -Depth 3 -Compress"
        )
        try:
            rows = self._runner.run_json(
                script, timeout=self._config.scan_timeout
            )
        except PowerShellError as exc:
            # PnP enrichment is best-effort: continue without it.
            _log.warning("PnP enrichment unavailable: %s", exc)
            return {}

        index: dict[str, dict] = {}
        for row in rows:
            friendly = (row.get("FriendlyName") or "").strip()
            instance = (row.get("InstanceId") or "").strip()
            class_guid = (row.get("ClassGuid") or "").strip()
            # Index by several keys so the merger can find matches even
            # when only one property overlaps with the adapter row.
            for key in (friendly, instance):
                if key:
                    index.setdefault(key.lower(), row)
            if class_guid:
                index.setdefault(class_guid.lower(), row)
        return index

    def _merge_pnp(self, adapter: Adapter, pnp_index: dict[str, dict]) -> None:
        """Populate ``pnp_device_id`` / ``class_guid`` from PnP data."""
        if not pnp_index:
            return
        keys = (
            adapter.interface_description.lower(),
            adapter.name.lower(),
            adapter.interface_guid.lower(),
        )
        for key in keys:
            row = pnp_index.get(key)
            if not row:
                continue
            if adapter.pnp_device_id in {"—", ""}:
                adapter.pnp_device_id = row.get("InstanceId") or adapter.pnp_device_id
            if adapter.class_guid in {"—", ""}:
                adapter.class_guid = row.get("ClassGuid") or adapter.class_guid
            # Hardware IDs require a second property fetch; keep it cheap
            # and only attempt when we are still missing them.
            if not adapter.hardware_ids:
                hw = self._fetch_hardware_ids(row.get("InstanceId"))
                if hw:
                    adapter.hardware_ids = hw
            break

    def _fetch_hardware_ids(self, instance_id: str) -> list[str]:
        """Return the list of hardware IDs for a PnP instance, best-effort."""
        if not instance_id:
            return []
        script = (
            "$d = Get-PnpDeviceProperty -InstanceId 'INSTANCE' "
            "-KeyName DEVPKEY_Device_HardwareIds -ErrorAction SilentlyContinue;"
            "if ($d) { $d.Data }"
        ).replace("INSTANCE", instance_id.replace("'", "''"))
        try:
            result = self._runner.run(script, timeout=self._config.scan_timeout)
        except PowerShellError as exc:
            _log.debug("Hardware IDs lookup failed for %s: %s", instance_id, exc)
            return []
        if not result.stdout:
            return []
        # Hardware IDs come back newline-delimited.
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
