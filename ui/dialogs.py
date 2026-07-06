"""
Modal dialogs for confirmations, filtering, export, and errors.

All dialogs are Textual :class:`ModalScreen` subclasses that return a
result to the caller via :meth:`App.pop_screen`. They are deliberately
small and self-contained -- the app holds the real logic and only asks
the dialog for a yes/no answer or a choice.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from network.export import ExportFormat
from ui.adapter_table import FilterKey
from utils.helpers import truncate


# --------------------------------------------------------------------- #
# Confirm dialog
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class ConfirmResult:
    """Outcome of a :class:`ConfirmDialog`.

    ``confirmed`` is ``True`` only when the user explicitly clicked
    *Confirm* (or pressed ``y``). Cancel / Escape resolve to ``False``.
    """

    confirmed: bool


class ConfirmDialog(ModalScreen[ConfirmResult]):
    """A generic destructive-action confirmation dialog.

    Used for every maintenance operation since NetMedic never performs a
    destructive action without an explicit confirmation.
    """

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }
    ConfirmDialog > Vertical {
        width: 64;
        height: auto;
        background: $panel;
        border: thick $warning;
        padding: 1 2;
    }
    ConfirmDialog #title {
        text-style: bold;
        color: $warning;
        padding-bottom: 1;
    }
    ConfirmDialog #body {
        padding-bottom: 1;
        color: $text;
    }
    ConfirmDialog Horizontal {
        align-horizontal: right;
        height: auto;
    }
    ConfirmDialog Button {
        margin-left: 1;
    }
    ConfirmDialog #confirm { background: $error; }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        """Render title, body, and Confirm/Cancel buttons."""
        with Vertical():
            yield Label(self._title, id="title")
            yield Static(self._body, id="body", markup=False)
            with Horizontal():
                yield Button("Cancel", id="cancel", variant="default")
                yield Button("Confirm", id="confirm", variant="error")

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Resolve the dialog when either button is pressed."""
        self.dismiss(ConfirmResult(confirmed=event.button.id == "confirm"))

    def on_key(self, event: events.Key) -> None:
        """Allow ``y``/``n``/Esc to resolve without the mouse."""
        if event.key in {"y", "enter"}:
            self.dismiss(ConfirmResult(confirmed=True))
        elif event.key in {"n", "escape"}:
            self.dismiss(ConfirmResult(confirmed=False))


