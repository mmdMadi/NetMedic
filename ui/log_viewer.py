"""
Log Viewer screen.

A full-screen modal that displays available log files and their contents.
Users can browse log files, view entries, and see file metadata.

Accessed via the **L** key binding or the *Logs* button in the actions bar.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from utils.logger import list_log_files, read_log_file
from utils.storage import Storage


class LogViewerScreen(ModalScreen[None]):
    """Full-screen log viewer overlay.

    Left panel: list of log files with metadata.
    Right panel: log file content (scrollable).
    """

    DEFAULT_CSS = """
    LogViewerScreen {
        background: #0b1016ee;
        align: center middle;
    }
    LogViewerScreen > Vertical {
        width: 100;
        height: 92%;
        background: #0f1923;
        border: thick #3b82f6;
        padding: 1 2;
    }
    LogViewerScreen #title {
        height: 2;
        text-align: center;
        color: #8ab4ff;
        text-style: bold;
        padding-bottom: 1;
    }
    LogViewerScreen #status {
        height: 1;
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }
    LogViewerScreen #content {
        height: 1fr;
    }
    LogViewerScreen #file-list {
        width: 30;
        border: round #223042;
        padding: 0 1;
        overflow-y: auto;
    }
    LogViewerScreen .file-item {
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
        border: round transparent;
    }
    LogViewerScreen .file-item:hover {
        background: #1e293b;
    }
    LogViewerScreen .file-item-selected {
        background: #1e3a5f;
        border: round #3b82f6;
    }
    LogViewerScreen .file-name {
        height: 1;
        color: #e2e8f0;
        text-style: bold;
    }
    LogViewerScreen .file-meta {
        height: 1;
        color: #64748b;
    }
    LogViewerScreen #log-content {
        width: 1fr;
        border: round #223042;
        padding: 1 2;
        overflow-y: auto;
        margin-left: 1;
        color: #d6dde6;
    }
    LogViewerScreen .log-line {
        height: auto;
        color: #d6dde6;
    }
    LogViewerScreen .log-error {
        color: #f87171;
    }
    LogViewerScreen .log-warning {
        color: #facc15;
    }
    LogViewerScreen .log-info {
        color: #94a3b8;
    }
    LogViewerScreen .no-selection {
        color: #64748b;
        text-align: center;
        padding-top: 4;
    }
    LogViewerScreen #close-btn {
        width: 100%;
        height: 3;
        margin-top: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._files: list[dict] = []
        self._selected_path: Optional[str] = None
        self._file_widgets: list[tuple[Static, Static, Static]] = []

        # Widgets
        self._title: Static
        self._status: Static
        self._file_list: VerticalScroll
        self._log_content: VerticalScroll

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        with Vertical():
            self._title = Static("Log Viewer", id="title")
            yield self._title

            self._status = Static("Loading log files…", id="status")
            yield self._status

            with Horizontal(id="content"):
                self._file_list = VerticalScroll(id="file-list")
                yield self._file_list

                self._log_content = VerticalScroll(id="log-content")
                yield self._log_content

            yield Button("Close  [Esc]", id="close-btn")

    def on_mount(self) -> None:
        """Load log files on a background thread."""
        self._load_files()

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
    # File loading
    # ------------------------------------------------------------------ #
    def _load_files(self) -> None:
        """Load log file list in a background thread."""
        def _worker() -> None:
            storage = Storage()
            files = list_log_files(storage.logs_dir)
            self.call_from_thread(self._show_files, files)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_files(self, files: list[dict]) -> None:
        """Render the file list."""
        self._files = files
        self._file_list.remove_children()
        self._file_widgets.clear()

        if not files:
            empty = Static("No log files found", classes="no-selection")
            self._file_list.mount(empty)
            self._status.update("No log files found")
            self._show_no_selection()
            return

        for f in files:
            size_kb = f["size_bytes"] / 1024
            name_widget = Static(f["name"], classes="file-name")
            meta_widget = Static(
                f"{size_kb:.1f} KB · {f['modified']}",
                classes="file-meta",
            )
            item_container = Vertical(classes="file-item")
            self._file_list.mount(item_container)
            item_container.mount(name_widget)
            item_container.mount(meta_widget)

            self._file_widgets.append((item_container, name_widget, meta_widget))
            item_container.on_click = self._make_click_handler(f["path"])

        self._status.update(f"{len(files)} log file(s) found")
        self._show_no_selection()

    def _make_click_handler(self, path: str):
        """Create a click handler for a file item."""
        def _handler() -> None:
            self._select_file(path)
        return _handler

    def _select_file(self, path: str) -> None:
        """Select a log file and display its contents."""
        self._selected_path = path

        # Update list highlighting
        for item_container, name_widget, _ in self._file_widgets:
            item_container.remove_class("file-item-selected")
            if name_widget.plain in path:
                item_container.add_class("file-item-selected")

        # Load content in background
        def _worker() -> None:
            content = read_log_file(path, max_lines=500)
            self.call_from_thread(self._show_content, content)

        self._log_content.remove_children()
        loading = Static("Loading…", classes="no-selection")
        self._log_content.mount(loading)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_content(self, content: str) -> None:
        """Display the log file content."""
        self._log_content.remove_children()

        for line in content.split("\n"):
            # Color-code by log level
            cls = "log-line"
            if "ERROR" in line:
                cls = "log-line log-error"
            elif "WARNING" in line:
                cls = "log-line log-warning"
            elif "INFO" in line:
                cls = "log-line log-info"

            widget = Static(line, classes=cls)
            self._log_content.mount(widget)

        self._status.update(f"Viewing: {Path(self._selected_path).name if self._selected_path else '—'}")

    def _show_no_selection(self) -> None:
        """Show the empty state in the content panel."""
        self._log_content.remove_children()
        empty = Static(
            "Select a log file to view its contents",
            classes="no-selection",
        )
        self._log_content.mount(empty)
