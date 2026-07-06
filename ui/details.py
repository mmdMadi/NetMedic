"""
Details panel widget.

Shown when the user presses Enter on an adapter. Renders a two-column
key/value layout describing everything NetMedic knows about the
adapter. The panel is fed by :meth:`DetailsPanel.show` and clears via
:meth:`DetailsPanel.clear_view`.
"""

from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from network.adapter import Adapter
from utils.helpers import safe_str


class DetailsPanel(VerticalScroll):
    """Right-hand detail view for a single adapter.

    The widget renders a header line, an identity section, a networking
    section, and (optionally) a hardware IDs section. Empty list-valued
    fields collapse to the ``"—"`` sentinel rather than showing blank.
    """

    DEFAULT_CSS = """
    DetailsPanel {
        width: 42;
        min-width: 32;
        max-width: 60;
        border-left: solid $primary;
        background: $panel;
        padding: 0 1;
    }
    DetailsPanel #details-title {
        background: $primary;
        color: $text;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }
    DetailsPanel .section {
        padding: 1 0 0 0;
        color: $accent;
        text-style: bold;
    }
    DetailsPanel .kv {
        padding: 0 1;
    }
    DetailsPanel .empty {
        padding: 1 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    can_focus = False

    def compose(self) -> ComposeResult:
        """Skeleton: title + a single body container we (re)build on demand."""
        yield Static("Adapter Details", id="details-title")
        yield Static("Select an adapter and press Enter.", id="details-body", markup=False)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def show(self, adapter: Adapter) -> None:
        """Render the details of ``adapter`` into the body widget."""
        body = self.query_one("#details-body", Static)
        body.update(self._build_text(adapter))

    def clear_view(self) -> None:
        """Reset the body to the empty-state placeholder text."""
        body = self.query_one("#details-body", Static)
        body.update("Select an adapter and press Enter.")

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def _build_text(self, adapter: Adapter) -> str:
        """Build the plain-text (markup-enabled) body for ``adapter``."""
        lines: list[str] = []
        lines.append("[b]Identity[/b]")
        lines.append(self._kv("Name", adapter.name))
        lines.append(self._kv("Description", adapter.interface_description))
        lines.append(self._kv("Category", adapter.category.value))
        lines.append(self._kv("Interface Index", adapter.if_index))
        lines.append(self._kv("Interface GUID", adapter.interface_guid))
        lines.append(self._kv("Status", safe_str(adapter.status).capitalize()))
        lines.append(self._kv("Connection", adapter.media_connection_state))

        lines.append("")
        lines.append("[b]Link Layer[/b]")
        lines.append(self._kv("MAC Address", adapter.mac_address))
        lines.append(self._kv("Link Speed", adapter.link_speed))

        lines.append("")
        lines.append("[b]IP Configuration[/b]")
        lines.append(self._kv("IPv4", adapter.ipv4_addresses))
        lines.append(self._kv("IPv6", adapter.ipv6_addresses))
        lines.append(self._kv("Subnet Prefixes", adapter.subnet_prefixes))
        lines.append(self._kv("Default Gateways", adapter.default_gateways))
        lines.append(self._kv("DNS Servers", adapter.dns_servers))

        lines.append("")
        lines.append("[b]Driver[/b]")
        lines.append(self._kv("Driver Version", adapter.driver_version))
        lines.append(self._kv("Driver Date", adapter.driver_date))
        lines.append(self._kv("Driver Provider", adapter.driver_provider))

        lines.append("")
        lines.append("[b]Hardware / Registry[/b]")
        lines.append(self._kv("PNP Device ID", adapter.pnp_device_id))
        lines.append(self._kv("Class GUID", adapter.class_guid))
        lines.append(self._kv("Hardware IDs", adapter.hardware_ids))

        lines.append("")
        lines.append("[b]Flags[/b]")
        lines.append(
            self._kv(
                "Attributes",
                ", ".join(
                    flag
                    for flag, on in (
                        ("Physical", adapter.physical),
                        ("Virtual", adapter.virtual),
                        ("Hidden", adapter.hidden),
                        ("Enabled", adapter.enabled),
                        ("Disabled", adapter.disabled),
                    )
                    if on
                )
                or "None",
            )
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _kv(label: str, value: object) -> str:
        """Render one key/value line, collapsing lists to a single cell."""
        if isinstance(value, list):
            if not value:
                text = "—"
            else:
                text = ", ".join(str(v) for v in value)
        else:
            text = safe_str(value)
        return f"[b]{label:<16}[/b] {text}"
