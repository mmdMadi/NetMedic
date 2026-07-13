"""
Dashboard widget: the system summary panel.

The dashboard renders:

1. **Info cards** — quick-glance tiles showing Internet Status (with
   latency), Local IP, Public IP (with ISP/country), Windows Version,
   Connected Adapter, and Current DNS (with provider name).
2. **Health score** — a large score (0–100) with grade, color-coded
   by severity, listing individual contributing checks.
3. **Elevation banner** — admin/standard-user privilege indicator.
4. **Adapter stats** — total, physical, virtual, VPN, ghost, disabled.

Each info card is a self-contained ``Static`` subclass with its own
styling and update method. Cards are populated by background workers
started in ``app.py`` on mount — the dashboard is a pure *view* that
receives data, never fetches it.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from network.health import HealthScore
from network.internet import InternetStatus
from network.scanner import ScanStats
from utils.admin import ElevationInfo, get_elevation_info
from utils.helpers import safe_str


# --------------------------------------------------------------------- #
# Info card — a single key/value tile
# --------------------------------------------------------------------- #

class InfoCard(Static):
    """A dashboard tile showing a label, a value, and an optional icon."""

    DEFAULT_CSS = """
    InfoCard {
        width: 1fr;
        height: 4;
        padding: 0 1;
        border: round #1e293b;
        background: #0f172a;
        content-align: left top;
    }
    InfoCard:hover {
        border: round #334155;
        background: #1e293b;
    }
    """

    def __init__(self, label: str, css_class: str = "") -> None:
        super().__init__()
        self._label = label
        self._value = "—"
        self._sub: str = ""
        if css_class:
            self.add_class(css_class)

    def render(self) -> str:  # type: ignore[override]
        if self._sub:
            return f"[dim]{self._label}[/]\n[b]{self._value}[/]\n[dim]{self._sub}[/]"
        return f"[dim]{self._label}[/]\n[b]{self._value}[/]"

    def set_value(self, value: str, sub: str = "") -> None:
        """Update the displayed value and optional subtitle."""
        self._value = value
        self._sub = sub
        self.refresh()


# --------------------------------------------------------------------- #
# Health score widget — large score with color + check list
# --------------------------------------------------------------------- #

class HealthScoreWidget(Static):
    """A prominent health score display with grade, color, and check list."""

    DEFAULT_CSS = """
    HealthScoreWidget {
        width: 28;
        height: auto;
        min-height: 8;
        padding: 0 1;
        border: round #0e7490;
        background: #0f172a;
        text-align: left;
    }
    HealthScoreWidget:hover {
        border: round #22d3ee;
        background: #1e293b;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._score: Optional[HealthScore] = None

    def render(self) -> str:  # type: ignore[override]
        if self._score is None:
            return "[dim]Health Score[/]\n[dim]Calculating…[/]"
        s = self._score
        color = _score_color(s.percentage)
        lines = [
            f"[b {color}]{s.status_symbol} {s.score} / {s.max_score}[/]",
            f"[{color}]{s.grade}[/]",
            "",
        ]
        for check in s.checks:
            icon = "✔" if check.passed else "✘"
            c = "green" if check.passed else "red"
            detail = f" — {check.detail}" if check.detail else ""
            lines.append(f"  [{c}]{icon}[/] {check.label}{detail}")
        return "\n".join(lines)


def _score_color(percentage: float) -> str:
    """Return a Textual color name based on score percentage."""
    if percentage >= 90:
        return "green"
    if percentage >= 70:
        return "yellow"
    if percentage >= 50:
        return "orange"
    return "red"


# --------------------------------------------------------------------- #
# Stat tile — adapter count tile (kept from v1)
# --------------------------------------------------------------------- #

class StatTile(Static):
    """A single dashboard tile showing a label and a big number."""

    def __init__(self, label: str, css_class: str) -> None:
        super().__init__()
        self._label = label
        self._css_class = css_class
        self.add_class(css_class)

    def render(self) -> str:  # type: ignore[override]
        return f"[b]{self._value_str}[/b]\n[dim]{self._label}[/]"

    @property
    def _value_str(self) -> str:
        value = getattr(self, "_value", None)
        return safe_str(value, default="—")

    def set_value(self, value: int) -> None:
        """Update the displayed number and trigger a refresh."""
        self._value = value
        self.refresh()


# --------------------------------------------------------------------- #
# Dashboard — the full top-of-screen panel
# --------------------------------------------------------------------- #

class Dashboard(Static):
    """Top-of-screen summary panel with info cards, health score, and stats.

    The dashboard exposes entry points for each data source. All are
    designed to be called from background workers via
    ``call_from_thread`` — they never perform I/O themselves.
    """

    DEFAULT_CSS = """
    Dashboard {
        layer: base;
        height: auto;
        padding: 0 1 1 1;
        border-bottom: thick $primary;
        background: $panel;
    }
    Dashboard #elevation {
        height: 1;
        padding: 0 1;
        background: $boost;
        color: $text;
        text-style: bold;
    }
    Dashboard #elevation.elevated { background: $success; color: $text; }
    Dashboard #elevation.limited  { background: $warning; color: $text; }
    Dashboard Horizontal { height: auto; }
    Dashboard #info-row {
        height: auto;
        padding: 0 0 1 0;
    }
    Dashboard #info-row InfoCard { margin-right: 1; }
    Dashboard #bottom-row {
        height: auto;
        padding: 0 0 0 0;
    }
    Dashboard #stats-section {
        width: 1fr;
        height: auto;
    }
    HealthScoreWidget { margin-right: 1; }
    StatTile {
        width: 1fr;
        padding: 0 1;
        border: round #1e293b;
        text-align: center;
        height: 4;
        content-align: center middle;
        background: #0f172a;
    }
    StatTile:hover {
        background: #1e293b;
    }
    StatTile.tile-total    { border: round #0e7490; }
    StatTile.tile-ghost    { border: round #92400e; }
    StatTile.tile-vpn      { border: round #6d28d9; }
    StatTile.tile-physical { border: round #166534; }
    StatTile.tile-disabled { border: round #991b1b; }
    StatTile.tile-virtual  { border: round #1e40af; }
    """

    can_focus = False

    elevation_text: reactive[str] = reactive("Detecting privileges…")
    elevation_class: reactive[str] = reactive("")

    def __init__(self) -> None:
        super().__init__()
        self._stats: Optional[ScanStats] = None

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        """Lay out the dashboard: elevation + info cards + health + stats."""
        yield Static(self.elevation_text, id="elevation")

        # Row 1: Info cards
        with Horizontal(id="info-row"):
            self._card_status = InfoCard("Internet Status", "card-status")
            self._card_local_ip = InfoCard("Local IP", "card-local-ip")
            self._card_public_ip = InfoCard("Public IP", "card-public-ip")
            self._card_windows = InfoCard("Windows", "card-windows")
            self._card_adapter = InfoCard("Connected Adapter", "card-adapter")
            self._card_dns = InfoCard("DNS Server", "card-dns")
            yield self._card_status
            yield self._card_local_ip
            yield self._card_public_ip
            yield self._card_windows
            yield self._card_adapter
            yield self._card_dns

        # Row 2: Health score + adapter stat tiles
        with Horizontal(id="bottom-row"):
            self._health = HealthScoreWidget()
            yield self._health
            with Vertical(id="stats-section"):
                with Horizontal():
                    self._tile_total = StatTile("Total", "tile-total")
                    self._tile_physical = StatTile("Physical", "tile-physical")
                    self._tile_vpn = StatTile("VPN", "tile-vpn")
                    self._tile_virtual = StatTile("Virtual", "tile-virtual")
                    self._tile_ghost = StatTile("Ghost", "tile-ghost")
                    self._tile_disabled = StatTile("Disabled", "tile-disabled")
                    yield self._tile_total
                    yield self._tile_physical
                    yield self._tile_vpn
                    yield self._tile_virtual
                    yield self._tile_ghost
                    yield self._tile_disabled

    def on_mount(self) -> None:
        """Refresh the elevation banner and set Windows version."""
        self.refresh_elevation()
        self._set_windows_version()

    # ------------------------------------------------------------------ #
    # Public API — called from app.py background workers
    # ------------------------------------------------------------------ #
    def refresh_elevation(self) -> ElevationInfo:
        """Query privileges and update the banner. Returns the info."""
        info = get_elevation_info()
        self.elevation_text = (
            f"  {info.as_text()}    "
            f"[dim]NetMedic — Windows Network Diagnostics & Repair Toolkit[/]"
        )
        self.elevation_class = "elevated" if info.is_admin else "limited"
        return info

    def update_internet_status(self, status: InternetStatus, latency_ms: Optional[float] = None) -> None:
        """Update the Internet Status card with status and optional latency."""
        color = "green" if status == InternetStatus.CONNECTED else "red"
        value = f"[{color}]{status.value}[/]"
        sub = ""
        if latency_ms is not None and status == InternetStatus.CONNECTED:
            if latency_ms < 1:
                sub = "Latency: <1 ms"
            else:
                sub = f"Latency: {latency_ms:.0f} ms"
        self._card_status.set_value(value, sub)

    def update_local_ip(self, ip: str) -> None:
        """Update the Local IP card."""
        self._card_local_ip.set_value(ip)

    def update_public_ip(self, ip: str,isp: str = "", country: str = "") -> None:
        """Update the Public IP card with optional ISP and country."""
        sub = ""
        parts = [p for p in (isp, country) if p and p != "—"]
        if parts:
            sub = " · ".join(parts)
        self._card_public_ip.set_value(ip, sub)

    def update_connected_adapter(self, name: str) -> None:
        """Update the Connected Adapter card."""
        self._card_adapter.set_value(name)

    def update_dns(self, dns_display: str) -> None:
        """Update the DNS Server card with provider-aware display."""
        self._card_dns.set_value(dns_display)

    def update_health_score(self, score: HealthScore) -> None:
        """Update the health score display."""
        self._health.set_score(score)

    def update_stats(self, stats: Optional[ScanStats]) -> None:
        """Repaint the stat tiles from a fresh ScanStats."""
        self._stats = stats
        if stats is None:
            for tile in self._all_tiles():
                tile.set_value(0)
            return
        self._tile_total.set_value(stats.total)
        self._tile_physical.set_value(stats.physical)
        self._tile_vpn.set_value(stats.vpn)
        self._tile_virtual.set_value(stats.virtual)
        self._tile_ghost.set_value(stats.ghost)
        self._tile_disabled.set_value(stats.disabled)

    # ------------------------------------------------------------------ #
    # Watchers
    # ------------------------------------------------------------------ #
    def watch_elevation_class(self, value: str) -> None:
        """Re-apply the elevation banner's state class on change."""
        elevation = self.query_one("#elevation", Static)
        elevation.remove_class("elevated", "limited")
        if value:
            elevation.add_class(value)

    def watch_elevation_text(self, value: str) -> None:
        """Push the new banner text to the underlying Static widget."""
        try:
            self.query_one("#elevation", Static).update(value)
        except Exception:  # noqa: BLE001 -- widget may not be mounted yet
            pass

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_windows_version(self) -> None:
        """Populate the Windows version card from platform info."""
        try:
            version = platform.platform()
            parts = version.split("-")
            if len(parts) >= 2 and parts[0] == "Windows":
                label = f"Windows {parts[1]}"
            else:
                label = version
            self._card_windows.set_value(label)
        except Exception:
            self._card_windows.set_value("Windows")

    def _all_tiles(self) -> list[StatTile]:
        return [
            self._tile_total,
            self._tile_physical,
            self._tile_vpn,
            self._tile_virtual,
            self._tile_ghost,
            self._tile_disabled,
        ]
