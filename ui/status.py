"""
Status bar and progress indicator.

A slim bar pinned under the table that shows the current operation
("Idle", "Scanning…", "Exporting…"), a live message, and an optional
:class:`ProgressBar` for long-running PowerShell calls.

Like the dashboard, this widget is a *view*; the app updates it via
:meth:`StatusBar.set_state` / :meth:`StatusBar.set_message`.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Static


class StatusState(str, Enum):
    """Coarse-grained operation state shown in the status bar."""

    IDLE = "Idle"
    SCANNING = "Scanning"
    EXPORTING = "Exporting"
    WORKING = "Working"
    ERROR = "Error"


class ProgressBar(Static):
    """A tiny text-based progress indicator.

    Textual ships a richer progress widget, but we keep this minimal so
    the status bar's height never changes and indeterminate states are
    represented cleanly with a spinning glyph.
    """

    DEFAULT_CSS = """
    ProgressBar {
        width: 16;
        height: 1;
        color: #60a5fa;
        padding: 0 1;
    }
    """

    active: reactive[bool] = reactive(False)
    _ticks: reactive[int] = reactive(0)

    _FRAMES: tuple[str, ...] = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def watch_active(self, value: bool) -> None:
        """Start / stop the animation timer when ``active`` toggles."""
        if value:
            self.set_interval(0.1, self._tick)  # type: ignore[arg-type]
        else:
            self._ticks = 0
            self.update("")

    def _tick(self) -> None:
        """Advance the spinner one frame."""
        self._ticks = (self._ticks + 1) % len(self._FRAMES)
        self.update(self._FRAMES[self._ticks])

    def render(self) -> str:  # type: ignore[override]
        """Show the current frame or empty space when inactive."""
        if not self.active:
            return ""
        return self._FRAMES[self._ticks]


class StatusBar(Horizontal):
    """Bottom status bar with state, message, and spinner.

    The bar is non-interactive (``can_focus = False``) -- it exists only
    to communicate state to the operator.
    """

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: #111822;
        color: #d6dde6;
        border-top: solid #1e293b;
    }
    StatusBar #state {
        width: 14;
        height: 1;
        padding: 0 1;
        background: #214d86;
        color: #e5edf6;
        text-style: bold;
    }
    StatusBar #state.idle     { background: #214d86; }
    StatusBar #state.scanning  { background: #0e7490; }
    StatusBar #state.exporting { background: #7c3aed; }
    StatusBar #state.working   { background: #0e7490; }
    StatusBar #state.error     { background: #991b1b; }
    StatusBar #message {
        width: 1fr;
        height: 1;
        padding: 0 1;
        color: #94a3b8;
    }
    """

    can_focus = False

    state: reactive[str] = reactive(StatusState.IDLE.value)

    def __init__(self) -> None:
        super().__init__()
        self._message: str = "Ready. Press R to scan."

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        """Lay out state label + message + spinner."""
        yield Static(self.state, id="state")
        yield Static(self._message, id="message", markup=False)
        yield ProgressBar(id="progress")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def set_state(
        self, state: StatusState, message: Optional[str] = None
    ) -> None:
        """Update the state label and (optionally) the message text.

        Activates the spinner for any non-idle state, and recolors the
        state cell using a CSS class derived from the state name.
        """
        self.state = state.value
        progress = self._progress()
        if progress:
            progress.active = state not in (StatusState.IDLE, StatusState.ERROR)
        if message is not None:
            self.set_message(message)

    def set_message(self, message: str) -> None:
        """Replace the message text."""
        self._message = message
        try:
            self.query_one("#message", Static).update(message)
        except Exception:  # noqa: BLE001 -- pre-mount
            pass

    def watch_state(self, value: str) -> None:
        """Re-apply the state-specific CSS class on the state cell."""
        try:
            state_label = self.query_one("#state", Static)
        except Exception:  # noqa: BLE001 -- pre-mount
            return
        state_label.remove_class(
            "scanning", "exporting", "working", "error", "idle"
        )
        cls = value.lower()
        if cls in {"scanning", "exporting", "working", "error"}:
            state_label.add_class(cls)
        else:
            state_label.add_class("idle")
        state_label.update(value)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _progress(self) -> Optional[ProgressBar]:
        try:
            return self.query_one("#progress", ProgressBar)
        except Exception:  # noqa: BLE001 -- pre-mount
            return None
