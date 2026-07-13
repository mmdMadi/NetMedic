"""
Quick-action toolbar for the top of the app.

The toolbar gives the common actions a visible home so users are not
forced to memorize every shortcut. It is intentionally lightweight:
buttons simply dispatch to the app's existing actions.

Buttons are grouped by function:
- Core: Scan, Filter, Export
- Tools: Diagnostics, Speed Test, DNS, Health
- Management: Adapters, Repair, Public Info, Report, Logs
- Destructive: Ignore, Disable, Remove
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static


class ActionsBar(Horizontal):
    """A compact row of action buttons with visual grouping."""

    DEFAULT_CSS = """
    ActionsBar {
        height: auto;
        padding: 0 1 1 1;
        background: #0d1219;
        border-bottom: thick #1e293b;
    }
    ActionsBar #hint {
        width: auto;
        padding: 0 1 0 0;
        color: #64748b;
        content-align: left middle;
        text-style: bold;
    }
    ActionsBar Button {
        margin-right: 1;
        min-width: 10;
    }
    ActionsBar .separator {
        width: 1;
        color: #334155;
        content-align: center middle;
    }
    """

    can_focus = False

    def __init__(self) -> None:
        super().__init__(id="actions-bar")

    def compose(self) -> ComposeResult:
        yield Static("Actions", id="hint")

        # Core actions
        yield Button("Scan [R]", id="scan", variant="primary")
        yield Button("Filter [F]", id="filter")

        # Separator
        yield Static("│", classes="separator")

        # Diagnostic tools
        yield Button("Diagnostics [T]", id="diagnostics")
        yield Button("Speed Test [S]", id="speed-test")
        yield Button("DNS [N]", id="dns-tools")
        yield Button("Health [H]", id="health")

        # Separator
        yield Static("│", classes="separator")

        # Management
        yield Button("Adapters [A]", id="adapter-mgr")
        yield Button("Repair [U]", id="repair", variant="warning")
        yield Button("Public Info [P]", id="public-info")
        yield Button("Report [G]", id="report")
        yield Button("Logs [L]", id="logs")

        # Separator
        yield Static("│", classes="separator")

        # Destructive actions
        yield Button("Export [E]", id="export")
        yield Button("Ignore [I]", id="ignore")
        yield Button("Disable [D]", id="disable", variant="warning")
        yield Button("Remove [X]", id="remove", variant="error")
