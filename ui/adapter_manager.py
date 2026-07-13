"""
Adapter Manager screen.

A full-screen modal that displays all network adapters in a selectable
list with full details and action buttons (Enable, Disable, Restart).

Accessed via the **A** key binding or the *Adapters* button in the actions bar.
"""

from __future__ import annotations

import threading
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from network.adapter_manager import (
    AdapterDetail,
    AdapterOperationResult,
    disable_adapter,
    enable_adapter,
    list_adapters,
    restart_adapter,
)


class AdapterManagerScreen(ModalScreen[None]):
    """Full-screen adapter manager with list, details, and actions.

    Left panel: selectable adapter list.
    Right panel: detail view for selected adapter.
    Bottom: action buttons (Enable, Disable, Restart).
    """

    DEFAULT_CSS = """
    AdapterManagerScreen {
        background: #0b1016ee;
        align: center middle;
    }
    AdapterManagerScreen > Vertical {
        width: 100;
        height: 92%;
        background: #0f1923;
        border: thick #3b82f6;
        padding: 1 2;
    }
    AdapterManagerScreen #title {
        height: 2;
        text-align: center;
        color: #8ab4ff;
        text-style: bold;
        padding-bottom: 1;
    }
    AdapterManagerScreen #status {
        height: 1;
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }
    AdapterManagerScreen #content {
        height: 1fr;
    }
    AdapterManagerScreen #adapter-list {
        width: 35;
        border: round #223042;
        padding: 0 1;
        overflow-y: auto;
    }
    AdapterManagerScreen .adapter-item {
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
        border: round transparent;
    }
    AdapterManagerScreen .adapter-item:hover {
        background: #1e293b;
    }
    AdapterManagerScreen .adapter-item-selected {
        background: #1e3a5f;
        border: round #3b82f6;
    }
    AdapterManagerScreen .adapter-name {
        height: 1;
        color: #e2e8f0;
        text-style: bold;
    }
    AdapterManagerScreen .adapter-info {
        height: 1;
        color: #64748b;
    }
    AdapterManagerScreen .adapter-status-up {
        color: #4ade80;
    }
    AdapterManagerScreen .adapter-status-down {
        color: #f87171;
    }
    AdapterManagerScreen #detail-panel {
        width: 1fr;
        border: round #223042;
        padding: 1 2;
        overflow-y: auto;
        margin-left: 1;
    }
    AdapterManagerScreen .detail-header {
        height: 1;
        color: #94a3b8;
        text-style: bold;
        padding: 0 0 1 0;
    }
    AdapterManagerScreen .detail-row {
        height: auto;
    }
    AdapterManagerScreen .detail-label {
        color: #64748b;
    }
    AdapterManagerScreen .detail-value {
        color: #e2e8f0;
    }
    AdapterManagerScreen #actions {
        height: auto;
        padding: 1 0 0 0;
    }
    AdapterManagerScreen #actions Button {
        margin-right: 1;
    }
    AdapterManagerScreen #close-btn {
        width: 100%;
        height: 3;
        margin-top: 1;
    }
    AdapterManagerScreen .no-selection {
        color: #64748b;
        text-align: center;
        padding-top: 4;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._adapters: list[AdapterDetail] = []
        self._selected: Optional[AdapterDetail] = None
        self._adapter_widgets: list[tuple[Static, Static, Static]] = []

        # Widgets
        self._title: Static
        self._status: Static
        self._adapter_list: VerticalScroll
        self._detail_panel: VerticalScroll
        self._no_selection: Static
        self._enable_btn: Button
        self._disable_btn: Button
        self._restart_btn: Button

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Vertical():
            self._title = Static("Adapter Manager", id="title")
            yield self._title

            self._status = Static("Loading adapters…", id="status")
            yield self._status

            with Horizontal(id="content"):
                # Left: adapter list
                self._adapter_list = VerticalScroll(id="adapter-list")
                yield self._adapter_list

                # Right: detail panel
                self._detail_panel = VerticalScroll(id="detail-panel")
                yield self._detail_panel

            # Action buttons
            with Horizontal(id="actions"):
                self._enable_btn = Button("Enable", id="enable-btn", variant="success")
                yield self._enable_btn
                self._disable_btn = Button("Disable", id="disable-btn", variant="warning")
                yield self._disable_btn
                self._restart_btn = Button("Restart", id="restart-btn")
                yield self._restart_btn

            yield Button("Close  [Esc]", id="close-btn")

    def on_mount(self) -> None:
        """Load adapters on a background thread."""
        self._load_adapters()

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "close-btn":
            self.dismiss()
            return

        if btn_id == "enable-btn":
            self._do_enable()
        elif btn_id == "disable-btn":
            self._do_disable()
        elif btn_id == "restart-btn":
            self._do_restart()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()

    # ------------------------------------------------------------------ #
    # Load adapters
    # ------------------------------------------------------------------ #
    def _load_adapters(self) -> None:
        """Fetch adapter list in a background thread."""
        def _worker() -> None:
            adapters = list_adapters()
            self.call_from_thread(self._show_adapters, adapters)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_adapters(self, adapters: list[AdapterDetail]) -> None:
        """Render the adapter list."""
        self._adapters = adapters
        self._adapter_list.remove_children()
        self._adapter_widgets.clear()
        self._selected = None

        if not adapters:
            empty = Static("No adapters found", classes="no-selection")
            self._adapter_list.mount(empty)
            self._status.update("No adapters found")
            self._show_no_selection()
            return

        for adapter in adapters:
            status_cls = "adapter-status-up" if adapter.enabled else "adapter-status-down"
            status_icon = "●" if adapter.enabled else "○"

            name_widget = Static(
                f"{status_icon} {adapter.name}",
                classes=f"adapter-name {status_cls}",
            )
            info_widget = Static(
                f"{adapter.category} · {adapter.link_speed or '—'}",
                classes="adapter-info",
            )
            item_container = Vertical(classes="adapter-item")
            self._adapter_list.mount(item_container)
            item_container.mount(name_widget)
            item_container.mount(info_widget)

            self._adapter_widgets.append((item_container, name_widget, info_widget))

            # Bind click
            item_container.on_click = self._make_click_handler(adapter)

        self._status.update(f"{len(adapters)} adapters loaded")
        self._show_no_selection()

    def _make_click_handler(self, adapter: AdapterDetail):
        """Create a click handler for an adapter item."""
        def _handler() -> None:
            self._select_adapter(adapter)
        return _handler

    def _select_adapter(self, adapter: AdapterDetail) -> None:
        """Select an adapter and show its details."""
        self._selected = adapter

        # Update list highlighting
        for item_container, name_widget, _ in self._adapter_widgets:
            item_container.remove_class("adapter-item-selected")
            if name_widget.plain.strip().endswith(adapter.name):
                item_container.add_class("adapter-item-selected")

        # Update detail panel
        self._detail_panel.remove_children()

        detail_title = Static(adapter.name, classes="detail-header")
        self._detail_panel.mount(detail_title)

        rows = [
            ("Description", adapter.description),
            ("Status", adapter.status),
            ("Enabled", "Yes" if adapter.enabled else "No"),
            ("Category", adapter.category),
            ("MAC Address", adapter.mac_address),
            ("Link Speed", adapter.link_speed or "—"),
            ("MTU", str(adapter.mtu) if adapter.mtu else "—"),
            ("IPv4", ", ".join(adapter.ipv4_addresses) if adapter.ipv4_addresses else "—"),
            ("IPv6", ", ".join(adapter.ipv6_addresses) if adapter.ipv6_addresses else "—"),
            ("Gateway", ", ".join(adapter.default_gateways) if adapter.default_gateways else "—"),
            ("DNS", ", ".join(adapter.dns_servers) if adapter.dns_servers else "—"),
            ("Driver", adapter.driver_version or "—"),
            ("Driver Provider", adapter.driver_provider or "—"),
        ]

        for label, value in rows:
            row = Static(f"  {label}: {value}", classes="detail-row")
            self._detail_panel.mount(row)

        # Update button states
        self._enable_btn.disabled = adapter.enabled
        self._disable_btn.disabled = not adapter.enabled

        self._status.update(f"Selected: {adapter.name}")

    def _show_no_selection(self) -> None:
        """Show the empty state in the detail panel."""
        self._detail_panel.remove_children()
        self._no_selection = Static(
            "Select an adapter to view details",
            classes="no-selection",
        )
        self._detail_panel.mount(self._no_selection)
        self._enable_btn.disabled = True
        self._disable_btn.disabled = True
        self._restart_btn.disabled = True

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _do_enable(self) -> None:
        """Enable the selected adapter."""
        if not self._selected:
            return

        adapter = self._selected
        self._set_status(f"Enabling {adapter.name}…")

        def _worker() -> None:
            result = enable_adapter(adapter.name)
            self.call_from_thread(self._on_operation_result, result)

        threading.Thread(target=_worker, daemon=True).start()

    def _do_disable(self) -> None:
        """Disable the selected adapter."""
        if not self._selected:
            return

        adapter = self._selected
        self._set_status(f"Disabling {adapter.name}…")

        def _worker() -> None:
            result = disable_adapter(adapter.name)
            self.call_from_thread(self._on_operation_result, result)

        threading.Thread(target=_worker, daemon=True).start()

    def _do_restart(self) -> None:
        """Restart the selected adapter."""
        if not self._selected:
            return

        adapter = self._selected
        self._set_status(f"Restarting {adapter.name}…")

        def _worker() -> None:
            result = restart_adapter(adapter.name)
            self.call_from_thread(self._on_operation_result, result)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_operation_result(self, result: AdapterOperationResult) -> None:
        """Handle the result of an adapter operation."""
        if result.success:
            self._set_status(f"[green]✔ {result.message}[/]")
            # Refresh the list
            self._load_adapters()
        else:
            self._set_status(f"[red]✘ {result.message}[/]")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_status(self, message: str) -> None:
        """Update the status label."""
        try:
            self._status.update(message)
        except Exception:
            pass
