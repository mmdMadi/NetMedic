"""
Quick-action toolbar for the top of the app.

The toolbar gives the common actions a visible home so users are not
forced to memorize every shortcut. It is intentionally lightweight:
buttons simply dispatch to the app's existing actions.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static


class ActionsBar(Horizontal):
    """A compact row of action buttons."""

    DEFAULT_CSS = """
    ActionsBar {
        height: auto;
        padding: 0 1 1 1;
    }
    ActionsBar #hint {
        width: auto;
        padding: 0 1 0 0;
        color: $text-muted;
        content-align: left middle;
    }
    ActionsBar Button {
        margin-right: 1;
    }
    ActionsBar #remove {
        background: $error;
    }
    """

    can_focus = False

    def __init__(self) -> None:
        super().__init__(id="actions-bar")

    def compose(self) -> ComposeResult:
        yield Static("Actions", id="hint")
        yield Button("Scan", id="scan", variant="primary")
        yield Button("Filter", id="filter")
        yield Button("Export", id="export")
        yield Button("Ignore", id="ignore")
        yield Button("Disable", id="disable", variant="warning")
        yield Button("Remove", id="remove", variant="error")
