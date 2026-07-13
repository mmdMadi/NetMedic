"""
DNS Tools screen.

A full-screen modal for viewing and managing DNS configuration.
Displays the current DNS for the active adapter, provides preset
buttons to switch DNS providers, and offers cache management actions.

Accessed via the **N** key binding or the *DNS* button in the actions bar.
"""

from __future__ import annotations

import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from network.dns_tools import (
    AdapterDns,
    DnsOperationResult,
    DnsPreset,
    DNS_PRESETS,
    flush_dns_cache,
    get_active_adapter_dns,
    register_dns,
    reset_dns_automatic,
    set_dns_servers,
)


class DnsToolsScreen(ModalScreen[None]):
    """Full-screen DNS tools overlay.

    Sections:
    1. Current DNS status for the active adapter
    2. DNS provider presets (click to apply)
    3. Cache management actions (Flush / Register / Reset)
    """

    DEFAULT_CSS = """
    DnsToolsScreen {
        background: #0b1016ee;
        align: center middle;
    }
    DnsToolsScreen > Vertical {
        width: 80;
        height: auto;
        max-height: 90%;
        background: #0f1923;
        border: thick #3b82f6;
        padding: 1 2;
    }
    DnsToolsScreen #title {
        height: 2;
        text-align: center;
        color: #8ab4ff;
        text-style: bold;
        padding-bottom: 1;
    }
    DnsToolsScreen #status {
        height: 1;
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }
    DnsToolsScreen .section-label {
        height: 1;
        color: #94a3b8;
        text-style: bold;
        padding: 1 0 0 0;
    }
    DnsToolsScreen #current-dns {
        height: auto;
        border: round #223042;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    DnsToolsScreen .dns-line {
        height: 1;
    }
    DnsToolsScreen #presets {
        height: auto;
        margin: 0 0 1 0;
    }
    DnsToolsScreen .preset-btn {
        margin: 0 1 1 0;
        min-width: 16;
    }
    DnsToolsScreen .preset-btn-active {
        border: tall #4ade80;
    }
    DnsToolsScreen #actions {
        height: auto;
        margin: 0 0 1 0;
    }
    DnsToolsScreen #actions Button {
        margin-right: 1;
    }
    DnsToolsScreen #close-btn {
        width: 100%;
        height: 3;
        margin-top: 1;
    }
    DnsToolsScreen .success {
        color: #4ade80;
    }
    DnsToolsScreen .error {
        color: #f87171;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_adapter: AdapterDns = AdapterDns(adapter_name="—")
        self._active_preset: str = ""
        self._preset_buttons: dict[str, Button] = {}

        # Widgets
        self._title: Static
        self._status: Static
        self._adapter_name: Static
        self._dns_servers: Static
        self._dns_mode: Static

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Vertical():
            self._title = Static("DNS Tools", id="title")
            yield self._title

            self._status = Static("Loading DNS configuration…", id="status")
            yield self._status

            # Current DNS section
            yield Static("CURRENT DNS", classes="section-label")
            with Vertical(id="current-dns"):
                self._adapter_name = Static("Adapter: —", classes="dns-line")
                yield self._adapter_name
                self._dns_servers = Static("DNS: —", classes="dns-line")
                yield self._dns_servers
                self._dns_mode = Static("Mode: —", classes="dns-line")
                yield self._dns_mode

            # Preset buttons
            yield Static("DNS PROVIDERS", classes="section-label")
            with Vertical(id="presets"):
                # Row 1: Automatic + major providers
                with Horizontal():
                    for preset in DNS_PRESETS[:4]:
                        btn = Button(
                            f"{preset.name}\n{preset.primary or 'DHCP'}",
                            id=f"preset-{preset.name.lower()}",
                            classes="preset-btn",
                        )
                        self._preset_buttons[preset.name] = btn
                        yield btn
                # Row 2: remaining providers
                with Horizontal():
                    for preset in DNS_PRESETS[4:]:
                        btn = Button(
                            f"{preset.name}\n{preset.primary}",
                            id=f"preset-{preset.name.lower()}",
                            classes="preset-btn",
                        )
                        self._preset_buttons[preset.name] = btn
                        yield btn

            # Cache actions
            yield Static("CACHE MANAGEMENT", classes="section-label")
            with Horizontal(id="actions"):
                yield Button("Flush DNS", id="flush", variant="primary")
                yield Button("Register DNS", id="register")
                yield Button("Reset Network Stack", id="reset", variant="warning")

            yield Button("Close  [Esc]", id="close-btn")

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def on_mount(self) -> None:
        """Load current DNS configuration on a background thread."""
        self._load_current_dns()

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "close-btn":
            self.dismiss()
            return

        if btn_id.startswith("preset-"):
            name = btn_id.replace("preset-", "")
            self._apply_preset(name)
            return

        action_map = {
            "flush": self._do_flush,
            "register": self._do_register,
            "reset": self._do_reset,
        }
        action = action_map.get(btn_id)
        if action:
            action()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()

    # ------------------------------------------------------------------ #
    # Load current DNS
    # ------------------------------------------------------------------ #
    def _load_current_dns(self) -> None:
        """Read DNS config in a background thread."""
        def _worker() -> None:
            try:
                adapter = get_active_adapter_dns()
            except Exception:
                adapter = AdapterDns(adapter_name="—")
            self.call_from_thread(self._show_current_dns, adapter)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_current_dns(self, adapter: AdapterDns) -> None:
        """Render the current DNS info."""
        self._current_adapter = adapter
        self._adapter_name.update(f"Adapter: {adapter.adapter_name}")

        if adapter.is_dhcp or not adapter.dns_servers:
            self._dns_servers.update("DNS: Automatic (DHCP)")
            self._dns_mode.update("Mode: Assigned by ISP/DHCP server")
            self._active_preset = "Automatic"
        else:
            servers_str = " / ".join(adapter.dns_servers)
            self._dns_servers.update(f"DNS: {servers_str}")
            self._dns_mode.update("Mode: Static (manually configured)")
            # Detect which preset matches
            self._active_preset = self._detect_preset(adapter.dns_servers)

        self._highlight_active_preset()
        self._status.update("DNS configuration loaded")

    def _detect_preset(self, servers: list[str]) -> str:
        """Identify which preset (if any) matches the current DNS servers."""
        for preset in DNS_PRESETS:
            if not preset.primary:
                continue
            if preset.primary in servers:
                return preset.name
        return ""

    def _highlight_active_preset(self) -> None:
        """Visually mark the currently active preset button."""
        for name, btn in self._preset_buttons.items():
            if name == self._active_preset:
                btn.add_class("preset-btn-active")
            else:
                btn.remove_class("preset-btn-active")

    # ------------------------------------------------------------------ #
    # Apply DNS preset
    # ------------------------------------------------------------------ #
    def _apply_preset(self, preset_name: str) -> None:
        """Apply a DNS preset to the active adapter."""
        preset_name_lower = preset_name.lower()
        preset = None
        for p in DNS_PRESETS:
            if p.name.lower() == preset_name_lower:
                preset = p
                break

        if not preset:
            return

        adapter = self._current_adapter
        if not adapter or adapter.adapter_name == "—":
            self._set_status("[red]No adapter detected[/]")
            return

        def _worker() -> None:
            if not preset.primary:
                # Automatic — reset to DHCP
                result = reset_dns_automatic(adapter.adapter_name)
            else:
                result = set_dns_servers(
                    adapter.adapter_name, preset.primary, preset.secondary,
                )
            self.call_from_thread(self._on_preset_applied, result, preset)

        self._set_status(f"Applying {preset.name} DNS…")
        threading.Thread(target=_worker, daemon=True).start()

    def _on_preset_applied(
        self, result: DnsOperationResult, preset: DnsPreset,
    ) -> None:
        """Handle the result of a DNS preset change."""
        if result.success:
            self._active_preset = preset.name
            self._highlight_active_preset()
            self._set_status(f"[green]✔ {result.message}[/]")
            # Refresh displayed DNS
            self._load_current_dns()
        else:
            self._set_status(f"[red]✘ {result.message}[/]")

    # ------------------------------------------------------------------ #
    # Cache actions
    # ------------------------------------------------------------------ #
    def _do_flush(self) -> None:
        """Flush the DNS resolver cache."""
        def _worker() -> None:
            result = flush_dns_cache()
            icon = "✔" if result.success else "✘"
            color = "green" if result.success else "red"
            self.call_from_thread(
                self._set_status, f"[{color}]{icon} {result.message}[/]",
            )

        self._set_status("Flushing DNS cache…")
        threading.Thread(target=_worker, daemon=True).start()

    def _do_register(self) -> None:
        """Register DNS records."""
        def _worker() -> None:
            result = register_dns()
            icon = "✔" if result.success else "✘"
            color = "green" if result.success else "red"
            self.call_from_thread(
                self._set_status, f"[{color}]{icon} {result.message}[/]",
            )

        self._set_status("Registering DNS records…")
        threading.Thread(target=_worker, daemon=True).start()

    def _do_reset(self) -> None:
        """Reset the network stack (requires admin)."""
        def _worker() -> None:
            result = clear_resolver_cache()
            icon = "✔" if result.success else "✘"
            color = "green" if result.success else "red"
            self.call_from_thread(
                self._set_status, f"[{color}]{icon} {result.message}[/]",
            )

        self._set_status("Resetting network stack…")
        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_status(self, message: str) -> None:
        """Update the status label."""
        try:
            self._status.update(message)
        except Exception:
            pass
