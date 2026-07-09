"""
NetMedic application entry point.

This module wires together every layer of NetMedic:

- :mod:`netmedic.utils` -- logging, storage, admin detection, helpers.
- :mod:`netmedic.network` -- PowerShell wrappers, adapter model,
  categorizer, scanner, diagnostics, exporter.
- :mod:`netmedic.ui` -- Textual widgets and modal dialogs.

The :class:`NetMedicApp` Textual ``App`` owns long-lived services (the
scanner, the diagnostics engine, the exporter) and exposes the
keyboard shortcuts that drive the UI. The app **never** performs a
destructive operation without an explicit confirmation dialog.

Run from the project root::

    python app.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Header

# Ensure the project root is importable when run directly as a script
# (``python app.py``) so ``import config`` / ``from utils import ...`` work.
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import config as config_module  # noqa: E402
from config import Config  # noqa: E402
from network.adapter import Adapter  # noqa: E402
from network.diagnostics import Diagnostics  # noqa: E402
from network.export import ExportFormat, Exporter  # noqa: E402
from network.health import compute_health  # noqa: E402
from network.internet import check_internet_with_latency  # noqa: E402
from network.local_info import (  # noqa: E402
    get_default_gateway,
    get_local_ip,
    get_connected_adapter,
    get_dns_display,
)
from network.public_info import get_public_ipv4, get_isp_info  # noqa: E402
from network.scanner import AdapterScanner, ScanResult  # noqa: E402
from ui.adapter_table import AdapterTable, FilterKey  # noqa: E402
from ui.actions_bar import ActionsBar  # noqa: E402
from ui.dashboard import Dashboard  # noqa: E402
from ui.details import DetailsPanel  # noqa: E402
from ui.dialogs import (  # noqa: E402
    ConfirmDialog,
    ConfirmResult,
    BulkRemoveConfirmDialog,
    ErrorDialog,
    ExportDialog,
    FilterDialog,
    RemoveConfirmDialog,
)
from ui.status import StatusBar, StatusState  # noqa: E402
from utils.admin import get_elevation_info  # noqa: E402
from utils.logger import LogManager, get_logger  # noqa: E402
from utils.storage import Storage  # noqa: E402

_log = get_logger("app")

#: Footer-friendly summary of every keyboard shortcut. Kept here so the
#: ``README`` can reference the same source of truth.
KEYBOARD_SHORTCUTS: tuple[tuple[str, str], ...] = (
    ("R", "Scan adapters"),
    ("F", "Filter"),
    ("Space", "Select / deselect row"),
    ("Ctrl+A", "Select all (visible)"),
    ("Ctrl+D", "Deselect all"),
    ("Enter", "Open details"),
    ("E", "Export (CSV / JSON / TXT)"),
    ("I", "Ignore selected adapter"),
    ("D", "Disable selected adapter (admin)"),
    ("X", "Remove selected adapter (admin, double-confirm)"),
    ("?", "Show shortcuts"),
    ("Q", "Quit"),
)


class NetMedicApp(App):
    """Top-level Textual application for NetMedic.

    A single instance is constructed in :func:`main` and runs until the
    user quits. Long-running PowerShell work is dispatched to a worker
    thread so the UI remains responsive (and the spinner animates).
    """

    CSS_PATH = "theme.tcss"
    TITLE = "NetMedic"
    SUB_TITLE = "Windows Network Diagnostics & Repair Toolkit"

    BINDINGS = [
        Binding("r", "scan", "Scan"),
        Binding("f", "filter", "Filter"),
        Binding("e", "export", "Export"),
        Binding("i", "ignore", "Ignore"),
        Binding("d", "disable", "Disable"),
        Binding("x", "remove", "Remove"),
        Binding("question", "shortcuts", "Help"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+a", "select_all", "Select All", show=False),
        Binding("ctrl+d", "deselect", "Deselect", show=False),
    ]

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    def __init__(self) -> None:
        super().__init__()
        self._storage = Storage()
        self._config: Config = Config.from_storage(self._storage)
        # Configure logging using the freshly-loaded config.
        LogManager.setup(
            self._storage.logs_dir,
            enable=self._config.logging,
        )
        self._scanner = AdapterScanner(self._config)
        self._diagnostics = Diagnostics(timeout=max(10, self._config.scan_timeout))
        self._last_result: Optional[ScanResult] = None

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        """Lay out the full screen: header, dashboard, table+details, status."""
        yield Header(show_clock=False)
        yield Dashboard()
        yield ActionsBar()
        with Horizontal(id="main"):
            yield AdapterTable()
            yield DetailsPanel()
        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        """Wire widgets together and perform an initial scan."""
        _log.info("NetMedic starting (config=%s).", self._config.to_json())
        table = self.query_one(AdapterTable)
        table.set_enter_callback(self._open_details)
        self.query_one(Dashboard).refresh_elevation()
        # Kick off the first scan automatically so the user sees data.
        self.action_scan()
        # Fetch dashboard intelligence in parallel background workers.
        self._fetch_internet_status()
        self._fetch_local_ip()
        self._fetch_public_ip()
        self._fetch_connected_adapter()
        self._fetch_dns()
        self._fetch_health_score()

    def on_button_pressed(self, event) -> None:
        """Dispatch top-level toolbar button clicks to actions."""
        button_id = getattr(event.button, "id", "")
        parent = getattr(event.button, "parent", None)
        if getattr(parent, "id", None) != "actions-bar":
            return
        mapping = {
            "scan": self.action_scan,
            "filter": self.action_filter,
            "export": self.action_export,
            "ignore": self.action_ignore,
            "disable": self.action_disable,
            "remove": self.action_remove,
        }
        action = mapping.get(button_id)
        if action:
            action()

    # ------------------------------------------------------------------ #
    # Actions (keyboard shortcuts)
    # ------------------------------------------------------------------ #
    def action_scan(self) -> None:
        """Run an adapter scan in a background worker thread."""
        self._set_status(StatusState.SCANNING, "Scanning adapters…")
        self._scan_worker()

    def action_filter(self) -> None:
        """Open the filter dialog and apply the selection."""
        table = self.query_one(AdapterTable)
        self.push_screen(FilterDialog(current=table.get_filter()), self._apply_filter)

    def action_export(self) -> None:
        """Open the export dialog and write the chosen format."""
        if not self._has_data():
            self._set_status(
                StatusState.ERROR, "Nothing to export — press R to scan first."
            )
            return
        self.push_screen(ExportDialog(), self._do_export)

    def action_ignore(self) -> None:
        """Add the selected adapter to the ignore list (persists config)."""
        table = self.query_one(AdapterTable)
        selected = table.get_selected() or ([table.get_current_adapter()] if table.get_current_adapter() else [])
        if not selected:
            self._set_status(StatusState.IDLE, "Select an adapter to ignore first.")
            return
        names = ", ".join(a.name for a in selected)
        self.push_screen(
            ConfirmDialog(
                title="Ignore adapter(s)?",
                body=(
                    f"Ignoring will hide {names} from future scans and is "
                    "fully reversible (edit config.json).\n\nContinue?"
                ),
            ),
            lambda r: self._after_ignore_confirm(r, selected),
        )

    def action_disable(self) -> None:
        """Open a confirmation dialog before disabling the selected adapter."""
        table = self.query_one(AdapterTable)
        selected = table.get_selected() or ([table.get_current_adapter()] if table.get_current_adapter() else [])
        if not selected:
            self._set_status(StatusState.IDLE, "Select an adapter to disable first.")
            return
        info = get_elevation_info()
        if not info.is_admin:
            self.push_screen(
                ErrorDialog(
                    title="Administrator required",
                    body=(
                        "Disabling an adapter needs elevation.\n"
                        f"{info.detail}\n\n"
                        "Please restart NetMedic as Administrator."
                    ),
                )
            )
            return
        names = ", ".join(a.name for a in selected)
        self.push_screen(
            ConfirmDialog(
                title="Disable adapter(s)?",
                body=(
                    "You are about to disable:\n"
                    f"    {names}\n\n"
                    "This will drop its network connectivity until manually "
                    "re-enabled. NetMedic will NOT remove the device.\n\n"
                    "Continue?"
                ),
            ),
            self._after_disable_confirm,
        )

    def action_remove(self) -> None:
        """Open a double-confirmation dialog before removing the selected adapter.

        Removal calls ``pnputil /remove-device`` which uninstalls the
        adapter from Windows. This is irreversible without reinstalling
        the driver, so the dialog forces the user to type the adapter
        name to prove intent.
        """
        table = self.query_one(AdapterTable)
        selected = table.get_selected() or ([table.get_current_adapter()] if table.get_current_adapter() else [])
        if not selected:
            self._set_status(StatusState.IDLE, "Select an adapter to remove first.")
            return
        info = get_elevation_info()
        if not info.is_admin:
            self.push_screen(
                ErrorDialog(
                    title="Administrator required",
                    body=(
                        "Removing an adapter needs elevation.\n"
                        f"{info.detail}\n\n"
                        "Please restart NetMedic as Administrator."
                    ),
                )
            )
            return
        if len(selected) == 1:
            adapter = selected[0]
            self.push_screen(
                RemoveConfirmDialog(adapter_name=adapter.name),
                lambda r: self._after_remove_confirm(r, adapter),
            )
            return
        names = [a.name for a in selected]
        self.push_screen(
            BulkRemoveConfirmDialog(adapter_names=names),
            lambda r: self._after_bulk_remove_confirm(r, selected),
        )

    def action_select_all(self) -> None:
        """Select every visible adapter row."""
        self.query_one(AdapterTable).select_all()
        self._set_status(StatusState.IDLE, "Selected all visible adapters.")

    def action_deselect(self) -> None:
        """Clear all adapter selections."""
        self.query_one(AdapterTable).deselect_all()
        self._set_status(StatusState.IDLE, "Selection cleared.")

    def action_shortcuts(self) -> None:
        """Show a modal listing all keyboard shortcuts."""
        lines = ["NetMedic — Keyboard Shortcuts", "=" * 40, ""]
        for key, desc in KEYBOARD_SHORTCUTS:
            lines.append(f"  {key:<10} {desc}")
        self.push_screen(ErrorDialog(title="Keyboard Shortcuts", body="\n".join(lines)))

    # ------------------------------------------------------------------ #
    # Background work
    # ------------------------------------------------------------------ #
    @work(thread=True)
    def _scan_worker(self) -> None:
        """Run the scanner off the UI thread and apply the result.

        Workers run on a background thread, so we must not touch widgets
        directly from here -- use :meth:`call_from_thread`.
        """
        try:
            result = self._scanner.scan()
        except Exception as exc:  # noqa: BLE001 -- never crash the UI
            _log.exception("Scan failed")
            self.call_from_thread(self._show_error, "Scan failed", str(exc))
            return
        self.call_from_thread(self._apply_scan_result, result)

    # ------------------------------------------------------------------ #
    # Dashboard data workers
    # ------------------------------------------------------------------ #
    @work(thread=True)
    def _fetch_internet_status(self) -> None:
        """Check internet connectivity and update the dashboard card."""
        try:
            result = check_internet_with_latency()
            status = result.status
            latency = result.latency_ms
        except Exception as exc:  # noqa: BLE001
            _log.warning("Internet check failed: %s", exc)
            from network.internet import InternetStatus
            status = InternetStatus.CHECK_FAILED
            latency = None
        self.call_from_thread(
            self.query_one(Dashboard).update_internet_status, status, latency
        )
        # Recompute health after internet check completes.
        self._recompute_health()

    @work(thread=True)
    def _fetch_local_ip(self) -> None:
        """Read the local IP and update the dashboard card."""
        try:
            ip = get_local_ip()
        except Exception as exc:  # noqa: BLE001
            _log.warning("Local IP fetch failed: %s", exc)
            ip = "—"
        self.call_from_thread(
            self.query_one(Dashboard).update_local_ip, ip
        )

    @work(thread=True)
    def _fetch_public_ip(self) -> None:
        """Fetch the public IP and ISP info, update the dashboard card."""
        try:
            ip = get_public_ipv4()
            isp_data = get_isp_info()
            isp = isp_data.get("isp", "")
            country = isp_data.get("country", "")
        except Exception as exc:  # noqa: BLE001
            _log.warning("Public IP fetch failed: %s", exc)
            ip = "—"
            isp = ""
            country = ""
        self.call_from_thread(
            self.query_one(Dashboard).update_public_ip, ip, isp, country
        )

    @work(thread=True)
    def _fetch_connected_adapter(self) -> None:
        """Detect the connected adapter and update the dashboard card."""
        try:
            name = get_connected_adapter()
        except Exception as exc:  # noqa: BLE001
            _log.warning("Connected adapter fetch failed: %s", exc)
            name = "—"
        self.call_from_thread(
            self.query_one(Dashboard).update_connected_adapter, name
        )

    @work(thread=True)
    def _fetch_dns(self) -> None:
        """Read the DNS server with provider name and update the dashboard card."""
        try:
            dns = get_dns_display()
        except Exception as exc:  # noqa: BLE001
            _log.warning("DNS fetch failed: %s", exc)
            dns = "—"
        self.call_from_thread(
            self.query_one(Dashboard).update_dns, dns
        )

    @work(thread=True)
    def _fetch_health_score(self) -> None:
        """Compute the health score and update the dashboard."""
        self._recompute_health()

    def _recompute_health(self) -> None:
        """Recompute health score from the latest available signals.

        Called after any individual check completes. Reads the current
        dashboard card values to build the score. Runs on a background
        thread.
        """
        try:
            dashboard = self.query_one(Dashboard)

            # Read current card values for the health computation.
            from network.internet import InternetStatus
            internet_status = InternetStatus.CHECK_FAILED
            try:
                status_text = dashboard._card_status._value
                for member in InternetStatus:
                    if member.value in status_text:
                        internet_status = member
                        break
            except Exception:
                pass

            gateway = get_default_gateway()
            adapter_connected = get_connected_adapter() != "—"

            score = compute_health(
                internet_status=internet_status,
                gateway=gateway,
                adapter_connected=adapter_connected,
            )
            self.call_from_thread(dashboard.update_health_score, score)
        except Exception as exc:  # noqa: BLE001
            _log.warning("Health score computation failed: %s", exc)

    @work(thread=True)
    def _diagnostics_worker(self, adapter: Adapter) -> None:
        """Enrich a single adapter with IP/DNS/gateway data."""
        try:
            enriched = self._diagnostics.enrich(adapter)
        except Exception as exc:  # noqa: BLE001
            _log.warning("Diagnostics failed for %s: %s", adapter.name, exc)
            enriched = adapter
        self.call_from_thread(self._show_details, enriched)

    @work(thread=True)
    def _disable_worker(self, adapter_name: str) -> None:
        """Invoke ``Disable-NetAdapter`` for ``adapter_name``."""
        # Imported lazily to avoid pulling PowerShell into dialogs that
        # may be shown on non-Windows hosts during demos.
        from network.powershell import PowerShellError, run_ps

        safe_name = adapter_name.replace("'", "''")
        script = (
            f"Disable-NetAdapter -Name '{safe_name}' -Confirm:$false"
        )
        try:
            run_ps(script, timeout=30)
            self.call_from_thread(
                self._set_status,
                StatusState.IDLE,
                f"Disabled {adapter_name}.",
            )
            self.call_from_thread(self.action_scan)
        except PowerShellError as exc:
            _log.error("Disable failed for %s: %s", adapter_name, exc)
            self.call_from_thread(self._show_error, "Disable failed", str(exc))

    @work(thread=True)
    def _remove_worker(self, instance_id: str, adapter_name: str) -> None:
        """Invoke ``pnputil /remove-device`` to uninstall an adapter.

        ``instance_id`` is the PNP Device ID obtained from the adapter
        details. If the adapter has no instance ID the worker falls back
        to ``Get-PnpDevice`` to resolve it by name.
        """
        from network.powershell import PowerShellError, run_ps

        _log.info("Remove worker started for %s (id=%s).", adapter_name, instance_id)
        resolved_id = self._resolve_instance_id(instance_id, adapter_name)
        if not resolved_id:
            _log.warning("Could not resolve instance ID for %s.", adapter_name)
            self.call_from_thread(
                self._show_error,
                "Remove failed",
                f"Could not find a PNP Instance ID for \"{adapter_name}\".\n"
                "The adapter may already have been removed.",
            )
            return

        _log.info("Resolved instance ID: %s", resolved_id)
        safe_id = resolved_id.replace("'", "''")
        script = (
            f"Start-Process -FilePath 'pnputil.exe' "
            f"-ArgumentList @('/remove-device', '{safe_id}') "
            f"-Wait -NoNewWindow"
        )
        try:
            _log.info("Running PowerShell: %s", script)
            run_ps(script, timeout=30)
            _log.info("PowerShell succeeded for %s.", adapter_name)
            self.call_from_thread(
                self._show_remove_result,
                adapter_name,
                True,
                "",
            )
            self.call_from_thread(self.action_scan)
        except PowerShellError as exc:
            _log.error("Remove failed for %s: %s", adapter_name, exc)
            self.call_from_thread(
                self._show_remove_result,
                adapter_name,
                False,
                str(exc),
            )

    @staticmethod
    def _resolve_instance_id(instance_id: str, adapter_name: str) -> str:
        """Return a usable PNP Instance ID, querying PowerShell if needed.

        If ``instance_id`` is a placeholder (``"—"``) the method falls
        back to a ``Get-PnpDevice`` lookup by friendly name.
        """
        if instance_id and instance_id.strip() not in {"—", ""}:
            return instance_id.strip()
        # Best-effort: ask PowerShell to resolve by name. We try the
        # PnP device lists first, then CIM's Win32_NetworkAdapter table,
        # which often exposes the exact PNPDeviceID we need.
        from network.powershell import PowerShellError, run_ps

        safe_name = adapter_name.replace("'", "''")
        lookup_scripts = [
            (
                f"Get-PnpDevice -Class Net -PresentOnly -ErrorAction SilentlyContinue | "
                f"Where-Object {{ $_.FriendlyName -eq '{safe_name}' -or $_.FriendlyName -like '*{safe_name}*' }} | "
                f"Select-Object -First 1 -ExpandProperty InstanceId"
            ),
            (
                f"Get-PnpDevice -Class Net -ErrorAction SilentlyContinue | "
                f"Where-Object {{ $_.FriendlyName -eq '{safe_name}' -or $_.FriendlyName -like '*{safe_name}*' }} | "
                f"Select-Object -First 1 -ExpandProperty InstanceId"
            ),
            (
                f"Get-PnpDevice -Class Net -ErrorAction SilentlyContinue | "
                f"Where-Object {{ $_.InstanceId -like '*{safe_name}*' -or $_.FriendlyName -like '*{safe_name}*' }} | "
                f"Select-Object -First 1 -ExpandProperty InstanceId"
            ),
            (
                f"Get-CimInstance Win32_NetworkAdapter -ErrorAction SilentlyContinue | "
                f"Where-Object {{ $_.NetConnectionID -eq '{safe_name}' -or $_.Name -like '*{safe_name}*' }} | "
                f"Select-Object -First 1 -ExpandProperty PNPDeviceID"
            ),
            (
                f"Get-CimInstance Win32_NetworkAdapter -ErrorAction SilentlyContinue | "
                f"Where-Object {{ $_.NetConnectionID -like '*{safe_name}*' -or $_.Name -like '*{safe_name}*' }} | "
                f"Select-Object -First 1 -ExpandProperty PNPDeviceID"
            ),
        ]
        for script in lookup_scripts:
            try:
                result = run_ps(script, timeout=15)
            except PowerShellError:
                continue
            resolved = (result.stdout or "").strip()
            if resolved:
                return resolved
        return ""

    @work(thread=True)
    def _export_worker(self, fmt: ExportFormat) -> None:
        """Write the current result set to disk in ``fmt``."""
        if not self._last_result:
            return
        self.call_from_thread(
            self._set_status, StatusState.EXPORTING, f"Exporting {fmt.value.upper()}…"
        )
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self._storage.base_dir / "exports" / f"netmedic-{stamp}.{fmt.value}"
        try:
            Exporter(fmt).export(
                self._last_result.adapters,
                target,
                stats=self._last_result.stats,
            )
        except Exception as exc:  # noqa: BLE001
            _log.exception("Export failed")
            self.call_from_thread(self._show_error, "Export failed", str(exc))
            return
        self.call_from_thread(
            self._set_status,
            StatusState.IDLE,
            f"Exported {len(self._last_result.adapters)} adapters → {target.name}",
        )

    # ------------------------------------------------------------------ #
    # Callbacks (run on the UI thread)
    # ------------------------------------------------------------------ #
    def _apply_scan_result(self, result: ScanResult) -> None:
        """Push a fresh scan into the table and dashboard widgets."""
        self._last_result = result
        if result.error:
            self._show_error("Scan failed", result.error)
            return
        table = self.query_one(AdapterTable)
        table.set_adapters(result.adapters)
        self.query_one(Dashboard).update_stats(result.stats)
        self._set_status(
            StatusState.IDLE,
            f"Scan complete — {result.stats.total} adapters found.",
        )

    def _apply_filter(self, key: Optional[FilterKey]) -> None:
        """Apply the filter chosen in :class:`FilterDialog`."""
        if key is None:
            return
        self.query_one(AdapterTable).set_filter(key)
        self._set_status(StatusState.IDLE, f"Filter applied: {key.value}")

    def _do_export(self, fmt: Optional[ExportFormat]) -> None:
        """Dispatch the export after the user picked a format."""
        if fmt is None:
            return
        self._export_worker(fmt)

    def _after_ignore_confirm(
        self, result: ConfirmResult, adapters: list[Adapter]
    ) -> None:
        """Persist ignored adapter names when the user confirmed."""
        if not result.confirmed:
            self._set_status(StatusState.IDLE, "Ignore cancelled.")
            return
        for adapter in adapters:
            self._config.ignore(adapter.name)
        if self._config.save(self._storage):
            self._set_status(
                StatusState.IDLE,
                f"Ignored {len(adapters)} adapter(s). Re-scan to refresh.",
            )
            self.action_scan()
        else:
            self._show_error("Config error", "Could not write config.json.")

    def _after_disable_confirm(self, result: ConfirmResult) -> None:
        """Trigger the disable worker once the user has confirmed."""
        if not result.confirmed:
            self._set_status(StatusState.IDLE, "Disable cancelled.")
            return
        table = self.query_one(AdapterTable)
        selected = table.get_selected()
        if not selected:
            return
        # NetMedic disables adapters one-by-one so a partial failure is
        # visible to the user and reverts cleanly.
        for adapter in selected:
            self._disable_worker(adapter.name)

    def _after_remove_confirm(
        self, result: ConfirmResult, adapter: Adapter
    ) -> None:
        """Trigger the remove worker once the user has double-confirmed."""
        if not result.confirmed:
            self._set_status(StatusState.IDLE, "Remove cancelled.")
            return
        _log.info("Remove confirmed for %s, launching worker.", adapter.name)
        self._set_status(
            StatusState.WORKING,
            f"Removing {adapter.name}… (this may take a moment)",
        )
        self._remove_worker(adapter.pnp_device_id, adapter.name)

    def _after_bulk_remove_confirm(
        self, result: ConfirmResult, adapters: list[Adapter]
    ) -> None:
        """Trigger a bulk remove pass after the user confirmed the list."""
        if not result.confirmed:
            self._set_status(StatusState.IDLE, "Remove cancelled.")
            return
        names = ", ".join(adapter.name for adapter in adapters)
        self._set_status(
            StatusState.WORKING,
            f"Removing {len(adapters)} adapters… {names}",
        )
        self._bulk_remove_worker(
            [(adapter.pnp_device_id, adapter.name) for adapter in adapters]
        )

    def _open_details(self, adapter: Adapter) -> None:
        """Show basic details immediately, then enrich with diagnostics."""
        self.query_one(DetailsPanel).show(adapter)
        self._set_status(StatusState.WORKING, f"Reading {adapter.name} details…")
        self._diagnostics_worker(adapter)

    def _show_details(self, adapter: Adapter) -> None:
        """Re-render the details panel with enriched IP data."""
        self.query_one(DetailsPanel).show(adapter)
        self._set_status(StatusState.IDLE, f"Details loaded for {adapter.name}.")

    def _show_remove_result(
        self, adapter_name: str, success: bool, error_msg: str
    ) -> None:
        """Show a dialog reporting whether adapter removal succeeded."""
        _log.info("Showing remove result: success=%s, adapter=%s", success, adapter_name)
        if success:
            self._set_status(
                StatusState.IDLE,
                f"Removed {adapter_name}.",
            )
            self.push_screen(
                ErrorDialog(
                    title="Adapter Removed",
                    body=(
                        f"Successfully removed adapter:\n"
                        f"    {adapter_name}\n\n"
                        "The adapter has been uninstalled from Windows. "
                        "The list will refresh."
                    ),
                )
            )
            self.action_scan()
        else:
            self._set_status(StatusState.ERROR, "Remove failed.")
            self.push_screen(
                ErrorDialog(
                    title="Remove Failed",
                    body=(
                        f"Failed to remove adapter:\n"
                        f"    {adapter_name}\n\n"
                        f"Error: {error_msg}"
                    ),
                )
            )

    @work(thread=True)
    def _bulk_remove_worker(self, items: list[tuple[str, str]]) -> None:
        """Remove adapters one at a time and report a combined result."""
        from network.powershell import PowerShellError, run_ps

        results: list[tuple[str, bool, str]] = []
        for instance_id, adapter_name in items:
            resolved_id = self._resolve_instance_id(instance_id, adapter_name)
            if not resolved_id:
                results.append(
                    (
                        adapter_name,
                        False,
                        "Could not resolve a PNP Instance ID.",
                    )
                )
                continue
            safe_id = resolved_id.replace("'", "''")
            script = (
                f"Start-Process -FilePath 'pnputil.exe' "
                f"-ArgumentList @('/remove-device', '{safe_id}') "
                f"-Wait -NoNewWindow"
            )
            try:
                run_ps(script, timeout=30)
                results.append((adapter_name, True, ""))
            except PowerShellError as exc:
                results.append((adapter_name, False, str(exc)))

        self.call_from_thread(self._show_bulk_remove_result, results)

    def _show_bulk_remove_result(
        self, results: list[tuple[str, bool, str]]
    ) -> None:
        """Display a summary after bulk removal completes."""
        removed = [name for name, success, _ in results if success]
        failed = [(name, error) for name, success, error in results if not success]
        if failed:
            lines = ["Some adapters could not be removed:", ""]
            for name, error in failed:
                lines.append(f"- {name}: {error}")
            if removed:
                lines.append("")
                lines.append("Removed successfully:")
                lines.extend(f"- {name}" for name in removed)
            self._set_status(
                StatusState.ERROR if removed == [] else StatusState.IDLE,
                f"Removed {len(removed)}/{len(results)} adapters.",
            )
            self.push_screen(
                ErrorDialog(
                    title="Bulk Remove Result",
                    body="\n".join(lines),
                )
            )
        else:
            self._set_status(
                StatusState.IDLE,
                f"Removed {len(removed)} adapter(s).",
            )
            self.push_screen(
                ErrorDialog(
                    title="Adapters Removed",
                    body=(
                        "Successfully removed:\n\n"
                        + "\n".join(f"- {name}" for name in removed)
                    ),
                )
            )
        self.action_scan()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_status(self, state: StatusState, message: str) -> None:
        """Update the status bar (safe to call from any thread)."""
        try:
            self.query_one(StatusBar).set_state(state, message)
        except Exception:  # noqa: BLE001 -- pre-mount
            _log.debug("status update before mount: %s / %s", state, message)

    def _show_error(self, title: str, body: str) -> None:
        """Log and present a friendly error dialog."""
        _log.error("%s: %s", title, body)
        self._set_status(StatusState.ERROR, title)
        self.push_screen(ErrorDialog(title=title, body=body))

    def _has_data(self) -> bool:
        """Return ``True`` when there is at least one scanned adapter."""
        return bool(self._last_result and self._last_result.adapters)


# --------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------- #
def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line flags.

    Currently supports ``--version`` (print and exit) and ``--no-scan``
    (skip the automatic scan on startup). Designed to grow with new
    flags without touching :func:`main`.
    """
    parser = argparse.ArgumentParser(
        prog="netmedic",
        description="NetMedic — Windows Network Adapter Manager (TUI).",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the NetMedic version and exit.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Application entry point.

    Returns the process exit code. Never raises -- every failure is
    logged and reported as a non-zero status.
    """
    args = _parse_args(argv)
    if args.version:
        import __init__ as pkg  # type: ignore

        print(f"NetMedic {pkg.__version__}")
        return 0
    try:
        app = NetMedicApp()
        app.run()
    except KeyboardInterrupt:
        _log.info("Interrupted by user.")
        return 130
    except Exception as exc:  # noqa: BLE001 -- last line of defense
        _log.exception("Fatal error")
        print(f"NetMedic failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