# --------------------------------------------------------------------- #
# Filter dialog
# --------------------------------------------------------------------- #
class FilterDialog(ModalScreen[FilterKey]):
    """Pick one of the available category filters.

    The dialog returns the selected :class:`FilterKey` (or the previous
    filter when cancelled), keeping filter state inside the table itself.
    """

    DEFAULT_CSS = """
    FilterDialog {
        align: center middle;
    }
    FilterDialog > Vertical {
        width: 48;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }
    FilterDialog #title {
        text-style: bold;
        padding-bottom: 1;
    }
    FilterDialog Button {
        width: 100%;
        margin-bottom: 1;
    }
    """

    def __init__(self, current: FilterKey = FilterKey.ALL) -> None:
        super().__init__()
        self._current = current

    def compose(self) -> ComposeResult:
        """Render one button per filter."""
        with Vertical():
            yield Label("Choose a filter", id="title")
            for key in FilterKey.all():
                label = key.value
                if key == self._current:
                    label = f"» {label}"
                yield Button(label, id=f"filter-{key.value.lower()}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Return the :class:`FilterKey` whose button was pressed."""
        name = (event.button.id or "").replace("filter-", "")
        for key in FilterKey:
            if key.value.lower() == name:
                self.dismiss(key)
                return
        self.dismiss(self._current)

    def on_key(self, event: events.Key) -> None:
        """Escape preserves the current filter."""
        if event.key == "escape":
            self.dismiss(self._current)


# --------------------------------------------------------------------- #
# Export dialog
# --------------------------------------------------------------------- #
class ExportDialog(ModalScreen[ExportFormat]):
    """Pick an export format (CSV / JSON / TXT)."""

    DEFAULT_CSS = """
    ExportDialog {
        align: center middle;
    }
    ExportDialog > Vertical {
        width: 44;
        height: auto;
        background: $panel;
        border: thick $secondary;
        padding: 1 2;
    }
    ExportDialog #title {
        text-style: bold;
        padding-bottom: 1;
    }
    ExportDialog Button {
        width: 100%;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Render one button per export format."""
        with Vertical():
            yield Label("Export format", id="title")
            yield Button("CSV  (Comma-separated)", id="export-csv")
            yield Button("JSON (Structured)", id="export-json")
            yield Button("TXT  (Human-readable)", id="export-txt")
            yield Button("Cancel", id="cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Return the chosen :class:`ExportFormat`."""
        mapping = {
            "export-csv": ExportFormat.CSV,
            "export-json": ExportFormat.JSON,
            "export-txt": ExportFormat.TXT,
        }
        result = mapping.get(event.button.id)
        self.dismiss(result)  # Cancel returns None

    def on_key(self, event: events.Key) -> None:
        """Escape cancels the export."""
        if event.key == "escape":
            self.dismiss(None)


# --------------------------------------------------------------------- #
# Remove confirmation dialog (double-confirm for device removal)
# --------------------------------------------------------------------- #
class RemoveConfirmDialog(ModalScreen[ConfirmResult]):
    """Two-step confirmation for permanently removing an adapter.

    Device removal is the most destructive action NetMedic offers, so
    the user must type the adapter name to prove intent.  The dialog
    resolves to ``ConfirmResult(confirmed=True)`` only when the typed
    text matches exactly (case-insensitive) and the user clicks
    *Permanently Remove*.
    """

    DEFAULT_CSS = """
    RemoveConfirmDialog {
        align: center middle;
    }
    RemoveConfirmDialog > Vertical {
        width: 72;
        height: auto;
        background: $panel;
        border: thick $error;
        padding: 1 2;
    }
    RemoveConfirmDialog #title {
        text-style: bold;
        color: $error;
        padding-bottom: 1;
    }
    RemoveConfirmDialog #body {
        padding-bottom: 1;
        color: $text;
    }
    RemoveConfirmDialog #warn {
        padding-bottom: 1;
        color: $warning;
        text-style: bold;
    }
    RemoveConfirmDialog #prompt {
        padding-bottom: 1;
        color: $text;
    }
    RemoveConfirmDialog #confirm-input {
        border: round $error;
        padding: 0 1;
    }
    RemoveConfirmDialog #feedback {
        height: 1;
        color: $error;
        padding: 0 1;
    }
    RemoveConfirmDialog Horizontal {
        align-horizontal: right;
        height: auto;
    }
    RemoveConfirmDialog Button {
        margin-left: 1;
    }
    RemoveConfirmDialog #confirm { background: $error; }
    """

    def __init__(self, adapter_name: str) -> None:
        super().__init__()
        self._adapter_name = adapter_name
        self._typed = ""

    def compose(self) -> ComposeResult:
        """Render warning body, type-to-confirm input, and buttons."""
        with Vertical():
            yield Label("⚠  Permanently Remove Adapter", id="title")
            yield Static(
                f"You are about to permanently remove the device:\n"
                f"    {self._adapter_name}\n\n"
                "This will uninstall the adapter from Windows. The device "
                "will disappear until its driver is reinstalled or "
                "Windows rediscovers the hardware.\n"
                "This action is NOT easily reversible.",
                id="body",
                markup=False,
            )
            yield Static(
                "Type the adapter name below to confirm:",
                id="prompt",
            )
            yield Input(
                placeholder=self._adapter_name,
                id="confirm-input",
            )
            yield Static("", id="feedback")
            with Horizontal():
                yield Button("Cancel", id="cancel", variant="default")
                yield Button("Permanently Remove", id="confirm", variant="error")

    # ------------------------------------------------------------------ #
    # Handlers
    # ------------------------------------------------------------------ #
    def on_input_changed(self, event: Input.Changed) -> None:
        """Track what the user has typed so we can gate the button."""
        self._typed = event.value.strip()
        feedback = self.query_one("#feedback", Static)
        button = self.query_one("#confirm", Button)
        if not self._typed:
            feedback.update("")
            button.disabled = True
        elif self._typed.lower() == self._adapter_name.lower():
            feedback.update("[green]Match — you may proceed.[/]")
            button.disabled = False
        else:
            feedback.update(f"[red]Does not match \"{self._adapter_name}\"[/]")
            button.disabled = True

    def on_mount(self) -> None:
        """Disable the confirm button on mount so typing is required."""
        self.query_one("#confirm", Button).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Resolve the dialog."""
        confirmed = (
            event.button.id == "confirm"
            and self._typed.lower() == self._adapter_name.lower()
        )
        self.dismiss(ConfirmResult(confirmed=confirmed))

    def on_key(self, event: events.Key) -> None:
        """Only Escape cancels — Enter alone is NOT enough for removal."""
        if event.key == "escape":
            self.dismiss(ConfirmResult(confirmed=False))


# --------------------------------------------------------------------- #
# Bulk remove confirmation
# --------------------------------------------------------------------- #
class BulkRemoveConfirmDialog(ModalScreen[ConfirmResult]):
    """Confirmation dialog for removing several adapters."""

    DEFAULT_CSS = """
    BulkRemoveConfirmDialog {
        align: center middle;
    }
    BulkRemoveConfirmDialog > Vertical {
        width: 80;
        height: auto;
        background: $panel;
        border: thick $error;
        padding: 1 2;
    }
    BulkRemoveConfirmDialog #title {
        text-style: bold;
        color: $error;
        padding-bottom: 1;
    }
    BulkRemoveConfirmDialog #body {
        padding-bottom: 1;
        color: $text;
    }
    BulkRemoveConfirmDialog #list {
        height: auto;
        max-height: 12;
        padding: 0 1 1 1;
        color: $text;
    }
    BulkRemoveConfirmDialog Horizontal {
        align-horizontal: right;
        height: auto;
    }
    BulkRemoveConfirmDialog Button {
        margin-left: 1;
    }
    BulkRemoveConfirmDialog #confirm { background: $error; }
    """

    def __init__(self, adapter_names: list[str]) -> None:
        super().__init__()
        self._adapter_names = adapter_names

    def compose(self) -> ComposeResult:
        """Render the warning text and the adapter list."""
        with Vertical():
            yield Label("⚠  Permanently Remove Adapters", id="title")
            yield Static(
                "You are about to permanently remove multiple devices from Windows.\n"
                "This action is irreversible without reinstalling drivers.",
                id="body",
                markup=False,
            )
            yield Static(
                "\n".join(f"• {name}" for name in self._adapter_names),
                id="list",
                markup=False,
            )
            with Horizontal():
                yield Button("Cancel", id="cancel", variant="default")
                yield Button("Remove Selected", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Resolve the dialog."""
        self.dismiss(ConfirmResult(confirmed=event.button.id == "confirm"))

    def on_key(self, event: events.Key) -> None:
        """Escape cancels removal."""
        if event.key == "escape":
            self.dismiss(ConfirmResult(confirmed=False))


# --------------------------------------------------------------------- #
# Error dialog
# --------------------------------------------------------------------- #
class ErrorDialog(ModalScreen[None]):
    """Friendly, non-blocking error display.

    NetMedic never crashes on a PowerShell failure; instead it shows the
    details here and lets the user dismiss with Esc / Enter.
    """

    DEFAULT_CSS = """
    ErrorDialog {
        align: center middle;
    }
    ErrorDialog > Vertical {
        width: 70;
        height: auto;
        max-height: 24;
        background: $panel;
        border: thick $error;
        padding: 1 2;
    }
    ErrorDialog #title {
        text-style: bold;
        color: $error;
        padding-bottom: 1;
    }
    ErrorDialog #body {
        padding-bottom: 1;
        color: $text;
    }
    ErrorDialog Button {
        width: 100%;
    }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = truncate(body, 1500)

    def compose(self) -> ComposeResult:
        """Render title + body + a single OK button."""
        with Vertical():
            yield Label(self._title, id="title")
            yield Static(self._body, id="body", markup=False)
            yield Button("OK", id="ok", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dismiss on OK."""
        self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        """Any key dismisses the dialog."""
        self.dismiss(None)
