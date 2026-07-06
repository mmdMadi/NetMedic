"""
Dashboard widget: the system summary panel.

The dashboard renders a compact grid of headline numbers (total
adapters, ghosts, VPN, physical, disabled) plus the admin/elevation
banner. It is a *view* -- it owns no data and is repainted by the app
via :meth:`Dashboard.update_stats`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from network.scanner import ScanStats
from utils.admin import ElevationInfo, get_elevation_info
from utils.helpers import safe_str


@dataclass(frozen=True)
class StatCard:
    """Static descriptor for one dashboard tile.

    Keeping the label / value / style together makes the render loop a
    pure map over a tuple of cards, with no conditionals.
    """

    label: str
    value: int
    css_class: str


class StatTile(Static):
    """A single dashboard tile showing a label and a big number."""

    def __init__(self, label: str, css_class: str) -> None:
        super().__init__()
        self._label = label
        self._css_class = css_class
        self.add_class(css_class)

    def render(self) -> str:  # type: ignore[override]
        """Render the tile as a two-line block."""
        return f"[b]{self._value_str}[/b]\n[dim]{self._label}[/]"

    @property
    def _value_str(self) -> str:
        # reactive value falls back to "—" before the first update
        value = getattr(self, "_value", None)
        return safe_str(value, default="—")

    def set_value(self, value: int) -> None:
        """Update the displayed number and trigger a refresh."""
        self._value = value
        self.refresh()


class Dashboard(Static):
    """Top-of-screen summary panel.

    The dashboard exposes a single public entry point,
    :meth:`update_stats`, and renders the elevation banner plus a row of
    :class:`StatTile` widgets.
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
    StatTile {
        width: 1fr;
        padding: 0 1;
        border: round $primary-darken-2;
        text-align: center;
        height: 4;
        content-align: center middle;
        background: $surface;
    }
    StatTile.tile-total    { border: round $accent; }
    StatTile.tile-ghost    { border: round $warning; }
    StatTile.tile-vpn      { border: round $secondary; }
    StatTile.tile-physical { border: round $success; }
    StatTile.tile-disabled { border: round $error; }
    StatTile.tile-virtual  { border: round $primary; }
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
        """Lay out the dashboard: elevation banner + stat tiles row."""
        yield Static(self.elevation_text, id="elevation")
        with Horizontal(id="stat-row"):
            self._tile_total = StatTile("Total Adapters", "tile-total")
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
        """Refresh the elevation banner on mount."""
        self.refresh_elevation()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def refresh_elevation(self) -> ElevationInfo:
        """Query privileges and update the banner. Returns the info."""
        info = get_elevation_info()
        self.elevation_text = (
            f"  {info.as_text()}    "
            f"[dim]NetMedic — Windows Network Adapter Manager[/]"
        )
        self.elevation_class = "elevated" if info.is_admin else "limited"
        return info

    def update_stats(self, stats: Optional[ScanStats]) -> None:
        """Repaint the stat tiles from a fresh :class:`ScanStats`."""
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
    def _all_tiles(self) -> list[StatTile]:
        return [
            self._tile_total,
            self._tile_physical,
            self._tile_vpn,
            self._tile_virtual,
            self._tile_ghost,
            self._tile_disabled,
        ]
