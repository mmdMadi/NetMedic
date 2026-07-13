"""
Public Network Information screen.

A full-screen modal that displays the host's public-facing network
identity: IPv4, IPv6, ISP, ASN, country, region, city, and timezone.
Data is fetched from free APIs on a background thread.

Accessed via the **P** key binding or the *Public Info* button in the actions bar.
"""

from __future__ import annotations

import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from network.public_info import PublicNetworkInfo, gather


class PublicInfoScreen(ModalScreen[None]):
    """Full-screen public network information overlay.

    Displays a grid of labeled information cards showing the host's
    public IP, ISP, and geolocation data.
    """

    DEFAULT_CSS = """
    PublicInfoScreen {
        background: #0b1016ee;
        align: center middle;
    }
    PublicInfoScreen > Vertical {
        width: 70;
        height: auto;
        max-height: 90%;
        background: #0f1923;
        border: thick #3b82f6;
        padding: 1 2;
    }
    PublicInfoScreen #title {
        height: 2;
        text-align: center;
        color: #8ab4ff;
        text-style: bold;
        padding-bottom: 1;
    }
    PublicInfoScreen #status {
        height: 1;
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }
    PublicInfoScreen .info-section {
        border: round #223042;
        padding: 1 2;
        margin: 0 0 1 0;
        height: auto;
    }
    PublicInfoScreen .section-header {
        height: 1;
        color: #94a3b8;
        text-style: bold;
        padding-bottom: 1;
    }
    PublicInfoScreen .info-row {
        height: 1;
    }
    PublicInfoScreen .info-label {
        color: #64748b;
    }
    PublicInfoScreen .info-value {
        color: #e2e8f0;
    }
    PublicInfoScreen .info-value-ip {
        color: #4ade80;
        text-style: bold;
    }
    PublicInfoScreen .info-value-error {
        color: #f87171;
    }
    PublicInfoScreen #close-btn {
        width: 100%;
        height: 3;
        margin-top: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._title: Static
        self._status: Static
        self._ipv4_value: Static
        self._ipv6_value: Static
        self._isp_value: Static
        self._asn_value: Static
        self._country_value: Static
        self._region_value: Static
        self._city_value: Static
        self._timezone_value: Static

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Vertical():
            self._title = Static("Public Network Information", id="title")
            yield self._title

            self._status = Static("Loading…", id="status")
            yield self._status

            # IP section
            with Vertical(classes="info-section"):
                yield Static("IP ADDRESSES", classes="section-header")
                self._ipv4_value = Static("  IPv4: Loading…", classes="info-row info-value-ip")
                yield self._ipv4_value
                self._ipv6_value = Static("  IPv6: Loading…", classes="info-row")
                yield self._ipv6_value

            # ISP section
            with Vertical(classes="info-section"):
                yield Static("ISP / NETWORK", classes="section-header")
                self._isp_value = Static("  ISP: Loading…", classes="info-row")
                yield self._isp_value
                self._asn_value = Static("  ASN: Loading…", classes="info-row")
                yield self._asn_value

            # Location section
            with Vertical(classes="info-section"):
                yield Static("LOCATION", classes="section-header")
                self._country_value = Static("  Country: Loading…", classes="info-row")
                yield self._country_value
                self._region_value = Static("  Region: Loading…", classes="info-row")
                yield self._region_value
                self._city_value = Static("  City: Loading…", classes="info-row")
                yield self._city_value
                self._timezone_value = Static("  Timezone: Loading…", classes="info-row")
                yield self._timezone_value

            yield Button("Close  [Esc]", id="close-btn")

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def on_mount(self) -> None:
        """Fetch public info on a background thread."""
        self._fetch_info()

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.dismiss()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()

    # ------------------------------------------------------------------ #
    # Data fetching
    # ------------------------------------------------------------------ #
    def _fetch_info(self) -> None:
        """Fetch all public info in a background thread."""
        def _worker() -> None:
            try:
                info = gather()
            except Exception as exc:
                info = PublicNetworkInfo(error=str(exc))
            self.call_from_thread(self._show_info, info)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_info(self, info: PublicNetworkInfo) -> None:
        """Render the fetched information."""
        if info.error:
            self._status.update(f"[red]Error: {info.error}[/]")
            return

        self._status.update("Public network information")

        # IP
        self._ipv4_value.update(f"  IPv4: {info.public_ipv4}")
        self._ipv6_value.update(f"  IPv6: {info.public_ipv6}")

        # ISP
        self._isp_value.update(f"  ISP: {info.isp}")
        self._asn_value.update(f"  ASN: {info.asn}")

        # Location
        self._country_value.update(f"  Country: {info.country}")
        self._region_value.update(f"  Region: {info.region}")
        self._city_value.update(f"  City: {info.city}")
        self._timezone_value.update(f"  Timezone: {info.timezone}")
