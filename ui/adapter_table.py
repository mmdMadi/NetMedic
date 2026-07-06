"""
The main adapter table widget.

:class:`AdapterTable` wraps a Textual ``DataTable`` and adds:

- search filtering (case-insensitive substring match),
- category filtering via :class:`FilterKey`,
- row selection state (Space toggle, Ctrl+A / Ctrl+D),
- a callback hook used by the app to open the details panel.

The widget never mutates the underlying adapter list -- filtering is
purely a display concern.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Input, Static
from textual import events

from network.adapter import Adapter, AdapterCategory
from utils.helpers import safe_str, truncate


class FilterKey(str, Enum):
    """Available category filters shown in the filter dialog.

    Subclasses ``str`` so values serialize cleanly to config / logs.
    """

    ALL = "All"
    PHYSICAL = "Physical"
    VPN = "VPN"
    VIRTUAL = "Virtual"
    GHOST = "Ghost"
    DISABLED = "Disabled"
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"

    @classmethod
    def all(cls) -> list["FilterKey"]:
        """Return every filter, in display order."""
        return [member for member in cls]


#: Columns displayed in the table, with their pixel widths.
COLUMNS: tuple[tuple[str, int], ...] = (
    ("✓", 3),
    ("Name", 26),
    ("Description", 32),
    ("Category", 12),
    ("Status", 12),
    ("MAC", 20),
    ("Speed", 12),
    ("Driver", 14),
)


class AdapterTable(Vertical):
    """Searchable, filterable, selectable adapter table.

    The widget is fully driven by :meth:`set_adapters`: call it whenever
    a fresh scan completes and the table re-renders itself.
    """

    DEFAULT_CSS = """
    AdapterTable {
        height: 1fr;
        padding: 0 1;
    }
    AdapterTable #search-wrap {
        height: 3;
        padding: 0 0 0 0;
    }
    AdapterTable #search {
        height: 1;
        border: round $primary;
        padding: 0 1;
    }
    AdapterTable #table-meta {
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }
    AdapterTable DataTable {
        height: 1fr;
        border: round $primary-darken-2;
    }
    """

    can_focus = True

    def __init__(self) -> None:
        super().__init__()
        self._all: list[Adapter] = []
        self._filtered: list[Adapter] = []
        self._selected: set[str] = set()
        self._filter: FilterKey = FilterKey.ALL
        self._search: str = ""
        self._on_enter: Optional[Callable[[Adapter], None]] = None

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        """Lay out search box + meta line + data table."""
        yield Static(
            "Type to filter the table below. Press Enter on a row for details.",
            id="search-wrap",
        )
        yield Input(placeholder="Search adapters…", id="search")
        yield Static("No data yet — press R to scan.", id="table-meta")
        yield DataTable(id="table")

    def on_mount(self) -> None:
        """Configure the DataTable columns and focus the search box."""
        table = self.query_one("#table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        for label, width in COLUMNS:
            table.add_column(label, width=width)
        try:
            self.query_one("#search", Input).focus()
        except Exception:  # noqa: BLE001 -- focus is best-effort
            pass

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def set_enter_callback(
        self, callback: Callable[[Adapter], None]
    ) -> None:
        """Register the handler invoked when the user presses Enter."""
        self._on_enter = callback

    def set_adapters(self, adapters: list[Adapter]) -> None:
        """Replace the backing data and refresh the table view."""
        self._all = list(adapters)
        # Selections for adapters that no longer exist are dropped.
        existing = {a.name for a in self._all}
        self._selected &= existing
        self._refresh()

    def set_filter(self, key: FilterKey) -> None:
        """Apply a category filter and re-render."""
        self._filter = key
        self._refresh()

    def get_filter(self) -> FilterKey:
        """Return the active filter."""
        return self._filter

    def get_selected(self) -> list[Adapter]:
        """Return adapters whose checkbox is currently checked."""
        return [a for a in self._filtered if a.name in self._selected]

    def select_all(self) -> None:
        """Mark every *visible* adapter as selected."""
        self._selected.update(a.name for a in self._filtered)
        self._refresh()

    def deselect_all(self) -> None:
        """Clear all selections."""
        self._selected.clear()
        self._refresh()

    def get_current_adapter(self) -> Optional[Adapter]:
        """Return the adapter under the cursor, or ``None``."""
        table = self.query_one("#table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        except Exception:  # noqa: BLE001 -- empty table has no cursor
            return None
        if row_key is None or row_key.value is None:
            return None
        try:
            index = int(row_key.value)
        except (TypeError, ValueError):
            return None
        if 0 <= index < len(self._filtered):
            return self._filtered[index]
        return None

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #
    def on_input_changed(self, event: Input.Changed) -> None:
        """Live-filter as the user types in the search box."""
        if event.input.id == "search":
            self._search = event.value.strip().lower()
            self._refresh()

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard shortcuts scoped to the table."""
        if event.key == "space":
            self._toggle_current()
            event.prevent_default()
        elif event.key == "enter":
            current = self.get_current_adapter()
            if current and self._on_enter:
                self._on_enter(current)
            event.prevent_default()

    # ------------------------------------------------------------------ #
    # Filtering & rendering
    # ------------------------------------------------------------------ #
    def _matches_filter(self, adapter: Adapter) -> bool:
        """Return ``True`` when ``adapter`` belongs in the current view."""
        f = self._filter
        if f is FilterKey.ALL:
            return True
        if f is FilterKey.CONNECTED:
            return adapter.is_connected
        if f is FilterKey.DISCONNECTED:
            return adapter.is_disconnected
        return adapter.category == AdapterCategory.from_raw(f.value)

    def _matches_search(self, adapter: Adapter) -> bool:
        """Return ``True`` when the adapter matches the search substring."""
        if not self._search:
            return True
        haystack = " ".join(
            [
                adapter.name,
                adapter.interface_description,
                adapter.mac_address,
                adapter.driver_provider,
                adapter.category.value,
            ]
        ).lower()
        return self._search in haystack

    def _refresh(self) -> None:
        """Recompute the filtered view and redraw the DataTable."""
        self._filtered = [
            adapter
            for adapter in self._all
            if self._matches_filter(adapter) and self._matches_search(adapter)
        ]
        table = self.query_one("#table", DataTable)
        table.clear()
        for index, adapter in enumerate(self._filtered):
            selected = "✓" if adapter.name in self._selected else ""
            table.add_row(
                selected,
                truncate(adapter.name, 26),
                truncate(adapter.interface_description, 32),
                adapter.category.value,
                safe_str(adapter.status).capitalize(),
                adapter.mac_address,
                adapter.link_speed,
                truncate(adapter.driver_version, 14),
                key=str(index),
            )
        meta = self.query_one("#table-meta", Static)
        shown = len(self._filtered)
        total = len(self._all)
        selected = len(self._selected)
        meta.update(
            f"Showing {shown}/{total} adapters • {selected} selected • "
            f"Filter: {self._filter.value}"
        )

    # ------------------------------------------------------------------ #
    # Selection helpers
    # ------------------------------------------------------------------ #
    def _toggle_current(self) -> None:
        """Toggle the selection of the adapter under the cursor."""
        current = self.get_current_adapter()
        if not current:
            return
        if current.name in self._selected:
            self._selected.discard(current.name)
        else:
            self._selected.add(current.name)
        self._refresh()
